"""Get笔记知识库 evidence collector.

Integrates with Get Notes (biji.com) OpenAPI for knowledge base search and recall.
API Docs: https://doc.biji.com/docs/QfMcwcoHqic5urkTBQKcAPIWnJe/

Endpoints:
  - POST /knowledge/search       - AI-powered Q&A search
  - POST /knowledge/search/recall - Raw document recall (returns matching docs)

Response format:
  {
    "h": {"c": 0, "e": "", "s": timestamp, "t": ms},
    "c": {"data": [{"id": "...", "title": "...", "content": "...", "score": 0.09, "type": "NOTE"}]}
  }
"""

import logging
import os
import time
import requests as http_requests

from models import new_evidence

logger = logging.getLogger("smartokr")

GETNOTE_API_BASE = "https://open-api.biji.com/getnote/openapi"
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]


class NotesCollector:
    def __init__(self, api_key: str = "", topic_id: str = "", api_base: str = ""):
        self.api_key = api_key or os.getenv("GETNOTE_API_KEY", "")
        self.topic_id = topic_id or os.getenv("GETNOTE_TOPIC_ID", "")
        self.api_base = api_base or os.getenv("GETNOTE_API_BASE", GETNOTE_API_BASE)

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Authorization": f"Bearer {self.api_key}",
            "X-OAuth-Version": "1",
        }

    def _post(self, url: str, payload: dict, timeout: int = 30) -> dict:
        """POST with proxy bypass and retry logic."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = http_requests.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                    timeout=timeout,
                    proxies={"http": None, "https": None},  # Bypass proxy
                )
                resp.raise_for_status()
                data = resp.json()

                # Check API-level error: h.c != 0 means error
                h = data.get("h", {})
                if isinstance(h, dict) and h.get("c", 0) != 0:
                    err_msg = h.get("e", "Unknown API error")
                    logger.error(f"Get笔记 API error (code={h.get('c')}): {err_msg}")
                    return {"error": err_msg, "api_code": h.get("c")}

                return data

            except http_requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF[attempt]
                    logger.warning(f"Connection failed (attempt {attempt+1}/{MAX_RETRIES}), retrying in {wait}s...")
                    time.sleep(wait)
            except http_requests.exceptions.Timeout as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF[attempt]
                    logger.warning(f"Request timeout (attempt {attempt+1}/{MAX_RETRIES}), retrying in {wait}s...")
                    time.sleep(wait)
            except Exception as e:
                logger.error(f"Get笔记 request failed: {e}")
                return {"error": str(e)}

        error_msg = str(last_error)
        if "ProxyError" in error_msg or "Tunnel connection failed" in error_msg:
            error_msg += (
                "\n\n提示：当前网络环境可能有代理限制，无法访问 open-api.biji.com。"
                "\n请在本地环境运行此脚本：cd SmartOKR && python scripts/analyze_all.py"
            )
        elif "name resolution" in error_msg.lower() or "getaddrinfo" in error_msg.lower():
            error_msg += (
                "\n\n提示：DNS 无法解析 open-api.biji.com，请检查网络连接或代理设置。"
            )

        logger.error(f"Get笔记 request failed after {MAX_RETRIES} retries: {error_msg}")
        return {"error": error_msg}

    def search(self, question: str, topic_ids: list = None, deep_seek: bool = False,
               history: list = None) -> dict:
        """AI-powered knowledge base search.

        Args:
            question: Search query / question
            topic_ids: Knowledge base topic IDs (defaults to configured topic_id)
            deep_seek: Enable deep search mode
            history: Conversation history [{content, role}]

        Returns:
            API response dict
        """
        url = f"{self.api_base}/knowledge/search"
        ids = topic_ids or [self.topic_id]
        payload = {
            "question": question,
            "topic_ids": ids,
            "deep_seek": deep_seek,
            "refs": False,
        }
        if history:
            payload["history"] = history

        return self._post(url, payload)

    def recall(self, question: str, topic_ids: list = None, top_k: int = 5,
               intent_rewrite: bool = True) -> dict:
        """Raw document recall from knowledge base.

        Args:
            question: Search query
            topic_ids: Knowledge base topic IDs
            top_k: Number of results to return
            intent_rewrite: Enable intent rewriting

        Returns:
            API response with matching documents:
            {h: {c: 0, ...}, c: {data: [{id, title, content, score, type, recall_source}]}}
        """
        url = f"{self.api_base}/knowledge/search/recall"
        ids = topic_ids or [self.topic_id]
        payload = {
            "question": question,
            "topic_ids": ids,
            "top_k": top_k,
            "intent_rewrite": intent_rewrite,
            "select_matrix": False,
        }

        return self._post(url, payload)

    def _parse_recall_items(self, resp: dict) -> list:
        """Parse recall response into data items list.

        Handles response format: {h: {...}, c: {data: [...]}}
        """
        if "error" in resp:
            return []

        content = resp.get("c", {})
        if isinstance(content, dict):
            return content.get("data", [])
        elif isinstance(content, list):
            return content
        return []

    def collect_evidence(self, person: str, queries: list = None,
                         topic_ids: list = None, top_k: int = 5) -> dict:
        """Collect work evidence from knowledge base by searching with multiple queries.

        Args:
            person: Person name to associate evidence with
            queries: List of search queries (e.g., person's work topics)
            topic_ids: Knowledge base topic IDs
            top_k: Number of recall results per query

        Returns:
            Dict with recall_results, evidence_items, and summary
        """
        if not queries:
            queries = [f"{person}的工作记录", f"{person}的项目进展", f"{person}的工作成果"]

        all_results = []
        evidence_items = []
        seen_ids = set()
        errors = []

        for query in queries:
            resp = self.recall(question=query, topic_ids=topic_ids, top_k=top_k)

            if "error" in resp:
                errors.append({"query": query, "error": resp["error"]})
                continue

            data_items = self._parse_recall_items(resp)

            for item in data_items:
                item_id = item.get("id", "")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                title = item.get("title", query)
                text = item.get("content", "")
                score = item.get("score", 0)

                all_results.append(item)
                ev = new_evidence(
                    person=person,
                    title=title[:200] if title else query,
                    description=text[:500] if text else "",
                    source_type="knowledge_base",
                    date_str="",
                    url=None,
                    metadata={
                        "source": "get_notes",
                        "topic_ids": topic_ids or [self.topic_id],
                        "query": query,
                        "doc_id": item_id,
                        "recall_score": score,
                        "recall_source": item.get("recall_source", ""),
                        "type": item.get("type", ""),
                    },
                    tags=["knowledge_base", "get_notes"],
                )
                evidence_items.append(ev)

        return {
            "recall_results": all_results,
            "evidence_items": evidence_items,
            "errors": errors,
            "summary": {
                "queries_executed": len(queries),
                "queries_failed": len(errors),
                "unique_documents": len(seen_ids),
                "evidence_items_created": len(evidence_items),
            },
        }

    def search_for_person(self, person: str, question: str, topic_ids: list = None) -> dict:
        """Perform an AI search about a specific person's work.

        Returns the AI-generated answer from the knowledge base.
        """
        full_question = f"关于{person}：{question}"
        return self.search(question=full_question, topic_ids=topic_ids, deep_seek=True)
