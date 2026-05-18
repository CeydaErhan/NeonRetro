"""Seed deterministic senior-project defense demo data."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.auth import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Ad, Campaign, Event, Impression, User, VisitorSession  # noqa: E402

DEMO_PREFIX = "defense-demo"
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "StrongPass123"

CAMPAIGN_DEFS = [
    {
        "name": "Defense Demo - Home Awareness",
        "target_page": "home",
        "ads": [
            {
                "key": "low_exposure",
                "title": "Fresh Drop: Neon Starter Deals",
                "content": "A low-exposure home campaign selected for new or low-engagement visitors.",
                "target_page": "home",
                "image_url": "https://images.pexels.com/photos/3945654/pexels-photo-3945654.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 1,
                "clicks": 0,
            },
            {
                "key": "popular",
                "title": "Most Viewed Retro Picks",
                "content": "A popular campaign with the strongest impression history for medium engagement visitors.",
                "target_page": "home",
                "image_url": "https://images.pexels.com/photos/5632398/pexels-photo-5632398.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 40,
                "clicks": 4,
            },
            {
                "key": "high_ctr",
                "title": "High Intent Checkout Boost",
                "content": "A high-CTR campaign selected when the session shows purchase intent.",
                "target_page": "home",
                "image_url": "https://images.pexels.com/photos/5632402/pexels-photo-5632402.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 12,
                "clicks": 9,
            },
        ],
    },
    {
        "name": "Defense Demo - Electronics Focus",
        "target_page": "electronics",
        "ads": [
            {
                "key": "electronics_bundle",
                "title": "Cyber Electronics Bundle",
                "content": "Electronics-focused placement for category-specific browsing behavior.",
                "target_page": "electronics",
                "image_url": "https://images.pexels.com/photos/5082576/pexels-photo-5082576.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 16,
                "clicks": 5,
            }
        ],
    },
    {
        "name": "Defense Demo - Clothing Focus",
        "target_page": "clothing",
        "ads": [
            {
                "key": "clothing_drop",
                "title": "Streetwear Layering Picks",
                "content": "Clothing-focused placement for visitors comparing apparel and accessory categories.",
                "target_page": "clothing",
                "image_url": "https://images.pexels.com/photos/1124465/pexels-photo-1124465.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 14,
                "clicks": 3,
            }
        ],
    },
    {
        "name": "Defense Demo - Beauty Focus",
        "target_page": "beauty",
        "ads": [
            {
                "key": "beauty_essentials",
                "title": "Glow Routine Essentials",
                "content": "Beauty-targeted promotion for visitors showing skincare or cosmetics interest.",
                "target_page": "beauty",
                "image_url": "https://images.pexels.com/photos/3762453/pexels-photo-3762453.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 11,
                "clicks": 2,
            }
        ],
    },
    {
        "name": "Defense Demo - Home Appliances Focus",
        "target_page": "home-appliances",
        "ads": [
            {
                "key": "home_appliance_upgrade",
                "title": "Smart Home Upgrade Week",
                "content": "Home-appliance placement for visitors exploring higher-consideration household products.",
                "target_page": "home-appliances",
                "image_url": "https://images.pexels.com/photos/4108711/pexels-photo-4108711.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 15,
                "clicks": 4,
            }
        ],
    },
    {
        "name": "Defense Demo - Books Focus",
        "target_page": "books",
        "ads": [
            {
                "key": "books_editor_picks",
                "title": "Weekend Reading Picks",
                "content": "Books-focused placement for visitors browsing discovery-driven catalog pages.",
                "target_page": "books",
                "image_url": "https://images.pexels.com/photos/590493/pexels-photo-590493.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 9,
                "clicks": 1,
            }
        ],
    },
    {
        "name": "Defense Demo - Sports Focus",
        "target_page": "sports",
        "ads": [
            {
                "key": "sports_active",
                "title": "Performance Gear Spotlight",
                "content": "Sports-targeted placement for visitors showing active lifestyle and equipment interest.",
                "target_page": "sports",
                "image_url": "https://images.pexels.com/photos/1552242/pexels-photo-1552242.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 13,
                "clicks": 3,
            }
        ],
    },
    {
        "name": "Defense Demo - All Pages Retargeting",
        "target_page": "all",
        "ads": [
            {
                "key": "all_pages",
                "title": "Sitewide Neon Rewards",
                "content": "A fallback all-pages campaign eligible across storefront placements.",
                "target_page": "all",
                "image_url": "https://images.pexels.com/photos/5625130/pexels-photo-5625130.jpeg?auto=compress&cs=tinysrgb&w=900",
                "impressions": 20,
                "clicks": 2,
            }
        ],
    },
]

PRODUCTS = {
    "iphone": {
        "product_id": 1,
        "product_name": "iPhone 14 Pro",
        "category": "electronics",
        "category_name": "Electronics",
        "price": 999.99,
        "discount": 0,
        "stock": 18,
        "available_attributes": {
            "brand": "Apple",
            "storage": ["128GB", "256GB", "512GB", "1TB"],
            "colors": ["Space Black", "Silver", "Gold", "Deep Purple"],
        },
    },
    "macbook": {
        "product_id": 4,
        "product_name": "MacBook Pro 16 Inch",
        "category": "electronics",
        "category_name": "Electronics",
        "price": 2499.99,
        "discount": 0,
        "stock": 12,
        "available_attributes": {
            "brand": "Apple",
            "storage": ["512GB", "1TB", "2TB"],
            "colors": ["Space Black", "Silver"],
        },
    },
    "headphones": {
        "product_id": 5,
        "product_name": "Sony WH-1000XM4 Headphones",
        "category": "electronics",
        "category_name": "Electronics",
        "price": 349.99,
        "discount": 10,
        "stock": 24,
        "available_attributes": {
            "brand": "Sony",
            "colors": ["Black", "Silver"],
        },
    },
    "vacuum": {
        "product_id": 2,
        "product_name": "Dyson V11 Vacuum",
        "category": "home-appliances",
        "category_name": "Home Appliances",
        "price": 499.99,
        "discount": 0,
        "stock": 31,
        "available_attributes": {
            "brand": "Dyson",
            "colors": ["Black", "White", "Silver", "Red"],
            "warranty": ["1 Year", "2 Years", "3 Years"],
        },
    },
    "jeans": {
        "product_id": 3,
        "product_name": "Levi's 501 Jeans",
        "category": "clothing",
        "category_name": "Clothing",
        "price": 69.99,
        "discount": 0,
        "stock": 44,
        "available_attributes": {
            "brand": "Levi's",
            "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
            "colors": ["Black", "White", "Navy", "Grey", "Beige", "Olive"],
            "gender": "Unisex",
        },
    },
    "shoes": {
        "product_id": 6,
        "product_name": "Nike Air Force 1",
        "category": "clothing",
        "category_name": "Clothing",
        "price": 109.99,
        "discount": 0,
        "stock": 29,
        "available_attributes": {
            "brand": "Nike",
            "sizes": ["38", "39", "40", "41", "42", "43", "44"],
            "colors": ["Black", "White", "Blue"],
            "gender": "Unisex",
        },
    },
}

DEMO_ML_PRICES = {
    "iphone": 129.99,
    "macbook": 179.99,
    "headphones": 99.99,
    "vacuum": 159.99,
    "jeans": 79.99,
    "shoes": 94.99,
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for deterministic demo seeding."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-email", default=DEFAULT_ADMIN_EMAIL)
    parser.add_argument("--admin-password", default=DEFAULT_ADMIN_PASSWORD)
    parser.add_argument("--reset-demo", action="store_true", help="Delete only prior defense demo records first.")
    return parser.parse_args()


def ensure_admin(email: str, password: str) -> None:
    """Create or refresh the defense demo admin user."""
    with SessionLocal() as db:
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is not None:
            existing.password_hash = hash_password(password)
            existing.role = "admin"
            db.commit()
            return
        db.add(User(email=email, password_hash=hash_password(password), role="admin"))
        db.commit()


def reset_demo_records() -> None:
    """Remove records previously created by this script without touching unrelated data."""
    with SessionLocal() as db:
        campaigns = list(
            db.execute(select(Campaign).where(Campaign.name.in_([item["name"] for item in CAMPAIGN_DEFS])))
            .scalars()
            .all()
        )
        for campaign in campaigns:
            db.delete(campaign)

        sessions = list(
            db.execute(select(VisitorSession).where(VisitorSession.visitor_id.like(f"{DEMO_PREFIX}%")))
            .scalars()
            .all()
        )
        for session in sessions:
            db.delete(session)

        db.commit()


def create_campaigns_and_ads() -> dict[str, Ad]:
    """Create active campaigns, ads, and deterministic impression/click history."""
    today = date.today()
    ad_by_key: dict[str, Ad] = {}

    with SessionLocal() as db:
        for campaign_def in CAMPAIGN_DEFS:
            campaign = db.execute(select(Campaign).where(Campaign.name == campaign_def["name"])).scalar_one_or_none()
            if campaign is None:
                campaign = Campaign(
                    name=campaign_def["name"],
                    start_date=today - timedelta(days=7),
                    end_date=today + timedelta(days=30),
                    status="active",
                    target_page=campaign_def["target_page"],
                )
                db.add(campaign)
                db.flush()

            for ad_def in campaign_def["ads"]:
                ad = db.execute(
                    select(Ad).where(Ad.campaign_id == campaign.id, Ad.title == ad_def["title"])
                ).scalar_one_or_none()
                if ad is None:
                    ad = Ad(
                        campaign_id=campaign.id,
                        title=ad_def["title"],
                        content=ad_def["content"],
                        image_url=ad_def["image_url"],
                        target_page=ad_def["target_page"],
                    )
                    db.add(ad)
                    db.flush()
                ad_by_key[ad_def["key"]] = ad

                existing_impressions = len(ad.impressions)
                if existing_impressions == 0:
                    _create_impression_history(db, ad, ad_def["key"], ad_def["impressions"], ad_def["clicks"])

        db.commit()
        return ad_by_key


def _create_history_session(db: Any, key: str, index: int, shown_at: datetime) -> VisitorSession:
    """Create a lightweight session used for historical impression metrics."""
    session = VisitorSession(
        visitor_id=f"{DEMO_PREFIX}-history-{key}-{index}",
        user_agent="Defense demo historical browser",
        referrer="http://localhost:8000/index.html",
        created_at=shown_at,
        started_at=shown_at,
        ended_at=shown_at + timedelta(seconds=30),
        page_count=1,
    )
    db.add(session)
    db.flush()
    return session


def _create_impression_history(db: Any, ad: Ad, key: str, impressions: int, clicks: int) -> None:
    """Create deterministic performance history for an ad."""
    base_time = datetime.now(UTC) - timedelta(days=3)
    for index in range(impressions):
        shown_at = base_time + timedelta(minutes=index * 7)
        session = _create_history_session(db, key, index, shown_at)
        clicked = index < clicks
        db.add(
            Impression(
                ad_id=ad.id,
                session_id=session.id,
                shown_at=shown_at,
                clicked=clicked,
                click_time=shown_at + timedelta(seconds=12) if clicked else None,
            )
        )


def product_metadata(product_key: str, **extra: Any) -> dict[str, Any]:
    """Build storefront-like product metadata for tracked events."""
    return {**PRODUCTS[product_key], **extra}


def ml_product_metadata(product_key: str, **extra: Any) -> dict[str, Any]:
    """Build seeded high-intent events without turning price into an outlier cluster."""
    return product_metadata(product_key, price=DEMO_ML_PRICES[product_key], **extra)


def event(
    session_id: int,
    timestamp: datetime,
    event_type: str,
    page: str,
    *,
    element: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Event:
    """Build an event row."""
    return Event(
        session_id=session_id,
        type=event_type,
        page=page,
        element=element,
        timestamp=timestamp,
        metadata_json=metadata,
    )


def create_session(db: Any, visitor_id: str, user_agent: str, started_at: datetime, dwell_seconds: int) -> VisitorSession:
    """Create a visitor session shell."""
    session = VisitorSession(
        visitor_id=visitor_id,
        user_agent=user_agent,
        referrer="http://localhost:8000/index.html",
        created_at=started_at,
        started_at=started_at,
        ended_at=started_at + timedelta(seconds=dwell_seconds),
        page_count=0,
    )
    db.add(session)
    db.flush()
    return session


def seed_demo_sessions() -> dict[str, int]:
    """Create deterministic defense demo sessions with realistic events."""
    now = datetime.now(UTC)
    created_ids: dict[str, int] = {}

    with SessionLocal() as db:
        low = create_session(db, f"{DEMO_PREFIX}-low", "Defense demo browser (low)", now - timedelta(hours=2), 75)
        low_events = [
            event(low.id, low.started_at, "page_view", "home", metadata={"path": "/index.html", "query": None}),
            event(
                low.id,
                low.started_at + timedelta(seconds=35),
                "click",
                "home",
                element="open-product",
                metadata=product_metadata("jeans", source="featured"),
            ),
            event(
                low.id,
                low.started_at + timedelta(seconds=50),
                "page_view",
                "product",
                metadata={"path": "/product.html", "query": "?id=3"},
            ),
            event(
                low.id,
                low.started_at + timedelta(seconds=62),
                "page_view",
                "books",
                metadata={"path": "/category.html", "query": "?cat=books", "category": "books", "category_name": "Books"},
            ),
        ]
        low.page_count = 3
        db.add_all(low_events)
        created_ids["low_engagement_session_id"] = low.id

        medium = create_session(
            db,
            f"{DEMO_PREFIX}-medium",
            "Defense demo browser (medium)",
            now - timedelta(hours=1),
            260,
        )
        medium_events = [
            event(medium.id, medium.started_at, "page_view", "home", metadata={"path": "/index.html", "query": None}),
            event(
                medium.id,
                medium.started_at + timedelta(seconds=40),
                "page_view",
                "electronics",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=electronics",
                    "category": "electronics",
                    "category_name": "Electronics",
                },
            ),
            event(
                medium.id,
                medium.started_at + timedelta(seconds=70),
                "click",
                "electronics",
                element="open-product",
                metadata=ml_product_metadata("iphone", source="category"),
            ),
            event(
                medium.id,
                medium.started_at + timedelta(seconds=95),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("iphone"),
            ),
            event(
                medium.id,
                medium.started_at + timedelta(seconds=130),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "iphone",
                    attribute_group="colors",
                    attribute_label="Color",
                    attribute_value="Deep Purple",
                    selected_attributes={"colors": "Deep Purple"},
                ),
            ),
            event(
                medium.id,
                medium.started_at + timedelta(seconds=175),
                "page_view",
                "home-appliances",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=home-appliances",
                    "category": "home-appliances",
                    "category_name": "Home Appliances",
                },
            ),
            event(
                medium.id,
                medium.started_at + timedelta(seconds=205),
                "page_view",
                "sports",
                metadata={"path": "/category.html", "query": "?cat=sports", "category": "sports", "category_name": "Sports"},
            ),
            event(
                medium.id,
                medium.started_at + timedelta(seconds=228),
                "click",
                "sports",
                element="open-product",
                metadata=product_metadata("shoes", source="category"),
            ),
            event(
                medium.id,
                medium.started_at + timedelta(seconds=245),
                "product_view",
                "product",
                element="product-detail",
                metadata=product_metadata("shoes"),
            ),
        ]
        medium.page_count = 5
        db.add_all(medium_events)
        created_ids["medium_engagement_session_id"] = medium.id

        high = create_session(
            db,
            f"{DEMO_PREFIX}-high",
            "Defense demo browser (high intent)",
            now - timedelta(minutes=20),
            960,
        )
        high_events = [
            event(high.id, high.started_at, "page_view", "home", metadata={"path": "/index.html", "query": None}),
            event(
                high.id,
                high.started_at + timedelta(seconds=35),
                "page_view",
                "electronics",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=electronics",
                    "category": "electronics",
                    "category_name": "Electronics",
                },
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=80),
                "click",
                "electronics",
                element="open-product",
                metadata=product_metadata("iphone", source="category"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=105),
                "page_view",
                "product",
                metadata={"path": "/product.html", "query": "?id=1"},
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=120),
                "product_view",
                "product",
                element="product-detail",
                metadata=product_metadata("iphone"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=165),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "iphone",
                    attribute_group="storage",
                    attribute_label="Storage",
                    attribute_value="512GB",
                    selected_attributes={"storage": "512GB"},
                ),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=210),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "iphone",
                    attribute_group="colors",
                    attribute_label="Color",
                    attribute_value="Space Black",
                    selected_attributes={"storage": "512GB", "colors": "Space Black"},
                ),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=270),
                "click",
                "product",
                element="add-to-cart",
                metadata=ml_product_metadata(
                    "iphone",
                    selected_attributes={"storage": "512GB", "colors": "Space Black"},
                    quantity=1,
                    cart_size_after_add=1,
                ),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=330),
                "click",
                "electronics",
                element="open-product",
                metadata=ml_product_metadata("macbook", source="recommended-products"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=350),
                "page_view",
                "product",
                metadata={"path": "/product.html", "query": "?id=4"},
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=380),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("macbook"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=420),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "macbook",
                    attribute_group="storage",
                    attribute_label="Storage",
                    attribute_value="1TB",
                    selected_attributes={"storage": "1TB"},
                ),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=455),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "macbook",
                    attribute_group="colors",
                    attribute_label="Color",
                    attribute_value="Silver",
                    selected_attributes={"storage": "1TB", "colors": "Silver"},
                ),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=500),
                "click",
                "product",
                element="add-to-cart",
                metadata=ml_product_metadata(
                    "macbook",
                    selected_attributes={"storage": "1TB", "colors": "Silver"},
                    quantity=1,
                    cart_size_after_add=2,
                ),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=545),
                "click",
                "electronics",
                element="open-product",
                metadata=ml_product_metadata("headphones", source="suggested-products"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=565),
                "page_view",
                "product",
                metadata={"path": "/product.html", "query": "?id=5"},
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=600),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("headphones"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=640),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "headphones",
                    attribute_group="colors",
                    attribute_label="Color",
                    attribute_value="Black",
                    selected_attributes={"colors": "Black"},
                ),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=675),
                "page_view",
                "home-appliances",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=home-appliances",
                    "category": "home-appliances",
                    "category_name": "Home Appliances",
                },
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=700),
                "click",
                "home-appliances",
                element="open-product",
                metadata=ml_product_metadata("vacuum", source="category"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=720),
                "page_view",
                "product",
                metadata={"path": "/product.html", "query": "?id=2"},
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=755),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("vacuum"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=800),
                "click",
                "product",
                element="add-to-cart",
                metadata=ml_product_metadata(
                    "vacuum",
                    selected_attributes={"colors": "Black", "warranty": "2 Years"},
                    quantity=1,
                    cart_size_after_add=3,
                ),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=835),
                "page_view",
                "clothing",
                metadata={"path": "/category.html", "query": "?cat=clothing", "category": "clothing", "category_name": "Clothing"},
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=860),
                "click",
                "clothing",
                element="open-product",
                metadata=ml_product_metadata("shoes", source="cross-sell"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=880),
                "page_view",
                "product",
                metadata={"path": "/product.html", "query": "?id=6"},
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=910),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("shoes"),
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=930),
                "page_view",
                "sports",
                metadata={"path": "/category.html", "query": "?cat=sports", "category": "sports", "category_name": "Sports"},
            ),
            event(
                high.id,
                high.started_at + timedelta(seconds=950),
                "click",
                "sports",
                element="open-product",
                metadata=ml_product_metadata("headphones", source="cross-category-active"),
            ),
        ]
        high.page_count = 10
        db.add_all(high_events)
        created_ids["high_intent_session_id"] = high.id

        window = create_session(
            db,
            f"{DEMO_PREFIX}-window-shopper",
            "Defense demo browser (window shopper)",
            now - timedelta(minutes=12),
            120,
        )
        window_events = [
            event(window.id, window.started_at, "page_view", "home", metadata={"path": "/index.html", "query": None}),
            event(
                window.id,
                window.started_at + timedelta(seconds=24),
                "page_view",
                "electronics",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=electronics",
                    "category": "electronics",
                    "category_name": "Electronics",
                },
            ),
            event(
                window.id,
                window.started_at + timedelta(seconds=54),
                "page_view",
                "books",
                metadata={"path": "/category.html", "query": "?cat=books", "category": "books", "category_name": "Books"},
            ),
            event(
                window.id,
                window.started_at + timedelta(seconds=86),
                "page_view",
                "beauty",
                metadata={"path": "/category.html", "query": "?cat=beauty", "category": "beauty", "category_name": "Beauty"},
            ),
        ]
        window.page_count = 4
        db.add_all(window_events)
        created_ids["window_shopper_session_id"] = window.id

        price_sensitive = create_session(
            db,
            f"{DEMO_PREFIX}-price-sensitive",
            "Defense demo browser (price sensitive)",
            now - timedelta(minutes=9),
            210,
        )
        price_sensitive_events = [
            event(price_sensitive.id, price_sensitive.started_at, "page_view", "home", metadata={"path": "/index.html", "query": None}),
            event(
                price_sensitive.id,
                price_sensitive.started_at + timedelta(seconds=24),
                "page_view",
                "clothing",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=clothing",
                    "category": "clothing",
                    "category_name": "Clothing",
                },
            ),
            event(
                price_sensitive.id,
                price_sensitive.started_at + timedelta(seconds=56),
                "click",
                "clothing",
                element="open-product",
                metadata=ml_product_metadata("jeans", source="sale-grid"),
            ),
            event(
                price_sensitive.id,
                price_sensitive.started_at + timedelta(seconds=82),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("jeans"),
            ),
            event(
                price_sensitive.id,
                price_sensitive.started_at + timedelta(seconds=128),
                "page_view",
                "books",
                metadata={"path": "/category.html", "query": "?cat=books", "category": "books", "category_name": "Books"},
            ),
        ]
        price_sensitive.page_count = 3
        db.add_all(price_sensitive_events)
        created_ids["price_sensitive_session_id"] = price_sensitive.id

        cross_category = create_session(
            db,
            f"{DEMO_PREFIX}-cross-category",
            "Defense demo browser (cross category)",
            now - timedelta(minutes=6),
            430,
        )
        cross_category_events = [
            event(cross_category.id, cross_category.started_at, "page_view", "home", metadata={"path": "/index.html", "query": None}),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=35),
                "page_view",
                "electronics",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=electronics",
                    "category": "electronics",
                    "category_name": "Electronics",
                },
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=65),
                "click",
                "electronics",
                element="open-product",
                metadata=ml_product_metadata("iphone", source="category"),
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=90),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("iphone"),
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=145),
                "page_view",
                "sports",
                metadata={"path": "/category.html", "query": "?cat=sports", "category": "sports", "category_name": "Sports"},
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=175),
                "click",
                "sports",
                element="open-product",
                metadata=ml_product_metadata("shoes", source="category"),
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=200),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("shoes"),
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=250),
                "page_view",
                "home-appliances",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=home-appliances",
                    "category": "home-appliances",
                    "category_name": "Home Appliances",
                },
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=285),
                "click",
                "home-appliances",
                element="open-product",
                metadata=ml_product_metadata("vacuum", source="category"),
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=310),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("vacuum"),
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=360),
                "page_view",
                "books",
                metadata={"path": "/category.html", "query": "?cat=books", "category": "books", "category_name": "Books"},
            ),
            event(
                cross_category.id,
                cross_category.started_at + timedelta(seconds=392),
                "page_view",
                "beauty",
                metadata={"path": "/category.html", "query": "?cat=beauty", "category": "beauty", "category_name": "Beauty"},
            ),
        ]
        cross_category.page_count = 6
        db.add_all(cross_category_events)
        created_ids["cross_category_session_id"] = cross_category.id

        attribute_heavy = create_session(
            db,
            f"{DEMO_PREFIX}-attribute-heavy",
            "Defense demo browser (attribute heavy)",
            now - timedelta(minutes=3),
            640,
        )
        attribute_heavy_events = [
            event(attribute_heavy.id, attribute_heavy.started_at, "page_view", "home", metadata={"path": "/index.html", "query": None}),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=25),
                "page_view",
                "electronics",
                metadata={
                    "path": "/category.html",
                    "query": "?cat=electronics",
                    "category": "electronics",
                    "category_name": "Electronics",
                },
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=58),
                "click",
                "electronics",
                element="open-product",
                metadata=ml_product_metadata("iphone", source="category"),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=82),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("iphone"),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=130),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "iphone",
                    attribute_group="storage",
                    attribute_label="Storage",
                    attribute_value="256GB",
                    selected_attributes={"storage": "256GB"},
                ),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=168),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "iphone",
                    attribute_group="colors",
                    attribute_label="Color",
                    attribute_value="Gold",
                    selected_attributes={"storage": "256GB", "colors": "Gold"},
                ),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=218),
                "click",
                "electronics",
                element="open-product",
                metadata=ml_product_metadata("macbook", source="recommended-products"),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=242),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("macbook"),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=290),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "macbook",
                    attribute_group="storage",
                    attribute_label="Storage",
                    attribute_value="1TB",
                    selected_attributes={"storage": "1TB"},
                ),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=330),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "macbook",
                    attribute_group="colors",
                    attribute_label="Color",
                    attribute_value="Space Black",
                    selected_attributes={"storage": "1TB", "colors": "Space Black"},
                ),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=360),
                "click",
                "product",
                element="add-to-cart",
                metadata=ml_product_metadata(
                    "macbook",
                    selected_attributes={"storage": "1TB", "colors": "Space Black"},
                    quantity=1,
                    cart_size_after_add=1,
                ),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=402),
                "page_view",
                "clothing",
                metadata={"path": "/category.html", "query": "?cat=clothing", "category": "clothing", "category_name": "Clothing"},
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=434),
                "click",
                "clothing",
                element="open-product",
                metadata=ml_product_metadata("shoes", source="cross-sell"),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=458),
                "product_view",
                "product",
                element="product-detail",
                metadata=ml_product_metadata("shoes"),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=494),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "shoes",
                    attribute_group="sizes",
                    attribute_label="Size",
                    attribute_value="42",
                    selected_attributes={"sizes": "42"},
                ),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=536),
                "click",
                "product",
                element="select-attribute",
                metadata=ml_product_metadata(
                    "shoes",
                    attribute_group="colors",
                    attribute_label="Color",
                    attribute_value="White",
                    selected_attributes={"sizes": "42", "colors": "White"},
                ),
            ),
            event(
                attribute_heavy.id,
                attribute_heavy.started_at + timedelta(seconds=575),
                "click",
                "product",
                element="add-to-cart",
                metadata=ml_product_metadata(
                    "shoes",
                    selected_attributes={"sizes": "42", "colors": "White"},
                    quantity=1,
                    cart_size_after_add=2,
                ),
            ),
        ]
        attribute_heavy.page_count = 4
        db.add_all(attribute_heavy_events)
        created_ids["attribute_heavy_session_id"] = attribute_heavy.id

        db.commit()

    return created_ids


def main() -> None:
    """Run the full deterministic defense demo seeding flow."""
    args = parse_args()
    if args.reset_demo:
        reset_demo_records()

    ensure_admin(args.admin_email, args.admin_password)
    create_campaigns_and_ads()
    session_ids = seed_demo_sessions()

    print("Defense demo seed complete.")
    print()
    print("Admin:")
    print(f"  email: {args.admin_email}")
    print(f"  password: {args.admin_password}")
    print()
    print("Demo sessions:")
    for key in (
        "low_engagement_session_id",
        "medium_engagement_session_id",
        "high_intent_session_id",
        "window_shopper_session_id",
        "price_sensitive_session_id",
        "cross_category_session_id",
        "attribute_heavy_session_id",
    ):
        print(f"  {key}: {session_ids[key]}")
    print()
    print("Try placement:")
    print(f"  /ads/placement?page=home&session_id={session_ids['low_engagement_session_id']}")
    print(f"  /ads/placement?page=home&session_id={session_ids['medium_engagement_session_id']}")
    print(f"  /ads/placement?page=home&session_id={session_ids['high_intent_session_id']}")
    print(f"  /ads/placement?page=home&session_id={session_ids['window_shopper_session_id']}")
    print(f"  /ads/placement?page=home&session_id={session_ids['price_sensitive_session_id']}")
    print(f"  /ads/placement?page=home&session_id={session_ids['cross_category_session_id']}")
    print(f"  /ads/placement?page=home&session_id={session_ids['attribute_heavy_session_id']}")


if __name__ == "__main__":
    main()
