"""SmartOKR MCP Server - Evidence-Based OKR Performance Analysis.

A "Rational Assistant Referee System" that integrates with GitHub and
Get笔记 knowledge base to collect work evidence, match it to OKR key results
using AI reasoning, and generate structured performance reports using the
Balanced Scorecard framework with role-based dynamic weights.

11 MCP Tools:
  OKR Management: create_okr_objective, create_key_result, list_okrs, update_okr
  Evidence Collection: collect_github_evidence, collect_notes_evidence, add_evidence_manually
  Analysis: match_evidence_to_okrs, store_evidence_matches, calculate_scores
  Reporting: generate_report
"""

import asyncio
import json
import logging
import sys
import os
from typing import List, Any

from dotenv import load_dotenv

# Add src directory to path for relative imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from store import DataStore
from github_collector import GitHubCollector
from notes_collector import NotesCollector
from scoring_engine import ScoringEngine
from report_generator import ReportGenerator
from models import new_objective, new_key_result, new_evidence
from utils import ROLE_WEIGHT_PRESETS, BSC_DIMENSIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartokr")

# Load environment
load_dotenv()

# Initialize services
DATA_DIR = os.getenv("SMARTOKR_DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
store = DataStore(data_dir=DATA_DIR)
github = GitHubCollector(token=os.getenv("GITHUB_TOKEN", ""))
notes = NotesCollector(
    api_key=os.getenv("GETNOTE_API_KEY", ""),
    topic_id=os.getenv("GETNOTE_TOPIC_ID", ""),
    api_base=os.getenv("GETNOTE_API_BASE", ""),
)
scoring = ScoringEngine()
reporter = ReportGenerator()

app = Server("smartokr-mcp")


def _json_response(data) -> List[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


def _error_response(message: str, details=None) -> List[TextContent]:
    err = {"error": message}
    if details:
        err["details"] = details
    return _json_response(err)


# ============================================================
# Tool Definitions
# ============================================================

@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        # --- OKR Management ---
        Tool(
            name="create_okr_objective",
            description="创建 OKR 目标，绑定到平衡计分卡(BSC)维度。维度：financial(财务), customer(客户), internal_process(内部流程), learning_growth(学习与成长)。",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "目标标题"},
                    "description": {"type": "string", "description": "目标详细描述"},
                    "bsc_dimension": {
                        "type": "string",
                        "enum": ["financial", "customer", "internal_process", "learning_growth"],
                        "description": "平衡计分卡维度",
                    },
                    "period": {"type": "string", "description": "考核周期，如 '2025-Q1', '2025-01'"},
                    "owner": {"type": "string", "description": "目标负责人"},
                    "weight": {"type": "number", "description": "目标在维度内的权重(0-1)，默认1.0", "default": 1.0},
                },
                "required": ["title", "bsc_dimension", "period", "owner"],
            },
        ),
        Tool(
            name="create_key_result",
            description="为已有目标添加关键成果(KR)，包含可衡量的目标值和权重。",
            inputSchema={
                "type": "object",
                "properties": {
                    "objective_id": {"type": "string", "description": "所属目标ID"},
                    "title": {"type": "string", "description": "关键成果标题"},
                    "description": {"type": "string", "description": "衡量标准说明"},
                    "target_value": {"type": "number", "description": "目标数值"},
                    "unit": {"type": "string", "description": "计量单位，如 '%', 'count', 'days'"},
                    "weight": {"type": "number", "description": "KR在目标内的权重(0-1)", "default": 1.0},
                    "current_value": {"type": "number", "description": "当前值", "default": 0},
                },
                "required": ["objective_id", "title", "target_value", "unit"],
            },
        ),
        Tool(
            name="list_okrs",
            description="查询 OKR 目标和关键成果树，支持按周期、负责人、BSC维度过滤。",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "按周期过滤"},
                    "owner": {"type": "string", "description": "按负责人过滤"},
                    "bsc_dimension": {
                        "type": "string",
                        "enum": ["financial", "customer", "internal_process", "learning_growth"],
                        "description": "按BSC维度过滤",
                    },
                },
            },
        ),
        Tool(
            name="update_okr",
            description="更新已有目标或关键成果的字段（标题、描述、权重、当前值等）。",
            inputSchema={
                "type": "object",
                "properties": {
                    "objective_id": {"type": "string", "description": "目标ID（更新目标时提供）"},
                    "kr_id": {"type": "string", "description": "关键成果ID（更新KR时提供）"},
                    "updates": {"type": "object", "description": "要更新的字段和值"},
                },
                "required": ["updates"],
            },
        ),
        # --- Evidence Collection ---
        Tool(
            name="collect_github_evidence",
            description="从 GitHub 采集工作证据：commits、PRs、issues。支持按用户和时间范围过滤。",
            inputSchema={
                "type": "object",
                "properties": {
                    "github_owner": {"type": "string", "description": "GitHub 仓库 owner（组织或用户）"},
                    "github_repo": {"type": "string", "description": "GitHub 仓库名"},
                    "author": {"type": "string", "description": "GitHub 用户名"},
                    "since": {"type": "string", "description": "开始日期 (YYYY-MM-DD)"},
                    "until": {"type": "string", "description": "结束日期 (YYYY-MM-DD)"},
                    "evidence_types": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["commits", "pull_requests", "issues"]},
                        "description": "采集类型（默认全部）",
                    },
                },
                "required": ["github_owner", "github_repo", "author", "since", "until"],
            },
        ),
        Tool(
            name="collect_notes_evidence",
            description="从 Get笔记知识库采集工作证据。通过知识库搜索/召回接口获取相关文档。",
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {"type": "string", "description": "关联的人员姓名"},
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "搜索查询列表（如不提供，自动生成基于人员的查询）",
                    },
                    "topic_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "知识库主题ID列表（默认使用配置的ID）",
                    },
                    "top_k": {"type": "integer", "description": "每次查询返回的文档数（默认5）", "default": 5},
                },
                "required": ["person"],
            },
        ),
        Tool(
            name="add_evidence_manually",
            description="手动补充工作证据，用于无法从 GitHub 或知识库自动采集的工作记录。每次评估都可以补充。",
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {"type": "string", "description": "证据所属人员"},
                    "title": {"type": "string", "description": "工作事项标题"},
                    "description": {"type": "string", "description": "详细描述"},
                    "source_type": {
                        "type": "string",
                        "enum": ["manual", "meeting", "presentation", "review", "other"],
                        "description": "证据来源类型",
                    },
                    "date": {"type": "string", "description": "日期 (YYYY-MM-DD)"},
                    "url": {"type": "string", "description": "参考链接（可选）"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "标签"},
                },
                "required": ["person", "title", "description", "source_type", "date"],
            },
        ),
        # --- Analysis & Scoring ---
        Tool(
            name="match_evidence_to_okrs",
            description="获取证据匹配上下文：列出未匹配的工作证据和所有KR定义，供AI进行证据链推理和匹配。返回数据后请分析每条证据与哪些KR相关，然后调用 store_evidence_matches 存储结果。",
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {"type": "string", "description": "人员姓名"},
                    "period": {"type": "string", "description": "OKR周期"},
                },
                "required": ["person", "period"],
            },
        ),
        Tool(
            name="store_evidence_matches",
            description="存储 AI 推理后的证据-KR匹配结果。在 match_evidence_to_okrs 后使用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "matches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "evidence_id": {"type": "string"},
                                "kr_id": {"type": "string"},
                                "relevance_score": {"type": "number", "description": "相关性得分 0-100"},
                                "reasoning": {"type": "string", "description": "匹配理由说明"},
                                "contribution_type": {
                                    "type": "string",
                                    "enum": ["direct", "indirect", "supporting"],
                                    "description": "贡献类型",
                                },
                            },
                            "required": ["evidence_id", "kr_id", "relevance_score", "reasoning"],
                        },
                        "description": "匹配结果数组",
                    },
                },
                "required": ["matches"],
            },
        ),
        Tool(
            name="calculate_scores",
            description="使用动态权重评分引擎计算 BSC 四维度加权得分。支持按岗位角色自动应用不同权重：engineer(工程师), product_manager(产品经理), sales(销售), designer(设计师), manager(管理者), researcher(研究员), operations(运营)。",
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {"type": "string", "description": "评估人员"},
                    "period": {"type": "string", "description": "OKR周期"},
                    "role": {
                        "type": "string",
                        "enum": ["engineer", "product_manager", "sales", "designer", "manager", "researcher", "operations", "default"],
                        "description": "岗位角色（决定四维度权重分配）",
                    },
                    "dimension_weights": {
                        "type": "object",
                        "description": "自定义维度权重（覆盖岗位预设）。键：financial, customer, internal_process, learning_growth，值：0-1，总和为1。",
                        "properties": {
                            "financial": {"type": "number"},
                            "customer": {"type": "number"},
                            "internal_process": {"type": "number"},
                            "learning_growth": {"type": "number"},
                        },
                    },
                },
                "required": ["person", "period"],
            },
        ),
        # --- Report ---
        Tool(
            name="generate_report",
            description="生成结构化绩效分析报告（Markdown格式），包含BSC概览、证据链、评分明细、进度分析。作为「理性辅助裁判系统」提供基于证据的分析而非最终判断。",
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {"type": "string", "description": "报告对象（或 'team' 生成团队报告）"},
                    "period": {"type": "string", "description": "OKR周期"},
                    "report_type": {
                        "type": "string",
                        "enum": ["individual", "team", "dimension"],
                        "description": "报告类型",
                        "default": "individual",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "输出格式",
                        "default": "markdown",
                    },
                    "save_to_file": {
                        "type": "boolean",
                        "description": "是否保存到 data/reports/ 目录",
                        "default": True,
                    },
                },
                "required": ["person", "period"],
            },
        ),
    ]


