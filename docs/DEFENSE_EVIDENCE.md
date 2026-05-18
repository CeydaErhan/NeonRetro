# Defense Evidence

## Primary Defense Story

NeonRetro demonstrates a real ML-backed advertising decision:

```text
Visitor behavior -> Feature extraction -> KMeans clustering -> Engagement segment -> Segment-aware ad placement
```

The main demo should use the dashboard page:

```text
http://localhost:5173/defense-demo
```

Avoid using the manual placement form as the primary flow. The scenario player is deterministic and easier to defend.

## ML Algorithm

The primary model is KMeans clustering:

- Implementation: `Senior-Project-Website_Add_Optimizer/backend/ml/scoring.py`
- Algorithm: `KMeans(n_clusters=3, random_state=42, n_init=10)`
- Preprocessing: `StandardScaler`
- Artifact: `Senior-Project-Website_Add_Optimizer/backend/ml/model.pkl`
- Endpoint using the model: `GET /ads/placement?page=home&session_id=<id>`

Cluster IDs are mapped to stable engagement labels:

- Low
- Medium
- High

The model must be trained before the main defense demo. If the dashboard shows `ML model is missing. Demo is in fallback mode.`, stop and run the bootstrap/check scripts before presenting.

## Features Used

The KMeans model uses these session features:

1. `page_count`
2. `click_count`
3. `dwell_time_seconds`
4. `unique_products`
5. `add_to_cart_count`
6. `attribute_selection_count`
7. `avg_price`
8. `price_stddev`
9. `category_diversity`
10. `electronics_ratio`
11. `clothing_ratio`
12. `beauty_ratio`
13. `home_appliances_ratio`
14. `books_ratio`
15. `sports_ratio`

These are derived from the real `visitor_sessions` and `events` tables. Product behavior lives in `events.metadata`.

## How ML Changes the Business Decision

The business decision is which eligible active ad appears on the storefront.

For the same `home` placement, the segment changes the ranking strategy:

| Segment | Strategy | Business meaning |
|---|---|---|
| Low | `least_exposed_ads` | Give a low-exposure ad a chance for casual visitors. |
| Medium | `impression_popularity` | Show the ad with strongest prior visibility to interested visitors. |
| High | `ctr_performance` | Prioritize the best click-through performer for purchase-intent visitors. |

This is the defense point: the banner is not static. The user behavior changes the segment, and the segment changes the ad selection rule.

## One-Command Docker Demo

From the repo root:

```bash
scripts/bootstrap_defense_demo.sh
```

The bootstrap script:

1. Starts Docker Compose services.
2. Runs backend migrations through the backend container startup command.
3. Seeds defense campaigns, ads, impressions, and scenario sessions.
4. Seeds enough ML demo sessions for training.
5. Trains `backend/ml/model.pkl`.
6. Verifies `/ads/placement` returns `explanation: "ml:kmeans_segment_placement"`.
7. Prints low/medium/high session IDs only as technical backup.

Open:

- Storefront: `http://localhost:8000`
- Backend: `http://localhost:10000`
- Dashboard: `http://localhost:5173`

Dashboard login:

- Email: `admin@example.com`
- Password: `StrongPass123`

## Host macOS Fallback

Use this only if Docker is not available.

Backend:

```bash
cd Senior-Project-Website_Add_Optimizer/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

If `psycopg2-binary` attempts a source build, install PostgreSQL client tooling so `pg_config` is available, or use Python 3.12/3.13 where the pinned wheels are available.

Dashboard:

```bash
cd Senior-Project-Website_Add_Optimizer/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Storefront:

```bash
cd frontend
python3 -m http.server 8000
```

Seed and train:

```bash
cd Senior-Project-Website_Add_Optimizer/backend
python scripts/seed_defense_demo.py --reset-demo
python scripts/seed_ml_demo_sessions.py --reset-demo --sessions-per-segment 20
python scripts/train_model.py --min-sessions 30
```

Then run:

```bash
scripts/run_defense_checks.sh
```

## Required Proof Outputs

Before presenting, this command must pass:

```bash
scripts/run_defense_checks.sh
```

It verifies:

