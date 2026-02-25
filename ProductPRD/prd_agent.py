#!/usr/bin/env python3
"""PRD Agent: conversational PRD capture + live Markdown/HTML renderer."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MODEL = os.getenv("PRD_AGENT_MODEL", "gpt-4.1-mini")

OUTPUT_DIR = "generated"
STATE_PATH = f"{OUTPUT_DIR}/prd_state.json"
MD_PATH = f"{OUTPUT_DIR}/PRD_LIVE.md"
HTML_PATH = f"{OUTPUT_DIR}/prd-live.html"

DEFAULT_STATE: dict[str, Any] = {
    "doc_info": {
        "product_name": "",
        "project_code": "",
        "pm_owner": "",
        "version": "v0.1.0",
        "status": "草稿",
        "created_date": "",
        "updated_date": "",
    },
    "background": {
        "current_problem": "",
        "business_opportunity": "",
        "timing": "",
    },
    "goals": {
        "business_goal": "",
        "user_goal": "",
        "system_goal": "",
    },
    "scope": {
        "in_scope": [],
        "out_scope": [],
    },
    "users": [],
    "scenarios": [],
    "requirements": [],
    "nfr": {
        "performance": "",
        "availability": "",
        "security": "",
        "observability": "",
    },
    "ai": {
        "can_do": "",
        "cannot_do": "",
        "forbidden": "",
        "prompt_strategy": "",
        "fallback": "",
    },
    "milestones": [],
    "open_questions": [],
    "meta": {
        "pending_key": "",
        "updated_at": "",
    },
}

REQUIRED_ITEMS = [
    ("doc_info.product_name", "产品名称是什么？"),
    ("doc_info.project_code", "项目代号是什么？"),
    ("doc_info.pm_owner", "PM负责人是谁？"),
    ("background.current_problem", "当前最核心要解决的问题是什么？"),
    ("goals.business_goal", "本期最关键的业务目标是什么？"),
    ("scope.in_scope", "本次要做的范围有哪些？可一次说多个。"),
    ("scope.out_scope", "本次明确不做哪些？可一次说多个。"),
    ("users.first.role", "核心用户是谁？"),
    ("scenarios.first.description", "第一个核心使用场景是什么？"),
    ("requirements.first.title", "请先给出至少1条需求标题。"),
    ("requirements.first.acceptance", "这条需求的验收标准是什么？"),
    ("ai.can_do", "AI在这个产品里能做什么？"),
    ("ai.cannot_do", "AI不能做什么或禁止做什么？"),
    ("ai.fallback", "AI失败时的兜底策略是什么？"),
    ("nfr.performance", "性能目标是什么？例如接口P95。"),
    ("nfr.availability", "可用性目标是什么？例如99.9%。"),
    ("nfr.security", "安全与隐私要求是什么？"),
    ("milestones.first.date", "首个里程碑（日期+目标）是什么？"),
]


def now_date() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def now_time() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        state = copy.deepcopy(DEFAULT_STATE)
        state["doc_info"]["created_date"] = now_date()
        state["doc_info"]["updated_date"] = now_date()
        return state
    with path.open("r", encoding="utf-8") as f:
        current = json.load(f)
    merged = copy.deepcopy(DEFAULT_STATE)
    deep_merge(merged, current)
    if not merged["doc_info"]["created_date"]:
        merged["doc_info"]["created_date"] = now_date()
    return merged


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> None:
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v


def split_items(text: str) -> list[str]:
    raw = re.split(r"[\n,，;；]+", text)
    return [x.strip(" -•\t") for x in raw if x.strip(" -•\t")]


def strip_label_prefix(text: str) -> str:
    if "：" in text:
        left, right = text.split("：", 1)
        if len(left) <= 12 and right.strip():
            return right.strip()
    if ":" in text:
        left, right = text.split(":", 1)
        if len(left) <= 12 and right.strip():
            return right.strip()
    return text.strip()


def normalize_req_title(text: str) -> str:
    cleaned = strip_label_prefix(text)
    cleaned = re.sub(r"^(需求标题|需求|功能)\s*", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def first_or_empty(items: list[str]) -> str:
    return items[0] if items else ""


def normalize_state(state: dict[str, Any]) -> None:
    state["doc_info"]["updated_date"] = now_date()
    state["meta"]["updated_at"] = now_time()

    for req in state["requirements"]:
        req.setdefault("id", "")
        req.setdefault("module", "待定模块")
        req.setdefault("title", "")
        req.setdefault("priority", "P1")
        req.setdefault("description", "")
        req.setdefault("rules", [])
        req.setdefault("exceptions", [])
        req.setdefault("acceptance", [])
        req.setdefault("tracking", [])
        if not req["id"]:
            req["id"] = next_req_id(state)


def next_req_id(state: dict[str, Any]) -> str:
    max_id = 0
    for req in state.get("requirements", []):
        m = re.match(r"REQ-(\d+)", req.get("id", ""))
        if m:
            max_id = max(max_id, int(m.group(1)))
    return f"REQ-{max_id + 1:03d}"


def get_path(state: dict[str, Any], key: str) -> Any:
    parts = key.split(".")
    cur: Any = state
    for p in parts:
        if p == "first":
            if not isinstance(cur, list) or not cur:
                return None
            cur = cur[0]
            continue
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur


def set_pending_answer(state: dict[str, Any], key: str, answer: str) -> None:
    answer = strip_label_prefix(answer.strip())
    if not answer:
        return

    if key == "doc_info.product_name":
        state["doc_info"]["product_name"] = answer
    elif key == "doc_info.project_code":
        state["doc_info"]["project_code"] = answer
    elif key == "doc_info.pm_owner":
        state["doc_info"]["pm_owner"] = answer
    elif key == "background.current_problem":
        state["background"]["current_problem"] = answer
    elif key == "goals.business_goal":
        state["goals"]["business_goal"] = answer
    elif key == "scope.in_scope":
        state["scope"]["in_scope"] = merge_list(state["scope"]["in_scope"], split_items(answer))
    elif key == "scope.out_scope":
        state["scope"]["out_scope"] = merge_list(state["scope"]["out_scope"], split_items(answer))
    elif key == "users.first.role":
        if not state["users"]:
            state["users"].append({"role": answer, "traits": "", "needs": ""})
        else:
            state["users"][0]["role"] = answer
    elif key == "scenarios.first.description":
        if not state["scenarios"]:
            state["scenarios"].append({"id": "SCN-001", "description": answer, "trigger": "", "success": ""})
        else:
            state["scenarios"][0]["description"] = answer
    elif key == "requirements.first.title":
        answer = normalize_req_title(answer)
        if not state["requirements"]:
            state["requirements"].append(
                {
                    "id": "REQ-001",
                    "module": "待定模块",
                    "title": answer,
                    "priority": "P1",
                    "description": "",
                    "rules": [],
                    "exceptions": [],
                    "acceptance": [],
                    "tracking": [],
                }
            )
        else:
            state["requirements"][0]["title"] = answer
    elif key == "requirements.first.acceptance":
        answer = re.sub(r"^(验收标准)\s*", "", answer).strip()
        if not state["requirements"]:
            state["requirements"].append(
                {
                    "id": "REQ-001",
                    "module": "待定模块",
                    "title": "待补充",
                    "priority": "P1",
                    "description": "",
                    "rules": [],
                    "exceptions": [],
                    "acceptance": split_items(answer),
                    "tracking": [],
                }
            )
        else:
            state["requirements"][0]["acceptance"] = merge_list(state["requirements"][0]["acceptance"], split_items(answer))
    elif key == "ai.can_do":
        state["ai"]["can_do"] = answer
    elif key == "ai.cannot_do":
        state["ai"]["cannot_do"] = answer
    elif key == "ai.fallback":
        state["ai"]["fallback"] = answer
    elif key == "nfr.performance":
        state["nfr"]["performance"] = answer
    elif key == "nfr.availability":
        state["nfr"]["availability"] = answer
    elif key == "nfr.security":
        state["nfr"]["security"] = answer
    elif key == "milestones.first.date":
        m = re.match(r"\s*(\d{4}-\d{2}-\d{2})\s*(.*)", answer)
        if m:
            date = m.group(1)
            target = m.group(2).strip() or "待补充目标"
        else:
            date = answer
            target = "待补充目标"
        if not state["milestones"]:
            state["milestones"].append({"stage": "里程碑1", "date": date, "target": target, "owner": state["doc_info"].get("pm_owner", "")})
        else:
            state["milestones"][0]["date"] = date
            if target:
                state["milestones"][0]["target"] = target


def merge_list(old: list[str], new: list[str]) -> list[str]:
    seen = {x.strip() for x in old if x.strip()}
    result = [x for x in old if x.strip()]
    for item in new:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def get_missing_items(state: dict[str, Any]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for key, question in REQUIRED_ITEMS:
        val = get_path(state, key)
        if key.endswith("in_scope") or key.endswith("out_scope"):
            if not isinstance(val, list) or not any(str(x).strip() for x in val):
                missing.append({"key": key, "question": question})
            continue
        if key == "requirements.first.acceptance":
            if not state.get("requirements"):
                missing.append({"key": key, "question": question})
            else:
                acc = state["requirements"][0].get("acceptance", [])
                if not acc:
                    missing.append({"key": key, "question": question})
            continue
        if key == "milestones.first.date":
            if not state.get("milestones") or not state["milestones"][0].get("date"):
                missing.append({"key": key, "question": question})
            continue

        if val is None:
            missing.append({"key": key, "question": question})
        elif isinstance(val, str) and not val.strip():
            missing.append({"key": key, "question": question})
    return missing


def apply_regex_extraction(state: dict[str, Any], text: str) -> None:
    patterns = {
        "doc_info.product_name": r"(?:产品名称|产品名)[:：]\s*(.+)",
        "doc_info.project_code": r"(?:项目代号|代号)[:：]\s*(.+)",
        "doc_info.pm_owner": r"(?:负责人|PM|产品负责人)[:：]\s*(.+)",
        "background.current_problem": r"(?:当前问题|核心问题|痛点)[:：]\s*(.+)",
        "goals.business_goal": r"(?:业务目标|目标)[:：]\s*(.+)",
        "ai.can_do": r"(?:AI能做|AI可以做|AI能力)[:：]\s*(.+)",
        "ai.cannot_do": r"(?:AI不能做|AI禁止|禁区)[:：]\s*(.+)",
        "ai.fallback": r"(?:兜底|降级策略|失败处理)[:：]\s*(.+)",
        "nfr.performance": r"(?:性能目标|性能)[:：]\s*(.+)",
        "nfr.availability": r"(?:可用性|稳定性目标)[:：]\s*(.+)",
        "nfr.security": r"(?:安全要求|隐私要求|合规要求)[:：]\s*(.+)",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            set_pending_answer(state, key, m.group(1).strip())

    in_scope_match = re.search(r"(?:范围内|In Scope|本次要做)[:：]\s*(.+)", text, flags=re.IGNORECASE)
    if in_scope_match:
        set_pending_answer(state, "scope.in_scope", in_scope_match.group(1))

    out_scope_match = re.search(r"(?:范围外|Out Scope|本次不做)[:：]\s*(.+)", text, flags=re.IGNORECASE)
    if out_scope_match:
        set_pending_answer(state, "scope.out_scope", out_scope_match.group(1))

    req_match = re.search(r"(?:需求标题|需求|功能)[:：]\s*(.+)", text, flags=re.IGNORECASE)
    if req_match:
        title = normalize_req_title(req_match.group(1))
        if title:
            upsert_requirement(state, {"title": title})


def upsert_requirement(state: dict[str, Any], req: dict[str, Any]) -> None:
    title = normalize_req_title(str(req.get("title", "")).strip())
    if not title:
        return

    for existing in state["requirements"]:
        if existing.get("title", "").strip().lower() == title.lower():
            merge_req(existing, req)
            return

    new_req = {
        "id": req.get("id") or next_req_id(state),
        "module": req.get("module") or "待定模块",
        "title": title,
        "priority": req.get("priority") or "P1",
        "description": req.get("description") or "",
        "rules": req.get("rules") or [],
        "exceptions": req.get("exceptions") or [],
        "acceptance": req.get("acceptance") or [],
        "tracking": req.get("tracking") or [],
    }
    state["requirements"].append(new_req)


def merge_req(existing: dict[str, Any], req: dict[str, Any]) -> None:
    scalar_keys = ["module", "priority", "description"]
    for k in scalar_keys:
        v = str(req.get(k, "")).strip()
        if v:
            existing[k] = v

    for lk in ["rules", "exceptions", "acceptance", "tracking"]:
        vals = req.get(lk) or []
        if isinstance(vals, list):
            existing[lk] = merge_list(existing.get(lk, []), [str(x).strip() for x in vals if str(x).strip()])


def maybe_apply_llm_extraction(state: dict[str, Any], text: str, model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "skip:no_api_key"

    system_prompt = textwrap.dedent(
        """
        你是一个PRD信息抽取器。请从用户口述中提取结构化字段。
        只返回JSON对象，字段必须存在，不知道就给空字符串或空数组。
        不要编造不存在的信息。
        """
    ).strip()

    schema_hint = {
        "doc_info": {"product_name": "", "project_code": "", "pm_owner": ""},
        "background": {"current_problem": "", "business_opportunity": "", "timing": ""},
        "goals": {"business_goal": "", "user_goal": "", "system_goal": ""},
        "scope": {"in_scope": [], "out_scope": []},
        "users": [{"role": "", "traits": "", "needs": ""}],
        "scenarios": [{"description": "", "trigger": "", "success": ""}],
        "requirements": [
            {
                "id": "",
                "module": "",
                "title": "",
                "priority": "",
                "description": "",
                "rules": [],
                "exceptions": [],
                "acceptance": [],
                "tracking": [],
            }
        ],
        "ai": {"can_do": "", "cannot_do": "", "forbidden": "", "prompt_strategy": "", "fallback": ""},
        "nfr": {"performance": "", "availability": "", "security": "", "observability": ""},
        "milestones": [{"stage": "", "date": "", "target": "", "owner": ""}],
        "open_questions": [],
    }

    user_prompt = (
        "当前已知状态（摘要）：\n"
        + json.dumps(
            {
                "product_name": state["doc_info"].get("product_name", ""),
                "requirements_count": len(state.get("requirements", [])),
                "pending_key": state.get("meta", {}).get("pending_key", ""),
            },
            ensure_ascii=False,
        )
        + "\n\n字段模板：\n"
        + json.dumps(schema_hint, ensure_ascii=False)
        + "\n\n用户最新输入：\n"
        + text
    )

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        extracted = json.loads(content)
        merge_extracted(state, extracted)
        return "ok"
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return "skip:llm_error"


def merge_extracted(state: dict[str, Any], ex: dict[str, Any]) -> None:
    for top in ["doc_info", "background", "goals", "nfr", "ai"]:
        vals = ex.get(top) or {}
        if isinstance(vals, dict):
            for k, v in vals.items():
                if isinstance(v, str) and v.strip():
                    state[top][k] = v.strip()

    scope = ex.get("scope") or {}
    if isinstance(scope, dict):
        if scope.get("in_scope"):
            state["scope"]["in_scope"] = merge_list(state["scope"]["in_scope"], [str(x).strip() for x in scope["in_scope"] if str(x).strip()])
        if scope.get("out_scope"):
            state["scope"]["out_scope"] = merge_list(state["scope"]["out_scope"], [str(x).strip() for x in scope["out_scope"] if str(x).strip()])

    users = ex.get("users") or []
    if isinstance(users, list):
        for u in users:
            if not isinstance(u, dict):
                continue
            role = str(u.get("role", "")).strip()
            if not role:
                continue
            state["users"].append(
                {
                    "role": role,
                    "traits": str(u.get("traits", "")).strip(),
                    "needs": str(u.get("needs", "")).strip(),
                }
            )

    scenarios = ex.get("scenarios") or []
    if isinstance(scenarios, list):
        for s in scenarios:
            if not isinstance(s, dict):
                continue
            desc = str(s.get("description", "")).strip()
            if not desc:
                continue
            sid = f"SCN-{len(state['scenarios']) + 1:03d}"
            state["scenarios"].append(
                {
                    "id": sid,
                    "description": desc,
                    "trigger": str(s.get("trigger", "")).strip(),
                    "success": str(s.get("success", "")).strip(),
                }
            )

    requirements = ex.get("requirements") or []
    if isinstance(requirements, list):
        for r in requirements:
            if isinstance(r, dict):
                upsert_requirement(state, r)

    milestones = ex.get("milestones") or []
    if isinstance(milestones, list):
        for m in milestones:
            if not isinstance(m, dict):
                continue
            date = str(m.get("date", "")).strip()
            target = str(m.get("target", "")).strip()
            if not date and not target:
                continue
            state["milestones"].append(
                {
                    "stage": str(m.get("stage", "")).strip() or f"里程碑{len(state['milestones']) + 1}",
                    "date": date,
                    "target": target,
                    "owner": str(m.get("owner", "")).strip(),
                }
            )

    open_questions = ex.get("open_questions") or []
    if isinstance(open_questions, list):
        state["open_questions"] = merge_list(state["open_questions"], [str(x).strip() for x in open_questions if str(x).strip()])


def render_markdown(state: dict[str, Any]) -> str:
    doc = state["doc_info"]
    bg = state["background"]
    goals = state["goals"]
    scope = state["scope"]
    nfr = state["nfr"]
    ai = state["ai"]

    req_rows = []
    for req in state["requirements"]:
        req_rows.append(f"| {req['id']} | {safe(req['module'])} | {safe(req['title'])} | {safe(req['priority'])} | 待分配 | 待开发 |")
    req_table = "\n".join(req_rows) if req_rows else "| - | - | - | - | - | - |"

    req_details = []
    for req in state["requirements"]:
        rules = "\n".join([f"  1. {safe(x)}" for x in req.get("rules", [])]) or "  1. 待补充"
        exceptions = "\n".join([f"  1. {safe(x)}" for x in req.get("exceptions", [])]) or "  1. 待补充"
        acceptance = "\n".join([f"  1. {safe(x)}" for x in req.get("acceptance", [])]) or "  1. 待补充"
        tracking = ", ".join([f"`{safe(x)}`" for x in req.get("tracking", [])]) or "待补充"
        req_details.append(
            f"""
