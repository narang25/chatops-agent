"""
LogHub Public Log Evaluation (Expansion B).
============================================

Evaluates the Drain3 log-pattern miner used in ChatOps (`mcp_servers.prometheus.server`)
on external public benchmark logs from LogHub (logpai/loghub) to demonstrate that
log pattern grouping generalizes to third-party distributed system logs (HDFS)
without domain-specific tuning or reliance on our synthetic microservice stack.

Usage:
  python -m agent.eval.eval_loghub
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.prometheus.server import _extract_log_patterns

RESULTS_DIR = PROJECT_ROOT / "agent" / "eval" / "results"
DEFAULT_LOG_PATH = PROJECT_ROOT / "data" / "external" / "loghub" / "HDFS_2k.log"


def evaluate_loghub(log_file: Path) -> dict:
    if not log_file.exists():
        raise FileNotFoundError(f"Log file not found: {log_file}")

    print(f"Reading public LogHub dataset: {log_file}")
    with open(log_file, encoding="utf-8", errors="replace") as f:
        raw_lines = [line.strip() for line in f if line.strip()]

    total_lines = len(raw_lines)
    log_dicts = [{"message": line, "timestamp": ""} for line in raw_lines]

    t0 = time.perf_counter()
    patterns_map = _extract_log_patterns(log_dicts)
    elapsed_s = time.perf_counter() - t0

    sorted_patterns = sorted(patterns_map.values(), key=lambda p: p["count"], reverse=True)
    num_templates = len(sorted_patterns)
    compression_ratio = round((1.0 - (num_templates / max(1, total_lines))) * 100.0, 2)

    result = {
        "dataset": log_file.stem,
        "source": "LogHub (logpai/loghub)",
        "file_path": str(log_file),
        "total_log_lines": total_lines,
        "distinct_templates_mined": num_templates,
        "compression_ratio_pct": compression_ratio,
        "mining_latency_s": round(elapsed_s, 3),
        "lines_per_second": round(total_lines / max(0.001, elapsed_s), 1),
        "top_patterns": [
            {
                "pattern": p["pattern"],
                "count": p["count"],
                "percentage": round((p["count"] / total_lines) * 100.0, 1),
                "sample": p["sample"][:120],
            }
            for p in sorted_patterns[:10]
        ],
    }

    # Save output artifact
    out_json = RESULTS_DIR / "loghub_eval.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("\n" + "=" * 70)
    print("LogHub Drain3 Log Clustering Results")
    print("=" * 70)
    print(f"Dataset:            {result['dataset']} ({result['source']})")
    print(f"Total Lines:        {total_lines:,}")
    print(f"Mined Templates:    {num_templates}")
    print(f"Compression Ratio:  {compression_ratio}%")
    print(f"Mining Latency:     {elapsed_s:.3f}s ({result['lines_per_second']} lines/sec)")
    print("\nTop 5 Discovered Templates:")
    for idx, p in enumerate(result["top_patterns"][:5], 1):
        print(f"  {idx}. [Count: {p['count']:>4} ({p['percentage']:>4.1f}%)] {p['pattern']}")
    print("=" * 70)
    print(f"Saved evaluation artifact to: {out_json}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Drain3 log template miner on public LogHub data")
    parser.add_argument("--log-path", type=str, default=str(DEFAULT_LOG_PATH), help="Path to raw log file")
    args = parser.parse_args()

    evaluate_loghub(Path(args.log_path))
