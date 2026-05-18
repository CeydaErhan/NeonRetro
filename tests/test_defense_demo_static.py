from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class DefenseDemoStaticTests(unittest.TestCase):
    def test_bootstrap_script_runs_full_ml_demo_sequence(self):
        script_path = ROOT / "scripts" / "bootstrap_defense_demo.sh"
        self.assertTrue(script_path.exists())
        script = read("scripts/bootstrap_defense_demo.sh")

        self.assertIn("seed_defense_demo.py --reset-demo", script)
        self.assertIn("seed_ml_demo_sessions.py --reset-demo", script)
        self.assertIn("train_model.py --min-sessions", script)
        self.assertIn("run_defense_checks.sh", script)
        self.assertIn("Docker is not available", script)

    def test_defense_checks_reject_fallback_placement(self):
        script_path = ROOT / "scripts" / "run_defense_checks.sh"
        self.assertTrue(script_path.exists())
        script = read("scripts/run_defense_checks.sh")

        self.assertIn("ml:kmeans_segment_placement", script)
        self.assertIn("fallback", script)
        self.assertIn("low_engagement_session_id", script)
        self.assertIn("medium_engagement_session_id", script)
        self.assertIn("high_intent_session_id", script)

    def test_dashboard_has_defense_demo_page_and_model_warning(self):
        page = read("Senior-Project-Website_Add_Optimizer/frontend/src/pages/DefenseDemo.jsx")
        app = read("Senior-Project-Website_Add_Optimizer/frontend/src/App.jsx")
        sidebar = read("Senior-Project-Website_Add_Optimizer/frontend/src/components/Sidebar.jsx")

        self.assertIn("ML Decision Demo", page)
        self.assertIn("Visitor Behavior", page)
        self.assertIn("Feature Extraction", page)
        self.assertIn("KMeans Model", page)
        self.assertIn("Ad Decision", page)
        self.assertIn("Run Casual Visitor Scenario", page)
        self.assertIn("Run Interested Visitor Scenario", page)
        self.assertIn("Run High Intent Visitor Scenario", page)
        self.assertIn("ML model is missing. Demo is in fallback mode.", page)
        self.assertIn("price_stddev", page)
        self.assertIn("beauty_ratio", page)
        self.assertIn("books_ratio", page)
        self.assertIn("sports_ratio", page)
        self.assertIn("ML Algorithm: KMeans Clustering", page)
        self.assertIn("Input: 15 visitor behavior features", page)
        self.assertIn("Preprocessing: StandardScaler", page)
        self.assertIn("Output: low / medium / high engagement segment", page)
        self.assertIn("Business action: segment-aware ad ranking strategy", page)
        self.assertIn("Why this segment?", page)
        self.assertIn("Explicit purchase signals can calibrate a medium behavioral cluster into high commercial intent", page)
        self.assertIn("Calibration Applied", page)
        self.assertIn("KMeans Cluster Segment", page)
        self.assertIn("low activity", page)
        self.assertIn("moderate browsing", page)
        self.assertIn("stronger click/product signals", page)
        self.assertIn("Marketing Meaning", page)
        self.assertIn("/defense-demo", app)
        self.assertIn("Defense Demo", sidebar)

    def test_ml_metadata_artifact_documents_defense_model(self):
        metadata_path = ROOT / "Senior-Project-Website_Add_Optimizer" / "backend" / "ml" / "model_metadata.json"
        self.assertTrue(metadata_path.exists())
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(metadata["algorithm"], "KMeans")
        self.assertEqual(metadata["n_clusters"], 3)
        self.assertEqual(metadata["scaler"], "StandardScaler")
        self.assertEqual(metadata["feature_count"], 15)
        self.assertEqual(len(metadata["feature_names"]), 15)
        self.assertEqual(
            metadata["segment_strategy_mapping"],
            {
                "low": "least_exposed_ads",
                "medium": "impression_popularity",
                "high": "ctr_performance",
            },
        )
        self.assertIn("silhouette_score", metadata)

    def test_existing_dashboard_manual_demo_shows_missing_model_warning_and_all_features(self):
        dashboard = read("Senior-Project-Website_Add_Optimizer/frontend/src/pages/Dashboard.jsx")

        self.assertIn("ML model is missing. Demo is in fallback mode.", dashboard)
        self.assertIn("price_stddev", dashboard)
        self.assertIn("beauty_ratio", dashboard)
        self.assertIn("books_ratio", dashboard)
        self.assertIn("sports_ratio", dashboard)

    def test_tracking_failures_are_visible_in_demo_mode(self):
        tracker = read("frontend/tracker.js")

        self.assertIn("NEON_TRACKING_DEBUG", tracker)
        self.assertIn("NeonRetro tracking failed", tracker)


if __name__ == "__main__":
    unittest.main()