#### {safe(req['id'])} {safe(req['title'])}

- 目标：{safe(req.get('description') or '待补充')}
- 业务规则：
{rules}
- 异常处理：
{exceptions}
- 验收标准：
{acceptance}
- 埋点：{tracking}
""".strip()
        )

    user_rows = []
    for u in state["users"]:
        user_rows.append(f"| {safe(u.get('role'))} | {safe(u.get('traits'))} | {safe(u.get('needs'))} | 待确认 |")
    users_table = "\n".join(user_rows) if user_rows else "| 待补充 | 待补充 | 待补充 | 待确认 |"

    scn_rows = []
    for s in state["scenarios"]:
        scn_rows.append(
            f"| {safe(s.get('id'))} | {safe(s.get('description'))} | {safe(s.get('trigger'))} | {safe(s.get('success'))} |"
        )
    scn_table = "\n".join(scn_rows) if scn_rows else "| SCN-001 | 待补充 | 待补充 | 待补充 |"

    ms_rows = []
    for m in state["milestones"]:
        ms_rows.append(f"| {safe(m.get('stage'))} | {safe(m.get('date'))} | {safe(m.get('target'))} | {safe(m.get('owner'))} |")
    ms_table = "\n".join(ms_rows) if ms_rows else "| 里程碑1 | 待补充 | 待补充 | 待补充 |"

    in_scope = "\n".join([f"- {safe(x)}" for x in scope.get("in_scope", [])]) or "- 待补充"
    out_scope = "\n".join([f"- {safe(x)}" for x in scope.get("out_scope", [])]) or "- 待补充"

    open_q = "\n".join([f"- {safe(x)}" for x in state.get("open_questions", [])]) or "- 暂无"

    return f"""# PRD（自动更新）

