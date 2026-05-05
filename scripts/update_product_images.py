import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


BRAND_STOPWORDS = [
    "levi's",
    "levis",
    "nike",
    "adidas",
    "apple",
    "samsung",
    "sony",
    "dell",
    "hp",
    "loreal",
    "l'oreal",
    "maybelline",
    "zara",
    "h&m",
    "dyson",
    "bose",
    "garmin",
    "fitbit",
    "canon",
    "google",
    "amazon",
    "kitchenaid",
    "breville",
    "cuisinart",
    "keurig",
    "ninja",
    "instant pot",
    "under armour",
    "north face",
    "patagonia",
    "columbia",
    "puma",
    "uniqlo",
    "gap",
    "old navy",
    "lululemon",
]

PRODUCT_TYPE_QUERIES = {
    "t-shirt": "plain t shirt product photography isolated",
    "t shirt": "plain t shirt product photography isolated",
    "tee": "plain t shirt product photography isolated",
    "jeans": "blue denim jeans folded product photography",
    "denim": "blue denim jeans folded product photography",
    "shirt": "shirt product photography isolated",
    "hoodie": "hoodie product photography isolated",
    "sweatshirt": "sweatshirt product photography isolated",
    "jacket": "jacket product photography isolated",
    "dress": "dress product photography studio",
    "sneakers": "sneakers product photography isolated",
    "sneaker": "sneakers product photography isolated",
    "shoes": "shoes product photography isolated",
    "shoe": "shoes product photography isolated",
    "air force": "sneakers product photography isolated",
    "ultraboost": "running shoes product photography isolated",
    "pegasus": "running shoes product photography isolated",
    "metcon": "training shoes product photography isolated",
    "watch": "watch product photography isolated",
    "smartwatch": "smartwatch product photography isolated",
    "pixelbook": "laptop product photography isolated",
    "iphone": "smartphone product photography isolated",
    "pixel": "smartphone product photography isolated",
    "phone": "smartphone product photography isolated",
    "smartphone": "smartphone product photography isolated",
    "macbook": "laptop product photography isolated",
    "laptop": "laptop product photography isolated",
    "headphones": "headphones product photography isolated",
    "headphone": "headphones product photography isolated",
    "quietcomfort": "headphones product photography isolated",
    "earbuds": "wireless earbuds product photography isolated",
    "airpods": "wireless earbuds product photography isolated",
    "speaker": "speaker product photography isolated",
    "soundbar": "soundbar product photography isolated",
    "camera": "camera product photography isolated",
    "monitor": "computer monitor product photography isolated",
    "tablet": "tablet product photography isolated",
    "ipad": "tablet product photography isolated",
    "tv": "television product photography isolated",
    "book": "book cover product photography",
    "novel": "book cover product photography",
    "makeup": "makeup cosmetics product photography",
    "lipstick": "lipstick cosmetics product photography",
    "concealer": "makeup cosmetics product photography",
    "perfume": "perfume bottle product photography isolated",
    "serum": "skincare serum bottle product photography",
    "cream": "skincare cream product photography",
    "cleanser": "facial cleanser product photography",
    "sunscreen": "sunscreen skincare product photography",
    "mascara": "mascara cosmetics product photography",
    "hair dryer": "hair dryer product photography isolated",
    "ball": "sports ball product photography",
    "basketball": "basketball product photography isolated",
    "football": "soccer ball product photography isolated",
    "yoga": "yoga mat product photography",
    "mat": "yoga mat product photography",
    "dumbbells": "dumbbells product photography isolated",
    "kettlebell": "kettlebell product photography isolated",
    "bike": "exercise bike product photography isolated",
    "racket": "tennis racket product photography isolated",
    "cooler": "portable cooler product photography isolated",
    "tumbler": "insulated tumbler product photography isolated",
    "bottle": "water bottle product photography isolated",
    "vacuum": "vacuum cleaner product photography isolated",
    "blender": "kitchen blender product photography isolated",
    "microwave": "microwave oven product photography isolated",
    "coffee maker": "coffee maker product photography isolated",
    "espresso": "espresso machine product photography isolated",
    "mixer": "stand mixer product photography isolated",
    "airfryer": "air fryer product photography isolated",
    "oven": "countertop oven product photography isolated",
    "grill": "electric grill product photography isolated",
    "toothbrush": "electric toothbrush product photography isolated",
    "charger": "portable charger product photography isolated",
    "mouse": "computer mouse product photography isolated",
    "router": "wifi router product photography isolated",
    "doorbell": "video doorbell product photography isolated",
    "switch": "portable game console product photography isolated",
    "playstation": "game console product photography isolated",
    "kindle": "e reader product photography isolated",
}

CATEGORY_FALLBACK_QUERIES = {
    "electronics": "modern electronics device product photography isolated",
    "clothing": "fashion clothing item product photography isolated",
    "beauty": "cosmetics product photography isolated",
    "home-appliances": "home appliance product photography isolated",
    "books": "book product photography",
    "sports": "sports equipment product photography isolated",
}

