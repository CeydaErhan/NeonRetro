# Senior Project Demo Script

This script is designed for a jury presentation. It shows that NeonRetro is not only a storefront; it is a tracked, ML-backed website and advertisement optimizer.

## Setup

Start the full local stack:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml up -d --build
```

Create the admin user manually if needed:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml exec backend python scripts/create_admin.py admin@example.com StrongPass123
```

Seed deterministic defense data:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml exec backend python scripts/seed_defense_demo.py --reset-demo
```

Record the printed session IDs:

```text
low_engagement_session_id: <id>
medium_engagement_session_id: <id>
high_intent_session_id: <id>
```

Open:

- Storefront: `http://localhost:8000`
- Dashboard: `http://localhost:5173`
- API docs: `http://localhost:10000/docs`

Dashboard login:

- Email: `admin@example.com`
- Password: `StrongPass123`

## Opening Explanation

Describe the system in one sentence:

NeonRetro is a demo e-commerce storefront connected to a FastAPI optimizer that tracks visitor behavior, stores it in PostgreSQL, segments sessions with KMeans, selects ads by segment, suggests products from session preferences, and exposes analytics in a React dashboard.

Important implementation facts:

- `tracker.js` stores a numeric backend session ID in `localStorage` under `neonretro_tracking_session_id`.
- Product behavior is stored in the `events.metadata` JSON column.
- The system uses session features such as page views, clicks, dwell time, unique products, add-to-cart count, attribute selections, price signals, and category ratios.

## Live Storefront Flow

1. Open `http://localhost:8000`.
2. Show product catalog, campaign banner, recently viewed area, and suggested products area.
3. Open a product, select an attribute, and add it to cart.
4. Explain that these actions generate page view, product view, click, attribute, and cart events.
5. Open dashboard Analytics and show recent event rows.

## Low Engagement Scenario

Use `low_engagement_session_id`.

Expected visitor behavior:

- Opens home.
- Opens one product.
- Leaves without cart action.

Expected events:

- `page_view home`
- `click open-product`
- `page_view product`

Expected features:

- low page count
- low click count
- low dwell time
- one product interest
- no add-to-cart

Expected segment:

- `0`, label `low`

Expected ranking strategy:

- `least_exposed_ads`

What to show:

- In dashboard ML Placement Demo, enter page `home` and the low session ID.
- Show `features_used`, `segment_label`, `ranking_strategy`, `decision_reason`, and `candidate_count`.
- Explain that a low-engagement visitor is used to give exposure to under-shown active ads.

## Medium Engagement Scenario

Use `medium_engagement_session_id`.

Expected visitor behavior:

- Browses home and electronics.
- Opens an electronics product.
- Selects one product attribute.
- Browses another category.

Expected events:

- multiple page views
- `open-product`
- `product_view`
- `select-attribute`

Expected features:

- medium page and click counts
- category diversity
- product and attribute preference signals
- no strong purchase intent yet

Expected segment:

- `1`, label `medium`

Expected ranking strategy:

- `impression_popularity`

What to show:

- Run placement demo with the medium session ID.
- Explain that medium visitors receive ads with proven visibility/popularity.

## High Intent Scenario

Use `high_intent_session_id`.

Expected visitor behavior:

- Browses electronics.
- Opens products.
- Selects storage/color attributes.
- Adds products to cart.
- Shows strong purchase intent.

Expected events:

- several page views
- product views
- attribute selections
- `add-to-cart`

Expected features:

- high click count
- high dwell time
- multiple products
- add-to-cart count greater than zero
- stronger price/category preference signals

Expected segment:

- `2`, label `high`

Expected ranking strategy:

- `ctr_performance`

What to show:

- Run placement demo with the high session ID.
- Explain that high-intent visitors get the ad with the strongest click-through performance.
- Show the selected ad and decision fields.

## Product Suggestion Story

On the storefront, product suggestions come from:

```text
/recommendations/public-suggested-products?session_id=<id>
```

The backend first checks for a trained supervised product ranker. If no generated ranker artifact exists, it falls back to preference scoring based on category, price, brand, color, size, storage, and skin type signals from event metadata.

For the jury, explain:

- ad placement optimizes campaign exposure/performance
- product suggestions personalize storefront content
- both are driven by tracked behavior

## API Checks

Use these examples after replacing IDs:

```bash
curl "http://localhost:10000/ads/placement?page=home&session_id=<low_engagement_session_id>"
curl "http://localhost:10000/ads/placement?page=home&session_id=<medium_engagement_session_id>"
curl "http://localhost:10000/ads/placement?page=home&session_id=<high_intent_session_id>"
```

Look for:

- `segment`
- `segment_label`
- `ranking_strategy`
- `features_used`
- `decision_reason`
- `fallback_reason`
- `candidate_count`

## Closing Statement

Close by emphasizing that the project demonstrates an end-to-end optimization loop:

visitor behavior -> tracked events -> database -> session features -> ML segment -> ad/product decision -> analytics dashboard -> explainable demo.
