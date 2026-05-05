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


PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY") or "FkLNr8WKUoKAeNjEc6wVMreMvJom3UdAUeMhYNbGd0y5NuPqUe6nJTcJ"

REQUEST_DELAY_SECONDS = 0.3
REQUEST_TIMEOUT_SECONDS = 20
RESULTS_PER_PAGE = 30

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "frontend" / "data"
PRODUCTS_PATH = DATA_DIR / "products.json"
BACKUP_PATH = DATA_DIR / "products_backup.json"
QUERY_OVERRIDES_PATH = DATA_DIR / "product_image_queries.json"
IMAGE_OVERRIDES_PATH = DATA_DIR / "product_image_overrides.json"

TYPE_RULES = {
    "phone": {
        "patterns": [r"\biphone\b", r"\bpixel\s+6\b", r"\bsmartphone\b", r"\bphone\b"],
        "queries": ["smartphone product photography isolated", "mobile phone product photography studio"],
        "required": ["phone", "smartphone", "mobile"],
        "banned": ["headphone", "headphones", "earbuds", "laptop", "camera"],
    },
    "headphones": {
        "patterns": [r"\bheadphones?\b", r"\bquietcomfort\b", r"\bheadset\b"],
        "queries": ["headphones product photography isolated", "wireless headphones product photography studio"],
        "required": ["headphone", "headphones", "earbuds", "earphone", "headset"],
        "banned": ["phone", "smartphone", "laptop"],
    },
    "earbuds": {
        "patterns": [r"\bearbuds?\b", r"\bearphones?\b", r"\bairpods\b"],
        "queries": ["wireless earbuds product photography isolated", "earbuds product photography studio"],
        "required": ["earbuds", "earphone", "earphones", "headphones"],
        "banned": ["phone", "smartphone", "laptop"],
    },
    "laptop": {
        "patterns": [r"\bmacbook\b", r"\bpixelbook\b", r"\blaptop\b", r"\bnotebook\b"],
        "queries": ["laptop product photography isolated", "notebook computer product photography studio"],
        "required": ["laptop", "computer", "notebook"],
        "banned": ["phone", "smartphone", "tablet", "headphones"],
    },
    "jeans": {
        "patterns": [r"\bjeans\b", r"\bdenim\b", r"\bpants\b", r"\btrousers\b"],
        "queries": ["blue denim jeans product photography", "folded jeans product photography"],
        "required": ["jeans", "denim", "pants", "trousers"],
        "banned": ["shoe", "shoes", "sneaker", "sneakers", "footwear", "boot"],
    },
    "sneakers": {
        "patterns": [r"\bsneakers?\b", r"\bshoes?\b", r"\bair\s+force\b", r"\bultraboost\b", r"\bpegasus\b", r"\bmetcon\b"],
        "queries": ["sneakers product photography isolated", "running shoes product photography isolated"],
        "required": ["shoe", "shoes", "sneaker", "sneakers", "footwear"],
        "banned": ["jeans", "denim", "pants", "shirt"],
    },
    "t-shirt": {
        "patterns": [r"\bt[\s-]?shirt\b", r"\btee\b"],
        "queries": ["plain t shirt product photography isolated", "cotton t shirt product photography studio"],
        "required": ["shirt", "t shirt", "tshirt", "tee"],
        "banned": ["shoe", "sneaker", "phone", "laptop"],
    },
    "shirt": {
        "patterns": [r"\bshirt\b", r"\bpolo\b"],
        "queries": ["shirt product photography isolated", "folded shirt product photography studio"],
        "required": ["shirt", "clothing", "apparel"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "hoodie": {
        "patterns": [r"\bhoodie\b"],
        "queries": ["hoodie product photography isolated", "fleece hoodie product photography studio"],
        "required": ["hoodie", "sweatshirt"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "jacket": {
        "patterns": [r"\bjacket\b", r"\bcoat\b"],
        "queries": ["jacket product photography isolated", "outerwear jacket product photography studio"],
        "required": ["jacket", "coat"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "dress": {
        "patterns": [r"\bdress\b"],
        "queries": ["dress product photography studio", "summer dress product photography isolated"],
        "required": ["dress", "gown"],
        "banned": ["shoe", "sneaker", "phone"],
    },
    "watch": {
        "patterns": [r"\bwatch\b", r"\bsmartwatch\b", r"\bforerunner\b", r"\bfenix\b", r"\bversa\b", r"\binspire\b", r"\bluxe\b", r"\bvantage\b"],
        "queries": ["watch product photography isolated", "smartwatch product photography studio"],
        "required": ["watch", "smartwatch"],
        "banned": ["phone", "smartphone", "laptop"],
    },
    "perfume": {
        "patterns": [r"\bperfume\b", r"\bfragrance\b", r"\bcologne\b"],
        "queries": ["perfume bottle product photography isolated", "fragrance bottle product photography studio"],
        "required": ["perfume", "bottle", "fragrance"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "lipstick": {
        "patterns": [r"\blipstick\b", r"\blip\s+treatment\b"],
        "queries": ["lipstick cosmetics product photography", "lipstick product photography isolated"],
        "required": ["lipstick", "cosmetic", "makeup"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "cream": {
        "patterns": [r"\bcream\b", r"\bmoistur", r"\blotion\b"],
        "queries": ["skincare cream product photography", "face cream jar product photography"],
        "required": ["cream", "skincare", "cosmetic"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "serum": {
        "patterns": [r"\bserum\b", r"\bnight\s+repair\b", r"\brecovery\b"],
        "queries": ["skincare serum bottle product photography", "face serum product photography studio"],
        "required": ["serum", "skincare", "bottle"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "book": {
        "patterns": [r"\bbook\b", r"\bnovel\b", r"\bdune\b", r"\b1984\b", r"\bharry\s+potter\b", r"\bda\s+vinci\b", r"\bhobbit\b", r"\bmockingbird\b"],
        "queries": ["book product photography", "books reading product photography"],
        "required": ["book", "books", "novel", "reading"],
        "banned": ["laptop", "phone", "perfume", "shoes"],
    },
    "yoga_mat": {
        "patterns": [r"\byoga\s+mat\b", r"\bmat\b"],
        "queries": ["yoga mat product photography", "rolled yoga mat product photography"],
        "required": ["yoga mat", "yoga", "mat"],
        "banned": ["ultimate", "phone", "laptop", "book"],
    },
    "ball": {
        "patterns": [r"\bbasketball\b", r"\bfootball\b", r"\bsoccer\b", r"\bballs?\b"],
        "queries": ["sports ball product photography isolated", "basketball soccer ball product photography"],
        "required": ["ball", "basketball", "football", "soccer"],
        "banned": ["shoe", "phone", "laptop"],
    },
    "camera": {
        "patterns": [r"\bcamera\b", r"\beos\b", r"\bgopro\b"],
        "queries": ["camera product photography isolated", "digital camera product photography studio"],
        "required": ["camera"],
        "banned": ["phone", "laptop", "headphones"],
    },
    "refrigerator": {
        "patterns": [r"\brefrigerator\b", r"\bfridge\b"],
        "queries": ["refrigerator product photography isolated", "modern fridge product photography"],
        "required": ["refrigerator", "fridge"],
        "banned": ["phone", "shoe", "book"],
    },
    "washing_machine": {
        "patterns": [r"\bwashing\s+machine\b", r"\bwasher\b"],
        "queries": ["washing machine product photography isolated", "front load washer product photography"],
        "required": ["washing", "washer", "machine"],
        "banned": ["phone", "shoe", "book"],
    },
    "blender": {
        "patterns": [r"\bblender\b"],
        "queries": ["kitchen blender product photography isolated", "countertop blender product photography"],
        "required": ["blender"],
        "banned": ["phone", "shoe", "book"],
    },
    "coffee_maker": {
        "patterns": [r"\bcoffee\s+maker\b", r"\bcoffee\s+center\b", r"\bk-elite\b", r"\bk-mini\b", r"\bflexbrew\b"],
        "queries": ["coffee maker product photography isolated", "coffee machine product photography studio"],
        "required": ["coffee", "maker", "machine"],
        "banned": ["phone", "shoe", "book"],
    },
    "microwave": {
        "patterns": [r"\bmicrowave\b"],
        "queries": ["microwave oven product photography isolated", "countertop microwave product photography"],
        "required": ["microwave", "oven"],
        "banned": ["phone", "shoe", "book"],
    },
}

CATEGORY_FALLBACK_QUERIES = {
    "electronics": ["modern electronics device product photography isolated", "consumer electronics product photography"],
    "clothing": ["fashion clothing item product photography isolated", "apparel product photography studio"],
    "beauty": ["cosmetics product photography isolated", "beauty product photography studio"],
    "home-appliances": ["home appliance product photography isolated", "kitchen appliance product photography"],
    "books": ["book product photography", "books reading product photography"],
    "sports": ["sports equipment product photography isolated", "fitness equipment product photography"],
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_products() -> list[dict[str, Any]]:
    data = load_json(PRODUCTS_PATH, [])
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


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def has_term(text: str, term: str) -> bool:
    normalized = normalize_text(term)
    return bool(re.search(rf"(^|\s){re.escape(normalized)}($|\s)", text))


def detect_product_type(product: dict[str, Any]) -> str | None:
    name = normalize_text(str(product.get("name", "")))
    for product_type, rule in TYPE_RULES.items():
        if any(re.search(pattern, name) for pattern in rule["patterns"]):
            return product_type
    if product.get("category") == "books":
        return "book"
    return None


def get_auto_queries(product: dict[str, Any], product_type: str | None) -> list[str]:
    if product_type:
        return list(TYPE_RULES[product_type]["queries"])[:2]
    return CATEGORY_FALLBACK_QUERIES.get(str(product.get("category", "")), ["product photography isolated"])[:2]


def get_queries(product: dict[str, Any], query_overrides: dict[str, Any], product_type: str | None) -> list[str]:
    override = query_overrides.get(str(product.get("id")))
    if isinstance(override, list) and override:
        return [str(query) for query in override[:2]]
    return get_auto_queries(product, product_type)


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

    def search(self, query: str) -> list[dict[str, Any]]:
        photos: list[dict[str, Any]] = []
        for orientation in ("square", "landscape"):
            photos.extend(self.search_with_orientation(query, orientation))
        return photos

    def search_with_orientation(self, query: str, orientation: str) -> list[dict[str, Any]]:
        params = urllib.parse.urlencode(
            {
                "query": query,
                "orientation": orientation,
                "per_page": RESULTS_PER_PAGE,
            }
        )
        request = urllib.request.Request(f"{PEXELS_SEARCH_URL}?{params}", headers=self.headers)

        self.wait_if_needed()
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            print(f"  HTTP {error.code}; skipped query={query} orientation={orientation}")
            return []
        except urllib.error.URLError as error:
            print(f"  Request failed; skipped query={query} orientation={orientation}: {error.reason}")
            return []
        except json.JSONDecodeError:
            print(f"  Invalid JSON; skipped query={query} orientation={orientation}")
            return []
        finally:
            self.last_request_at = time.monotonic()

        return payload.get("photos") or []


def image_url(photo: dict[str, Any]) -> str | None:
    src = photo.get("src") or {}
    return src.get("large2x") or src.get("large") or src.get("medium")


def photo_text(photo: dict[str, Any]) -> str:
    src = photo.get("src") or {}
    parts = [
        str(photo.get("alt") or ""),
        str(photo.get("url") or ""),
        " ".join(str(value) for value in src.values()),
    ]
    return normalize_text(" ".join(parts))


def query_terms(query: str) -> list[str]:
    ignored = {"product", "photography", "isolated", "studio"}
    return [term for term in normalize_text(query).split() if len(term) > 3 and term not in ignored]


def score_photo(
    photo: dict[str, Any],
    query: str,
    product_type: str | None,
    used_image_urls: set[str],
    allow_duplicate: bool,
) -> tuple[int, str] | None:
    selected_url = image_url(photo)
    if not selected_url:
        return None

    text = photo_text(photo)
    alt = normalize_text(str(photo.get("alt") or ""))
    required = TYPE_RULES.get(product_type or "", {}).get("required", [])
    banned = TYPE_RULES.get(product_type or "", {}).get("banned", [])

    if any(has_term(text, term) for term in banned):
        return None

    required_hits = sum(1 for term in required if has_term(alt, term))
    if product_type and required and required_hits == 0:
        return None

    duplicate = selected_url in used_image_urls
    if duplicate and not allow_duplicate:
        return None

    score = required_hits * 10
    score += sum(6 for term in query_terms(query) if has_term(alt, term))

    width = photo.get("width")
    height = photo.get("height")
    if isinstance(width, int) and isinstance(height, int):
        if width >= 1000 and height >= 1000:
            score += 3
        if height:
            ratio = width / height
            if 0.75 <= ratio <= 1.5:
                score += 2

    if duplicate:
        score -= 5

    return score, selected_url


def choose_photo(
    candidates: list[tuple[str, dict[str, Any]]],
    product_type: str | None,
    used_image_urls: set[str],
) -> tuple[dict[str, Any], str, int, str] | None:
    for allow_duplicate in (False, True):
        scored: list[tuple[int, dict[str, Any], str, str]] = []
        for query, photo in candidates:
            result = score_photo(photo, query, product_type, used_image_urls, allow_duplicate)
            if result is None:
                continue
            score, selected_url = result
            scored.append((score, photo, query, selected_url))
        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            score, photo, query, selected_url = scored[0]
            return photo, query, score, selected_url
    return None


def apply_photo(product: dict[str, Any], selected_url: str) -> None:
    product["image"] = selected_url
    product.pop("variants", None)
    product.pop("image_source", None)
    product.pop("image_photographer", None)
    product.pop("image_photographer_url", None)
    product.pop("image_pexels_url", None)


def report_entry(
    product: dict[str, Any],
    product_type: str | None,
    query: str,
    image: str | None,
    alt_text: str,
    score: int | str,
    status: str,
) -> dict[str, Any]:
    return {
        "id": product.get("id"),
        "name": product.get("name"),
        "category": product.get("category"),
        "detected_type": product_type or "unknown",
        "query_used": query,
        "selected_image": image,
        "alt_text": alt_text,
        "score": score,
        "status": status,
    }


def main() -> None:
    if not PEXELS_API_KEY:
        raise SystemExit("PEXELS_API_KEY is required.")

    products = load_products()
    query_overrides = load_json(QUERY_OVERRIDES_PATH, {})
    image_overrides = load_json(IMAGE_OVERRIDES_PATH, {})
    backup_path = create_backup()
    client = PexelsClient(PEXELS_API_KEY)
    used_image_urls: set[str] = set()
    report: list[dict[str, Any]] = []
    updated_count = 0
    skipped_count = 0

    print(f"Backup created: {backup_path}")

    for product in products:
        product_id = str(product.get("id"))
        old_image = product.get("image")
        product_type = detect_product_type(product)
        queries = get_queries(product, query_overrides, product_type)

        if isinstance(image_overrides.get(product_id), str):
            selected_url = image_overrides[product_id]
            apply_photo(product, selected_url)
            used_image_urls.add(selected_url)
            updated_count += 1
            entry = report_entry(product, product_type, "manual override", selected_url, "manual override", "override", "updated")
            report.append(entry)
            print(f"{product_id} | {product.get('name')} | {entry['detected_type']} | manual override | updated")
            continue

        candidates: list[tuple[str, dict[str, Any]]] = []
        for query in queries:
            for photo in client.search(query):
                candidates.append((query, photo))

        choice = choose_photo(candidates, product_type, used_image_urls)
        if choice:
            photo, query_used, score, selected_url = choice
            apply_photo(product, selected_url)
            used_image_urls.add(selected_url)
            updated_count += 1
            entry = report_entry(product, product_type, query_used, selected_url, str(photo.get("alt") or ""), score, "updated")
        else:
            product["image"] = old_image
            product.pop("variants", None)
            if isinstance(old_image, str):
                used_image_urls.add(old_image)
            skipped_count += 1
            entry = report_entry(product, product_type, queries[0] if queries else "", old_image, "", "skipped", "skipped")

        report.append(entry)
        print(
            f"{product_id} | {product.get('name')} | {entry['detected_type']} | "
            f"{entry['query_used']} | {entry['status']} | score={entry['score']}"
        )

    write_products(products)

    duplicates = len(products) - len({product.get("image") for product in products if product.get("image")})
    missing_image = [product.get("id") for product in products if not product.get("image")]
    remaining_variants = [product.get("id") for product in products if "variants" in product]
    non_pexels = [product.get("id") for product in products if "pexels.com" not in str(product.get("image", ""))]

    print("=== SUMMARY ===")
    print(f"total: {len(products)}")
    print(f"missing_image: {len(missing_image)}")
    print(f"remaining_variants: {len(remaining_variants)}")
    print(f"non_pexels: {len(non_pexels)}")
    print(f"duplicated_image_count: {duplicates}")
    print(f"updated_count: {updated_count}")
    print(f"skipped_count: {skipped_count}")

    important_names = (
        "Levi's 501 Jeans",
        "Nike Air Force 1",
        "Adidas Ultraboost Shoes",
        "iPhone 14 Pro",
        "Google Pixel 6 Pro",
        "MacBook Pro 16-inch",
        "HP Spectre x360 Laptop",
        "Sony WH-1000XM4 Headphones",
        "Yoga Mat",
        "Dune",
        "1984",
        "Harry Potter",
        "Chanel",
        "Lipstick",
        "Cream",
    )
    print("=== IMPORTANT SAMPLE ===")
    for entry in report:
        name = str(entry["name"])
        if any(term.lower() in name.lower() for term in important_names):
            print(
                f"{entry['id']} | {entry['name']} | {entry['detected_type']} | "
                f"{entry['query_used']} | {entry['selected_image']} | {entry['alt_text']} | {entry['score']}"
            )


if __name__ == "__main__":
    main()
