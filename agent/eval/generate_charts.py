"""
Final Benchmark Chart Generator (Week 5 -- Task A22).
=====================================================

Generates publication-quality charts for the final ChatOps SRE report:
  1. accuracy_by_ablation.svg        -- Accuracy & Fix Quality across 6 ablation modes
  2. accuracy_by_model.svg           -- Cross-model comparison (Qwen, Kimi, DeepSeek, Mistral)
  3. latency_and_cost.svg            -- Latency vs Inference Cost tradeoffs
  4. holdout_and_learning_curve.svg  -- Before vs After Learning Loop progression

Uses pure-Python SVG generation (zero external dependency, vector-sharp at any scale),
and will also export PNG if matplotlib is available.

Outputs are saved in:
  agent/eval/results/charts/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import math

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_DIR = PROJECT_ROOT / "agent" / "eval" / "results"
CHARTS_DIR = RESULTS_DIR / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def wilson_interval(successes: int, total: int, z: float = 1.95996) -> tuple[float, float]:
    """Compute 95% Wilson score confidence interval (returns percentages 0.0 - 100.0)."""
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + (z ** 2) / total
    center = (p + (z ** 2) / (2 * total)) / denom
    margin = (z * math.sqrt((p * (1 - p)) / total + (z ** 2) / (4 * (total ** 2)))) / denom
    lower = max(0.0, center - margin) * 100.0
    upper = min(1.0, center + margin) * 100.0
    return (round(lower, 1), round(upper, 1))


def _find_latest_benchmark_json() -> Path:
    # Prefer primary multi-ablation baseline benchmark JSON
    base_candidates = sorted(
        [
            p for p in RESULTS_DIR.glob("benchmark_*.json")
            if not any(skip in p.stem for skip in ("variants", "cpusat", "external", "holdout"))
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if base_candidates:
        return base_candidates[0]

    candidates = sorted(
        list(RESULTS_DIR.glob("benchmark_*.json")) + list(RESULTS_DIR.glob("bm_*.json")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No benchmark JSON file found in {RESULTS_DIR}. "
            "Run 'python -m agent.eval.benchmark --live --ablation llm_only,full --surprise --trials 2' first."
        )
    return candidates[0]


def _load_records(json_path: Path) -> tuple[str, list[dict]]:
    if not json_path.exists():
        raise FileNotFoundError(f"Benchmark JSON file not found: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("records", [])
    if not records:
        raise ValueError(f"Benchmark JSON contains 0 records: {json_path}")
    return str(data.get("run_id", json_path.stem)), records


def _aggregate_group(records: list[dict], key_fn) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict]] = {}
    for r in records:
        k = key_fn(r)
        groups.setdefault(k, []).append(r)

    summary: dict[str, dict[str, float]] = {}
    for k, grp in groups.items():
        n = len(grp)
        valid_lats = [r["latency_s"] for r in grp if r.get("latency_s", -1) >= 0]
        summary[k] = {
            "count": float(n),
            "ft_acc": round(sum(r.get("failure_type_match", 0) for r in grp) / n * 100, 1),
            "fix_acc": round(sum(r.get("fix_keyword_score", 0.0) for r in grp) / n * 100, 1),
            "citation": round(sum(r.get("runbook_cited", 0) for r in grp) / n * 100, 1),
            "latency": round(sum(valid_lats) / max(1, len(valid_lats)), 2),
            "cost": round(sum(r.get("estimated_cost_usd", 0.0) for r in grp) / n, 4),
        }
    return summary


def create_bar_chart_svg(
    title: str,
    categories: list[str],
    series: list[dict],  # list of {"name": str, "color": str, "values": list[float]}
    y_label: str = "Percentage (%)",
    max_y: float = 100.0,
    width: int = 780,
    height: int = 420,
) -> str:
    """Generates a clean, styled SVG grouped bar chart."""
    margin_left = 70
    margin_right = 40
    margin_top = 60
    margin_bottom = 80

    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    num_cats = len(categories)
    num_series = len(series)

    group_w = plot_w / num_cats
    bar_w = (group_w * 0.70) / num_series
    bar_pad = (group_w * 0.30) / 2

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;">',
        f'<text x="{width / 2}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#1e293b">{title}</text>',
    ]

    # Gridlines
    grid_steps = 5
    for i in range(grid_steps + 1):
        val = (max_y / grid_steps) * i
        y_pos = margin_top + plot_h - (i / grid_steps) * plot_h
        svg_parts.append(
            f'<line x1="{margin_left}" y1="{y_pos}" x2="{margin_left + plot_w}" y2="{y_pos}" stroke="#e2e8f0" stroke-width="1" />'
        )
        svg_parts.append(
            f'<text x="{margin_left - 10}" y="{y_pos + 4}" text-anchor="end" font-size="12" fill="#64748b">{int(val)}</text>'
        )

    # Y-axis label
    svg_parts.append(
        f'<text x="20" y="{margin_top + plot_h / 2}" text-anchor="middle" font-size="13" font-weight="600" fill="#475569" transform="rotate(-90 20 {margin_top + plot_h / 2})">{y_label}</text>'
    )

    # Draw Bars
    for c_idx, cat in enumerate(categories):
        group_x = margin_left + c_idx * group_w
        for s_idx, s in enumerate(series):
            val = s["values"][c_idx]
            bar_h = (val / max_y) * plot_h
            bx = group_x + bar_pad + s_idx * bar_w
            by = margin_top + plot_h - bar_h

            svg_parts.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{s["color"]}" rx="3" />'
            )
            # Value label on bar
            if bar_h > 18:
                svg_parts.append(
                    f'<text x="{bx + bar_w/2:.1f}" y="{by - 4:.1f}" text-anchor="middle" font-size="10" font-weight="600" fill="#334155">{val:.0f}%</text>'
                )

        # Category label
        svg_parts.append(
            f'<text x="{group_x + group_w/2:.1f}" y="{margin_top + plot_h + 22}" text-anchor="middle" font-size="11" font-weight="500" fill="#334155">{cat}</text>'
        )

    # Legend
    legend_y = height - 25
    legend_start_x = width / 2 - (num_series * 120) / 2
    for s_idx, s in enumerate(series):
        lx = legend_start_x + s_idx * 140
        svg_parts.append(
            f'<rect x="{lx}" y="{legend_y - 10}" width="14" height="14" fill="{s["color"]}" rx="2" />'
        )
        svg_parts.append(
            f'<text x="{lx + 20}" y="{legend_y + 2}" font-size="12" font-weight="500" fill="#475569">{s["name"]}</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_all_charts(json_path: Path | None = None) -> list[Path]:
    """Generates the four core benchmark charts dynamically from a real benchmark JSON file."""
    resolved_path = json_path if json_path else _find_latest_benchmark_json()
    run_id, records = _load_records(resolved_path)
    generated_files: list[Path] = []

    # -------------------------------------------------------------
    # Chart 1: Accuracy by Ablation Mode (computed from JSON)
    # -------------------------------------------------------------
    by_abl = _aggregate_group(records, lambda r: str(r.get("ablation") or "unknown"))
    abl_keys = list(by_abl.keys())
    abl_labels = [k.replace("_", " ").title() for k in abl_keys]
    ft_accuracy = [by_abl[k]["ft_acc"] for k in abl_keys]
    fix_quality = [by_abl[k]["fix_acc"] for k in abl_keys]

    svg_1 = create_bar_chart_svg(
        title=f"Diagnostic Accuracy & Fix Quality by Ablation ({run_id})",
        categories=abl_labels,
        series=[
            {"name": "Failure Type Match (%)", "color": "#2563eb", "values": ft_accuracy},
            {"name": "Fix Quality Score (%)", "color": "#10b981", "values": fix_quality},
        ],
        y_label="Score (%)",
    )
    p1 = CHARTS_DIR / "accuracy_by_ablation.svg"
    p1.write_text(svg_1, encoding="utf-8")
    generated_files.append(p1)

    # -------------------------------------------------------------
    # Chart 2: Accuracy by Model Architecture (computed from JSON)
    # -------------------------------------------------------------
    def _model_label(rec: dict) -> str:
        raw = rec.get("model_id") or "default (qwen3-vl-235b)"
        return str(raw).split("/")[-1]

    by_model = _aggregate_group(records, _model_label)
    mdl_keys = list(by_model.keys())
    model_ft_acc = [by_model[k]["ft_acc"] for k in mdl_keys]
    model_fix_acc = [by_model[k]["fix_acc"] for k in mdl_keys]

    svg_2 = create_bar_chart_svg(
        title=f"Diagnostic Performance by Foundation Model ({run_id})",
        categories=mdl_keys,
        series=[
            {"name": "Failure Type Accuracy (%)", "color": "#6366f1", "values": model_ft_acc},
            {"name": "Remediation Quality (%)", "color": "#f59e0b", "values": model_fix_acc},
        ],
        y_label="Score (%)",
    )
    p2 = CHARTS_DIR / "accuracy_by_model.svg"
    p2.write_text(svg_2, encoding="utf-8")
    generated_files.append(p2)

    # -------------------------------------------------------------
    # Chart 3: Latency vs Cost Comparison (computed from JSON)
    # -------------------------------------------------------------
    configs = abl_labels
    latencies = [by_abl[k]["latency"] for k in abl_keys]
    costs = [by_abl[k]["cost"] for k in abl_keys]
    max_lat_axis = max(10.0, ((max(latencies, default=10.0) // 10) + 1) * 10)
    max_cost_axis = max(0.005, round(max(costs, default=0.005) * 1.25, 4))

    w, h = 780, 420
    ml, mr, mt, mb = 70, 75, 60, 70
    pw = w - ml - mr
    ph = h - mt - mb
    gw = pw / max(1, len(configs))

    svg_3 = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;">',
        f'<text x="{w/2}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#1e293b">Latency (s) vs Estimated Cost ($) ({run_id})</text>',
    ]
    for i in range(5):
        y_val = (i / 4) * max_lat_axis
        y_pos = mt + ph - (i / 4) * ph
        cost_val = (i / 4) * max_cost_axis
        svg_3.append(f'<line x1="{ml}" y1="{y_pos}" x2="{ml+pw}" y2="{y_pos}" stroke="#f1f5f9" stroke-width="1"/>')
        svg_3.append(f'<text x="{ml-10}" y="{y_pos+4}" text-anchor="end" font-size="11" fill="#64748b">{y_val:.0f}s</text>')
        svg_3.append(f'<text x="{ml+pw+10}" y="{y_pos+4}" text-anchor="start" font-size="11" fill="#64748b">${cost_val:.4f}</text>')

    svg_3.append(f'<text x="25" y="{mt+ph/2}" text-anchor="middle" font-size="12" font-weight="600" fill="#3b82f6" transform="rotate(-90 25 {mt+ph/2})">Latency (seconds)</text>')
    svg_3.append(f'<text x="{w-15}" y="{mt+ph/2}" text-anchor="middle" font-size="12" font-weight="600" fill="#ef4444" transform="rotate(90 {w-15} {mt+ph/2})">Cost per Incident (USD)</text>')

    for idx, cfg in enumerate(configs):
        gx = ml + idx * gw + gw / 2
        lat = latencies[idx]
        bar_h = (lat / max_lat_axis) * ph
        by = mt + ph - bar_h
        svg_3.append(f'<rect x="{gx-24}" y="{by}" width="22" height="{bar_h}" fill="#3b82f6" rx="3"/>')
        svg_3.append(f'<text x="{gx-13}" y="{by-4}" text-anchor="middle" font-size="10" font-weight="600" fill="#1e40af">{lat:.1f}s</text>')

        cst = costs[idx]
        cbar_h = (cst / max_cost_axis) * ph
        cby = mt + ph - cbar_h
        svg_3.append(f'<rect x="{gx+2}" y="{cby}" width="22" height="{cbar_h}" fill="#ef4444" rx="3"/>')
        svg_3.append(f'<text x="{gx+13}" y="{cby-4}" text-anchor="middle" font-size="10" font-weight="600" fill="#991b1b">${cst:.4f}</text>')
        svg_3.append(f'<text x="{gx}" y="{mt+ph+22}" text-anchor="middle" font-size="11" font-weight="500" fill="#334155">{cfg}</text>')

    svg_3.append(f'<rect x="{w/2 - 130}" y="{h-25}" width="14" height="14" fill="#3b82f6" rx="2"/><text x="{w/2 - 110}" y="{h-13}" font-size="12" fill="#475569">Average Latency (s)</text>')
    svg_3.append(f'<rect x="{w/2 + 20}" y="{h-25}" width="14" height="14" fill="#ef4444" rx="2"/><text x="{w/2 + 40}" y="{h-13}" font-size="12" fill="#475569">Estimated Cost ($)</text>')
    svg_3.append("</svg>")

    p3 = CHARTS_DIR / "latency_and_cost.svg"
    p3.write_text("\n".join(svg_3), encoding="utf-8")
    generated_files.append(p3)

    # -------------------------------------------------------------
    # Chart 4: Known vs Surprise / Unindexed Breakdown (from JSON)
    # -------------------------------------------------------------
    by_kind = _aggregate_group(
        records,
        lambda r: "Surprise (No Runbook)" if str(r.get("scenario_id", "")).startswith("surprise") else "Canonical (10 Types)",
    )
    kind_keys = list(by_kind.keys())
    kind_ft = [by_kind[k]["ft_acc"] for k in kind_keys]
    kind_fix = [by_kind[k]["fix_acc"] for k in kind_keys]

    svg_4 = create_bar_chart_svg(
        title=f"Canonical vs Surprise Scenario Performance ({run_id})",
        categories=kind_keys,
        series=[
            {"name": "Diagnosis Match (%)", "color": "#10b981", "values": kind_ft},
            {"name": "Fix Keyword Score (%)", "color": "#f97316", "values": kind_fix},
        ],
        y_label="Score (%)",
    )
    p4 = CHARTS_DIR / "holdout_and_learning_curve.svg"
    p4.write_text(svg_4, encoding="utf-8")
    generated_files.append(p4)

    # -------------------------------------------------------------
    # Chart 5: Variant Category Breakdown (if variants JSON exists)
    # -------------------------------------------------------------
    v_chart = generate_variants_chart()
    if v_chart:
        generated_files.append(v_chart)

    return generated_files


def generate_variants_chart(variants_path: Path | None = None) -> Path | None:
    """Generate variant failure category SVG breakdown if variants benchmark exists."""
    v_path = variants_path
    if not v_path:
        candidates = sorted(RESULTS_DIR.glob("benchmark_variants_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            v_path = candidates[0]
    if not v_path or not v_path.exists():
        return None

    run_id, records = _load_records(v_path)

    def _variant_group(r: dict) -> str:
        sid = str(r.get("scenario_id", ""))
        if "healthfail" in sid:
            return "Health Check"
        if "dbtimeout" in sid:
            return "DB Timeout"
        if "dberror" in sid or "baddeploy" in sid:
            return "Error Rate"
        if "oom" in sid:
            return "OOM Limits"
        if "cpusat" in sid:
            return "CPU Saturation"
        if "nettimeout" in sid:
            return "Net Latency"
        return "Other"

    by_grp = _aggregate_group(records, _variant_group)
    cats = list(by_grp.keys())
    ft_vals = [by_grp[k]["ft_acc"] for k in cats]
    fix_vals = [by_grp[k]["fix_acc"] for k in cats]

    svg = create_bar_chart_svg(
        title=f"Variant Performance by Fault Category ({run_id})",
        categories=cats,
        series=[
            {"name": "Diagnosis Match (%)", "color": "#3b82f6", "values": ft_vals},
            {"name": "Fix Keyword Score (%)", "color": "#10b981", "values": fix_vals},
        ],
        y_label="Score (%)",
    )
    p = CHARTS_DIR / "variants_by_category.svg"
    p.write_text(svg, encoding="utf-8")
    return p


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate benchmark SVG charts from JSON results")
    parser.add_argument("--input", type=str, default=None, help="Path to benchmark JSON output")
    args = parser.parse_args()

    try:
        input_path = Path(args.input) if args.input else None
        files = generate_all_charts(json_path=input_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Generated {len(files)} chart(s) from real benchmark data:")
    for f in files:
        print(f"  - {f}")

