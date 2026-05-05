"""Seed synthetic visitor sessions and events for local demos and ML experiments."""

from __future__ import annotations

import argparse
import json
import os
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import delete

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models import Event, VisitorSession  # noqa: E402

PRODUCTS_PATH_CANDIDATES = [
    Path(os.getenv("PRODUCTS_PATH", "")) if os.getenv("PRODUCTS_PATH") else None,
    ROOT_DIR.parent / "frontend" / "data" / "products.json",
    ROOT_DIR.parents[1] / "frontend" / "data" / "products.json" if len(ROOT_DIR.parents) > 1 else None,
    Path("/seed-data/products.json"),
]

CATEGORY_WEIGHTS = {
    "electronics": 0.24,
    "clothing": 0.18,
    "beauty": 0.14,
    "home-appliances": 0.14,
    "books": 0.12,
    "sports": 0.18,
}

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

REFERRERS = [
    "http://localhost:8000",
    "http://localhost:8000/index.html",
    "http://localhost:8000/category.html?cat=electronics",
    "http://localhost:8000/search.html?q=wireless",
]

SEARCH_TERMS = {
    "electronics": ["iphone", "headphones", "laptop", "camera"],
    "clothing": ["jacket", "shoes", "dress", "jeans"],
    "beauty": ["skincare", "lipstick", "serum", "shampoo"],
    "home-appliances": ["vacuum", "blender", "coffee", "air fryer"],
    "books": ["thriller", "fantasy", "history", "cookbook"],
    "sports": ["tennis", "basketball", "yoga", "fitness"],
}


@dataclass(frozen=True)
class Persona:
    name: str
    weight: float
    min_events: int
    max_events: int
    price_bias: str
    cart_probability: float
    attribute_probability: float
    compare_probability: float
    favorite_probability: float
    search_probability: float