QUALITY_RULES = {
    "blue denim jeans folded product photography": {
        "required": ["jeans", "denim", "pants"],
        "banned": ["shoe", "sneaker", "footwear", "boot"],
    },
    "plain t shirt product photography isolated": {
        "required": ["shirt", "t shirt", "tshirt", "tee"],
        "banned": ["shoe", "sneaker", "phone", "laptop"],
    },
    "shirt product photography isolated": {
        "required": ["shirt", "clothing", "apparel"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "hoodie product photography isolated": {
        "required": ["hoodie", "sweatshirt"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "sweatshirt product photography isolated": {
        "required": ["sweatshirt", "shirt", "clothing"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "jacket product photography isolated": {
        "required": ["jacket", "coat"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "dress product photography studio": {
        "required": ["dress", "gown"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "sneakers product photography isolated": {
        "required": ["shoe", "shoes", "sneaker", "sneakers", "footwear"],
        "banned": ["jeans", "pants", "shirt", "phone"],
    },
    "running shoes product photography isolated": {
        "required": ["shoe", "shoes", "sneaker", "sneakers", "footwear"],
        "banned": ["jeans", "pants", "shirt", "phone"],
    },
    "training shoes product photography isolated": {
        "required": ["shoe", "shoes", "sneaker", "sneakers", "footwear"],
        "banned": ["jeans", "pants", "shirt", "phone"],
    },
    "smartphone product photography isolated": {
        "required": ["phone", "smartphone", "mobile"],
        "banned": ["headphone", "headphones", "laptop", "tablet"],
    },
    "laptop product photography isolated": {
        "required": ["laptop", "computer", "notebook"],
        "banned": ["phone", "smartphone", "tablet", "headphones"],
    },
    "headphones product photography isolated": {
        "required": ["headphone", "headphones", "headset"],
        "banned": ["phone", "smartphone", "laptop"],
    },
    "smartwatch product photography isolated": {
        "required": ["watch", "smartwatch"],
        "banned": ["phone", "smartphone", "laptop"],
    },
    "wireless earbuds product photography isolated": {
        "required": ["earbuds", "earphones", "headphones"],
        "banned": ["phone", "smartphone", "laptop"],
    },
    "book product photography": {
        "required": ["book", "books"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "book cover product photography": {
        "required": ["book", "books", "cover"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "perfume bottle product photography isolated": {
        "required": ["perfume", "bottle", "fragrance"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "lipstick cosmetics product photography": {
        "required": ["lipstick", "cosmetic", "makeup"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "makeup cosmetics product photography": {
        "required": ["makeup", "cosmetic", "cosmetics"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "skincare cream product photography": {
        "required": ["cream", "skincare", "cosmetic"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "skincare serum bottle product photography": {
        "required": ["serum", "skincare", "bottle"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "cosmetics product photography isolated": {
        "required": ["cosmetic", "cosmetics", "makeup", "skincare"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "hair dryer product photography isolated": {
        "required": ["hair", "dryer"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "basketball product photography isolated": {
        "required": ["basketball", "ball"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "soccer ball product photography isolated": {
        "required": ["football", "soccer", "ball"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "yoga mat product photography": {
        "required": ["yoga", "mat"],
        "banned": ["phone", "laptop"],
    },
}

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY") or "FkLNr8WKUoKAeNjEc6wVMreMvJom3UdAUeMhYNbGd0y5NuPqUe6nJTcJ"

REQUEST_DELAY_SECONDS = 0.3
REQUEST_TIMEOUT_SECONDS = 20
RESULTS_PER_PAGE = 10

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_PATH = REPO_ROOT / "frontend" / "data" / "products.json"
BACKUP_PATH = REPO_ROOT / "frontend" / "data" / "products_backup.json"


def load_products() -> list[dict[str, Any]]:
    with PRODUCTS_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("products.json must contain a list of products")

    return data


def write_products(products: list[dict[str, Any]]) -> None:
    with PRODUCTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(products, file, indent=2, ensure_ascii=False)
        file.write("\n")


def create_backup() -> Path:
    shutil.copy2(PRODUCTS_PATH, BACKUP_PATH)
    return BACKUP_PATH


def normalize_for_matching(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def contains_product_type(name: str, product_type: str) -> bool:
    normalized_type = normalize_for_matching(product_type)
    return bool(re.search(rf"(^|\s){re.escape(normalized_type)}($|\s)", name))


def get_keyword(product: dict[str, Any]) -> str:
    cleaned_name = normalize_for_matching(str(product.get("name", "")))
    for brand in BRAND_STOPWORDS:
        normalized_brand = normalize_for_matching(brand)
        cleaned_name = re.sub(rf"(^|\s){re.escape(normalized_brand)}($|\s)", " ", cleaned_name)
    cleaned_name = " ".join(cleaned_name.split())

    for product_type, query in PRODUCT_TYPE_QUERIES.items():
        if contains_product_type(cleaned_name, product_type):
            return query

    category = str(product.get("category", ""))
    return CATEGORY_FALLBACK_QUERIES.get(category, "product photography isolated")


class PexelsClient:
    def __init__(self, api_key: str) -> None:
        self.headers = {
            "Authorization": api_key,
            "User-Agent": "NeonRetroImageUpdater/1.0",
        }
        self.last_request_at = 0.0

    def wait_if_needed(self) -> None:
        if not self.last_request_at:
            return

        elapsed = time.monotonic() - self.last_request_at
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)

    def search(self, query: str) -> dict[str, Any] | None:
        for orientation in ("square", "landscape"):
            photo = self.search_with_orientation(query, orientation)
            if photo:
                return photo
        return None

    def search_with_orientation(self, query: str, orientation: str) -> dict[str, Any] | None:
        params = urllib.parse.urlencode(
            {
                "query": query,
                "orientation": orientation,
                "per_page": RESULTS_PER_PAGE,
            }
        )

        request = urllib.request.Request(
            f"{PEXELS_SEARCH_URL}?{params}",
            headers=self.headers,
        )

        self.wait_if_needed()

        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            print(f"  HTTP {error.code}; skipped orientation={orientation}")
            return None
        except urllib.error.URLError as error:
            print(f"  Request failed; skipped orientation={orientation}: {error.reason}")
            return None
        except json.JSONDecodeError:
            print(f"  Invalid JSON; skipped orientation={orientation}")
            return None
        finally:
            self.last_request_at = time.monotonic()

        photos = payload.get("photos") or []
        if not photos:
            return None

        return select_best_photo(query, photos)


def text_has_term(text: str, term: str) -> bool:
    normalized_term = normalize_for_matching(term)
    return bool(re.search(rf"(^|\s){re.escape(normalized_term)}($|\s)", text))


def photo_text(photo: dict[str, Any]) -> str:
    parts = [
        str(photo.get("alt") or ""),
        str(photo.get("url") or ""),
        str(photo.get("photographer") or ""),
    ]
    return normalize_for_matching(" ".join(parts))


def score_photo(query: str, photo: dict[str, Any]) -> int | None:
    text = photo_text(photo)
    rules = QUALITY_RULES.get(query, {})
    required = rules.get("required", [])
    banned = rules.get("banned", [])

    if any(text_has_term(text, term) for term in banned):
        return None

    matched_required = sum(1 for term in required if text_has_term(text, term))
    if required and matched_required == 0:
        return None

    score = matched_required * 10
    for term in query.split():
        if len(term) > 3 and text_has_term(text, term):
            score += 1

    width = photo.get("width") or 0
    height = photo.get("height") or 0
    if isinstance(width, int) and isinstance(height, int) and width and height:
        ratio = width / height
        if 0.8 <= ratio <= 1.4:
            score += 2

    return score


def select_best_photo(query: str, photos: list[dict[str, Any]]) -> dict[str, Any] | None:
    scored: list[tuple[int, dict[str, Any]]] = []
    for photo in photos:
        score = score_photo(query, photo)
        if score is not None:
            scored.append((score, photo))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def apply_photo(product: dict[str, Any], photo: dict[str, Any]) -> bool:
    src = photo.get("src") or {}
    image_url = src.get("large") or src.get("medium")

    if not image_url:
        return False

    product["image"] = image_url
    product["image_source"] = "pexels"
    product["image_photographer"] = photo.get("photographer")
    product["image_photographer_url"] = photo.get("photographer_url")
    product["image_pexels_url"] = photo.get("url")
    return True


def main() -> None:
    if not PEXELS_API_KEY:
        raise SystemExit("PEXELS_API_KEY is required.")

    products = load_products()
    backup_path = create_backup()
    client = PexelsClient(PEXELS_API_KEY)

    updated_count = 0
    skipped_count = 0

    print(f"Backup created: {backup_path}")

    for product in products:
        product_id = product.get("id")
        name = product.get("name", "Unknown product")
        old_image = product.get("image")

        product.pop("variants", None)

        query = get_keyword(product)

        try:
            photo = client.search(query)
            if photo and apply_photo(product, photo):
                updated_count += 1
                status = "updated"
            else:
                product["image"] = old_image
                skipped_count += 1
                status = "skipped"
        except Exception as error:
            product["image"] = old_image
            skipped_count += 1
            status = f"skipped ({error.__class__.__name__})"

        print(f"{product_id} | {name} | {query} | {status}")

    write_products(products)

    remaining_variants = sum(1 for product in products if "variants" in product)
    pexels_images = sum(
        1
        for product in products
        if isinstance(product.get("image"), str) and "pexels.com" in product["image"]
    )

    print("=== SUMMARY ===")
    print(f"Processed: {len(products)}")
    print(f"Updated: {updated_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Pexels images: {pexels_images}")
    print(f"Remaining variants: {remaining_variants}")


if __name__ == "__main__":
    main()