# ============================================================
# Tool Handlers
# ============================================================

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    try:
        # --- OKR Management ---
        if name == "create_okr_objective":
            obj = new_objective(
                title=arguments["title"],
                bsc_dimension=arguments["bsc_dimension"],
                period=arguments["period"],
                owner=arguments["owner"],
                description=arguments.get("description", ""),
                weight=arguments.get("weight", 1.0),
            )
            store.add_objective(obj)
            return _json_response({"success": True, "objective": obj})

        elif name == "create_key_result":
            obj = store.find_objective(arguments["objective_id"])
            if not obj:
                return _error_response(f"Objective not found: {arguments['objective_id']}")

            kr = new_key_result(
                objective_id=arguments["objective_id"],
                title=arguments["title"],
                target_value=arguments["target_value"],
                unit=arguments["unit"],
                description=arguments.get("description", ""),
                weight=arguments.get("weight", 1.0),
                current_value=arguments.get("current_value", 0),
            )
            result = store.add_key_result(arguments["objective_id"], kr)
            if result:
                return _json_response({"success": True, "key_result": kr})
            return _error_response("Failed to add key result")

        elif name == "list_okrs":
            objectives = store.list_objectives(
                period=arguments.get("period"),
                owner=arguments.get("owner"),
                bsc_dimension=arguments.get("bsc_dimension"),
            )
            # Add evidence counts
            for obj in objectives:
                for kr in obj.get("key_results", []):
                    kr["evidence_count"] = len(kr.get("evidence_ids", []))
            return _json_response({
                "objectives": objectives,
                "total": len(objectives),
                "role_weight_presets": list(ROLE_WEIGHT_PRESETS.keys()),
            })

        elif name == "update_okr":
            updates = arguments.get("updates", {})
            kr_id = arguments.get("kr_id")
            obj_id = arguments.get("objective_id")

            if kr_id:
                result = store.update_key_result(kr_id, updates)
                if result:
                    return _json_response({"success": True, "updated_key_result": result})
                return _error_response(f"Key result not found: {kr_id}")
            elif obj_id:
                result = store.update_objective(obj_id, updates)
                if result:
                    return _json_response({"success": True, "updated_objective": result})
                return _error_response(f"Objective not found: {obj_id}")
            else:
                return _error_response("Provide either objective_id or kr_id")

        # --- Evidence Collection ---
        elif name == "collect_github_evidence":
            result = github.collect(
                owner=arguments["github_owner"],
                repo=arguments["github_repo"],
                author=arguments["author"],
                since=arguments["since"],
                until=arguments["until"],
                evidence_types=arguments.get("evidence_types"),
            )
            # Store collected evidence
            stored = store.add_evidence_batch(result["evidence_items"])
            result["stored_count"] = stored
            # Remove full evidence_items from response (already stored)
            result.pop("evidence_items", None)
            return _json_response(result)

        elif name == "collect_notes_evidence":
            result = notes.collect_evidence(
                person=arguments["person"],
                queries=arguments.get("queries"),
                topic_ids=arguments.get("topic_ids"),
                top_k=arguments.get("top_k", 5),
            )
            # Store collected evidence
            stored = store.add_evidence_batch(result["evidence_items"])
            result["stored_count"] = stored
            result.pop("evidence_items", None)
            return _json_response(result)

        elif name == "add_evidence_manually":
            ev = new_evidence(
                person=arguments["person"],
                title=arguments["title"],
                description=arguments["description"],
                source_type=arguments["source_type"],
                date_str=arguments["date"],
                url=arguments.get("url"),
                tags=arguments.get("tags"),
            )
            store.add_evidence(ev)
            return _json_response({"success": True, "evidence": ev})

        # --- Analysis & Scoring ---
        elif name == "match_evidence_to_okrs":
            person = arguments["person"]
            period = arguments["period"]

            unmatched = store.get_unmatched_evidence(person)
            objectives = store.list_objectives(owner=person, period=period)

            # Build KR list for matching context
            kr_list = []
            for obj in objectives:
                for kr in obj.get("key_results", []):
                    kr_list.append({
                        "kr_id": kr["kr_id"],
                        "kr_title": kr["title"],
                        "kr_description": kr.get("description", ""),
                        "objective_title": obj["title"],
                        "bsc_dimension": obj["bsc_dimension"],
                    })

            evidence_summaries = [
                {
                    "evidence_id": e["evidence_id"],
                    "title": e["title"],
                    "description": e.get("description", "")[:300],
                    "source_type": e["source_type"],
                    "date": e.get("date", ""),
                    "tags": e.get("tags", []),
                }
                for e in unmatched
            ]

            return _json_response({
                "unmatched_evidence": evidence_summaries,
                "key_results": kr_list,
                "total_unmatched": len(evidence_summaries),
                "total_krs": len(kr_list),
                "instructions": (
                    "请分析每条证据与哪些 KR 相关。对每个匹配提供：\n"
                    "1. evidence_id 和 kr_id\n"
                    "2. relevance_score (0-100，相关性得分)\n"
                    "3. reasoning (1-2句话说明关联原因)\n"
                    "4. contribution_type (direct/indirect/supporting)\n"
                    "分析完成后，请调用 store_evidence_matches 工具存储结果。"
                ),
            })

        elif name == "store_evidence_matches":
            matches = arguments.get("matches", [])
            count = store.store_matches(matches)
            return _json_response({
                "success": True,
                "matches_stored": count,
                "total_submitted": len(matches),
            })

        elif name == "calculate_scores":
            person = arguments["person"]
            period = arguments["period"]
            role = arguments.get("role")
            dim_weights = arguments.get("dimension_weights")

            objectives = store.list_objectives(owner=person, period=period)
            evidence = store.get_evidence(person=person)

            score_record = scoring.calculate(
                person=person,
                period=period,
                objectives=objectives,
                evidence=evidence,
                dimension_weights=dim_weights,
                role=role,
            )
            store.add_score_record(score_record)

            return _json_response(score_record)

        # --- Report ---
        elif name == "generate_report":
            person = arguments["person"]
            period = arguments["period"]
            report_type = arguments.get("report_type", "individual")
            output_format = arguments.get("output_format", "markdown")
            save_to_file = arguments.get("save_to_file", True)

            objectives = store.list_objectives(owner=person, period=period)
            evidence = store.get_evidence(person=person)
            score_record = store.get_latest_score(person, period) or {}
            progress = scoring.analyze_progress(person, period, objectives, evidence)

            report = reporter.generate(
                person=person,
                period=period,
                score_record=score_record,
                progress=progress,
                evidence=evidence,
                objectives=objectives,
                report_type=report_type,
                output_format=output_format,
            )

            result = {"report": report}
            if save_to_file and output_format == "markdown":
                from datetime import datetime
                filename = f"{person}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                filepath = store.save_report(filename, report)
                result["saved_to"] = filepath

            return _json_response(result)

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Tool {name} error: {e}", exc_info=True)
        return _error_response(str(e))


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
