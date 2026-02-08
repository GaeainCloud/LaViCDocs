"""SmartOKR JSON file persistence layer."""

import json
import os
import logging

logger = logging.getLogger("smartokr")

EMPTY_OKR_STORE = {"version": "1.0", "objectives": []}
EMPTY_EVIDENCE_STORE = {"version": "1.0", "evidence": []}
EMPTY_SCORE_STORE = {"version": "1.0", "score_records": []}


class DataStore:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.reports_dir = os.path.join(data_dir, "reports")
        os.makedirs(self.reports_dir, exist_ok=True)

        self.okr_file = os.path.join(data_dir, "okr_definitions.json")
        self.evidence_file = os.path.join(data_dir, "evidence_records.json")
        self.scores_file = os.path.join(data_dir, "scores.json")

    def _load(self, filepath: str, default: dict) -> dict:
        if not os.path.exists(filepath):
            return json.loads(json.dumps(default))
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load {filepath}: {e}, using default")
            return json.loads(json.dumps(default))

    def _save(self, filepath: str, data: dict):
        tmp = filepath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, filepath)

    # --- OKR operations ---

    def load_okrs(self) -> dict:
        return self._load(self.okr_file, EMPTY_OKR_STORE)

    def save_okrs(self, data: dict):
        self._save(self.okr_file, data)

    def add_objective(self, obj: dict) -> dict:
        store = self.load_okrs()
        store["objectives"].append(obj)
        self.save_okrs(store)
        return obj

    def find_objective(self, objective_id: str) -> dict | None:
        store = self.load_okrs()
        for obj in store["objectives"]:
            if obj["objective_id"] == objective_id:
                return obj
        return None

    def add_key_result(self, objective_id: str, kr: dict) -> dict | None:
        store = self.load_okrs()
        for obj in store["objectives"]:
            if obj["objective_id"] == objective_id:
                obj["key_results"].append(kr)
                self.save_okrs(store)
                return kr
        return None

    def list_objectives(self, period=None, owner=None, bsc_dimension=None) -> list:
        store = self.load_okrs()
        results = store["objectives"]
        if period:
            results = [o for o in results if o.get("period") == period]
        if owner:
            results = [o for o in results if o.get("owner") == owner]
        if bsc_dimension:
            results = [o for o in results if o.get("bsc_dimension") == bsc_dimension]
        return results

    def update_objective(self, objective_id: str, updates: dict) -> dict | None:
        store = self.load_okrs()
        for obj in store["objectives"]:
            if obj["objective_id"] == objective_id:
                for k, v in updates.items():
                    if k != "objective_id" and k != "key_results":
                        obj[k] = v
                from utils import now_iso
                obj["updated_at"] = now_iso()
                self.save_okrs(store)
                return obj
        return None

    def update_key_result(self, kr_id: str, updates: dict) -> dict | None:
        store = self.load_okrs()
        for obj in store["objectives"]:
            for kr in obj["key_results"]:
                if kr["kr_id"] == kr_id:
                    for k, v in updates.items():
                        if k != "kr_id" and k != "objective_id":
                            kr[k] = v
                    from utils import now_iso
                    kr["updated_at"] = now_iso()
                    self.save_okrs(store)
                    return kr
        return None

    # --- Evidence operations ---

    def load_evidence(self) -> dict:
        return self._load(self.evidence_file, EMPTY_EVIDENCE_STORE)

    def save_evidence(self, data: dict):
        self._save(self.evidence_file, data)

    def add_evidence(self, item: dict) -> dict:
        store = self.load_evidence()
        store["evidence"].append(item)
        self.save_evidence(store)
        return item

    def add_evidence_batch(self, items: list) -> int:
        store = self.load_evidence()
        store["evidence"].extend(items)
        self.save_evidence(store)
        return len(items)

    def get_evidence(self, person=None, source_type=None) -> list:
        store = self.load_evidence()
        results = store["evidence"]
        if person:
            results = [e for e in results if e.get("person") == person]
        if source_type:
            results = [e for e in results if e.get("source_type") == source_type]
        return results

    def get_unmatched_evidence(self, person: str) -> list:
        all_ev = self.get_evidence(person=person)
        return [e for e in all_ev if not e.get("matched_krs")]

    def store_matches(self, matches: list) -> int:
        """Store evidence-to-KR match results."""
        store = self.load_evidence()
        ev_map = {e["evidence_id"]: e for e in store["evidence"]}

        count = 0
        for match in matches:
            eid = match.get("evidence_id")
            if eid in ev_map:
                ev = ev_map[eid]
                # Avoid duplicate matches
                existing_kr_ids = {m["kr_id"] for m in ev.get("matched_krs", [])}
                if match.get("kr_id") not in existing_kr_ids:
                    ev.setdefault("matched_krs", []).append({
                        "kr_id": match["kr_id"],
                        "relevance_score": match.get("relevance_score", 0),
                        "reasoning": match.get("reasoning", ""),
                        "contribution_type": match.get("contribution_type", "direct"),
                    })
                    count += 1

                # Also update the KR's evidence_ids in OKR store
                self._link_evidence_to_kr(eid, match["kr_id"])

        self.save_evidence(store)
        return count

    def _link_evidence_to_kr(self, evidence_id: str, kr_id: str):
        """Add evidence_id to the KR's evidence_ids list."""
        okr_store = self.load_okrs()
        for obj in okr_store["objectives"]:
            for kr in obj["key_results"]:
                if kr["kr_id"] == kr_id:
                    if evidence_id not in kr.get("evidence_ids", []):
                        kr.setdefault("evidence_ids", []).append(evidence_id)
                        self.save_okrs(okr_store)
                    return

    # --- Score operations ---

    def load_scores(self) -> dict:
        return self._load(self.scores_file, EMPTY_SCORE_STORE)

    def save_scores(self, data: dict):
        self._save(self.scores_file, data)

    def add_score_record(self, record: dict) -> dict:
        store = self.load_scores()
        store["score_records"].append(record)
        self.save_scores(store)
        return record

    def get_latest_score(self, person: str, period: str) -> dict | None:
        store = self.load_scores()
        matching = [
            s for s in store["score_records"]
            if s.get("person") == person and s.get("period") == period
        ]
        if matching:
            return matching[-1]
        return None

    # --- Report operations ---

    def save_report(self, filename: str, content: str) -> str:
        filepath = os.path.join(self.reports_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return os.path.abspath(filepath)
