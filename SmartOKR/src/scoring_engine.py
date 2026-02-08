"""BSC dynamic weight scoring engine.

Supports role-based weight presets where different job positions have
different weight distributions across the 4 BSC dimensions:
  - Financial (财务)
  - Customer (客户)
  - Internal Process (内部流程)
  - Learning & Growth (学习与成长)

Scoring formula:
  KR Score = completion% * 0.7 + evidence_strength * 0.3
  Objective Score = weighted_avg(KR scores)
  Dimension Score = weighted_avg(Objective scores)
  Overall Score = weighted_avg(Dimension scores, dimension_weights)
"""

import logging

from utils import ROLE_WEIGHT_PRESETS, BSC_DIMENSIONS
from models import new_score_record

logger = logging.getLogger("smartokr")


class ScoringEngine:

    def get_role_weights(self, role: str = None) -> dict:
        """Get BSC dimension weights for a role. Returns default if role not found."""
        if role and role in ROLE_WEIGHT_PRESETS:
            return ROLE_WEIGHT_PRESETS[role].copy()
        return ROLE_WEIGHT_PRESETS["default"].copy()

    def list_role_presets(self) -> dict:
        """List all available role weight presets."""
        return {
            role: {
                "weights": weights,
                "description": self._role_description(role),
            }
            for role, weights in ROLE_WEIGHT_PRESETS.items()
        }

    def _role_description(self, role: str) -> str:
        descriptions = {
            "engineer": "工程师/开发 - 侧重内部流程和学习成长",
            "product_manager": "产品经理 - 侧重客户维度",
            "sales": "销售 - 侧重财务和客户维度",
            "designer": "设计师 - 侧重客户和内部流程",
            "manager": "管理者 - 四维度均衡偏内部流程",
            "researcher": "研究员 - 侧重学习成长和内部流程",
            "operations": "运营 - 侧重内部流程和均衡分布",
            "default": "默认 - 通用权重分配",
        }
        return descriptions.get(role, role)

    def calculate(self, person: str, period: str, objectives: list,
                  evidence: list, dimension_weights: dict = None,
                  role: str = None) -> dict:
        """Calculate weighted scores across BSC dimensions.

        Args:
            person: Person being evaluated
            period: OKR period
            objectives: List of objective dicts with key_results
            evidence: List of evidence items for this person
            dimension_weights: Custom weights (overrides role preset)
            role: Role key for weight preset (e.g., 'engineer', 'sales')

        Returns:
            Score record dict
        """
        # Determine weights: explicit > role preset > default
        if dimension_weights:
            weights = dimension_weights
        else:
            weights = self.get_role_weights(role)

        # Build evidence lookup: evidence_id -> evidence item
        ev_map = {e["evidence_id"]: e for e in evidence}

        # Group objectives by BSC dimension
        dim_objectives = {}
        for obj in objectives:
            dim = obj.get("bsc_dimension", "internal_process")
            dim_objectives.setdefault(dim, []).append(obj)

        dimensions = {}
        total_evidence = 0
        matched_evidence = 0
        at_risk_krs = []

        for dim_key in BSC_DIMENSIONS:
            objs = dim_objectives.get(dim_key, [])
            obj_results = []

            for obj in objs:
                kr_results = []
                for kr in obj.get("key_results", []):
                    kr_score, completion_pct, ev_count = self._score_kr(kr, ev_map)
                    total_evidence += ev_count
                    if ev_count > 0:
                        matched_evidence += ev_count

                    if completion_pct < 50:
                        at_risk_krs.append(kr["kr_id"])

                    kr_results.append({
                        "kr_id": kr["kr_id"],
                        "title": kr["title"],
                        "weight": kr.get("weight", 1.0),
                        "target_value": kr.get("target_value", 0),
                        "current_value": kr.get("current_value", 0),
                        "unit": kr.get("unit", ""),
                        "completion_pct": round(completion_pct, 1),
                        "evidence_count": ev_count,
                        "score": round(kr_score, 1),
                    })

                obj_score = self._weighted_avg(
                    [(kr["score"], kr["weight"]) for kr in kr_results]
                )
                obj_results.append({
                    "objective_id": obj["objective_id"],
                    "title": obj["title"],
                    "weight": obj.get("weight", 1.0),
                    "key_results": kr_results,
                    "objective_score": round(obj_score, 1),
                })

            dim_score = self._weighted_avg(
                [(o["objective_score"], o["weight"]) for o in obj_results]
            )
            dimensions[dim_key] = {
                "label": BSC_DIMENSIONS[dim_key]["label"],
                "weight": weights.get(dim_key, 0),
                "objectives": obj_results,
                "dimension_score": round(dim_score, 1),
            }

        # Overall score
        overall = self._weighted_avg(
            [(dimensions[d]["dimension_score"], weights.get(d, 0))
             for d in BSC_DIMENSIONS]
        )

        # Find strongest / weakest
        scored_dims = [(d, dimensions[d]["dimension_score"]) for d in BSC_DIMENSIONS
                       if dimensions[d]["objectives"]]
        strongest = max(scored_dims, key=lambda x: x[1])[0] if scored_dims else None
        weakest = min(scored_dims, key=lambda x: x[1])[0] if scored_dims else None

        summary = {
            "total_evidence_items": total_evidence,
            "matched_evidence_items": matched_evidence,
            "strongest_dimension": strongest,
            "weakest_dimension": weakest,
            "at_risk_krs": at_risk_krs,
            "role_applied": role or "default",
            "weights_used": weights,
        }

        return new_score_record(
            person=person,
            period=period,
            dimension_weights=weights,
            dimensions=dimensions,
            overall_score=round(overall, 1),
            summary=summary,
        )

    def _score_kr(self, kr: dict, ev_map: dict) -> tuple:
        """Score a single key result.

        Returns (kr_score, completion_pct, evidence_count).
        """
        target = kr.get("target_value", 0)
        current = kr.get("current_value", 0)

        # Completion percentage
        if target == 0:
            completion_pct = 100.0 if current >= 0 else 0.0
        elif kr.get("unit") == "count" and target > 0:
            # For "lower is better" like incident count
            if current <= target:
                completion_pct = 100.0
            else:
                completion_pct = max(0, (1 - (current - target) / target) * 100)
        else:
            completion_pct = min(100.0, (current / target) * 100) if target > 0 else 0

        # Evidence strength from matched evidence
        evidence_ids = kr.get("evidence_ids", [])
        relevance_scores = []
        for eid in evidence_ids:
            ev = ev_map.get(eid)
            if ev:
                for match in ev.get("matched_krs", []):
                    if match.get("kr_id") == kr["kr_id"]:
                        relevance_scores.append(match.get("relevance_score", 0))

        ev_strength = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

        # Combined score: 70% completion + 30% evidence strength
        kr_score = completion_pct * 0.7 + ev_strength * 0.3

        return kr_score, completion_pct, len(evidence_ids)

    def _weighted_avg(self, items: list) -> float:
        """Calculate weighted average from [(value, weight), ...].

        Returns 0 if no items or all weights are 0.
        """
        if not items:
            return 0.0
        total_weight = sum(w for _, w in items)
        if total_weight == 0:
            return 0.0
        return sum(v * w for v, w in items) / total_weight

    def analyze_progress(self, person: str, period: str, objectives: list,
                         evidence: list) -> dict:
        """Analyze work progress with completion, time distribution, workload stats.

        Returns a progress analysis dict.
        """
        # Per-objective completion
        obj_progress = []
        for obj in objectives:
            krs = obj.get("key_results", [])
            if not krs:
                obj_progress.append({
                    "objective_id": obj["objective_id"],
                    "title": obj["title"],
                    "bsc_dimension": obj["bsc_dimension"],
                    "completion_pct": 0,
                    "kr_count": 0,
                })
                continue

            kr_completions = []
            for kr in krs:
                target = kr.get("target_value", 0)
                current = kr.get("current_value", 0)
                if target > 0:
                    pct = min(100, (current / target) * 100)
                else:
                    pct = 100 if current >= 0 else 0
                kr_completions.append(pct)

            avg_completion = sum(kr_completions) / len(kr_completions) if kr_completions else 0
            obj_progress.append({
                "objective_id": obj["objective_id"],
                "title": obj["title"],
                "bsc_dimension": obj["bsc_dimension"],
                "completion_pct": round(avg_completion, 1),
                "kr_count": len(krs),
            })

        # Time distribution across BSC dimensions (evidence count per dimension)
        dim_evidence_count = {d: 0 for d in BSC_DIMENSIONS}
        obj_dim_map = {o["objective_id"]: o["bsc_dimension"] for o in objectives}
        for ev in evidence:
            for match in ev.get("matched_krs", []):
                kr_id = match.get("kr_id", "")
                for obj in objectives:
                    for kr in obj.get("key_results", []):
                        if kr["kr_id"] == kr_id:
                            dim = obj["bsc_dimension"]
                            dim_evidence_count[dim] = dim_evidence_count.get(dim, 0) + 1

        # Workload statistics
        source_counts = {}
        for ev in evidence:
            st = ev.get("source_type", "unknown")
            source_counts[st] = source_counts.get(st, 0) + 1

        dates = [ev.get("date", "")[:10] for ev in evidence if ev.get("date")]
        active_days = len(set(dates))

        return {
            "person": person,
            "period": period,
            "objective_progress": obj_progress,
            "overall_completion_pct": round(
                sum(o["completion_pct"] for o in obj_progress) / len(obj_progress), 1
            ) if obj_progress else 0,
            "time_distribution": {
                dim: {
                    "label": BSC_DIMENSIONS[dim]["label"],
                    "evidence_count": dim_evidence_count.get(dim, 0),
                }
                for dim in BSC_DIMENSIONS
            },
            "workload_statistics": {
                "total_evidence_items": len(evidence),
                "by_source": source_counts,
                "active_days": active_days,
            },
            "at_risk_objectives": [
                o for o in obj_progress if o["completion_pct"] < 50
            ],
        }
