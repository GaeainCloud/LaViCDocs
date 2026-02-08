"""Get笔记知识库 evidence collector.

Integrates with Get Notes (biji.com) OpenAPI for knowledge base search and recall.
API Docs: https://doc.biji.com/docs/QfMcwcoHqic5urkTBQKcAPIWnJe/

Endpoints:
  - POST /knowledge/search       - AI-powered Q&A search
  - POST /knowledge/search/recall - Raw document recall (returns matching docs)
"""

import logging
import os
import requests as http_requests

from models import new_evidence

logger = logging.getLogger("smartokr")

GETNOTE_API_BASE = "https://open-api.biji.com/getnote/openapi"


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

        try:
            resp = http_requests.post(url, json=payload, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Get笔记 search failed: {e}")
            return {"error": str(e)}

    def recall(self, question: str, topic_ids: list = None, top_k: int = 5,
               intent_rewrite: bool = True) -> dict:
        """Raw document recall from knowledge base.

        Args:
            question: Search query
            topic_ids: Knowledge base topic IDs
            top_k: Number of results to return
            intent_rewrite: Enable intent rewriting

        Returns:
            API response with matching documents
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

        try:
            resp = http_requests.post(url, json=payload, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Get笔记 recall failed: {e}")
            return {"error": str(e)}

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

        for query in queries:
            # Use recall to get raw document matches
            resp = self.recall(question=query, topic_ids=topic_ids, top_k=top_k)

            if "error" in resp:
                logger.warning(f"Recall failed for query '{query}': {resp['error']}")
                continue

            # Parse response: {h: {c: status}, c: {data: [...]}}
            content = resp.get("c", resp)
            data_items = []
            if isinstance(content, dict):
                data_items = content.get("data", [])
            elif isinstance(content, list):
                data_items = content

            for item in data_items:
                item_id = item.get("id", "")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                title = item.get("title", query)
                text = item.get("content", "")

                all_results.append(item)
                ev = new_evidence(
                    person=person,
                    title=title[:200] if title else query,
                    description=text[:500] if text else "",
                    source_type="knowledge_base",
                    date_str="",  # KB docs may not have dates
                    url=None,
                    metadata={
                        "source": "get_notes",
                        "topic_ids": topic_ids or [self.topic_id],
                        "query": query,
                        "doc_id": item_id,
                    },
                    tags=["knowledge_base", "get_notes"],
                )
                evidence_items.append(ev)

        return {
            "recall_results": all_results,
            "evidence_items": evidence_items,
            "summary": {
                "queries_executed": len(queries),
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
