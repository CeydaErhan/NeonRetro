"""Recommendation route for ML-driven session-aware ad suggestions."""

from collections import Counter, defaultdict
from datetime import datetime
import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Event, User, VisitorSession
from app.schemas import (
    PreferenceStatRead,
    SessionPreferenceProfileRead,
    SessionProductInteractionRead,
    SessionProfileRead,
    SuggestedProductRead,
)
from ml.product_ranker import PRODUCT_RANKER_PATH, rank_products_with_model
from ml.recommendation import get_recommendations as get_segment_recommendations
from ml.scoring import CATEGORY_SLUGS, score_session

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

PRODUCTS_PATHS = []
_rec_file = Path(__file__).resolve()
for _idx in (2, 3, 4):
    try:
        PRODUCTS_PATHS.append(_rec_file.parents[_idx] / "frontend" / "data" / "products.json")
    except IndexError:
        pass
PRODUCTS_PATHS.extend([Path("/seed-data/products.json"), Path("/app/frontend/data/products.json")])
PRODUCTS_PATHS = tuple(PRODUCTS_PATHS)


def _get_session_or_404(db: Session, session_id: int) -> VisitorSession:
    visitor_session = db.execute(select(VisitorSession).where(VisitorSession.id == session_id)).scalar_one_or_none()
    if visitor_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor session not found")
    return visitor_session


