"""Evaluate the trained session engagement model on real session data."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import joblib
import numpy as np
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.scoring import FEATURE_NAMES, MODEL_PATH  # noqa: E402
from scripts.train_model import load_training_rows  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI flags."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Only evaluate the most recent N sessions.")
    parser.add_argument("--days", type=int, default=None, help="Only evaluate sessions from the last N days.")
    parser.add_argument(
        "--min-sessions",
        type=int,
        default=20,
        help="Require at least this many sessions before evaluation.",
    )
    return parser.parse_args()


def _format_float(value: float) -> str:
    """Format floating values for terminal output."""
    return f"{value:.3f}"


def _print_cluster_summary(
    cluster_id: int,
    segment: int,
    raw_features: np.ndarray,
) -> None:
    """Print one cluster summary block."""
    session_count = raw_features.shape[0]
    averages = raw_features.mean(axis=0)
    print(f"Cluster {cluster_id} -> Segment {segment}")
    print(f"  Sessions: {session_count}")
    for feature_name, avg_value in zip(FEATURE_NAMES, averages, strict=True):
        print(f"  Avg {feature_name}: {_format_float(float(avg_value))}")


def main() -> int:
    """Load the saved model, score the available sessions, and print quality metrics."""
    args = parse_args()

    if not MODEL_PATH.exists():
        print(f"Model file not found: {MODEL_PATH}", file=sys.stderr)
        print("Train the model first with `python scripts/train_model.py`.", file=sys.stderr)
        return 1

    feature_matrix, used_sessions = load_training_rows(limit=args.limit, days=args.days)
    if used_sessions < args.min_sessions:
        print(
            f"Not enough sessions to evaluate model: found {used_sessions}, need at least {args.min_sessions}.",
            file=sys.stderr,
        )
        return 1

    payload = joblib.load(MODEL_PATH)
    model = payload["model"]
    scaler = payload.get("scaler")
    cluster_to_segment: dict[int, int] = payload["cluster_to_segment"]

    scaled_matrix = scaler.transform(feature_matrix) if scaler is not None else feature_matrix
    cluster_labels = np.asarray(model.predict(scaled_matrix), dtype=int)
    segment_labels = np.asarray([cluster_to_segment[int(cluster)] for cluster in cluster_labels], dtype=int)

    print(f"Evaluated sessions: {used_sessions}")
    print(f"Model file: {MODEL_PATH}")
    print(f"Feature set: {', '.join(FEATURE_NAMES)}")
    print()

    unique_clusters = np.unique(cluster_labels)
    if len(unique_clusters) > 1 and used_sessions > len(unique_clusters):
        print(f"Silhouette score: {_format_float(float(silhouette_score(scaled_matrix, cluster_labels)))}")
        print(f"Davies-Bouldin score: {_format_float(float(davies_bouldin_score(scaled_matrix, cluster_labels)))}")
        print(
            "Calinski-Harabasz score: "
            f"{_format_float(float(calinski_harabasz_score(scaled_matrix, cluster_labels)))}"
        )
    else:
        print("Not enough cluster separation to compute clustering metrics.")

    print()
    print("Cluster summaries")
    for cluster_id in sorted(unique_clusters):
        segment = cluster_to_segment[int(cluster_id)]
        cluster_rows = feature_matrix[cluster_labels == cluster_id]
        _print_cluster_summary(int(cluster_id), int(segment), cluster_rows)
        print()

    print("Segment distribution")
    for segment in sorted(np.unique(segment_labels)):
        count = int(np.sum(segment_labels == segment))
        share = (count / used_sessions) * 100.0
        print(f"  Segment {segment}: {count} sessions ({share:.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
