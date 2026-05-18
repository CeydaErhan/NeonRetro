# Codex Audit: NeonRetro Defense Demo

Date: 2026-05-18

Scope: inspect and run only. No refactors or feature changes were made.

## Executive Summary

The repository already contains a real ML path for the defense story: a persisted `sklearn.cluster.KMeans` session segmentation model in `Senior-Project-Website_Add_Optimizer/backend/ml/scoring.py`, used by the public storefront ad placement endpoint `GET /ads/placement`.

However, the checkout is not currently defense-ready on this Mac without setup work:

- No `backend/ml/model.pkl` is present, so `/ads/placement` will use fallback placement with `fallback:model_missing`.
- No `backend/ml/product_ranker.pkl` is present, so product suggestions fall back to heuristic preference scoring.
- Docker is not available in this environment.
- Host backend dependencies are not installed, and `psycopg2-binary==2.9.10` fails a dry-run install under the active Python 3.14 pip environment because `pg_config` is missing.
- Dashboard `node_modules` is missing, so the Vite build cannot run.
- The static storefront serves locally, but it cannot actually create sessions/events unless the backend is running at `http://localhost:10000` or the deployed backend is reachable.

## 1. Where the ML Algorithm Is Implemented

Primary ML implementation:

- `Senior-Project-Website_Add_Optimizer/backend/ml/scoring.py`
  - Defines `MODEL_PATH = backend/ml/model.pkl`.
  - Defines the feature list.
  - Trains `KMeans(n_clusters=3, random_state=42, n_init=10)` with `StandardScaler`.
  - Persists a joblib payload containing model, scaler, feature names, cluster-to-segment mapping, and metadata.
  - Performs inference in `score_session(...)`.

Ad recommendation/placement helpers:

- `Senior-Project-Website_Add_Optimizer/backend/ml/recommendation.py`
  - Orders ads by segment-specific strategy.

Route integration:

- `Senior-Project-Website_Add_Optimizer/backend/app/routers/ads.py`
  - Public storefront placement endpoint: `GET /ads/placement`.
- `Senior-Project-Website_Add_Optimizer/backend/app/routers/recommendations.py`
  - Authenticated ad recommendation endpoint: `GET /recommendations`.
  - Public product suggestion endpoints.

Secondary optional product ranker:

- `Senior-Project-Website_Add_Optimizer/backend/ml/product_ranker.py`
  - Optional supervised product ranker using a persisted `product_ranker.pkl`.
  - Trained by `backend/scripts/train_product_ranker.py` with `LogisticRegression`.
  - This is separate from the KMeans ad-placement story.

## 2. Real KMeans Inference or Fallback Logic

It is real KMeans inference when `backend/ml/model.pkl` exists.

The KMeans inference path:

1. Build session features from `visitor_sessions` and `events`.
2. Load `model.pkl`.
3. Apply the saved `StandardScaler`.
4. Call `model.predict(...)`.
5. Map raw cluster id to stable segment `0`, `1`, or `2`.

Important fallback behavior:

- `score_session(...)` itself calls `_load_or_train_model()`. If `model.pkl` is missing, that helper trains and writes a synthetic fallback KMeans model.
- `GET /ads/placement` does **not** call `score_session(...)` when `model.pkl` is missing. It explicitly checks `MODEL_PATH.exists()` and returns fallback placement with `fallback:model_missing`.
- `GET /recommendations` calls `score_session(...)` directly. If dependencies and DB are running but `model.pkl` is missing, this endpoint can create a synthetic fallback model.
- `public-suggested-products` uses `product_ranker.pkl` only if that artifact exists. If missing, it falls back to rule-based preference scoring.

Current artifact status from this checkout:

```text
backend/ml/model.pkl: missing
backend/ml/product_ranker.pkl: missing
```

So the defense-critical `/ads/placement` path is currently fallback-only until `model.pkl` is generated.

## 3. How the Model Is Trained/Generated

Canonical KMeans trainer:

- `Senior-Project-Website_Add_Optimizer/backend/scripts/train_model.py`

Training flow:

