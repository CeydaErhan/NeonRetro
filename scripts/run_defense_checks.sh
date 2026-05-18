#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://localhost:10000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-StrongPass123}"

cd "$ROOT_DIR"

python3 - <<'PY'
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


backend_url = os.environ.get("BACKEND_URL", "http://localhost:10000").rstrip("/")
admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
admin_password = os.environ.get("ADMIN_PASSWORD", "StrongPass123")


def request_json(method, path, payload=None, token=None, query=None):
    url = backend_url + path
    if query:
        url += "?" + urlencode(query)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as error:
        body_text = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {error.code} {body_text}") from error
    except URLError as error:
        raise RuntimeError(f"{method} {url} failed: {error.reason}") from error


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


print(f"Checking backend health: {backend_url}/")
health = request_json("GET", "/")
require(health and health.get("status") == "ok", "Backend healthcheck did not return status=ok")

print("Logging in for protected defense demo endpoints...")
token_payload = request_json("POST", "/auth/login", {"email": admin_email, "password": admin_password})
token = token_payload.get("access_token") if isinstance(token_payload, dict) else None
require(token, "Could not obtain dashboard auth token")

status_payload = request_json("GET", "/recommendations/defense-demo/status", token=token)
require(status_payload.get("model_exists") is True, "model.pkl exists check failed: backend reports missing model")

scenario_map = {
    "low_engagement_session_id": "casual",
    "medium_engagement_session_id": "interested",
    "high_intent_session_id": "high-intent",
}

seen_segments = set()
seen_strategies = set()
backup_ids = {}

for backup_key, scenario_key in scenario_map.items():
    scenario = request_json("POST", f"/recommendations/defense-demo/scenarios/{scenario_key}", {}, token=token)
    session_id = scenario.get("session_id")
    require(isinstance(session_id, int), f"{scenario_key} did not return a numeric session_id")
    backup_ids[backup_key] = session_id

    placement = request_json("GET", "/ads/placement", query={"page": "home", "session_id": session_id})
    explanation = placement.get("explanation") if isinstance(placement, dict) else None
    require(explanation == "ml:kmeans_segment_placement", f"{scenario_key} placement is fallback: {explanation}")
    require("fallback" not in str(placement.get("explanation")), f"{scenario_key} returned fallback explanation")

    for field in ("segment", "segment_label", "ranking_strategy", "model_version", "features_used", "decision_reason", "candidate_count"):
        require(placement.get(field) is not None, f"{scenario_key} placement missing {field}")

    seen_segments.add(placement["segment_label"])
    seen_strategies.add(placement["ranking_strategy"])
    print(f"{scenario_key}: segment={placement['segment_label']} strategy={placement['ranking_strategy']} session={session_id}")

require(len(seen_segments) == 3, f"Expected three distinct segment labels, got {sorted(seen_segments)}")
require(len(seen_strategies) == 3, f"Expected three distinct ranking strategies, got {sorted(seen_strategies)}")

print("Checking storefront tracking endpoints...")
session = request_json("POST", "/visitor-sessions", {
    "user_agent": "Defense check script",
    "referrer": "http://localhost:8000/index.html",
})
session_id = session.get("id") if isinstance(session, dict) else None
require(isinstance(session_id, int), "visitor session endpoint did not return numeric id")
event = request_json("POST", "/events/track", {
    "session_id": session_id,
    "type": "click",
    "page": "home",
    "element": "defense-check",
    "metadata": {"source": "run_defense_checks"},
})
require(isinstance(event, dict) and event.get("id"), "events tracking endpoint did not return event id")

print("Technical backup session IDs:")
for key in ("low_engagement_session_id", "medium_engagement_session_id", "high_intent_session_id"):
    print(f"  {key}: {backup_ids[key]}")

print("Defense checks passed.")
PY

if command -v npm >/dev/null 2>&1 && [ -d "$ROOT_DIR/Senior-Project-Website_Add_Optimizer/frontend/node_modules" ]; then
  echo "Running dashboard build check..."
  npm --prefix "$ROOT_DIR/Senior-Project-Website_Add_Optimizer/frontend" run build
else
  echo "Skipping dashboard build check because npm or node_modules is not available."
fi
