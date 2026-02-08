#!/usr/bin/env python3
"""SmartOKR 全员分析脚本

从 Get笔记知识库采集所有人的工作记录，自动进行 OKR 分析并生成报告。

使用方式:
    cd SmartOKR
    python scripts/analyze_all.py

需要配置 .env 文件（参考 .env.example），或直接在下方修改配置。

前置条件:
    1. pip install -r requirements.txt
    2. 网络可访问 open-api.biji.com
    3. 配置好 GETNOTE_API_KEY 和 GETNOTE_TOPIC_ID
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from store import DataStore
from notes_collector import NotesCollector
from scoring_engine import ScoringEngine
from report_generator import ReportGenerator
from models import new_objective, new_key_result, new_evidence
from utils import ROLE_WEIGHT_PRESETS, BSC_DIMENSIONS

# ============================================================
# Configuration
# ============================================================

GETNOTE_API_KEY = os.getenv("GETNOTE_API_KEY", "B6Xec+VklOztQvKhIIZicViWUlXlV6lrxvoXixA9j5OL1Io4XyOHwUDAUbRY3f9A2rj/YSpeINxUqwIiyeJ9F+7LvuJiv4SeaZtt")
GETNOTE_TOPIC_ID = os.getenv("GETNOTE_TOPIC_ID", "rYMVXjK0")
PERIOD = "2025-Q1"  # Analysis period

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


# ============================================================
# Step 1: Discover team members from knowledge base
# ============================================================

def discover_members(nc: NotesCollector) -> list:
    """Query knowledge base to find all team members."""
    print("\n📋 Step 1: 从知识库发现团队成员...")

    member_queries = [
        "团队所有成员名单",
        "每个人的工作职责和岗位",
        "团队分工和角色",
        "项目成员列表",
        "团队人员组成",
        "所有人的OKR",
        "工作进展汇总",
    ]

    all_docs = []
    seen_ids = set()

    for q in member_queries:
        resp = nc.recall(question=q, top_k=10)

        # Check for errors
        if "error" in resp:
            print(f"   ⚠️  查询「{q}」失败: {resp['error'][:100]}")
            continue

        # Parse response: {h: {c: 0}, c: {data: [...]}}
        data_items = nc._parse_recall_items(resp)

        for item in data_items:
            item_id = item.get("id", "")
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                all_docs.append(item)

    print(f"   召回 {len(all_docs)} 篇相关文档")

    if all_docs:
        print(f"\n   📄 文档预览:")
        for i, doc in enumerate(all_docs[:5]):
            title = doc.get("title", "无标题")
            score = doc.get("score", 0)
            content_preview = doc.get("content", "")[:80].replace("\n", " ")
            print(f"   [{i+1}] {title} (相关性: {score:.4f})")
            print(f"       {content_preview}...")

    return all_docs


def extract_members_from_docs(docs: list) -> list:
    """Extract member names from recalled documents.

    This uses heuristic matching. In production, the AI assistant
    would do intelligent reasoning on the recalled docs.
    Returns list of dicts with name and role.
    """
    all_text = "\n".join(d.get("content", "") + " " + d.get("title", "") for d in docs)

    members = []
    seen_names = set()

    lines = all_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or len(line) > 100:
            continue

        for role_key, role_data in [
            ("工程师", "engineer"), ("开发", "engineer"), ("前端", "engineer"),
            ("后端", "engineer"), ("算法", "researcher"), ("研发", "engineer"),
            ("产品", "product_manager"), ("设计", "designer"),
            ("销售", "sales"), ("运营", "operations"), ("经理", "manager"),
            ("主管", "manager"), ("总监", "manager"), ("研究", "researcher"),
            ("测试", "engineer"),
        ]:
            if role_key in line:
                name = line[:20].strip()
                if name not in seen_names:
                    seen_names.add(name)
                    members.append({"name": name, "role": role_data, "raw": line})

    return members


# ============================================================
# Step 2: Collect work evidence for each person
# ============================================================

def collect_person_evidence(nc: NotesCollector, person_name: str) -> list:
    """Collect work evidence for a specific person from knowledge base."""
    queries = [
        f"{person_name}的工作记录和成果",
        f"{person_name}完成的项目和任务",
        f"{person_name}的技术贡献",
        f"{person_name}的工作进展",
    ]

    evidence_items = []
    seen_ids = set()

    for q in queries:
        resp = nc.recall(question=q, top_k=5)

        if "error" in resp:
            continue

        data_items = nc._parse_recall_items(resp)

        for item in data_items:
            item_id = item.get("id", "")
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            ev = new_evidence(
                person=person_name,
                title=item.get("title", q)[:200],
                description=item.get("content", "")[:500],
                source_type="knowledge_base",
                date_str="",
                metadata={
                    "source": "get_notes",
                    "query": q,
                    "doc_id": item_id,
                    "recall_score": item.get("score", 0),
                },
                tags=["knowledge_base"],
            )
            evidence_items.append(ev)

    return evidence_items


# ============================================================
# Step 3: Auto-generate OKRs based on work patterns
# ============================================================

def create_default_okrs(store: DataStore, person_name: str, role: str) -> list:
    """Create default BSC-based OKRs for a person based on their role."""
    objectives = []

    # Financial dimension
    obj_fin = new_objective(
        title="业务价值贡献",
        bsc_dimension="financial",
        period=PERIOD,
        owner=person_name,
        description="通过工作产出为业务创造价值",
        weight=1.0,
    )
    store.add_objective(obj_fin)
    kr1 = new_key_result(obj_fin["objective_id"], "完成核心业务交付目标", 100, "%", weight=1.0, current_value=0)
    store.add_key_result(obj_fin["objective_id"], kr1)
    objectives.append(obj_fin)

    # Customer dimension
    obj_cust = new_objective(
        title="客户/用户满意度",
        bsc_dimension="customer",
        period=PERIOD,
        owner=person_name,
        description="提升内外部客户满意度和需求响应",
        weight=1.0,
    )
    store.add_objective(obj_cust)
    kr2 = new_key_result(obj_cust["objective_id"], "需求响应与用户反馈处理", 100, "%", weight=1.0, current_value=0)
    store.add_key_result(obj_cust["objective_id"], kr2)
    objectives.append(obj_cust)

    # Internal Process dimension
    obj_proc = new_objective(
        title="工作效率与质量",
        bsc_dimension="internal_process",
        period=PERIOD,
        owner=person_name,
        description="提升工作流程效率和交付质量",
        weight=1.0,
    )
    store.add_objective(obj_proc)
    kr3 = new_key_result(obj_proc["objective_id"], "项目任务按时交付率", 100, "%", weight=0.5, current_value=0)
    store.add_key_result(obj_proc["objective_id"], kr3)
    kr4 = new_key_result(obj_proc["objective_id"], "工作质量与代码/文档产出", 100, "%", weight=0.5, current_value=0)
    store.add_key_result(obj_proc["objective_id"], kr4)
    objectives.append(obj_proc)

    # Learning & Growth dimension
    obj_learn = new_objective(
        title="学习与成长",
        bsc_dimension="learning_growth",
        period=PERIOD,
        owner=person_name,
        description="技能提升、知识分享和创新贡献",
        weight=1.0,
    )
    store.add_objective(obj_learn)
    kr5 = new_key_result(obj_learn["objective_id"], "技能提升与知识沉淀", 100, "%", weight=1.0, current_value=0)
    store.add_key_result(obj_learn["objective_id"], kr5)
    objectives.append(obj_learn)

    return objectives


# ============================================================
# Step 4: Match evidence and calculate scores
# ============================================================

def auto_match_evidence(store: DataStore, person_name: str, objectives: list, evidence: list):
    """Auto-match evidence to KRs based on content similarity.

    In production, the AI assistant would do sophisticated reasoning here.
    This uses keyword-based heuristic matching.
    """
    matches = []

    for ev in evidence:
        text = (ev.get("title", "") + " " + ev.get("description", "")).lower()

        for obj in objectives:
            dim = obj["bsc_dimension"]
            for kr in obj.get("key_results", []):
                score = 30  # Base score

                if dim == "financial" and any(k in text for k in ["收入", "营收", "成本", "价值", "业务", "客户", "项目交付"]):
                    score += 40
                elif dim == "customer" and any(k in text for k in ["用户", "客户", "需求", "反馈", "满意", "体验", "服务"]):
                    score += 40
                elif dim == "internal_process" and any(k in text for k in ["开发", "代码", "部署", "修复", "优化", "测试", "发布", "交付", "流程", "效率"]):
                    score += 40
                elif dim == "learning_growth" and any(k in text for k in ["学习", "培训", "分享", "研究", "技术", "创新", "文档", "知识"]):
                    score += 40

                if score > 30:
                    matches.append({
                        "evidence_id": ev["evidence_id"],
                        "kr_id": kr["kr_id"],
                        "relevance_score": min(score, 90),
                        "reasoning": f"证据「{ev['title'][:50]}」与KR「{kr['title']}」在{BSC_DIMENSIONS[dim]['label']}维度相关",
                        "contribution_type": "direct" if score > 60 else "indirect",
                    })

    if matches:
        store.store_matches(matches)

    return matches


# ============================================================
# Main Pipeline
# ============================================================

def main():
    print("=" * 60)
    print("  SmartOKR 全员 OKR 分析")
    print("  理性辅助裁判系统")
    print("=" * 60)

    # Initialize
    store = DataStore(data_dir=DATA_DIR)
    nc = NotesCollector(api_key=GETNOTE_API_KEY, topic_id=GETNOTE_TOPIC_ID)
    scoring = ScoringEngine()
    reporter = ReportGenerator()

    # Connectivity test
    print("\n🔗 测试知识库连接...")
    test_resp = nc.recall(question="测试连接", top_k=1)
    if "error" in test_resp:
        print(f"\n❌ 无法连接到 Get笔记知识库 API!")
        print(f"   错误: {test_resp['error'][:200]}")
        print(f"\n   请检查：")
        print(f"   1. 网络是否可以访问 https://open-api.biji.com")
        print(f"   2. GETNOTE_API_KEY 是否正确")
        print(f"   3. GETNOTE_TOPIC_ID 是否正确")
        print(f"   4. 是否有代理限制（尝试: export no_proxy=open-api.biji.com）")
        return
    print("   ✅ 知识库连接成功!")

    # Step 1: Discover members
    docs = discover_members(nc)

    if not docs:
        print("\n⚠️  未从知识库中召回任何文档。")
        print("   知识库可能为空，或者查询关键词未命中。")
        return

    members = extract_members_from_docs(docs)
    if not members:
        print("\n   ℹ️  未能自动提取成员名单。")
        print("   以下是从知识库召回的文档内容，请根据内容手动设定成员列表：")
        print()
        for i, doc in enumerate(docs[:10]):
            print(f"   文档 {i+1}: {doc.get('title', 'N/A')}")
            content = doc.get("content", "")[:300].replace("\n", "\n       ")
            print(f"       {content}")
            print()
        print("   提示: 在脚本中修改 main() 函数，手动设定 members 列表后重新运行。")
        print('   示例: members = [{"name": "张三", "role": "engineer"}, ...]')
        return

    print(f"\n👥 发现 {len(members)} 位团队成员：")
    for m in members:
        print(f"   - {m['name']} ({m['role']})")

    # Process each member
    all_reports = []

    for member in members:
        name = member["name"]
        role = member["role"]
        print(f"\n{'─' * 50}")
        print(f"  分析: {name} ({role})")
        print(f"{'─' * 50}")

        # Step 2: Collect evidence
        print(f"   📥 采集工作证据...")
        evidence = collect_person_evidence(nc, name)
        stored = store.add_evidence_batch(evidence)
        print(f"   ✅ 采集到 {stored} 条证据")

        # Step 3: Create OKRs
        print(f"   🎯 创建 BSC 四维度 OKR...")
        objectives = create_default_okrs(store, name, role)
        print(f"   ✅ 创建 {len(objectives)} 个目标")

        # Step 4: Match evidence
        print(f"   🔗 匹配证据到 OKR...")
        matches = auto_match_evidence(store, name, objectives, evidence)
        print(f"   ✅ 建立 {len(matches)} 条匹配关系")

        # Step 5: Calculate scores
        print(f"   📊 计算得分 (岗位: {role})...")
        objectives = store.list_objectives(owner=name, period=PERIOD)
        all_evidence = store.get_evidence(person=name)

        score_record = scoring.calculate(
            person=name, period=PERIOD,
            objectives=objectives, evidence=all_evidence,
            role=role,
        )
        store.add_score_record(score_record)
        print(f"   ✅ 综合得分: {score_record['overall_score']}")

        # Step 6: Generate report
        print(f"   📝 生成报告...")
        progress = scoring.analyze_progress(name, PERIOD, objectives, all_evidence)
        report = reporter.generate(
            person=name, period=PERIOD,
            score_record=score_record, progress=progress,
            evidence=all_evidence, objectives=objectives,
        )

        from datetime import datetime
        filename = f"{name}_{PERIOD}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = store.save_report(filename, report)
        print(f"   ✅ 报告已保存: {filepath}")
        all_reports.append({"name": name, "role": role, "score": score_record["overall_score"], "file": filepath})

    # Summary
    print(f"\n{'=' * 60}")
    print("  📊 全员分析汇总")
    print(f"{'=' * 60}")
    print(f"\n| 姓名 | 岗位 | 综合得分 | 报告文件 |")
    print(f"|------|------|----------|----------|")
    for r in all_reports:
        print(f"| {r['name']} | {r['role']} | {r['score']} | {os.path.basename(r['file'])} |")

    print(f"\n✅ 分析完成！共处理 {len(all_reports)} 位成员。")
    print(f"   报告目录: {store.reports_dir}")
    print(f"\n   提示: 报告为初始分析结果，建议通过 SmartOKR MCP 工具进行：")
    print(f"   1. 补充更多工作证据 (add_evidence_manually)")
    print(f"   2. AI 精细匹配 (match_evidence_to_okrs + store_evidence_matches)")
    print(f"   3. 重新评分 (calculate_scores)")


if __name__ == "__main__":
    main()
