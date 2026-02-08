"""SmartOKR data model definitions."""

from utils import generate_id, now_iso


def new_objective(title, bsc_dimension, period, owner, description="", weight=1.0):
    return {
        "objective_id": generate_id("obj"),
        "title": title,
        "description": description,
        "bsc_dimension": bsc_dimension,
        "period": period,
        "owner": owner,
        "weight": weight,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "key_results": [],
    }


def new_key_result(objective_id, title, target_value, unit, description="", weight=1.0, current_value=0):
    return {
        "kr_id": generate_id("kr"),
        "objective_id": objective_id,
        "title": title,
        "description": description,
        "target_value": target_value,
        "current_value": current_value,
        "unit": unit,
        "weight": weight,
        "score": None,
        "evidence_ids": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def new_evidence(person, title, description, source_type, date_str, url=None, metadata=None, tags=None):
    return {
        "evidence_id": generate_id("ev"),
        "person": person,
        "source_type": source_type,
        "title": title,
        "description": description,
        "date": date_str,
        "url": url,
        "metadata": metadata or {},
        "tags": tags or [],
        "matched_krs": [],
        "collected_at": now_iso(),
    }


def new_score_record(person, period, dimension_weights, dimensions, overall_score, summary):
    return {
        "score_id": generate_id("score"),
        "person": person,
        "period": period,
        "calculated_at": now_iso(),
        "dimension_weights": dimension_weights,
        "dimensions": dimensions,
        "overall_score": overall_score,
        "summary": summary,
    }