> 本文件由 `prd_agent.py` 自动生成。更新时间：{safe(state['meta'].get('updated_at', ''))}

## 0. 文档信息

- 产品名称：{safe(doc.get('product_name') or '待补充')}
- 项目代号：{safe(doc.get('project_code') or '待补充')}
- 负责人（PM）：{safe(doc.get('pm_owner') or '待补充')}
- 版本号：{safe(doc.get('version') or 'v0.1.0')}
- 状态：{safe(doc.get('status') or '草稿')}
- 创建日期：{safe(doc.get('created_date') or now_date())}
- 最近更新：{safe(doc.get('updated_date') or now_date())}

## 1. 背景与目标

### 1.1 项目背景

- 当前问题：{safe(bg.get('current_problem') or '待补充')}
- 业务机会：{safe(bg.get('business_opportunity') or '待补充')}
- 为什么现在做：{safe(bg.get('timing') or '待补充')}

### 1.2 目标

- 业务目标：{safe(goals.get('business_goal') or '待补充')}
- 用户目标：{safe(goals.get('user_goal') or '待补充')}
- 系统目标：{safe(goals.get('system_goal') or '待补充')}

### 1.3 范围边界

**In Scope**
{in_scope}

**Out of Scope**
{out_scope}

## 2. 用户与场景

