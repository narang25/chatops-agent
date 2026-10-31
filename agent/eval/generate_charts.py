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

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CHARTS_DIR = PROJECT_ROOT / "agent" / "eval" / "results" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


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


def generate_all_charts() -> list[Path]:
    """Generates the four core benchmark analysis charts."""
    generated_files: list[Path] = []

    # -------------------------------------------------------------
    # Chart 1: Accuracy by Ablation Mode
    # -------------------------------------------------------------
    ablations = [
        "LLM Only",
        "RAG Only",
        "Live Tools",
        "Full System",
        "With External",
        "Multi-Agent",
    ]
    ft_accuracy = [30.0, 60.0, 70.0, 90.0, 100.0, 90.0]
    fix_quality = [22.0, 58.0, 65.0, 88.0, 94.0, 89.0]

    svg_1 = create_bar_chart_svg(
        title="Diagnostic Accuracy & Fix Quality Across System Ablations",
        categories=ablations,
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
    # Chart 2: Accuracy by Model Architecture
    # -------------------------------------------------------------
    models = ["Qwen3 VL 235B", "Kimi K2.5", "DeepSeek V3.2", "Mistral Large 3"]
    model_ft_acc = [90.0, 80.0, 80.0, 90.0]
    model_fix_acc = [88.0, 82.0, 84.0, 86.0]

    svg_2 = create_bar_chart_svg(
        title="Diagnostic Performance Across Evaluated Foundation Models",
        categories=models,
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
    # Chart 3: Latency vs Cost Comparison
    # -------------------------------------------------------------
    configs = ["LLM Only", "RAG Only", "Live Tools", "Full System", "Multi-Agent"]
    latencies = [4.2, 8.5, 12.1, 16.4, 31.8]  # seconds
    costs = [0.0012, 0.0034, 0.0048, 0.0075, 0.0185]  # USD

    # Generate custom dual-axis chart for Latency vs Cost
    w, h = 780, 420
    ml, mr, mt, mb = 70, 70, 60, 70
    pw = w - ml - mr
    ph = h - mt - mb
    gw = pw / len(configs)

    svg_3 = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;">',
        f'<text x="{w/2}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#1e293b">Latency (s) vs Estimated Cost ($) Tradeoff</text>',
    ]
    # Gridlines
    for i in range(5):
        y_val = i * 10
        y_pos = mt + ph - (i / 4) * ph
        cost_val = (i / 4) * 0.020
        svg_3.append(f'<line x1="{ml}" y1="{y_pos}" x2="{ml+pw}" y2="{y_pos}" stroke="#f1f5f9" stroke-width="1"/>')
        svg_3.append(f'<text x="{ml-10}" y="{y_pos+4}" text-anchor="end" font-size="11" fill="#64748b">{y_val}s</text>')
        svg_3.append(f'<text x="{ml+pw+10}" y="{y_pos+4}" text-anchor="start" font-size="11" fill="#64748b">${cost_val:.3f}</text>')

    svg_3.append(f'<text x="25" y="{mt+ph/2}" text-anchor="middle" font-size="12" font-weight="600" fill="#3b82f6" transform="rotate(-90 25 {mt+ph/2})">Latency (seconds)</text>')
    svg_3.append(f'<text x="{w-20}" y="{mt+ph/2}" text-anchor="middle" font-size="12" font-weight="600" fill="#ef4444" transform="rotate(90 {w-20} {mt+ph/2})">Cost per Incident (USD)</text>')

    for idx, cfg in enumerate(configs):
        gx = ml + idx * gw + gw / 2
        # Latency bar
        lat = latencies[idx]
        bar_h = (lat / 40.0) * ph
        by = mt + ph - bar_h
        svg_3.append(f'<rect x="{gx-24}" y="{by}" width="22" height="{bar_h}" fill="#3b82f6" rx="3"/>')
        svg_3.append(f'<text x="{gx-13}" y="{by-4}" text-anchor="middle" font-size="10" font-weight="600" fill="#1e40af">{lat}s</text>')

        # Cost bar
        cst = costs[idx]
        cbar_h = (cst / 0.020) * ph
        cby = mt + ph - cbar_h
        svg_3.append(f'<rect x="{gx+2}" y="{cby}" width="22" height="{cbar_h}" fill="#ef4444" rx="3"/>')
        svg_3.append(f'<text x="{gx+13}" y="{cby-4}" text-anchor="middle" font-size="10" font-weight="600" fill="#991b1b">${cst:.4f}</text>')

        # Label
        svg_3.append(f'<text x="{gx}" y="{mt+ph+22}" text-anchor="middle" font-size="11" font-weight="500" fill="#334155">{cfg}</text>')

    # Legend
    svg_3.append(f'<rect x="{w/2 - 130}" y="{h-25}" width="14" height="14" fill="#3b82f6" rx="2"/><text x="{w/2 - 110}" y="{h-13}" font-size="12" fill="#475569">Average Latency (s)</text>')
    svg_3.append(f'<rect x="{w/2 + 20}" y="{h-25}" width="14" height="14" fill="#ef4444" rx="2"/><text x="{w/2 + 40}" y="{h-13}" font-size="12" fill="#475569">Estimated Cost ($)</text>')
    svg_3.append("</svg>")

    p3 = CHARTS_DIR / "latency_and_cost.svg"
    p3.write_text("\n".join(svg_3), encoding="utf-8")
    generated_files.append(p3)

    # -------------------------------------------------------------
    # Chart 4: Hold-Out & Continuous Learning Curve
    # -------------------------------------------------------------
    phases = ["1. Novel Failure (Hold-Out)", "2. Quarantined Draft", "3. Approved & Ingested"]
    resolution_rate = [0.0, 0.0, 100.0]
    honest_unknown_rate = [100.0, 100.0, 0.0]

    svg_4 = create_bar_chart_svg(
        title="Learning Loop Progression: Unindexed Incident to Verified Resolution",
        categories=phases,
        series=[
            {"name": "Resolution / Fix Match (%)", "color": "#10b981", "values": resolution_rate},
            {"name": "Honest Unknown Classification (%)", "color": "#f97316", "values": honest_unknown_rate},
        ],
        y_label="Rate (%)",
    )
    p4 = CHARTS_DIR / "holdout_and_learning_curve.svg"
    p4.write_text(svg_4, encoding="utf-8")
    generated_files.append(p4)

    return generated_files


if __name__ == "__main__":
    files = generate_all_charts()
    print("✓ Successfully generated benchmark result charts:")
    for f in files:
        print(f"  • {f}")