1. Load `VisitorSession` rows with related `Event` rows.
2. Extract one feature row per session.
3. Require at least `--min-sessions` rows, default `50`.
4. Fit `StandardScaler`.
5. Fit `KMeans(n_clusters=3, random_state=42, n_init=10)`.
6. Inverse-transform cluster centers.
7. Rank clusters by engagement score.
8. Save joblib artifact to `backend/ml/model.pkl`.

Demo data generators:

- `backend/scripts/seed_defense_demo.py`
  - Creates admin user, campaigns, ads, impressions/click history, and low/medium/high demo sessions.
- `backend/scripts/seed_ml_demo_sessions.py`
  - Creates balanced low/medium/high session event histories for ML training.

Fallback synthetic model:

- `ml/scoring.py` can generate 500 synthetic low/medium/high engagement rows if `score_session(...)` is called without a saved model.
- This is useful as a fallback, but for defense it is weaker than explicitly showing a trained artifact generated from seeded or real sessions.

Optional product ranker:

- `backend/scripts/train_product_ranker.py`
  - Builds session-product examples from tracked interactions.
  - Uses `DictVectorizer` plus `LogisticRegression`.
  - Saves `backend/ml/product_ranker.pkl`.

## 4. Features Used for Prediction

KMeans session segmentation features, in order:

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

The backend derives these in `recommendations._derive_session_ml_features(...)` and `scripts/train_model.extract_session_features(...)`.

Optional product ranker features:

- Candidate product category, brand, price, discount, rating, sales count.
- Session top category, average/min/max price.
- Price delta ratio.
- Category match and price-range match booleans.
- Brand/color/size/storage/skin-type preference weights.
- Session seen product count and category diversity.

## 5. Which Endpoint Uses the ML Output

Primary defense endpoint:

- `GET /ads/placement?page=<page>&session_id=<id>`
  - Public endpoint used by the storefront.
  - If `model.pkl` exists and session is valid, returns ML explanation fields:
    - `segment`
    - `segment_label`
    - `ranking_strategy`
    - `model_version`
    - `explanation`
    - `features_used`
    - `decision_reason`
    - `candidate_count`
  - Records an `impressions` row when a valid session is available.

Secondary endpoint:

- `GET /recommendations?session_id=<id>`
  - Authenticated endpoint.
  - Scores session and returns a list of ML-ranked ads with model metadata.

Product suggestion endpoints:

- `GET /recommendations/public-suggested-products`
- `GET /recommendations/suggested-products`

These do not use the KMeans ad segment directly. They use the optional product ranker artifact if available; otherwise they use heuristic preference scoring.

## 6. How Ad Placement/Recommendation Decisions Are Made

For `GET /ads/placement`:

1. Normalize the requested `page`.
2. If no session is provided, use fallback.
3. If session is not found, use fallback.
4. If `model.pkl` is missing, use fallback.
5. Otherwise:
   - Load events for the session.
   - Derive ML features.
   - Score KMeans segment.
   - Query active campaigns and ads eligible for the page or `all`.
   - Sort candidates by the segment strategy.
   - Return the top ad and create an impression.

Segment strategies for `/ads/placement`:

- Segment `0` / low: `least_exposed_ads`
  - Sort by lowest impression count, then newest campaign/ad.
- Segment `1` / medium: `impression_popularity`
  - Sort by highest impression count.
- Segment `2` / high: `ctr_performance`
  - Sort by highest CTR, then clicks, then impressions.

Fallback strategy:

- `least_exposed_ads`.
- Used for no session, session not found, missing model, scoring failure, or no ML ad.

There is a small naming difference in `GET /recommendations`:

- Segment `0` is labeled `newest_ads` there.
- In `/ads/placement`, segment `0` is `least_exposed_ads`.

For defense, prefer `/ads/placement` because it is public, used by the storefront, records impressions, and returns explanation fields.

## 7. Whether Storefront Tracking Actually Creates Sessions/Events

Yes, when the backend is reachable.

Storefront tracking implementation:

- `frontend/tracker.js` chooses backend base URL:
  - localhost storefront -> `http://localhost:10000`
  - otherwise -> deployed Render backend
- On first tracked action/page load:
  - Calls `POST /visitor-sessions`.
  - Stores numeric backend session ID in `localStorage` key `neonretro_tracking_session_id`.
- Page views:
  - `trackPageview(...)` sends `type: "page_view"` to `POST /events/track`.