def _load_product_events(db: Session, session_id: int) -> list[Event]:
    stmt = (
        select(Event)
        .where(Event.session_id == session_id)
        .where(Event.metadata_json.is_not(None))
        .order_by(Event.timestamp.desc(), Event.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


@lru_cache(maxsize=1)
def _load_products_catalog() -> list[dict[str, object]]:
    """Load the storefront product catalog used for recommendation ranking."""
    for path in PRODUCTS_PATHS:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("Unable to locate frontend/data/products.json")


def _derive_session_ml_features(visitor_session: VisitorSession, events: list[Event]) -> dict[str, float]:
    """Compute the feature set consumed by the persisted session model."""
    page_count = sum(1 for event in events if event.type in {"page_view", "pageview"})
    click_count = sum(1 for event in events if event.type == "click")
    add_to_cart_count = sum(1 for event in events if event.element == "add-to-cart")
    attribute_selection_count = sum(1 for event in events if event.element == "select-attribute")

    product_ids: set[int] = set()
    categories: set[str] = set()
    prices: list[float] = []
    category_counts = {slug: 0 for slug in CATEGORY_SLUGS}

    for event in events:
        metadata = event.metadata_json or {}

        product_id = metadata.get("product_id")
        if isinstance(product_id, int):
            product_ids.add(product_id)

        category = metadata.get("category")
        if isinstance(category, str) and category:
            categories.add(category)
            if category in category_counts:
                category_counts[category] += 1

        price = metadata.get("price")
        if isinstance(price, (int, float)):
            prices.append(float(price))

    session_end = visitor_session.ended_at or (events[-1].timestamp if events else None) or datetime.utcnow()
    dwell_time_seconds = max((session_end - visitor_session.started_at).total_seconds(), 0.0)
    avg_price = float(sum(prices) / len(prices)) if prices else 0.0
    price_stddev = float(sum((price - avg_price) ** 2 for price in prices) / len(prices)) ** 0.5 if len(prices) > 1 else 0.0
    total_category_hits = sum(category_counts.values()) or 1

    return {
        "page_count": page_count,
        "click_count": click_count,
        "dwell_time_seconds": dwell_time_seconds,
        "unique_products": len(product_ids),
        "add_to_cart_count": add_to_cart_count,
        "attribute_selection_count": attribute_selection_count,
        "avg_price": avg_price,
        "price_stddev": price_stddev,
        "category_diversity": len(categories),
        "electronics_ratio": category_counts["electronics"] / total_category_hits,
        "clothing_ratio": category_counts["clothing"] / total_category_hits,
        "beauty_ratio": category_counts["beauty"] / total_category_hits,
        "home_appliances_ratio": category_counts["home-appliances"] / total_category_hits,
        "books_ratio": category_counts["books"] / total_category_hits,
        "sports_ratio": category_counts["sports"] / total_category_hits,
    }


def _top_preference_stats(counter: Counter[str], limit: int = 5) -> list[PreferenceStatRead]:
    """Convert a preference counter into a sorted response payload."""
    return [PreferenceStatRead(value=value, count=count) for value, count in counter.most_common(limit)]


def _derive_session_preference_profile(session_id: int, events: list[Event]) -> SessionPreferenceProfileRead:
    """Summarize category, price, and attribute preferences for a visitor session."""
    category_counts: Counter[str] = Counter()
    brand_counts: Counter[str] = Counter()
    color_counts: Counter[str] = Counter()
    size_counts: Counter[str] = Counter()
    storage_counts: Counter[str] = Counter()
    skin_type_counts: Counter[str] = Counter()
    prices: list[float] = []

    for event in events:
        metadata = event.metadata_json or {}
        category = metadata.get("category")
        if isinstance(category, str) and category:
            category_counts[category] += 1

        price = metadata.get("price")
        if isinstance(price, (int, float)):
            prices.append(float(price))

        available_attributes = metadata.get("available_attributes") or {}
        selected_attributes = metadata.get("selected_attributes") or {}

        brand = available_attributes.get("brand")
        if isinstance(brand, str) and brand:
            brand_counts[brand] += 1

        for key, value in selected_attributes.items():
            if not isinstance(value, str) or not value:
                continue
            if key == "colors":
                color_counts[value] += 1
            elif key == "sizes":
                size_counts[value] += 1
            elif key == "storage":
                storage_counts[value] += 1
            elif key == "skin_type":
                skin_type_counts[value] += 1

        attribute_group = metadata.get("attribute_group")
        attribute_value = metadata.get("attribute_value")
        if isinstance(attribute_group, str) and isinstance(attribute_value, str) and attribute_value:
            if attribute_group == "colors":
                color_counts[attribute_value] += 1
            elif attribute_group == "sizes":
                size_counts[attribute_value] += 1
            elif attribute_group == "storage":
                storage_counts[attribute_value] += 1
            elif attribute_group == "skin_type":
                skin_type_counts[attribute_value] += 1

    top_category = category_counts.most_common(1)[0][0] if category_counts else None

    return SessionPreferenceProfileRead(
        session_id=session_id,
        top_category=top_category,
        category_counts=dict(category_counts),
        average_price=(sum(prices) / len(prices)) if prices else None,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        preferred_brands=_top_preference_stats(brand_counts),
        preferred_colors=_top_preference_stats(color_counts),
        preferred_sizes=_top_preference_stats(size_counts),
        preferred_storage=_top_preference_stats(storage_counts),
        preferred_skin_types=_top_preference_stats(skin_type_counts),
    )


def _preference_weights(preferences: list[PreferenceStatRead]) -> dict[str, float]:
    """Turn top preference counts into weighted lookup scores."""
    if not preferences:
        return {}
    top_count = max(preference.count for preference in preferences) or 1
    return {preference.value: preference.count / top_count for preference in preferences}


def _score_catalog_product(
    product: dict[str, object],
    profile: SessionPreferenceProfileRead,
    seen_product_ids: set[int],
    exclude_viewed: bool,
) -> SuggestedProductRead | None:
    """Compute a personalized score for one catalog product."""
    product_id = product.get("id")
    category = product.get("category")
    category_name = product.get("categoryName")
    name = product.get("name")
    price = product.get("price")
    image = product.get("image")

    if not all(
        [
            isinstance(product_id, int),
            isinstance(category, str),
            isinstance(category_name, str),
            isinstance(name, str),
            isinstance(price, (int, float)),
            isinstance(image, str),
        ]
    ):
        return None

    if exclude_viewed and product_id in seen_product_ids:
        return None

    score = 0.0
    matched_signals: list[str] = []
    attributes = product.get("attributes") or {}
    if not isinstance(attributes, dict):
        attributes = {}

    if profile.top_category and category == profile.top_category:
        score += 4.0
        matched_signals.append(f"category:{category}")

    average_price = profile.average_price
    min_price = profile.min_price
    max_price = profile.max_price
    product_price = float(price)

    if average_price is not None and average_price > 0:
        closeness = max(0.0, 1.0 - (abs(product_price - average_price) / average_price))
        if closeness > 0:
            score += closeness * 3.0
            matched_signals.append("price:avg-match")

    if min_price is not None and max_price is not None and min_price <= product_price <= max_price:
        score += 2.0
        matched_signals.append("price:range-match")

    brand_weights = _preference_weights(profile.preferred_brands)
    color_weights = _preference_weights(profile.preferred_colors)
    size_weights = _preference_weights(profile.preferred_sizes)
    storage_weights = _preference_weights(profile.preferred_storage)
    skin_type_weights = _preference_weights(profile.preferred_skin_types)

    brand = attributes.get("brand")
    if isinstance(brand, str) and brand in brand_weights:
        score += 2.0 * brand_weights[brand]
        matched_signals.append(f"brand:{brand}")

    def score_attribute_list(attribute_key: str, weights: dict[str, float], label: str, max_bonus: float) -> None:
        nonlocal score
        values = attributes.get(attribute_key)
        if not isinstance(values, list):
            return
        best_match = 0.0
        best_value = None
        for value in values:
            if isinstance(value, str) and value in weights and weights[value] > best_match:
                best_match = weights[value]
                best_value = value
        if best_value is not None:
            score += max_bonus * best_match
            matched_signals.append(f"{label}:{best_value}")

    score_attribute_list("colors", color_weights, "color", 2.5)
    score_attribute_list("sizes", size_weights, "size", 3.0)
    score_attribute_list("storage", storage_weights, "storage", 3.0)
    score_attribute_list("skin_type", skin_type_weights, "skin_type", 2.0)

    if score <= 0:
        return None

    return SuggestedProductRead(
        product_id=product_id,
        name=name,
        category=category,
        category_name=category_name,
        price=product_price,
        image=image,
        score=round(score, 3),
        matched_signals=matched_signals,
    )


def _matched_signals_for_product(product: dict[str, object], profile: SessionPreferenceProfileRead) -> list[str]:
    """Explain which preference signals matched for a suggested product."""
    matched_signals: list[str] = []
    category = product.get("category")
    if isinstance(category, str) and profile.top_category and category == profile.top_category:
        matched_signals.append(f"category:{category}")

    price = product.get("price")
    if isinstance(price, (int, float)):
        if profile.average_price is not None and profile.average_price > 0:
            matched_signals.append("price:avg-match")
        if (
            profile.min_price is not None
            and profile.max_price is not None
            and profile.min_price <= float(price) <= profile.max_price
        ):
            matched_signals.append("price:range-match")

    attributes = product.get("attributes") or {}
    if isinstance(attributes, dict):
        brand = attributes.get("brand")
        if isinstance(brand, str) and any(item.value == brand for item in profile.preferred_brands):
            matched_signals.append(f"brand:{brand}")

        def append_attribute_match(attribute_key: str, preferences: list[PreferenceStatRead], label: str) -> None:
            values = attributes.get(attribute_key)
            if not isinstance(values, list):
                return
            preference_values = {item.value for item in preferences}
            for value in values:
                if isinstance(value, str) and value in preference_values:
                    matched_signals.append(f"{label}:{value}")
                    return

        append_attribute_match("colors", profile.preferred_colors, "color")
        append_attribute_match("sizes", profile.preferred_sizes, "size")
        append_attribute_match("storage", profile.preferred_storage, "storage")
        append_attribute_match("skin_type", profile.preferred_skin_types, "skin_type")

    return matched_signals


def _build_suggested_products(
    session_id: int,
    events: list[Event],
    limit: int,
    exclude_viewed: bool,
) -> list[SuggestedProductRead]:
    """Rank catalog products for one visitor session using attribute-aware preferences."""
    profile = _derive_session_preference_profile(session_id, events)
    if PRODUCT_RANKER_PATH.exists():
        model_ranked = rank_products_with_model(events, limit=limit, exclude_viewed=exclude_viewed)
        suggestions: list[SuggestedProductRead] = []
        for row in model_ranked:
            product = row["product"]
            product_id = product.get("id")
            name = product.get("name")
            category = product.get("category")
            category_name = product.get("categoryName")
            price = product.get("price")
            image = product.get("image")
            if not all(
                [
                    isinstance(product_id, int),
                    isinstance(name, str),
                    isinstance(category, str),
                    isinstance(category_name, str),
                    isinstance(price, (int, float)),
                    isinstance(image, str),
                ]
            ):
                continue
            suggestions.append(
                SuggestedProductRead(
                    product_id=product_id,
                    name=name,
                    category=category,
                    category_name=category_name,
                    price=float(price),
                    image=image,
                    score=round(float(row["score"]), 3),
                    matched_signals=_matched_signals_for_product(product, profile),
                )
            )
        if suggestions:
            return suggestions

    seen_product_ids = {
        metadata.get("product_id")
        for event in events
        for metadata in [event.metadata_json or {}]
        if isinstance(metadata.get("product_id"), int)
    }

    ranked_products: list[SuggestedProductRead] = []
    for product in _load_products_catalog():
        suggestion = _score_catalog_product(product, profile, seen_product_ids, exclude_viewed)
        if suggestion is not None:
            ranked_products.append(suggestion)

    ranked_products.sort(key=lambda item: (-item.score, item.price, item.name))
    return ranked_products[:limit]


@router.get("")
async def list_recommendations(
    session_id: int = Query(..., ge=1),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    """Return ML-ranked ads for the provided visitor session."""
    visitor_session = _get_session_or_404(db, session_id)
    events = list(
        db.execute(select(Event).where(Event.session_id == session_id).order_by(Event.timestamp.asc(), Event.id.asc()))
        .scalars()
        .all()
    )
    features = _derive_session_ml_features(visitor_session, events)
    segment = score_session(**features)

    recommended_ads = get_segment_recommendations(segment=segment, db_session=db, limit=3)
    return [
        {
            "id": ad.id,
            "campaign_id": ad.campaign_id,
            "title": ad.title,
            "content": ad.content,
            "image_url": ad.image_url,
            "target_page": ad.target_page,
            "segment": segment,
        }
        for ad in recommended_ads
    ]


@router.get("/recently-viewed", response_model=list[SessionProductInteractionRead])
async def recently_viewed_products(
    session_id: int = Query(..., ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionProductInteractionRead]:
    """Return the most recently interacted-with unique products for a visitor session."""
    _get_session_or_404(db, session_id)
    product_events = _load_product_events(db, session_id)

    aggregated: dict[int, SessionProductInteractionRead] = {}
    interaction_counts: dict[int, int] = defaultdict(int)

    for event in product_events:
        metadata = event.metadata_json or {}
        product_id = metadata.get("product_id")
        product_name = metadata.get("product_name")
        category = metadata.get("category")

        if not isinstance(product_id, int) or not product_name or not category:
            continue

        interaction_counts[product_id] += 1
        if product_id in aggregated:
            continue

        aggregated[product_id] = SessionProductInteractionRead(
            product_id=product_id,
            product_name=str(product_name),
            category=str(category),
            category_name=metadata.get("category_name"),
            price=float(metadata["price"]) if metadata.get("price") is not None else None,
            image=metadata.get("image"),
            last_interaction_at=event.timestamp,
            interaction_count=0,
            last_event_type=event.type,
            last_element=event.element,
        )

    results: list[SessionProductInteractionRead] = []
    for product_id, item in aggregated.items():
        item.interaction_count = interaction_counts[product_id]
        results.append(item)

    results.sort(key=lambda item: item.last_interaction_at, reverse=True)
    return results[:limit]


@router.get("/session-recently-viewed", response_model=list[SessionProductInteractionRead])
async def session_recently_viewed_products(
    session_id: int = Query(..., ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[SessionProductInteractionRead]:
    """Public store-facing variant of recently viewed products for a visitor session."""
    _get_session_or_404(db, session_id)
    product_events = _load_product_events(db, session_id)

    aggregated: dict[int, SessionProductInteractionRead] = {}
    interaction_counts: dict[int, int] = defaultdict(int)

    for event in product_events:
        metadata = event.metadata_json or {}
        product_id = metadata.get("product_id")
        product_name = metadata.get("product_name")
        category = metadata.get("category")

        if not isinstance(product_id, int) or not product_name or not category:
            continue

        interaction_counts[product_id] += 1
        if product_id in aggregated:
            continue

        aggregated[product_id] = SessionProductInteractionRead(
            product_id=product_id,
            product_name=str(product_name),
            category=str(category),
            category_name=metadata.get("category_name"),
            price=float(metadata["price"]) if metadata.get("price") is not None else None,
            image=metadata.get("image"),
            last_interaction_at=event.timestamp,
            interaction_count=0,
            last_event_type=event.type,
            last_element=event.element,
        )

    results: list[SessionProductInteractionRead] = []
    for product_id, item in aggregated.items():
        item.interaction_count = interaction_counts[product_id]
        results.append(item)

    results.sort(key=lambda item: item.last_interaction_at, reverse=True)
    return results[:limit]


@router.get("/session-profile", response_model=SessionProfileRead)
async def session_profile(
    session_id: int = Query(..., ge=1),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionProfileRead:
    """Return a compact summary of product interest for the visitor session."""
    _get_session_or_404(db, session_id)
    events = _load_product_events(db, session_id)

    category_counts: dict[str, int] = defaultdict(int)
    product_ids: set[int] = set()
    product_interaction_count = 0

    for event in events:
        metadata = event.metadata_json or {}
        product_id = metadata.get("product_id")
        category = metadata.get("category")
        if isinstance(product_id, int):
            product_ids.add(product_id)
            product_interaction_count += 1
        if isinstance(category, str) and category:
            category_counts[category] += 1

    top_category = None
    top_category_interactions = 0
    if category_counts:
        top_category, top_category_interactions = max(category_counts.items(), key=lambda item: item[1])

    total_events = int(db.scalar(select(func.count(Event.id)).where(Event.session_id == session_id)) or 0)
    return SessionProfileRead(
        session_id=session_id,
        total_events=total_events,
        total_product_interactions=product_interaction_count,
        unique_products=len(product_ids),
        top_category=top_category,
        top_category_interactions=top_category_interactions,
    )


@router.get("/session-preferences", response_model=SessionPreferenceProfileRead)
async def session_preferences(
    session_id: int = Query(..., ge=1),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionPreferenceProfileRead:
    """Return an attribute-aware preference profile for the visitor session."""
    _get_session_or_404(db, session_id)
    events = _load_product_events(db, session_id)
    return _derive_session_preference_profile(session_id, events)


@router.get("/public-session-preferences", response_model=SessionPreferenceProfileRead)
async def public_session_preferences(
    session_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> SessionPreferenceProfileRead:
    """Public storefront variant of the session preference profile."""
    _get_session_or_404(db, session_id)
    events = _load_product_events(db, session_id)
    return _derive_session_preference_profile(session_id, events)


@router.get("/suggested-products", response_model=list[SuggestedProductRead])
async def suggested_products(
    session_id: int = Query(..., ge=1),
    limit: int = Query(default=8, ge=1, le=24),
    exclude_viewed: bool = Query(default=True),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SuggestedProductRead]:
    """Return attribute-aware personalized product suggestions for the visitor session."""
    _get_session_or_404(db, session_id)
    events = _load_product_events(db, session_id)
    return _build_suggested_products(session_id, events, limit, exclude_viewed)


@router.get("/public-suggested-products", response_model=list[SuggestedProductRead])
async def public_suggested_products(
    session_id: int = Query(..., ge=1),
    limit: int = Query(default=8, ge=1, le=24),
    exclude_viewed: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[SuggestedProductRead]:
    """Public storefront variant of personalized product suggestions."""
    _get_session_or_404(db, session_id)
    events = _load_product_events(db, session_id)
    return _build_suggested_products(session_id, events, limit, exclude_viewed)
