# Manual Test Plan

This project currently uses manual verification for the defense demo. Automated backend/frontend/e2e tests are future work.

## 1. Environment Startup

Command:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml up -d --build
```

Expected:

- storefront responds at `http://localhost:8000`
- backend responds at `http://localhost:10000`
- dashboard responds at `http://localhost:5173`
- PostgreSQL container is healthy

Check:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml ps
```

## 2. Admin User

Command:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml exec backend python scripts/create_admin.py admin@example.com StrongPass123
```

Expected:

- prints either user created or user already exists
- dashboard login succeeds with `admin@example.com / StrongPass123`

## 3. Defense Seed Data

Command:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml exec backend python scripts/seed_defense_demo.py --reset-demo
```

Expected output format:

```text
Defense demo seed complete.

Admin:
  email: admin@example.com
  password: StrongPass123

Demo sessions:
  low_engagement_session_id: <id>
  medium_engagement_session_id: <id>
  high_intent_session_id: <id>
```

Expected data:

- three active campaigns
- home/electronics/all ads
- impression and click histories with different CTRs
- three named visitor sessions
- realistic events stored in `events.metadata`

## 4. Storefront Tracking

Steps:

1. Open `http://localhost:8000`.
2. Open a product.
3. Select an attribute.
4. Add to cart.
5. Open dashboard Analytics.

Expected:

- a numeric session ID exists in browser localStorage under `neonretro_tracking_session_id`
- recent event rows appear in Analytics
- product actions include metadata JSON in backend responses

API check:

```bash
curl -H "Authorization: Bearer <token>" "http://localhost:10000/events/list?limit=20"
```

## 5. Ad Placement Explainability

Run placement calls for the seeded sessions:

```bash
curl "http://localhost:10000/ads/placement?page=home&session_id=<low_engagement_session_id>"
curl "http://localhost:10000/ads/placement?page=home&session_id=<medium_engagement_session_id>"
curl "http://localhost:10000/ads/placement?page=home&session_id=<high_intent_session_id>"
```

Expected response fields:

- `ad_id`
- `campaign_id`
- `title`
- `segment`
- `segment_label`
- `ranking_strategy`
- `model_version`
- `explanation`
- `features_used`
- `decision_reason`
- `fallback_reason`
- `candidate_count`

Expected strategy story:

- low: least exposed ad strategy
- medium: impression popularity strategy
- high: CTR performance strategy

If `fallback_reason` is present, explain why the ML path did not run, such as missing model or invalid session.

## 6. Product Suggestions

API check:

```bash
curl "http://localhost:10000/recommendations/public-suggested-products?session_id=<high_intent_session_id>&limit=8&exclude_viewed=true"
```

Expected:

- returns product suggestions
- includes `score`
- includes `matched_signals`

Storefront check:

- open home page after generating behavior
- suggested products section should appear when recommendations are returned

## 7. Dashboard

Steps:

1. Log in at `http://localhost:5173`.
2. Open Dashboard.
3. Confirm KPI cards show sessions, events, impressions, and CTR.
4. Run ML Placement Demo with each seeded session ID.
5. Open Analytics.
6. Confirm recent events are visible.
7. Open Campaigns.
8. Confirm seeded campaigns are listed.

Expected:

- dashboard loads without auth errors
- placement demo returns selected ad and explanation fields
- campaign and event data are visible enough for jury discussion

## 8. Known Test Gaps

- No automated pytest suite yet.
- No frontend unit tests yet.
- No Playwright/e2e test yet.
- Alembic/schema drift is not repaired in this phase.
- Ads management page is not implemented in this phase.