- Clicks:
  - Elements with `data-track` are tracked.
  - Product pages and catalog pages send richer metadata through `tracker.track(...)`.

Backend storage:

- `POST /visitor-sessions` creates a `VisitorSession`.
- `POST /events/track` creates an `Event`.
- Product fields are stored in the `events.metadata` JSON column, not in separate columns.

Important current caveat:

- Tracking failures are swallowed with `.catch(() => {})`.
- If the backend is down, the storefront still loads but silently creates no backend sessions/events.
- The current code uses `localStorage` for tracking session ID. This differs from the AGENTS.md note that says session ID is in-memory only.

Local verification in this environment:

- Static storefront served successfully at `http://127.0.0.1:8000/index.html`.
- Backend at `http://127.0.0.1:10000/` returned no response because it was not running.
- Therefore, local storefront tracking could not create sessions/events in this environment.

## 8. Whether Dashboard Can Show ML Decisions

Yes, partially.

Dashboard support:

- `Senior-Project-Website_Add_Optimizer/frontend/src/pages/Dashboard.jsx` contains an "ML Placement Demo" card.
- It accepts page and session ID.
- It calls `GET /ads/placement`.
- It displays:
  - selected ad preview
  - segment
  - segment label
  - ranking strategy
  - model version
  - explanation
  - decision reason
  - candidate count
  - fallback reason
  - impression ID
  - a feature table

Limitations:

- It is a manual demo card, not a historical ML decision log.
- The feature table omits some KMeans features currently returned by the backend:
  - `price_stddev`
  - `beauty_ratio`
  - `books_ratio`
  - `sports_ratio`
- The dashboard only works after dependencies are installed and backend auth/data are available.

## 9. What Is Currently Broken on macOS Local Run

Commands run from this checkout:

```text
python3 --version
python3 -c "import fastapi, sqlalchemy, sklearn, joblib, psycopg2"
python3 -c "from app.main import app; print(app.title)"
python3 scripts/train_model.py --min-sessions 1
python3 -m pip install --dry-run -r requirements.txt
python3 -m http.server 8000 --bind 127.0.0.1
curl -I http://127.0.0.1:8000/index.html
curl http://127.0.0.1:10000/
curl http://127.0.0.1:5173/
npm run build
docker --version
docker compose version
```

Observed:

- Storefront static server works:
  - `curl -I http://127.0.0.1:8000/index.html` returned `HTTP/1.0 200 OK`.
- Backend is not running:
  - `curl http://127.0.0.1:10000/` returned HTTP code `000`.
- Dashboard is not running:
  - `curl http://127.0.0.1:5173/` returned HTTP code `000`.
- Host Python imports fail:
  - `ModuleNotFoundError: No module named 'fastapi'`
  - `ModuleNotFoundError: No module named 'joblib'`
  - `ModuleNotFoundError: No module named 'numpy'`
- `alembic` is not on PATH.
- `python3 -m pip install --dry-run -r requirements.txt` fails on `psycopg2-binary==2.9.10`:
  - Active pip is under Python 3.14.
  - `psycopg2-binary` attempts a source build.
  - Build fails with `Error: pg_config executable not found`.
- Docker is not available:
  - `zsh: command not found: docker`.
- Dashboard dependencies are missing:
  - `Senior-Project-Website_Add_Optimizer/frontend/node_modules` is missing.
  - `npm run build` fails because `node_modules/vite/bin/vite.js` does not exist.
- The root default backend DB URL is `optimizer_db`, while Docker Compose uses `adoptimizer`.
  - This is fine inside Compose because `DATABASE_URL` is set.
  - Host backend runs need an explicit `DATABASE_URL` if using the Compose database.

## 10. Minimum Changes Needed for a Defense-Ready Demo

These are the minimum changes/setup steps. They are not implemented in this audit.

### Required setup

1. Make local runtime deterministic.
   - Prefer Docker Compose if Docker is available.
   - If running on host macOS, use a Python version with wheels for the pinned dependencies or install PostgreSQL tooling so `pg_config` exists.

2. Ensure backend database starts cleanly.
   - Run migrations.
   - Seed defense data:
     - `python scripts/seed_defense_demo.py --reset-demo`
     - or the documented Docker Compose equivalent.