### 2.1 用户角色

| 角色 | 特征 | 核心诉求 | 使用频率 |
|---|---|---|---|
{users_table}

### 2.2 核心场景

| 场景ID | 场景描述 | 触发条件 | 成功定义 |
|---|---|---|---|
{scn_table}

## 3. 功能需求

| 需求ID | 模块 | 需求标题 | 优先级 | 负责人 | 状态 |
|---|---|---|---|---|---|
{req_table}

{chr(10).join(req_details) if req_details else '暂无需求，请继续口述输入。'}

## 4. 非功能需求

| 类别 | 指标/要求 |
|---|---|
| 性能 | {safe(nfr.get('performance') or '待补充')} |
| 可用性 | {safe(nfr.get('availability') or '待补充')} |
| 安全与隐私 | {safe(nfr.get('security') or '待补充')} |
| 可观测性 | {safe(nfr.get('observability') or '待补充')} |

## 5. AI 专项

- 能做：{safe(ai.get('can_do') or '待补充')}
- 不能做：{safe(ai.get('cannot_do') or '待补充')}
- 禁止场景：{safe(ai.get('forbidden') or '待补充')}
- Prompt策略：{safe(ai.get('prompt_strategy') or '待补充')}
- 兜底策略：{safe(ai.get('fallback') or '待补充')}