- Backend health.
- Model presence from backend model status.
- Casual, interested, and high-intent scenarios do not return fallback placement.
- Each seeded scenario returns:
  - `explanation: "ml:kmeans_segment_placement"`
  - `segment`
  - `segment_label`
  - `ranking_strategy`
  - `model_version`
  - `features_used`
  - `decision_reason`
  - `candidate_count`
- Low/medium/high scenarios produce distinct segment and strategy outputs.
- Storefront tracking endpoints accept a session and event.
- Dashboard build runs if local `npm` and `node_modules` are available.

## Actual Verification On Defense Mac

Verified on May 18, 2026 with Docker Desktop running:

```text
Docker version 29.4.3, build 055a478
Docker Compose version v5.1.3
```

Bootstrap command from repo root:

```bash
scripts/bootstrap_defense_demo.sh
```

Successful output excerpt:

```text
Defense demo seed complete.

Demo sessions:
  low_engagement_session_id: 396
  medium_engagement_session_id: 397
  high_intent_session_id: 398

Training KMeans model...
Model trained successfully: /app/ml/model.pkl
Sessions used: 65
Feature set: page_count, click_count, dwell_time_seconds, unique_products, add_to_cart_count, attribute_selection_count, avg_price, price_stddev, category_diversity, electronics_ratio, clothing_ratio, beauty_ratio, home_appliances_ratio, books_ratio, sports_ratio
Output file: /app/ml/model.pkl

Running defense checks...
casual: segment=low strategy=least_exposed_ads session=396
interested: segment=medium strategy=impression_popularity session=397
high-intent: segment=high strategy=ctr_performance session=398
Defense checks passed.

Defense demo is ready.
```

Standalone check command:

```bash
scripts/run_defense_checks.sh
```

Successful output:

```text
Checking backend health: http://localhost:10000/
Logging in for protected defense demo endpoints...
casual: segment=low strategy=least_exposed_ads session=396
interested: segment=medium strategy=impression_popularity session=397
high-intent: segment=high strategy=ctr_performance session=398
Checking storefront tracking endpoints...
Technical backup session IDs:
  low_engagement_session_id: 396
  medium_engagement_session_id: 397
  high_intent_session_id: 398
Defense checks passed.
Skipping dashboard build check because npm or node_modules is not available.
```

Dashboard build was verified inside the Docker frontend container:

```text
vite v5.4.21 building for production...
✓ 894 modules transformed.
✓ built in 1.38s
```

Visual browser verification:

- `http://localhost:5173/defense-demo` opens and shows `Real ML model loaded`.
- Casual scenario shows `Low` and `least_exposed_ads`.
- Interested scenario shows `Medium` and `impression_popularity`.
- High intent scenario shows `High` and `ctr_performance`.
- No `fallback:model_missing` text appears in the main demo.
- `http://localhost:8000` opens the NeonRetro storefront.
- `http://localhost:10000/docs` opens Swagger UI and includes `/ads/placement` plus the defense demo endpoints.

## Screenshots to Capture

Capture these for defense backup:

1. Dashboard `Defense Demo` page before running scenarios, showing `Real ML model loaded`.
2. Casual scenario result showing low segment and `least_exposed_ads`.
3. Interested scenario result showing medium segment and `impression_popularity`.
4. High intent scenario result showing high segment and `ctr_performance`.
5. Live Storefront Tracking panel after one storefront click.
6. Terminal output from `scripts/run_defense_checks.sh`.

## Fallback Rules

Fallback is allowed only as an explicit failure state, never as the main demo.

If the dashboard shows:

```text
ML model is missing. Demo is in fallback mode.
```

Then the main demo is not ready. Run:

```bash
scripts/bootstrap_defense_demo.sh
```

or manually seed and train the model, then rerun:

```bash
scripts/run_defense_checks.sh
```

## Naming Consistency

The defense demo uses `/ads/placement`.

For `/ads/placement`, the low segment strategy is:

```text
least_exposed_ads
```

There is a legacy naming difference in the authenticated `/recommendations` endpoint, where low segment is labeled:

```text
newest_ads
```

Use `/ads/placement` terminology in the defense presentation.
