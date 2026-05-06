# ML Pipeline: KMeans Session Segmentation

The primary ML algorithm for the Website & Advertisement Optimizer is KMeans session segmentation. It groups visitor sessions into low, medium, and high engagement segments from tracked session behavior.

## Model

- Algorithm: `KMeans(n_clusters=3, random_state=42, n_init=10)`
- Preprocessing: `StandardScaler`
- Artifact: `backend/ml/model.pkl`
- Artifact status: generated locally and ignored by git
- Canonical trainer: `backend/scripts/train_model.py`

The persisted artifact is a `joblib` payload with:

- `model`: fitted KMeans model
- `scaler`: fitted StandardScaler
- `feature_names`: stable ordered feature list
- `cluster_to_segment`: KMeans cluster id mapped to segment `0`, `1`, or `2`
- `metadata`: model type, version, training time, training source, session count, scaler type, cluster count, random state, and segment labels

## Features

The feature vector is built in this fixed order:

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

## Segment Mapping

KMeans cluster ids are not stable semantic labels, so the trainer ranks cluster centers by engagement strength and maps them to stable segments:

- `0`: low engagement
- `1`: medium engagement
- `2`: high engagement

The ranking score uses page views, clicks, dwell time, unique products, add-to-cart count, attribute selections, price signals, and category diversity.

## Demo Data

Use the ML demo seeder to create balanced low, medium, and high sessions with the current database schema:

```bash
cd Senior-Project-Website_Add_Optimizer/backend
python scripts/seed_ml_demo_sessions.py --reset-demo
```

By default this creates 12 sessions per segment, for 36 total sessions. To create more:

```bash
python scripts/seed_ml_demo_sessions.py --reset-demo --sessions-per-segment 20
```

The seeder only writes `visitor_sessions` and `events` rows. It does not require a schema migration.

## Training

Train the KMeans model from real database sessions:

```bash
cd Senior-Project-Website_Add_Optimizer/backend
python scripts/train_model.py --min-sessions 30
```

Useful options:

```bash
python scripts/train_model.py --days 30 --min-sessions 30
python scripts/train_model.py --limit 500 --min-sessions 50
```

The output file is:

```text
backend/ml/model.pkl
```

## Evaluation

Evaluate the saved model on current session data:

```bash
cd Senior-Project-Website_Add_Optimizer/backend
python scripts/evaluate_model.py --min-sessions 20
```

The evaluator prints artifact metadata, clustering metrics, cluster summaries, and segment distribution.

## Smoke Check

After training:

```bash
python -c "from ml.scoring import ensure_model, score_session; print(ensure_model()); print(score_session(page_count=2, click_count=1, dwell_time_seconds=60, unique_products=1, avg_price=39.99, category_diversity=1, beauty_ratio=1)); print(score_session(page_count=6, click_count=4, dwell_time_seconds=240, unique_products=2, add_to_cart_count=1, attribute_selection_count=2, avg_price=129.99, price_stddev=20, category_diversity=2, electronics_ratio=0.5, sports_ratio=0.5)); print(score_session(page_count=12, click_count=9, dwell_time_seconds=720, unique_products=5, add_to_cart_count=2, attribute_selection_count=4, avg_price=159.99, price_stddev=55, category_diversity=3, electronics_ratio=0.4, home_appliances_ratio=0.3, sports_ratio=0.3))"
```

This confirms that `model.pkl` can be loaded and used for inference.

## Final Demo Flow

This project is a demo-ready prototype for behavior-based segmentation and explainable ML placement. For the final local demo, run the full stack and ML scripts from `Senior-Project-Website_Add_Optimizer`.

Start the existing Docker Compose services:

```bash
docker compose up -d postgres backend admin-frontend store
```

Seed balanced demo sessions, train the KMeans model, and evaluate the saved artifact:

```bash
docker compose exec backend python scripts/seed_ml_demo_sessions.py --reset-demo
docker compose exec backend python scripts/train_model.py --min-sessions 30
docker compose exec backend python scripts/evaluate_model.py --min-sessions 20
```

Then open the local apps:

- Storefront: `http://localhost:8000`
- Backend API: `http://localhost:10000`
- Admin dashboard: `http://localhost:5173`

Use the Dashboard ML Placement Demo card to test `GET /ads/placement?page=home&session_id=<session_id>`. A valid seeded session should return a selected ad plus ML explanation fields. A blank or invalid session demonstrates fallback behavior.

Important local command note: on this machine, host Python 3.14 caused `psycopg2-binary` install/build issues because the package attempted a source build and required `pg_config`. The recommended demo path is to run the ML scripts inside the Docker backend container, where the pinned backend dependencies are already installed.

## Explainable ML Placement Story

The ML demo uses `StandardScaler` plus KMeans to group visitor sessions by behavior-based segmentation signals. The model consumes session behavior features such as page views, click count, dwell time, unique products, add-to-cart count, attribute selections, average price, price spread, category diversity, and category ratios.

The trainer maps KMeans clusters into stable engagement segments:

- `0`: low engagement
- `1`: medium engagement
- `2`: high engagement

The ad placement endpoint uses the segment to choose a segment-based ranking strategy:

- Low engagement: least exposed ads
- Medium engagement: impression popularity
- High engagement: CTR performance

The placement response is intentionally explainable for demo use. When model scoring is available, the response includes:

- `segment`
- `segment_label`
- `ranking_strategy`
- `model_version`
- `explanation`

For a valid ML placement, `explanation` is `ml:kmeans_segment_placement`. Fallback responses use explicit explanations such as `fallback:no_session_id`, `fallback:session_not_found`, or `fallback:model_missing`.

## Known Limitations

- Model retraining is manual and script-based in this prototype.
- A dedicated A/B experiment module is future work.
- The current project supports comparison through campaign and ad metrics such as impressions, clicks, and CTR.
- Production-grade model monitoring, drift detection, automated retraining, and rollout controls are future work.
- `backend/ml/model.pkl` is a generated local artifact and must not be committed.