## 6. 发布计划

| 阶段 | 时间 | 目标 | 负责人 |
|---|---|---|---|
{ms_table}

## 7. 待确认问题

{open_q}
"""


def build_html_pages(state: dict[str, Any]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for req in state.get("requirements", []):
        title = req.get("title", "").strip()
        if not title:
            continue
        pages.append(
            {
                "key": req.get("id", "req").lower().replace("-", "_"),
                "name": title,
                "reqId": req.get("id", "REQ-XXX"),
                "subtitle": req.get("module", "待定模块"),
                "objective": req.get("description", "待补充"),
                "rules": req.get("rules") or ["待补充"],
                "acceptance": req.get("acceptance") or ["待补充"],
                "points": req.get("tracking") or ["待补充"],
            }
        )

    if not pages:
        pages = [
            {
                "key": "placeholder",
                "name": "等待需求输入",
                "reqId": "REQ-XXX",
                "subtitle": "请在聊天里先说一条需求",
                "objective": "例如：支持手机号验证码登录",
                "rules": ["输入后将自动生成页面"],
                "acceptance": ["输入验收标准后自动更新"],
                "points": ["需求追踪", "状态切换"],
            }
        ]
    return pages


def render_html(state: dict[str, Any]) -> str:
    pages_json = json.dumps(build_html_pages(state), ensure_ascii=False)
    title = safe(state.get("doc_info", {}).get("product_name", "PRD交互原型"))

    template = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__ - PRD Live Prototype</title>
  <style>
    :root {
      --bg: #f4f1ea;
      --panel: #fffdf8;
      --text: #1f2937;
      --muted: #6b7280;
      --primary: #0f766e;
      --accent: #c2410c;
      --line: #e7e2d8;
      --ok: #166534;
      --warn: #9a3412;
      --err: #991b1b;
      --radius: 14px;
      --shadow: 0 10px 30px rgba(15, 23, 42, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      font-family: "Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at 10% 10%, #ede6d8 0%, transparent 45%),
        radial-gradient(circle at 90% 90%, #d9efe8 0%, transparent 40%),
        var(--bg);
      min-height: 100vh;
    }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 10;
      border-bottom: 1px solid var(--line);
      background: rgba(244,241,234,.85);
      backdrop-filter: blur(6px);
    }
    .topbar-inner {
      max-width: 1200px;
      margin: 0 auto;
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .container {
      max-width: 1200px;
      margin: 18px auto;
      padding: 0 16px 24px;
      display: grid;
      grid-template-columns: 250px 1fr 330px;
      gap: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .panel h3 {
      margin: 0;
      font-size: 14px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    .nav-list { padding: 10px; display: grid; gap: 8px; }
    .nav-item {
      width: 100%; text-align: left; cursor: pointer;
      border: 1px solid var(--line); background: #fff;
      border-radius: 10px; padding: 10px;
    }
    .nav-item.active { border-color: var(--primary); background: #f0fdfa; }
    .screen { min-height: 620px; display: grid; grid-template-rows: auto 1fr auto; }
    .screen-header { padding: 14px; border-bottom: 1px solid var(--line); }
    .screen-title { font-size: 18px; font-weight: 700; }
    .status-tabs { display: flex; gap: 8px; padding: 10px 14px; border-bottom: 1px dashed var(--line); }
    .status-tab {
      cursor: pointer; font-size: 12px; padding: 6px 10px; border-radius: 8px;
      border: 1px solid var(--line); background: #fff;
    }
    .status-tab.active { border-color: var(--accent); color: var(--accent); }
    .screen-body { padding: 14px; display: grid; gap: 12px; }
    .card { border: 1px solid var(--line); border-radius: 12px; padding: 12px; background: #fff; }
    .muted { color: var(--muted); font-size: 13px; }
    .feedback { border-radius: 10px; padding: 8px 10px; font-size: 13px; }
    .ok { background: #ecfdf5; color: var(--ok); border: 1px solid #bbf7d0; }
    .warn { background: #fff7ed; color: var(--warn); border: 1px solid #fed7aa; }
    .err { background: #fef2f2; color: var(--err); border: 1px solid #fecaca; }
    .tag {
      display: inline-block; font-size: 11px; border: 1px solid var(--line);
      border-radius: 999px; padding: 2px 8px; margin-right: 4px; background: #fff;
    }
    .detail { padding: 12px 14px; display: grid; gap: 10px; font-size: 13px; line-height: 1.5; }
    .detail-block { border: 1px solid var(--line); border-radius: 10px; padding: 10px; background: #fff; }
    .footer { padding: 10px 14px; border-top: 1px solid var(--line); font-size: 12px; color: var(--muted); background: #fff; }
    @media (max-width: 980px) { .container { grid-template-columns: 1fr; } .screen { min-height: auto; } }
  </style>
</head>
<body>
  <div class="topbar"><div class="topbar-inner"><strong>__TITLE__</strong><span class="muted">实时更新原型</span></div></div>
  <div class="container">
    <aside class="panel"><h3>流程导航</h3><div class="nav-list" id="navList"></div></aside>
    <main class="panel screen">
      <div class="screen-header">
        <div class="screen-title" id="screenTitle">-</div>
        <div class="muted" id="screenSubtitle">-</div>
        <div class="tag" id="reqTag">REQ-XXX</div>
      </div>
      <div><div class="status-tabs" id="statusTabs"></div><div class="screen-body" id="screenBody"></div></div>
      <div class="footer" id="footerInfo">-</div>
    </main>
    <section class="panel"><h3>需求说明面板</h3><div class="detail" id="detailPanel"></div></section>
  </div>

  <script>
    const pages = __PAGES_JSON__;
    const states = ["normal", "empty", "error", "no_auth"];
    const labels = { normal: "正常态", empty: "空态", error: "异常态", no_auth: "权限不足" };

    let currentPage = pages[0];
    let currentState = "normal";

    const navList = document.getElementById("navList");
    const statusTabs = document.getElementById("statusTabs");
    const screenTitle = document.getElementById("screenTitle");
    const screenSubtitle = document.getElementById("screenSubtitle");
    const reqTag = document.getElementById("reqTag");
    const screenBody = document.getElementById("screenBody");
    const detailPanel = document.getElementById("detailPanel");
    const footerInfo = document.getElementById("footerInfo");

    function renderNav() {
      navList.innerHTML = pages.map(page => `
        <button class="nav-item ${currentPage.key === page.key ? "active" : ""}" data-key="${page.key}">
          <div><strong>${page.name}</strong></div>
          <div class="muted">${page.reqId}</div>
        </button>
      `).join("");

      navList.querySelectorAll(".nav-item").forEach(btn => {
        btn.addEventListener("click", () => {
          currentPage = pages.find(p => p.key === btn.dataset.key);
          currentState = "normal";
          paint();
        });
      });
    }

    function renderStatusTabs() {
      statusTabs.innerHTML = states.map(state => `
        <button class="status-tab ${currentState === state ? "active" : ""}" data-state="${state}">${labels[state]}</button>
      `).join("");
      statusTabs.querySelectorAll(".status-tab").forEach(btn => {
        btn.addEventListener("click", () => {
          currentState = btn.dataset.state;
          paint();
        });
      });
    }

    function renderScreen() {
      const feedback = {
        normal: ["ok", "可用于评审演示和验收走查"],
        empty: ["warn", "当前状态模拟为空数据表现"],
        error: ["err", "当前状态模拟接口异常或超时"],
        no_auth: ["warn", "当前状态模拟权限受限"],
      };
      const [cls, text] = feedback[currentState];

      screenBody.innerHTML = `
        <div class="card">
          <strong>${currentPage.name}</strong>
          <p class="muted">${currentPage.subtitle}</p>
          <div class="feedback ${cls}">${text}</div>
          <div style="margin-top:10px">${(currentPage.points || []).map(x => `<span class="tag">${x}</span>`).join("")}</div>
        </div>
      `;
    }

    function renderDetail() {
      detailPanel.innerHTML = `
        <div class="detail-block"><h4>需求追踪</h4><div><strong>${currentPage.reqId}</strong></div></div>
        <div class="detail-block"><h4>目标</h4><div>${currentPage.objective || "待补充"}</div></div>
        <div class="detail-block"><h4>业务规则</h4>${(currentPage.rules || ["待补充"]).map(x => `<div>• ${x}</div>`).join("")}</div>
        <div class="detail-block"><h4>验收标准</h4>${(currentPage.acceptance || ["待补充"]).map(x => `<div>• ${x}</div>`).join("")}</div>
      `;
    }

    function paint() {
      renderNav();
      renderStatusTabs();
      screenTitle.textContent = currentPage.name;
      screenSubtitle.textContent = `${currentPage.subtitle} | 当前状态：${labels[currentState]}`;
      reqTag.textContent = currentPage.reqId;
      renderScreen();
      renderDetail();
      footerInfo.textContent = `页面：${currentPage.name} | 需求ID：${currentPage.reqId} | 状态：${labels[currentState]}`;
    }

    paint();
  </script>
</body>
</html>
"""

    return template.replace("__PAGES_JSON__", pages_json).replace("__TITLE__", title or "PRD交互原型")


