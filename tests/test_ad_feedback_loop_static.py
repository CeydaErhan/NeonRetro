from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class AdFeedbackLoopStaticTests(unittest.TestCase):
    def test_placement_response_creates_impression_for_valid_session(self):
        ads_router = read("Senior-Project-Website_Add_Optimizer/backend/app/routers/ads.py")
        schemas = read("Senior-Project-Website_Add_Optimizer/backend/app/schemas.py")
        storefront_home = read("frontend/index.html")

        self.assertIn("def _create_impression", ads_router)
        self.assertIn("Impression(ad_id=ad.id, session_id=session.id, clicked=False)", ads_router)
        self.assertIn("impression_id = _create_impression(db, ad, session)", ads_router)
        self.assertIn("impression_id: int | None = None", schemas)
        self.assertIn("activeCampaignPlacement = placement", storefront_home)
        self.assertIn("activeCampaignPlacement?.impression_id", storefront_home)

    def test_ad_click_endpoint_marks_existing_impression_clicked(self):
        ads_router = read("Senior-Project-Website_Add_Optimizer/backend/app/routers/ads.py")
        storefront_home = read("frontend/index.html")

        self.assertIn('@router.post("/impressions/{impression_id}/click")', ads_router)
        self.assertIn("Session does not match impression", ads_router)
        self.assertIn("impression.clicked = True", ads_router)
        self.assertIn("impression.click_time = datetime.utcnow()", ads_router)
        self.assertIn("/ads/impressions/${activeCampaignPlacement.impression_id}/click", storefront_home)
        self.assertIn("body: JSON.stringify({ session_id: sessionId })", storefront_home)

    def test_analytics_calculates_feedback_metrics_from_impressions(self):
        analytics = read("Senior-Project-Website_Add_Optimizer/backend/app/routers/analytics.py")
        dashboard = read("Senior-Project-Website_Add_Optimizer/frontend/src/pages/Dashboard.jsx")

        self.assertIn("impression_total = db.scalar(select(func.count(Impression.id)))", analytics)
        self.assertIn("click_total = db.scalar(select(func.count(Impression.id)).where(Impression.clicked.is_(True)))", analytics)
        self.assertIn("ctr = (clicks / impressions) if impressions else 0.0", analytics)
        self.assertIn("Total Impressions", dashboard)
        self.assertIn("Avg CTR", dashboard)

    def test_segment_ranking_uses_impression_and_ctr_metrics(self):
        ads_router = read("Senior-Project-Website_Add_Optimizer/backend/app/routers/ads.py")
        recommendation = read("Senior-Project-Website_Add_Optimizer/backend/ml/recommendation.py")

        self.assertIn("impressions_count = func.count(Impression.id)", ads_router)
        self.assertIn("clicks_count = func.sum(case((Impression.clicked.is_(True), 1), else_=0))", ads_router)
        self.assertIn("ctr_value = func.coalesce", ads_router)
        self.assertIn("return stmt.order_by(desc(impressions_count), Campaign.id.desc(), Ad.id.desc())", ads_router)
        self.assertIn("return stmt.order_by(desc(ctr_value), desc(clicks_count), desc(impressions_count), Ad.id.desc())", ads_router)
        self.assertIn("stmt = stmt.order_by(desc(impressions_count), Ad.id.desc())", recommendation)
        self.assertIn("stmt = stmt.order_by(desc(ctr_value), desc(clicks_count), desc(impressions_count), Ad.id.desc())", recommendation)

    def test_recommendations_endpoint_does_not_create_impressions(self):
        recommendations_router = read("Senior-Project-Website_Add_Optimizer/backend/app/routers/recommendations.py")
        list_recommendations_block = recommendations_router[
            recommendations_router.index("@router.get(\"\")"):
            recommendations_router.index("@router.get(\"/defense-demo/status\")")
        ]

        self.assertIn("recommended_ads = get_segment_recommendations", list_recommendations_block)
        self.assertNotIn("_create_impression", list_recommendations_block)
        self.assertNotIn("Impression(", list_recommendations_block)


if __name__ == "__main__":
    unittest.main()
