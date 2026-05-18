#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/Senior-Project-Website_Add_Optimizer/docker-compose.yml"
BACKEND_URL="${BACKEND_URL:-http://localhost:10000}"
SESSIONS_PER_SEGMENT="${SESSIONS_PER_SEGMENT:-20}"
MIN_SESSIONS="${MIN_SESSIONS:-30}"
DOCKER_BIN="${DOCKER_BIN:-}"

if [[ -z "$DOCKER_BIN" ]]; then
  if command -v docker >/dev/null 2>&1; then
    DOCKER_BIN="$(command -v docker)"
  elif [[ -x "/Applications/Docker.app/Contents/Resources/bin/docker" ]]; then
    DOCKER_BIN="/Applications/Docker.app/Contents/Resources/bin/docker"
    export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
  fi
fi
if [[ -n "$DOCKER_BIN" ]]; then
  export PATH="$(dirname "$DOCKER_BIN"):$PATH"
fi

cd "$ROOT_DIR"

if [[ -z "$DOCKER_BIN" || ! -x "$DOCKER_BIN" ]]; then
  cat <<'EOF'
Docker is not available on PATH, so the Docker Compose defense bootstrap cannot run.

Host setup fallback:
  1. Use Python 3.12 or 3.13 for the backend virtual environment.
  2. Install PostgreSQL client tooling so pg_config is available, or use a Python version with psycopg2-binary wheels.
  3. Start PostgreSQL and set:
       DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/adoptimizer
       ALEMBIC_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/adoptimizer
       CORS_ALLOW_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173
  4. From Senior-Project-Website_Add_Optimizer/backend:
       python -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt
       alembic upgrade head
       uvicorn app.main:app --host 0.0.0.0 --port 10000
  5. In another terminal, from Senior-Project-Website_Add_Optimizer/frontend:
       npm install
       npm run dev -- --host 0.0.0.0 --port 5173
  6. In another terminal, from frontend:
       python3 -m http.server 8000
  7. From Senior-Project-Website_Add_Optimizer/backend:
       python scripts/seed_defense_demo.py --reset-demo
       python scripts/seed_ml_demo_sessions.py --reset-demo --sessions-per-segment 20
       python scripts/train_model.py --min-sessions 30
  8. From the repo root:
       scripts/run_defense_checks.sh
EOF
  exit 1
fi

echo "Starting Docker Compose defense stack..."
"$DOCKER_BIN" compose -f "$COMPOSE_FILE" up -d --build

echo "Waiting for backend at $BACKEND_URL..."
for attempt in {1..60}; do
  if curl -fsS "$BACKEND_URL/" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" == "60" ]]; then
    echo "Backend did not become healthy at $BACKEND_URL" >&2
    "$DOCKER_BIN" compose -f "$COMPOSE_FILE" ps
    exit 1
  fi
  sleep 2
done

echo "Seeding defense campaigns, ads, and scenario sessions..."
"$DOCKER_BIN" compose -f "$COMPOSE_FILE" exec -T backend python scripts/seed_defense_demo.py --reset-demo

echo "Seeding ML training sessions..."
"$DOCKER_BIN" compose -f "$COMPOSE_FILE" exec -T backend python scripts/seed_ml_demo_sessions.py --reset-demo --sessions-per-segment "$SESSIONS_PER_SEGMENT"

echo "Training KMeans model..."
"$DOCKER_BIN" compose -f "$COMPOSE_FILE" exec -T backend python scripts/train_model.py --min-sessions "$MIN_SESSIONS"

echo "Running defense checks..."
"$ROOT_DIR/scripts/run_defense_checks.sh"

cat <<EOF

Defense demo is ready.

Open:
  Storefront: http://localhost:8000
  Backend:    http://localhost:10000
  Dashboard:  http://localhost:5173

Login:
  email:    admin@example.com
  password: StrongPass123

Use Dashboard -> Defense Demo for the main ML decision flow.
EOF
