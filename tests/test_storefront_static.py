from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class StorefrontStaticTests(unittest.TestCase):
    def test_featured_products_are_deterministic_and_not_randomized(self):
        home = read("frontend/index.html")

        self.assertNotIn("Math.random", home)
        self.assertIn("function getFeaturedProducts()", home)
        self.assertIn("featured flag first, then rating and sales", home)
        self.assertIn("const featured = getFeaturedProducts();", home)

    def test_catalog_controls_make_filter_state_explicit(self):
        home = read("frontend/index.html")

        self.assertIn('id="active-filter-label"', home)
        self.assertIn('id="reset-catalog-btn"', home)
        self.assertIn("function resetCatalogControls()", home)
        self.assertIn("Showing all products", home)
        self.assertIn("Regular catalog controls", home)

    def test_recommended_for_you_uses_session_recommendation_endpoint(self):
        home = read("frontend/index.html")

        self.assertIn("Recommended for You", home)
        self.assertIn("Based on your browsing behavior and session signals.", home)
        self.assertIn("recommended-products-section", home)
        self.assertIn("recommended-products-track", home)
        self.assertIn("/recommendations/public-suggested-products?session_id=${sessionId}", home)
        self.assertIn("loadRecommendedProducts", home)
        self.assertIn("matched_signals", home)
        self.assertNotIn("ML-ranked products matched to this session", home)

    def test_recommendations_refresh_after_session_behavior(self):
        home = read("frontend/index.html")
        tracker = read("frontend/tracker.js")

        self.assertIn("function trackCategoryInterest", home)
        self.assertIn("loadRecommendedProducts();", home)
        self.assertIn("category_filter", home)
        self.assertIn("return sendEvent", tracker)

    def test_best_seller_sort_has_stable_tie_breakers(self):
        home = read("frontend/index.html")

        self.assertIn("function compareBestSellers", home)
        self.assertIn("salesCount", home)
        self.assertIn("rating", home)
        self.assertIn("name.localeCompare", home)

    def test_search_empty_state_is_useful(self):
        search = read("frontend/search.html")

        self.assertIn("No products matched your search", search)
        self.assertIn("Try a product name, category, or brand", search)
        self.assertIn("Browse all products", search)

    def test_tracker_recovers_from_stale_session_ids(self):
        tracker = read("frontend/tracker.js")
        home = read("frontend/index.html")
        events = read("Senior-Project-Website_Add_Optimizer/backend/app/routers/events.py")

        self.assertIn("clearStoredSessionId", tracker)
        self.assertIn("retryWithFreshSession", tracker)
        self.assertIn("stale_session_recovered", tracker)
        self.assertIn("response.status === 404", tracker)
        self.assertIn("response.status === 422", tracker)
        self.assertIn("tracker.js?v=defense-session-recovery", home)
        self.assertIn("db.get(VisitorSession, payload.session_id)", events)
        self.assertIn('detail="session_not_found"', events)

    def test_public_product_suggestions_have_stable_popular_fallback(self):
        recommendations = read("Senior-Project-Website_Add_Optimizer/backend/app/routers/recommendations.py")

        self.assertIn("def _stable_popular_product_suggestions", recommendations)
        self.assertIn("popular:fallback", recommendations)
        self.assertIn("return _stable_popular_product_suggestions(limit, exclude_viewed, seen_product_ids)", recommendations)


if __name__ == "__main__":
    unittest.main()
