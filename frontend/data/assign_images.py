import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_KEY = "FkLNr8WKUoKAeNjEc6wVMreMvJom3UdAUeMhYNbGd0y5NuPqUe6nJTcJ"
BASE_URL = "https://api.pexels.com/v1/search"
HEADERS = {
    "Authorization": API_KEY,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
SUPPORTED_COLOR_FILTERS = {
    "black",
    "white",
    "red",
    "green",
    "blue",
    "gray",
    "brown",
    "pink",
    "yellow",
    "orange",
}
DATA_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = DATA_DIR / "products.json"
CACHE_PATH = DATA_DIR / "image_cache.json"
OUTPUT_PATH = DATA_DIR / "products_updated.json"
API_SLEEP_SECONDS = 0.35
RETRY_SLEEP_SECONDS = 10


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_cache(cache: dict[str, str]) -> None:
    with CACHE_PATH.open("w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2, ensure_ascii=False)


def normalize_color(value: str) -> str:
    return value.strip().lower()


def build_cache_key(query: str, color_filter: str | None) -> str:
    return f"{query} | color={color_filter}" if color_filter else query


class PexelsClient:
    def __init__(self, cache: dict[str, str]):
        self.cache = cache
        self.api_calls_since_save = 0
        self.last_api_call_at = 0.0
        self.cache_hits = 0
        self.success_count = 0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self.last_api_call_at
        if elapsed < API_SLEEP_SECONDS:
            time.sleep(API_SLEEP_SECONDS - elapsed)

    def _request(self, query: str, color_filter: str | None) -> str | None:
        params = {"query": query, "per_page": 1}
        if color_filter:
            params["color"] = color_filter
        url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers=HEADERS)

        for attempt in range(2):
            try:
                self._rate_limit()
                with urllib.request.urlopen(request, timeout=30) as response:
                    self.last_api_call_at = time.time()
                    self.api_calls_since_save += 1
                    if self.api_calls_since_save >= 10:
                        save_cache(self.cache)
                        self.api_calls_since_save = 0
                    payload = json.load(response)
                    photos = payload.get("photos") or []
                    if not photos:
                        return None
                    src = photos[0].get("src") or {}
                    image_url = src.get("medium")
                    if image_url:
                        self.success_count += 1
                    return image_url
            except urllib.error.HTTPError as error:
                self.last_api_call_at = time.time()
                if error.code == 429 and attempt == 0:
                    time.sleep(RETRY_SLEEP_SECONDS)
                    continue
                return None
            except Exception:
                self.last_api_call_at = time.time()
                return None

        return None

    def fetch(self, query: str, color_filter: str | None = None) -> str | None:
        cache_key = build_cache_key(query, color_filter)
        cached = self.cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            return cached

        image_url = self._request(query, color_filter)
        if image_url:
            self.cache[cache_key] = image_url
        return image_url

    def flush(self) -> None:
        save_cache(self.cache)


def get_brand(product: dict) -> str:
    attributes = product.get("attributes") or {}
    brand = attributes.get("brand")
    return brand if isinstance(brand, str) else ""


def get_author(product: dict) -> str:
    attributes = product.get("attributes") or {}
    author = attributes.get("author")
    return author if isinstance(author, str) else ""


def get_colors(product: dict) -> list[str]:
    attributes = product.get("attributes") or {}
    colors = attributes.get("colors")
    return colors if isinstance(colors, list) else []


def assign_clothing_images(product: dict, client: PexelsClient) -> tuple[str, dict, int]:
    variant_images = {"color": {}}
    default_image = product["image"]
    clothing_variants_fetched = 0

    for color in get_colors(product):
        normalized = normalize_color(color)
        if normalized in SUPPORTED_COLOR_FILTERS:
            query = f'{product["name"]} {color}'
            color_filter = normalized
        else:
            query = f'{product["name"]} {color} clothing'
            color_filter = None

        image_url = client.fetch(query, color_filter=color_filter)
        if not image_url:
            continue

        variant_images["color"][normalized] = image_url
        clothing_variants_fetched += 1
        if default_image == product["image"]:
            default_image = image_url

    return default_image, variant_images, clothing_variants_fetched


def assign_non_clothing_image(product: dict, client: PexelsClient) -> tuple[str, str, dict]:
    category = product["category"]
    brand = get_brand(product)

    if category == "electronics":
        image_strategy = "css-filter"
        query = f'{brand} {product["name"]} product technology'.strip()
    elif category == "sports":
        image_strategy = "css-filter"
        query = f'{product["name"]} sport equipment'
    elif category == "home-appliances":
        image_strategy = "css-filter"
        if brand == "Generic":
            query = f'{product["name"]} home appliance'
        else:
            query = f"{brand} {product['name']} appliance"
    elif category == "beauty":
        image_strategy = "single"
        query = f"{brand} {product['name']} beauty cosmetic".strip()
    elif category == "books":
        image_strategy = "single"
        author = get_author(product)
        query = f"{product['name']} {author} book".strip()
    else:
        image_strategy = "single"
        query = product["name"]

    image_url = client.fetch(query) or product["image"]
    return image_url, image_strategy, {}


def main() -> None:
    products = load_json(PRODUCTS_PATH, [])
    cache = load_json(CACHE_PATH, {})
    client = PexelsClient(cache)

    updated_products = []
    fallback_used = 0
    clothing_variants_fetched = 0

    total = len(products)
    for index, product in enumerate(products, start=1):
        print(f'[{index}/{total}] {product["category"]} - {product["name"]}')

        updated_product = dict(product)
        if product["category"] == "clothing":
            default_image, variant_images, fetched_count = assign_clothing_images(product, client)
            image_strategy = "per-color"
            clothing_variants_fetched += fetched_count
        else:
            default_image, image_strategy, variant_images = assign_non_clothing_image(product, client)

        if default_image == product["image"]:
            fallback_used += 1

        updated_product["defaultImage"] = default_image
        updated_product["imageStrategy"] = image_strategy
        updated_product["variantImages"] = variant_images
        updated_products.append(updated_product)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(updated_products, file, indent=2, ensure_ascii=False)
        file.write("\n")

    client.flush()

    print("=== SUMMARY ===")
    print(f"Total: {total}")
    print(f"Success (Pexels): {client.success_count}")
    print(f"From cache: {client.cache_hits}")
    print(f"Fallback used: {fallback_used}")
    print(f"Clothing variants fetched: {clothing_variants_fetched}")


if __name__ == "__main__":
    main()
