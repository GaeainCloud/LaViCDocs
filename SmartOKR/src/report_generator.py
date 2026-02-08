"""SmartOKR structured report generator.

Generates Markdown performance analysis reports with:
  - Executive summary
  - BSC dimension breakdown
  - Evidence chains with AI reasoning
  - Progress analysis
  - Workload statistics
"""

import logging
from datetime import datetime

from utils import BSC_DIMENSIONS

logger = logging.getLogger("smartokr")


class ReportGenerator:

    def generate(self, person: str, period: str, score_record: dict,
                 progress: dict, evidence: list, objectives: list,
                 report_type: str = "individual",
                 output_format: str = "markdown") -> str | dict:
        """Generate a structured performance analysis report.

        Args:
            person: Person name
            period: OKR period
            score_record: Score record from ScoringEngine
            progress: Progress analysis from ScoringEngine
            evidence: Evidence items list
            objectives: Objectives list
            report_type: 'individual', 'team', or 'dimension'
            output_format: 'markdown' or 'json'

        Returns:
            Markdown string or dict
        """
        report_data = self._build_report_data(
            person, period, score_record, progress, evidence, objectives
        )

        if output_format == "json":
            return report_data

        return self._render_markdown(report_data, report_type)

    def _build_report_data(self, person, period, score_record, progress,
                           evidence, objectives) -> dict:
        return {
            "person": person,
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "score_record": score_record,
            "progress": progress,
            "evidence_count": len(evidence),
            "objectives_count": len(objectives),
        }

    def _render_markdown(self, data: dict, report_type: str) -> str:
        score = data.get("score_record", {})
        progress = data.get("progress", {})
        dims = score.get("dimensions", {})
        summary = score.get("summary", {})
        person = data["person"]
        period = data["period"]

        lines = []
        lines.append(f"# OKR 绩效分析报告")
        lines.append(f"## {person} | {period}")
        lines.append(f"生成时间: {data['generated_at']}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Executive Summary
        lines.append("## 概览")
        lines.append("")
        lines.append(f"- **综合得分**: {score.get('overall_score', 0)} / 100")
        lines.append(f"- **证据总数**: {data.get('evidence_count', 0)}")
        lines.append(f"- **目标总数**: {data.get('objectives_count', 0)}")
        if summary.get("strongest_dimension"):
            label = BSC_DIMENSIONS.get(summary["strongest_dimension"], {}).get("label", "")
            lines.append(f"- **最强维度**: {label}")
        if summary.get("weakest_dimension"):
            label = BSC_DIMENSIONS.get(summary["weakest_dimension"], {}).get("label", "")
            lines.append(f"- **待提升维度**: {label}")
        if summary.get("role_applied"):
            lines.append(f"- **岗位权重**: {summary['role_applied']}")
        lines.append("")

        # BSC Overview Table
        lines.append("## 平衡计分卡概览")
        lines.append("")
        lines.append("| 维度 | 权重 | 得分 | 目标数 |")
        lines.append("|------|------|------|--------|")
        for dim_key in BSC_DIMENSIONS:
            dim = dims.get(dim_key, {})
            label = BSC_DIMENSIONS[dim_key]["label"]
            weight_pct = int(dim.get("weight", 0) * 100)
            dim_score = dim.get("dimension_score", 0)
            obj_count = len(dim.get("objectives", []))
            lines.append(f"| {label} | {weight_pct}% | {dim_score} | {obj_count} |")
        lines.append("")

        # Detailed Analysis by Dimension
        lines.append("## 各维度详细分析")
        lines.append("")
        for dim_key in BSC_DIMENSIONS:
            dim = dims.get(dim_key, {})
            label = BSC_DIMENSIONS[dim_key]["label"]
            weight_pct = int(dim.get("weight", 0) * 100)
            lines.append(f"### {label} - 权重: {weight_pct}%")
            lines.append("")

            objs = dim.get("objectives", [])
            if not objs:
                lines.append("_本维度暂无设定目标_")
                lines.append("")
                continue

            for obj in objs:
                obj_weight = int(obj.get("weight", 1) * 100)
                lines.append(f"#### 目标: {obj['title']} (权重: {obj_weight}%)")
                lines.append(f"**目标得分**: {obj.get('objective_score', 0)}")
                lines.append("")

                for kr in obj.get("key_results", []):
                    status = "✅" if kr.get("completion_pct", 0) >= 100 else "🔄" if kr.get("completion_pct", 0) >= 50 else "⚠️"
                    lines.append(f"- {status} **{kr['title']}**")
                    lines.append(f"  - 目标: {kr.get('target_value', 0)} {kr.get('unit', '')} | "
                                 f"当前: {kr.get('current_value', 0)} {kr.get('unit', '')} | "
                                 f"完成度: {kr.get('completion_pct', 0)}%")
                    lines.append(f"  - KR得分: {kr.get('score', 0)} | 证据数: {kr.get('evidence_count', 0)}")
                lines.append("")

        # Progress Analysis
        if progress:
            lines.append("## 进度与工作量分析")
            lines.append("")

            lines.append(f"**整体完成度**: {progress.get('overall_completion_pct', 0)}%")
            lines.append("")

            # Time Distribution
            td = progress.get("time_distribution", {})
            if td:
                lines.append("### 时间分布（按维度）")
                lines.append("")
                lines.append("| 维度 | 证据数量 |")
                lines.append("|------|----------|")
                for dim_key in BSC_DIMENSIONS:
                    dim_td = td.get(dim_key, {})
                    label = dim_td.get("label", dim_key)
                    count = dim_td.get("evidence_count", 0)
                    lines.append(f"| {label} | {count} |")
                lines.append("")

            # Workload Stats
            ws = progress.get("workload_statistics", {})
            if ws:
                lines.append("### 工作量统计")
                lines.append("")
                lines.append(f"- 证据总数: {ws.get('total_evidence_items', 0)}")
                lines.append(f"- 活跃天数: {ws.get('active_days', 0)}")
                by_source = ws.get("by_source", {})
                if by_source:
                    lines.append("- 来源分布:")
                    for src, cnt in by_source.items():
                        lines.append(f"  - {src}: {cnt}")
                lines.append("")

            # At-risk objectives
            at_risk = progress.get("at_risk_objectives", [])
            if at_risk:
                lines.append("### ⚠️ 风险目标（完成度 < 50%）")
                lines.append("")
                for o in at_risk:
                    lines.append(f"- **{o['title']}** - 完成度: {o['completion_pct']}%")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append("*由 SmartOKR 理性辅助裁判系统生成*")
        lines.append("*本报告基于证据分析，仅供参考，不代表最终评价。*")

        return "\n".join(lines)