def safe(text: Any) -> str:
    if text is None:
        return ""
    return str(text).replace("|", "\\|").strip()


def write_outputs(state: dict[str, Any], md_path: Path, html_path: Path) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(state), encoding="utf-8")
    html_path.write_text(render_html(state), encoding="utf-8")


def print_status(state: dict[str, Any]) -> None:
    missing = get_missing_items(state)
    print(f"\n当前已采集需求：{len(state.get('requirements', []))} 条")
    print(f"当前缺失必填项：{len(missing)} 项")
    if missing:
        for i, item in enumerate(missing[:8], start=1):
            print(f"{i}. {item['key']}")
        if len(missing) > 8:
            print("...")
    print(f"Markdown: {MD_PATH}")
    print(f"HTML: {HTML_PATH}\n")


def run_chat(state_path: Path, md_path: Path, html_path: Path, model: str) -> None:
    state = load_state(state_path)
    normalize_state(state)
    write_outputs(state, md_path, html_path)
    save_state(state_path, state)

    print("PRD Agent 已启动。输入 /exit 结束，/status 查看进度，/render 强制重渲染。")
    missing = get_missing_items(state)
    if missing:
        state["meta"]["pending_key"] = missing[0]["key"]
        print(f"首个问题：{missing[0]['question']}")

    while True:
        try:
            text = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n会话结束。")
            break

        if not text:
            continue
        if text == "/exit":
            break
        if text == "/status":
            print_status(state)
            continue
        if text == "/render":
            normalize_state(state)
            write_outputs(state, md_path, html_path)
            save_state(state_path, state)
            print("已重渲染输出文件。")
            continue

        pending_key = state.get("meta", {}).get("pending_key", "")
        if pending_key:
            set_pending_answer(state, pending_key, text)

        apply_regex_extraction(state, text)
        llm_status = maybe_apply_llm_extraction(state, text, model)

        normalize_state(state)
        write_outputs(state, md_path, html_path)

        missing = get_missing_items(state)
        if missing:
            nxt = missing[0]
            state["meta"]["pending_key"] = nxt["key"]
            print(f"已更新文档（LLM抽取：{llm_status}）。还缺 {len(missing)} 项。")
            print(f"下一问：{nxt['question']}")
        else:
            state["meta"]["pending_key"] = ""
            print(f"已更新文档（LLM抽取：{llm_status}）。所有必填项已完整。")
            print("你可以继续补充更多细节，我会继续增量更新。")

        save_state(state_path, state)

    normalize_state(state)
    write_outputs(state, md_path, html_path)
    save_state(state_path, state)
    print("输出已保存。")


