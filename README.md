# NeonRetro Website & Advertisement Optimizer

NeonRetro is a senior project demo that combines a tracked e-commerce storefront with an ML-backed advertisement optimizer and analytics dashboard.

The project has two main parts:

- `frontend/`: the NeonRetro storefront. It is a static HTML + vanilla JavaScript store that generates real visitor behavior.
- `Senior-Project-Website_Add_Optimizer/`: the optimizer system. It contains a FastAPI backend, PostgreSQL schema, ML modules, Docker Compose setup, and React admin dashboard.

## Architecture

The storefront loads products from `frontend/data/products.json` and renders category, search, product detail, cart, favorites, campaign banner, recently viewed, and suggested-product experiences.

`frontend/tracker.js` connects the storefront to the optimizer backend. On first load it calls `POST /visitor-sessions`, receives a numeric backend session ID, and stores it in browser `localStorage` with the key `neonretro_tracking_session_id`. Later page views and clicks reuse that numeric session ID. This is the current implementation; it is not an in-memory string session.

Tracked events are sent to `POST /events/track`. Product behavior is stored in the `events.metadata` JSON column, not in separate event columns. Metadata includes fields such as `product_id`, `product_name`, `category`, `price`, `available_attributes`, `selected_attributes`, quantity, and cart size.

The FastAPI backend stores data in PostgreSQL:

- `visitor_sessions`: browser sessions
- `events`: page views, product views, clicks, cart actions, and metadata JSON
- `campaigns`: campaign lifecycle records
- `ads`: campaign ad units
- `impressions`: ad views and clicks
- `users`: dashboard accounts

The ML layer uses KMeans session segmentation in `backend/ml/scoring.py`. Session features are extracted from tracked events, then mapped to stable demo labels:

- `0`: low engagement
- `1`: medium engagement
- `2`: high intent / high engagement

`GET /ads/placement` chooses an eligible active ad for a storefront placement. With a valid session and model, it scores the session and applies a segment-specific strategy:

- low: least exposed ads
- medium: impression popularity
- high: CTR performance

Product suggestions are served by `/recommendations/public-suggested-products`. The backend uses a trained product ranker if present, otherwise it falls back to preference-based scoring from session behavior.

The React dashboard shows KPIs, recent events, campaign management, and an ML placement demo card. It is intentionally separate from the storefront so the jury can see both the visitor experience and the operator analytics console.

## Run Locally With Docker Compose

From the repo root:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml up -d --build
```

Apps:

- Storefront: `http://localhost:8000`
- FastAPI backend: `http://localhost:10000`
- Admin dashboard: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

Check services:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml ps
```

## Create Admin User

The defense seed script creates the default admin if missing. You can also create it manually:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml exec backend python scripts/create_admin.py admin@example.com StrongPass123
```

Dashboard login:

- Email: `admin@example.com`
- Password: `StrongPass123`

## Seed Defense Demo Data

Run:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml exec backend python scripts/seed_defense_demo.py --reset-demo
```

The script creates:

- admin user if missing
- active home, electronics, and all-pages campaigns
- ads with low-exposure, high-impression, and high-CTR histories
- impressions and clicks for visible CTR behavior
- three visitor sessions: low engagement, medium engagement, high intent
- realistic storefront events with product metadata stored in `events.metadata`

The output prints the demo session IDs:

```text
Defense demo seed complete.

Admin:
  email: admin@example.com
  password: StrongPass123

Demo sessions:
  low_engagement_session_id: <id>
  medium_engagement_session_id: <id>
  high_intent_session_id: <id>

Try placement:
  /ads/placement?page=home&session_id=<low>
  /ads/placement?page=home&session_id=<medium>
  /ads/placement?page=home&session_id=<high>
```

## Senior Project Defense Story

1. Open the storefront and show that it behaves like a real e-commerce site.
2. Explain that `tracker.js` creates a backend visitor session and records behavior.
3. Click products, attributes, and add-to-cart to show event generation.
4. Open the dashboard and show sessions, events, impressions, clicks, and CTR.
5. Use the seeded low, medium, and high session IDs in the ML Placement Demo card.
6. Show that the backend returns segment, ranking strategy, features used, decision reason, and candidate count.
7. Explain that the selected ad changes because the optimizer uses behavior-based segmentation, not a static banner.
8. Show suggested products on the storefront as session-aware content recommendations.

More detailed presentation steps are in `docs/DEMO_SCRIPT.md`. Manual validation steps are in `docs/TEST_PLAN.md`.

## Important Current Limits

- Ads CRUD exists in the backend, but the dashboard does not yet have a dedicated Ads page.
- Settings is still a placeholder.
- ML training is script-based and not automatic.
- Generated model files such as `backend/ml/model.pkl` and `backend/ml/product_ranker.pkl` should not be committed.
- Alembic/schema drift around visitor session fields still exists and is intentionally not repaired in this small demo-focused phase.