3. Generate `backend/ml/model.pkl` before the demo.
   - Seed enough sessions.
   - Run `python scripts/train_model.py --min-sessions <n>`.
   - Verify `GET /ads/placement?page=home&session_id=<id>` returns:
     - `explanation: "ml:kmeans_segment_placement"`
     - non-null `segment`
     - non-null `features_used`
     - non-null `model_version`

4. Install dashboard dependencies and verify dashboard build/dev server.
   - `npm install`
   - `npm run build`
   - `npm run dev`

5. Verify storefront-to-backend tracking.
   - Open `http://localhost:8000`.
   - Confirm `POST /visitor-sessions` succeeds.
   - Click product/detail/add-to-cart paths.
   - Confirm `POST /events/track` succeeds.
   - Confirm dashboard Analytics shows the events.

### Minimum code/config fixes likely needed

1. Add a demo bootstrap script or documented one-command sequence that:
   - starts dependencies
   - runs migrations
   - seeds defense data
   - trains `model.pkl`
   - prints demo session IDs

2. Make the ML model state explicit in the dashboard/demo docs.
   - The defense should not accidentally show `fallback:model_missing`.

3. Add the missing dashboard feature rows:
   - `price_stddev`
   - `beauty_ratio`
   - `books_ratio`
   - `sports_ratio`

4. Align or document strategy naming:
   - `/ads/placement` segment `0`: `least_exposed_ads`
   - `/recommendations` segment `0`: `newest_ads`

5. Consider surfacing tracking failures during local demo.
   - Current storefront silently ignores failed tracking POSTs.
   - For defense, a visible debug flag or console warning would make setup issues easier to catch.

6. Decide whether the tracking session should be `localStorage` or in-memory.
   - Current code uses `localStorage`.
   - AGENTS.md says in-memory only.

## Defense-Ready Demo Checklist

- [ ] Docker or host runtime works on the presenting Mac.
- [ ] Backend reachable at `http://localhost:10000/`.
- [ ] Storefront reachable at `http://localhost:8000/`.
- [ ] Dashboard reachable at `http://localhost:5173/`.
- [ ] Admin login works.
- [ ] Defense data seeded.
- [ ] `backend/ml/model.pkl` exists.
- [ ] `/ads/placement` returns `ml:kmeans_segment_placement` for seeded sessions.
- [ ] Storefront product actions create `visitor_sessions` and `events`.
- [ ] Dashboard Analytics shows recent events.
- [ ] Dashboard ML Placement Demo shows segment, ranking strategy, model version, features, and decision reason.

## Files Inspected

- `frontend/tracker.js`
- `frontend/index.html`
- `frontend/product.html`
- `Senior-Project-Website_Add_Optimizer/backend/ml/scoring.py`
- `Senior-Project-Website_Add_Optimizer/backend/ml/recommendation.py`
- `Senior-Project-Website_Add_Optimizer/backend/ml/product_ranker.py`
- `Senior-Project-Website_Add_Optimizer/backend/scripts/train_model.py`
- `Senior-Project-Website_Add_Optimizer/backend/scripts/train_product_ranker.py`
- `Senior-Project-Website_Add_Optimizer/backend/scripts/seed_defense_demo.py`
- `Senior-Project-Website_Add_Optimizer/backend/scripts/seed_ml_demo_sessions.py`
- `Senior-Project-Website_Add_Optimizer/backend/app/routers/ads.py`
- `Senior-Project-Website_Add_Optimizer/backend/app/routers/recommendations.py`
- `Senior-Project-Website_Add_Optimizer/backend/app/routers/events.py`
- `Senior-Project-Website_Add_Optimizer/backend/app/routers/visitor_sessions.py`
- `Senior-Project-Website_Add_Optimizer/backend/app/models.py`
- `Senior-Project-Website_Add_Optimizer/backend/app/schemas.py`
- `Senior-Project-Website_Add_Optimizer/backend/app/database.py`
- `Senior-Project-Website_Add_Optimizer/backend/app/main.py`
- `Senior-Project-Website_Add_Optimizer/frontend/src/pages/Dashboard.jsx`
- `Senior-Project-Website_Add_Optimizer/docker-compose.yml`
- `README.md`
- `LOCAL_DEMO.md`
- `docs/DEMO_SCRIPT.md`
- `docs/TEST_PLAN.md`