PERSONAS = [
    Persona(
        name="budget_browser",
        weight=0.30,
        min_events=8,
        max_events=12,
        price_bias="low",
        cart_probability=0.24,
        attribute_probability=0.50,
        compare_probability=0.58,
        favorite_probability=0.22,
        search_probability=0.32,
    ),
    Persona(
        name="premium_shopper",
        weight=0.20,
        min_events=10,
        max_events=16,
        price_bias="high",
        cart_probability=0.46,
        attribute_probability=0.82,
        compare_probability=0.42,
        favorite_probability=0.10,
        search_probability=0.24,
    ),
    Persona(
        name="category_focused",
        weight=0.24,
        min_events=9,
        max_events=14,
        price_bias="mid",
        cart_probability=0.34,
        attribute_probability=0.62,
        compare_probability=0.54,
        favorite_probability=0.16,
        search_probability=0.20,
    ),
    Persona(
        name="impulse_buyer",
        weight=0.14,
        min_events=6,
        max_events=10,
        price_bias="discount",
        cart_probability=0.60,
        attribute_probability=0.42,
        compare_probability=0.16,
        favorite_probability=0.08,
        search_probability=0.12,
    ),
    Persona(
        name="comparison_user",
        weight=0.12,
        min_events=12,
        max_events=20,
        price_bias="mid_high",
        cart_probability=0.30,
        attribute_probability=0.76,
        compare_probability=0.82,
        favorite_probability=0.12,
        search_probability=0.28,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic visitor sessions and events.")
    parser.add_argument("--sessions", type=int, default=500, help="Number of visitor sessions to generate.")
    parser.add_argument("--days", type=int, default=30, help="How many past days the synthetic data should span.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible output.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing events and visitor sessions before seeding.",
    )
    return parser.parse_args()


def load_products() -> list[dict[str, Any]]:
    for candidate in PRODUCTS_PATH_CANDIDATES:
        if candidate and candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError("Could not locate products.json for synthetic event seeding")


def weighted_choice(items: list[Any], weights: list[float]) -> Any:
    return random.choices(items, weights=weights, k=1)[0]


def normalize_slug_to_page(category: str) -> str:
    return category


def build_product_groups(products: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for product in products:
        grouped[product["category"]].append(product)

    for category_products in grouped.values():
        category_products.sort(key=lambda product: product["price"])

    return dict(grouped)


def choose_persona() -> Persona:
    return weighted_choice(PERSONAS, [persona.weight for persona in PERSONAS])


def choose_category() -> str:
    categories = list(CATEGORY_WEIGHTS.keys())
    return weighted_choice(categories, [CATEGORY_WEIGHTS[category] for category in categories])


def choose_product(products: list[dict[str, Any]], bias: str) -> dict[str, Any]:
    if len(products) == 1:
        return products[0]

    if bias == "low":
        pool = products[: max(1, len(products) * 2 // 5)]
    elif bias == "high":
        pool = products[-max(1, len(products) // 4) :]
    elif bias == "mid":
        start = max(0, len(products) // 4)
        end = min(len(products), start + max(2, len(products) // 2))
        pool = products[start:end]
    elif bias == "mid_high":
        start = max(0, len(products) // 3)
        pool = products[start:]
    elif bias == "discount":
        discounted = [product for product in products if (product.get("discount") or 0) > 0]
        pool = discounted or products
    else:
        pool = products

    return random.choice(pool)


def build_available_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in attributes.items():
        normalized[key] = list(value) if isinstance(value, list) else value
    return normalized


def choose_selected_attributes(product: dict[str, Any], persona: Persona) -> tuple[dict[str, str], list[tuple[str, str]]]:
    attributes = product.get("attributes") or {}
    available_selectors = [(key, value) for key, value in attributes.items() if isinstance(value, list) and value]
    if not available_selectors:
        return {}, []

    selected: dict[str, str] = {}
    interaction_pairs: list[tuple[str, str]] = []

    for key, value in available_selectors:
        if random.random() > persona.attribute_probability:
            continue
        chosen_value = random.choice(value)
        selected[key] = chosen_value
        interaction_pairs.append((key, chosen_value))

    if not selected and random.random() < persona.attribute_probability:
        key, value = random.choice(available_selectors)
        chosen_value = random.choice(value)
        selected[key] = chosen_value
        interaction_pairs.append((key, chosen_value))

    return selected, interaction_pairs


def format_attribute_label(attribute_key: str) -> str:
    return attribute_key.replace("_", " ").title()


def build_product_metadata(product: dict[str, Any], selected_attributes: dict[str, str] | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "product_id": product["id"],
        "product_name": product["name"],
        "category": product["category"],
        "category_name": product["categoryName"],
        "price": product["price"],
        "image": product.get("image"),
        "discount": product.get("discount", 0),
        "stock": product.get("stock"),
        "available_attributes": build_available_attributes(product.get("attributes") or {}),
    }
    if selected_attributes:
        metadata["selected_attributes"] = dict(selected_attributes)
    return metadata


def session_start_time(days: int) -> datetime:
    now = datetime.now(UTC)
    day_offset = random.randint(0, max(0, days - 1))
    seconds_offset = random.randint(0, 60 * 60 * 23)
    return now - timedelta(days=day_offset, seconds=seconds_offset)


def append_event(
    events: list[Event],
    session_id: int,
    timestamp: datetime,
    event_type: str,
    page: str,
    *,
    element: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> datetime:
    events.append(
        Event(
            session_id=session_id,
            type=event_type,
            page=page,
            element=element,
            timestamp=timestamp,
            metadata_json=metadata,
        )
    )
    return timestamp + timedelta(seconds=random.randint(3, 45))


def generate_session_events(
    session: VisitorSession,
    persona: Persona,
    grouped_products: dict[str, list[dict[str, Any]]],
) -> list[Event]:
    category = choose_category()
    category_products = grouped_products[category]
    target_events = random.randint(persona.min_events, persona.max_events)
    current_time = session.started_at
    events: list[Event] = []
    cart_size = 0

    current_time = append_event(
        events,
        session.id,
        current_time,
        "page_view",
        "home",
        metadata={"path": "/index.html", "query": None},
    )

    if random.random() < persona.search_probability and len(events) < target_events:
        search_term = random.choice(SEARCH_TERMS[category])
        current_time = append_event(
            events,
            session.id,
            current_time,
            "page_view",
            "search",
            metadata={"path": "/search.html", "query": f"?q={search_term}"},
        )

    viewed_product_ids: set[int] = set()

    while len(events) < target_events:
        product = choose_product(category_products, persona.price_bias)
        if events[-1].page == "search":
            source_page = "search"
            source_name = "search-results"
        elif events[-1].page in grouped_products:
            source_page = events[-1].page
            source_name = "category"
        else:
            source_page = "home"
            source_name = "home"

        current_time = append_event(
            events,
            session.id,
            current_time,
            "click",
            source_page,
            element="open-product",
            metadata={
                **build_product_metadata(product),
                "source": source_name,
            },
        )
        if len(events) >= target_events:
            break

        current_time = append_event(
            events,
            session.id,
            current_time,
            "page_view",
            "product",
            metadata={"path": "/product.html", "query": f"?id={product['id']}"},
        )
        viewed_product_ids.add(product["id"])
        if len(events) >= target_events:
            break

        selected_attributes, interactions = choose_selected_attributes(product, persona)
        for attribute_key, attribute_value in interactions:
            current_time = append_event(
                events,
                session.id,
                current_time,
                "click",
                "product",
                element="select-attribute",
                metadata={
                    **build_product_metadata(product, selected_attributes),
                    "attribute_group": attribute_key,
                    "attribute_label": format_attribute_label(attribute_key),
                    "attribute_value": attribute_value,
                },
            )
            if len(events) >= target_events:
                break
        if len(events) >= target_events:
            break

        if random.random() < persona.favorite_probability and len(events) < target_events:
            current_time = append_event(
                events,
                session.id,
                current_time,
                "click",
                "product",
                element="add-favorite",
                metadata=build_product_metadata(product, selected_attributes),
            )

        if random.random() < persona.cart_probability and len(events) < target_events:
            cart_size += 1
            current_time = append_event(
                events,
                session.id,
                current_time,
                "click",
                "product",
                element="add-to-cart",
                metadata={
                    **build_product_metadata(product, selected_attributes),
                    "quantity": 1,
                    "cart_size_after_add": cart_size,
                },
            )

        if len(events) >= target_events:
            break

        if random.random() < persona.compare_probability:
            comparison_categories = [category]
            if random.random() < 0.35:
                comparison_categories.append(choose_category())
            category = random.choice(comparison_categories)
            category_products = grouped_products[category]
            current_time += timedelta(seconds=random.randint(10, 35))
            if len(events) < target_events and random.random() < 0.80:
                current_time = append_event(
                    events,
                    session.id,
                    current_time,
                    "page_view",
                    normalize_slug_to_page(category),
                    metadata={"path": "/category.html", "query": f"?cat={category}"},
                )
        else:
            if random.random() < 0.55:
                current_time = append_event(
                    events,
                    session.id,
                    current_time,
                    "page_view",
                    normalize_slug_to_page(category),
                    metadata={"path": "/category.html", "query": f"?cat={category}"},
                )
            else:
                if len(events) + 2 < target_events:
                    if random.random() < 0.50:
                        search_term = random.choice(SEARCH_TERMS[category])
                        current_time = append_event(
                            events,
                            session.id,
                            current_time,
                            "page_view",
                            "search",
                            metadata={"path": "/search.html", "query": f"?q={search_term}"},
                        )
                    else:
                        current_time = append_event(
                            events,
                            session.id,
                            current_time,
                            "page_view",
                            "home",
                            metadata={"path": "/index.html", "query": None},
                        )
                else:
                    break

    session.page_count = sum(1 for event in events if event.type == "page_view")
    session.ended_at = current_time
    return events


def create_session(days: int) -> VisitorSession:
    started_at = session_start_time(days)
    return VisitorSession(
        user_agent=random.choice(USER_AGENTS),
        referrer=random.choice(REFERRERS),
        created_at=started_at,
        visitor_id=None,
        started_at=started_at,
        ended_at=started_at,
        page_count=0,
    )


def reset_tables(db_session: Any) -> None:
    db_session.execute(delete(Event))
    db_session.execute(delete(VisitorSession))
    db_session.commit()


def seed_data(sessions_count: int, days: int, reset: bool) -> None:
    products = load_products()
    grouped_products = build_product_groups(products)

    with SessionLocal() as db_session:
        if reset:
            reset_tables(db_session)

        total_events = 0
        persona_counts: dict[str, int] = defaultdict(int)

        for _ in range(sessions_count):
            persona = choose_persona()
            persona_counts[persona.name] += 1

            session = create_session(days)
            db_session.add(session)
            db_session.flush()

            session_events = generate_session_events(session, persona, grouped_products)
            total_events += len(session_events)
            db_session.add_all(session_events)

        db_session.commit()

    print(f"Seeded {sessions_count} visitor sessions")
    print(f"Seeded {total_events} events")
    print("Persona breakdown:")
    for persona in PERSONAS:
        print(f"  - {persona.name}: {persona_counts.get(persona.name, 0)}")


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    seed_data(sessions_count=args.sessions, days=args.days, reset=args.reset)


if __name__ == "__main__":
    main()