def run_render(state_path: Path, md_path: Path, html_path: Path) -> None:
    state = load_state(state_path)
    normalize_state(state)
    write_outputs(state, md_path, html_path)
    save_state(state_path, state)
    print(f"已输出：{md_path} 和 {html_path}")


def run_reset(state_path: Path, md_path: Path, html_path: Path) -> None:
    state = copy.deepcopy(DEFAULT_STATE)
    state["doc_info"]["created_date"] = now_date()
    normalize_state(state)
    save_state(state_path, state)
    write_outputs(state, md_path, html_path)
    print("已重置状态并重建输出。")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PRD conversational agent")
    p.add_argument("command", choices=["chat", "render", "status", "reset"], nargs="?", default="chat")
    p.add_argument("--state", default=STATE_PATH)
    p.add_argument("--md", default=MD_PATH)
    p.add_argument("--html", default=HTML_PATH)
    p.add_argument("--model", default=DEFAULT_MODEL)
    return p


def main() -> None:
    args = build_parser().parse_args()
    state_path = Path(args.state)
    md_path = Path(args.md)
    html_path = Path(args.html)

    if args.command == "chat":
        run_chat(state_path, md_path, html_path, args.model)
        return

    state = load_state(state_path)
    if args.command == "status":
        normalize_state(state)
        write_outputs(state, md_path, html_path)
        save_state(state_path, state)
        print_status(state)
    elif args.command == "render":
        run_render(state_path, md_path, html_path)
    elif args.command == "reset":
        run_reset(state_path, md_path, html_path)


if __name__ == "__main__":
    main()
