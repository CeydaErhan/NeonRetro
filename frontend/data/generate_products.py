import csv
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


CATEGORY_MAP = {
    "Electronics": ("electronics", "Electronics"),
    "Clothing": ("clothing", "Clothing"),
    "Beauty Products": ("beauty", "Beauty"),
    "Home Appliances": ("home-appliances", "Home Appliances"),
    "Books": ("books", "Books"),
    "Sports": ("sports", "Sports"),
}

CATEGORY_HINTS = {
    "electronics": ["device", "gadget", "tech"],
    "clothing": ["apparel", "fashion", "wear"],
    "beauty": ["cosmetic", "skincare", "makeup"],
    "home-appliances": ["appliance", "home", "kitchen"],
    "books": ["book", "novel", "cover"],
    "sports": ["fitness", "sport", "gear"],
}

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"
IMAGE_CACHE_VERSION = 5
IMAGE_CACHE_FILENAME = "product_image_cache.json"
PRODUCT_IMAGE_DIR = "assets/products"
FALLBACK_DIR = "fallbacks"
MIN_MATCH_SCORE = 6.0
MAX_SEARCH_RESULTS = 8
REQUEST_TIMEOUT_SECONDS = 8
SEARCH_MIN_INTERVAL_SECONDS = 1.0
SEARCH_RETRY_DELAYS_SECONDS = (2.0, 5.0, 10.0)

STOPWORDS = {
    "and",
    "edition",
    "for",
    "kit",
    "new",
    "set",
    "the",
    "with",
}

BANNED_IMAGE_TOKENS = {
    "advertisement",
    "banner",
    "diagram",
    "drawing",
    "icon",
    "illustration",
    "label",
    "logo",
    "poster",
    "symbol",
    "vector",
}

GENERIC_BRANDS = {"Generic", "Unknown Author"}

FALLBACK_SVGS = {
    "electronics": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#08121f"/>
  <rect x="44" y="44" width="312" height="312" rx="36" fill="#0d1d31" stroke="#00d4ff" stroke-width="8"/>
  <rect x="104" y="90" width="192" height="220" rx="24" fill="#09111b" stroke="#00ff88" stroke-width="8"/>
  <circle cx="200" cy="280" r="12" fill="#00ff88"/>
  <text x="200" y="340" fill="#e5f7ff" font-family="Arial, sans-serif" font-size="28" font-weight="700" text-anchor="middle">Electronics</text>
</svg>
""",
    "clothing": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#1d1020"/>
  <path d="M140 76l28 36h64l28-36 52 36-34 52-34-18v150H156V146l-34 18-34-52z" fill="#ff2d75" stroke="#ffd6e7" stroke-width="8" stroke-linejoin="round"/>
  <text x="200" y="342" fill="#ffe7ef" font-family="Arial, sans-serif" font-size="28" font-weight="700" text-anchor="middle">Clothing</text>
</svg>
""",
    "beauty": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#1f0b16"/>
  <rect x="154" y="70" width="92" height="64" rx="14" fill="#ffd3e3"/>
  <rect x="130" y="128" width="140" height="182" rx="24" fill="#ff6fa7" stroke="#fff0f5" stroke-width="8"/>
  <path d="M170 110h60" stroke="#a3124d" stroke-width="10" stroke-linecap="round"/>
  <circle cx="200" cy="214" r="34" fill="#fff2f7"/>
  <text x="200" y="346" fill="#fff0f5" font-family="Arial, sans-serif" font-size="28" font-weight="700" text-anchor="middle">Beauty</text>
</svg>
""",
    "home-appliances": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#101820"/>
  <rect x="108" y="64" width="184" height="256" rx="24" fill="#e9eef2" stroke="#5d6d7e" stroke-width="8"/>
  <circle cx="200" cy="200" r="52" fill="#b8c4cf" stroke="#5d6d7e" stroke-width="8"/>
  <circle cx="200" cy="200" r="22" fill="#6e7e8d"/>
  <text x="200" y="352" fill="#f7fbff" font-family="Arial, sans-serif" font-size="24" font-weight="700" text-anchor="middle">Home Appliances</text>
</svg>
""",
    "books": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#13101f"/>
  <path d="M108 84h144c24 0 40 10 40 34v180c0 18-10 26-28 26H132c-20 0-32-10-32-30V110c0-18 10-26 32-26z" fill="#00d4ff"/>
  <path d="M140 84h132c18 0 28 10 28 28v184c0 18-10 28-28 28H140z" fill="#0d2a4d"/>
  <path d="M154 132h92M154 170h92M154 208h92" stroke="#9ee8ff" stroke-width="10" stroke-linecap="round"/>
  <text x="200" y="346" fill="#eef9ff" font-family="Arial, sans-serif" font-size="28" font-weight="700" text-anchor="middle">Books</text>
</svg>
""",
    "sports": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#0b1d16"/>
  <circle cx="200" cy="172" r="86" fill="#00ff88" stroke="#d8ffea" stroke-width="8"/>
  <path d="M142 128c38 12 78 44 116 102M258 128c-38 12-78 44-116 102M116 172h168" stroke="#0b1d16" stroke-width="8" stroke-linecap="round"/>
  <text x="200" y="336" fill="#ebfff4" font-family="Arial, sans-serif" font-size="28" font-weight="700" text-anchor="middle">Sports</text>
</svg>
""",
}

SHOE_KEYWORDS = [
    "shoes",
    "sneaker",
    "air force",
    "ultraboost",
    "990v5",
    "boot",
    "jordan",
    "runner",
    "trainer",
]

SPORTS_SHOE_KEYWORDS = ["shoe", "sneaker", "boot", "runner", "trainer"]

NO_SIZE_CLOTHING = [
    "sunglasses",
    "glasses",
    "watch",
    "wallet",
    "bag",
    "backpack",
    "purse",
    "jewel",
    "bracelet",
    "necklace",
    "earring",
    "ring",
    "perfume",
    "cologne",
]

SPORTS_NO_SIZE_BRANDS = [
    "Garmin",
    "Fitbit",
    "Polar",
    "GoPro",
    "Bose",
    "Yeti",
    "YETI",
    "Hydro Flask",
    "Bowflex",
    "TRX",
    "TriggerPoint",
    "Rogue",
    "Spalding",
    "Titleist",
    "Hyperice",
]

CLOTHING_KEYWORDS = [
    "jeans",
    "leggings",
    "dress",
    "shirt",
    "sweater",
    "t-shirt",
    "tshirt",
    "top",
    "jacket",
    "coat",
    "hoodie",
    "sweatshirt",
    "shorts",
    "pants",
    "trouser",
    "skirt",
    "blouse",
    "cardigan",
    "vest",
    "polo",
    "tee",
    "pullover",
    "windbreaker",
    "parka",
    "blazer",
    "suit",
    "romper",
    "jumpsuit",
    "bodysuit",
    "tank",
    "camisole",
    "bra",
    "underwear",
    "brief",
    "boxer",
    "sock",
    "legging",
    "tracksuit",
    "sweatpant",
    "jogger",
    "overall",
    "dungaree",
    "tunic",
    "kaftan",
    "kurta",
    "saree",
    "kimono",
    "robe",
    "nightwear",
    "pajama",
    "swimwear",
    "bikini",
    "wetsuit",
    "glove",
    "mitten",
    "scarf",
    "hat",
    "cap",
    "beanie",
    "sunglasses",
    "belt",
    "bag",
    "backpack",
    "wallet",
    "purse",
    "watch",
    "bracelet",
    "necklace",
    "earring",
    "ring",
]


def contains_any(name: str, needles: list[str]) -> bool:
    return any(needle in name for needle in needles)


def slugify(name: str) -> str:
    lowered = name.lower().strip()
    cleaned = re.sub(r"[^a-z0-9\s-]", "", lowered)
    collapsed = re.sub(r"[\s_-]+", "-", cleaned).strip("-")
    return collapsed or "product"


def normalize_text(value: str) -> str:
    lowered = value.lower()
    sanitized = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", sanitized).strip()


def tokenize(value: str) -> list[str]:
    tokens = []
    for token in normalize_text(value).split():
        if len(token) < 2 or token in STOPWORDS:
            continue
        tokens.append(token)
    return tokens


def resolve_csv_path(repo_root: Path) -> Path:
    preferred = repo_root / "frontend" / "data" / "Online Sales Data.csv"
    fallback = repo_root / "frontend" / "Online Sales Data.csv"
    if preferred.exists():
        return preferred
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        "Could not find 'Online Sales Data.csv' in frontend/data/ or frontend/."
    )


def electronics_attributes(product_name: str) -> dict:
    if contains_any(product_name, ["iPhone", "iPad", "MacBook", "AirPods"]):
        brand = "Apple"
    elif "Samsung" in product_name:
        brand = "Samsung"
    elif "Sony" in product_name:
        brand = "Sony"
    elif "Nintendo" in product_name:
        brand = "Nintendo"
    elif "Dell" in product_name:
        brand = "Dell"
    elif "Canon" in product_name:
        brand = "Canon"
    elif "GoPro" in product_name:
        brand = "GoPro"
    else:
        brand = "Generic"

    if contains_any(product_name, ["iPhone", "iPad", "MacBook"]):
        storage = ["128GB", "256GB", "512GB", "1TB"]
    elif contains_any(product_name, ["SSD", "storage"]):
        storage = ["256GB", "512GB", "1TB", "2TB"]
    else:
        storage = []

    if brand == "Apple":
        colors = ["Space Black", "Silver", "Gold", "Deep Purple"]
    elif brand == "Samsung":
        colors = ["Phantom Black", "Cream", "Green", "Lavender"]
    else:
        colors = ["Black", "White", "Silver"]

    return {"brand": brand, "storage": storage, "colors": colors}


def clothing_attributes(product_name: str) -> dict:
    name_lower = product_name.lower()

    if "Levi's" in product_name:
        brand = "Levi's"
    elif "Nike" in product_name:
        brand = "Nike"
    elif "Lululemon" in product_name:
        brand = "Lululemon"
    elif "Gap" in product_name:
        brand = "Gap"
    elif "Adidas" in product_name:
        brand = "Adidas"
    elif "Patagonia" in product_name:
        brand = "Patagonia"
    elif "Zara" in product_name:
        brand = "Zara"
    elif "Under Armour" in product_name:
        brand = "Under Armour"
    elif "New Balance" in product_name:
        brand = "New Balance"
    elif "Ray-Ban" in product_name:
        brand = "Ray-Ban"
    else:
        brand = "Generic"

    if any(keyword in name_lower for keyword in NO_SIZE_CLOTHING):
        sizes = ["One Size"]
    elif any(keyword in name_lower for keyword in SHOE_KEYWORDS):
        sizes = ["38", "39", "40", "41", "42", "43", "44", "45", "46"]
    elif any(keyword in name_lower for keyword in CLOTHING_KEYWORDS):
        sizes = ["XS", "S", "M", "L", "XL", "XXL"]
    else:
        sizes = ["XS", "S", "M", "L", "XL", "XXL"]

    if contains_any(product_name, ["Women", "Feminine", "Dress", "Leggings"]):
        gender = "Women"
    elif contains_any(product_name, ["Men", "Unisex"]):
        gender = "Men"
    else:
        gender = "Unisex"

    return {
        "brand": brand,
        "sizes": sizes,
        "colors": ["Black", "White", "Navy", "Grey", "Beige", "Olive"],
        "gender": gender,
    }


def beauty_attributes(product_name: str) -> dict:
    if "Neutrogena" in product_name:
        brand = "Neutrogena"
    elif "CeraVe" in product_name:
        brand = "CeraVe"
    elif "MAC" in product_name:
        brand = "MAC"
    elif "Chanel" in product_name:
        brand = "Chanel"
    elif "Anastasia" in product_name:
        brand = "Anastasia Beverly Hills"
    elif "Glossier" in product_name:
        brand = "Glossier"
    elif "First Aid Beauty" in product_name:
        brand = "First Aid Beauty"
    elif "L'Occitane" in product_name:
        brand = "L'Occitane"
    elif "NARS" in product_name:
        brand = "NARS"
    elif "Dyson" in product_name:
        brand = "Dyson"
    else:
        brand = "Generic"

    return {
        "brand": brand,
        "skin_type": ["Normal", "Dry", "Oily", "Combination", "Sensitive"],
        "sizes": ["30ml", "50ml", "100ml", "200ml"],
    }


def books_attributes(product_name: str) -> dict:
    if "The Da Vinci Code" in product_name:
        author = "Dan Brown"
    elif "Dune" in product_name:
        author = "Frank Herbert"
    elif "Atomic Habits" in product_name:
        author = "James Clear"
    elif "Harry Potter" in product_name:
        author = "J.K. Rowling"
    elif "1984" in product_name:
        author = "George Orwell"
    elif "The Alchemist" in product_name:
        author = "Paulo Coelho"
    elif "Sapiens" in product_name:
        author = "Yuval Noah Harari"
    elif "The Great Gatsby" in product_name:
        author = "F. Scott Fitzgerald"
    elif "To Kill a Mockingbird" in product_name:
        author = "Harper Lee"
    elif "Hitchhiker's Guide" in product_name:
        author = "Douglas Adams"
    else:
        author = "Unknown Author"

    if contains_any(product_name, ["Dune", "1984", "Hitchhiker"]):
        genre = "Sci-Fi"
    elif "Harry Potter" in product_name:
        genre = "Fantasy"
    elif contains_any(product_name, ["Atomic Habits", "Sapiens"]):
        genre = "Non-Fiction"
    elif contains_any(product_name, ["The Alchemist", "Great Gatsby", "To Kill"]):
        genre = "Fiction"
    elif "Da Vinci" in product_name:
        genre = "Thriller"
    else:
        genre = "Fiction"

    return {
        "author": author,
        "genre": genre,
        "format": ["Paperback", "Hardcover", "E-Book"],
    }


def home_appliances_attributes(product_name: str) -> dict:
    if "Dyson" in product_name:
        brand = "Dyson"
    elif "Instant Pot" in product_name:
        brand = "Instant Pot"
    elif "KitchenAid" in product_name:
        brand = "KitchenAid"
    elif "iRobot" in product_name:
        brand = "iRobot"
    elif "Keurig" in product_name:
        brand = "Keurig"
    elif "Ninja" in product_name:
        brand = "Ninja"
    elif "Vitamix" in product_name:
        brand = "Vitamix"
    elif "Nespresso" in product_name:
        brand = "Nespresso"
    elif "Philips" in product_name:
        brand = "Philips"
    elif "Nest" in product_name:
        brand = "Google Nest"
    else:
        brand = "Generic"

    return {
        "brand": brand,
        "colors": ["Black", "White", "Silver", "Red"],
        "warranty": ["1 Year", "2 Years", "3 Years"],
    }


def sports_attributes(product_name: str) -> dict:
    name_lower = product_name.lower()

    if "Wilson" in product_name:
        brand = "Wilson"
    elif "Peloton" in product_name:
        brand = "Peloton"
    elif "Garmin" in product_name:
        brand = "Garmin"
    elif "Hydro Flask" in product_name:
        brand = "Hydro Flask"
    elif "Manduka" in product_name:
        brand = "Manduka"
    elif "TRX" in product_name:
        brand = "TRX"
    elif "Callaway" in product_name:
        brand = "Callaway"
    elif "Fitbit" in product_name:
        brand = "Fitbit"
    elif "Osprey" in product_name:
        brand = "Osprey"
    elif "Schwinn" in product_name:
        brand = "Schwinn"
    elif "Yeti" in product_name:
        brand = "Yeti"
    else:
        brand = "Generic"

    has_shoe = any(
        re.search(r"\b" + re.escape(keyword) + r"\b", name_lower)
        for keyword in SPORTS_SHOE_KEYWORDS
    )
    no_size_brand = any(brand in product_name for brand in SPORTS_NO_SIZE_BRANDS)

    if has_shoe and not no_size_brand:
        sizes = ["38", "39", "40", "41", "42", "43", "44", "45", "46"]
    else:
        sizes = []

    return {
        "brand": brand,
        "sizes": sizes,
        "colors": ["Black", "Blue", "Red", "Grey", "Green"],
    }


def build_attributes(category_slug: str, product_name: str) -> dict:
    if category_slug == "electronics":
        return electronics_attributes(product_name)
    if category_slug == "clothing":
        return clothing_attributes(product_name)
    if category_slug == "beauty":
        return beauty_attributes(product_name)
    if category_slug == "books":
        return books_attributes(product_name)
    if category_slug == "home-appliances":
        return home_appliances_attributes(product_name)
    if category_slug == "sports":
        return sports_attributes(product_name)
    return {}


def get_product_brand(product: dict) -> str | None:
    attributes = product.get("attributes", {})
    brand = attributes.get("brand") or attributes.get("author")
    if not brand or brand in GENERIC_BRANDS:
        return None
    return str(brand)


def build_image_query(product: dict) -> str:
    parts = [product["name"], product["categoryName"]]
    brand = get_product_brand(product)
    if brand and brand.lower() not in product["name"].lower():
        parts.insert(1, brand)
    return " ".join(part for part in parts if part).strip()


def build_image_queries(product: dict) -> list[str]:
    queries = []
    seen = set()
    brand = get_product_brand(product)
    candidates = [
        build_image_query(product),
        product["name"],
    ]

    if brand:
        candidates.append(f"{brand} {product['name']}")
        candidates.append(f"{brand} {product['categoryName']}")

    for query in candidates:
        normalized = " ".join(query.split())
        if not normalized or normalized in seen:
            continue
        queries.append(normalized)
        seen.add(normalized)

    return queries


def get_relative_product_asset_path(filename: str) -> str:
    return f"{PRODUCT_IMAGE_DIR}/{filename}".replace("\\", "/")


def get_fallback_relative_path(category_slug: str) -> str:
    filename = f"fallback-{category_slug}.svg"
    return get_relative_product_asset_path(f"{FALLBACK_DIR}/{filename}")


def build_product_cache_key(product: dict) -> str:
    brand = get_product_brand(product) or "unbranded"
    return f"{product['id']}::{slugify(product['name'])}::{slugify(brand)}"


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def relative_path_exists(repo_root: Path, relative_path: str) -> bool:
    return (repo_root / "frontend" / relative_path).exists()


def extension_from_mime(mime: str, url: str = "") -> str:
    mime_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    if mime:
        mapped = mime_map.get(mime.lower())
        if mapped:
            return mapped

    parsed_path = urllib.parse.urlparse(url).path.lower()
    for extension in (".jpg", ".jpeg", ".png", ".webp"):
        if parsed_path.endswith(extension):
            return ".jpg" if extension == ".jpeg" else extension

    return ".jpg"


class ProductImageResolver:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.assets_dir = repo_root / "frontend" / "assets" / "products"
        self.cache_path = repo_root / "frontend" / "data" / IMAGE_CACHE_FILENAME
        self.cache = self._load_cache()

        self.search_cache_hits = 0
        self.product_cache_hits = 0
        self.downloaded_count = 0
        self.fallback_count = 0
        self.network_enabled = True
        self.consecutive_search_failures = 0
        self.last_search_request_at = 0.0

        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_fallback_assets()

    def _load_cache(self) -> dict:
        default_cache = {
            "version": IMAGE_CACHE_VERSION,
            "products": {},
            "searches": {},
            "downloads": {},
        }

        if not self.cache_path.exists():
            return default_cache

        try:
            loaded = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default_cache

        if loaded.get("version") != IMAGE_CACHE_VERSION:
            return default_cache

        for key in ("products", "searches", "downloads"):
            loaded.setdefault(key, {})
        return loaded

    def save_cache(self) -> None:
        ensure_parent_dir(self.cache_path)
        self.cache_path.write_text(
            json.dumps(self.cache, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def resolve_image(self, product: dict) -> str:
        cache_key = build_product_cache_key(product)
        cached_product = self.cache["products"].get(cache_key)
        if cached_product and relative_path_exists(
            self.repo_root, cached_product["relative_path"]
        ):
            self.product_cache_hits += 1
            return cached_product["relative_path"]

        queries = build_image_queries(product)
        candidate, score, matched_query = self._find_best_candidate(product, queries)

        if candidate and score >= MIN_MATCH_SCORE:
            relative_path = self._download_candidate(product, candidate)
            if relative_path:
                self.cache["products"][cache_key] = {
                    "relative_path": relative_path,
                    "match_type": "search",
                    "query": matched_query,
                    "score": round(score, 2),
                    "source_title": candidate["title"],
                }
                return relative_path

        relative_path = self._fallback_relative_path(product["category"])
        self.cache["products"][cache_key] = {
            "relative_path": relative_path,
            "match_type": "fallback",
            "query": queries[0] if queries else product["name"],
            "score": round(score, 2),
        }
        self.fallback_count += 1
        return relative_path

    def _find_best_candidate(
        self, product: dict, queries: list[str]
    ) -> tuple[dict | None, float, str]:
        best_candidate = None
        best_score = float("-inf")
        best_query = queries[0] if queries else product["name"]

        for query in queries:
            candidates = self._search_candidates(query)
            for candidate in candidates:
                score = self._score_candidate(product, candidate)
                if score > best_score:
                    best_candidate = candidate
                    best_score = score
                    best_query = query
            if best_score >= MIN_MATCH_SCORE:
                break

        return best_candidate, best_score, best_query

    def _search_candidates(self, query: str) -> list[dict]:
        if not self.network_enabled:
            return []

        cached_search = self.cache["searches"].get(query)
        if cached_search:
            self.search_cache_hits += 1
            return cached_search["results"]

        try:
            results = self._search_openverse_candidates(query)
            if not results:
                results = self._search_commons_candidates(query)
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError):
            self.consecutive_search_failures += 1
            if self.consecutive_search_failures >= 5:
                self.network_enabled = False
            self.cache["searches"][query] = {"results": []}
            return []
        self.consecutive_search_failures = 0

        self.cache["searches"][query] = {"results": results}
        return results

    def _search_openverse_candidates(self, query: str) -> list[dict]:
        params = {
            "q": query,
            "page_size": str(MAX_SEARCH_RESULTS),
            "mature": "false",
        }
        url = f"{OPENVERSE_API_URL}?{urllib.parse.urlencode(params)}"
        response = self._fetch_json(url)

        results = []
        for item in response.get("results", []):
            image_url = item.get("url")
            if not image_url:
                continue

            results.append(
                {
                    "title": item.get("title") or "",
                    "url": image_url,
                    "mime": item.get("filetype") or "",
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "source": "openverse",
                    "tags": [tag.get("name", "") for tag in item.get("tags", [])],
                }
            )

        return results

    def _search_commons_candidates(self, query: str) -> list[dict]:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": query,
            "gsrlimit": str(MAX_SEARCH_RESULTS),
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "iiurlwidth": "800",
        }
        url = f"{COMMONS_API_URL}?{urllib.parse.urlencode(params)}"
        response = self._fetch_search_json(url)

        pages = response.get("query", {}).get("pages", {})
        results = []
        for page in pages.values():
            image_info = (page.get("imageinfo") or [{}])[0]
            mime = image_info.get("mime", "")
            if mime not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
                continue

            image_url = image_info.get("thumburl") or image_info.get("url")
            if not image_url:
                continue

            results.append(
                {
                    "title": page.get("title", "").removeprefix("File:"),
                    "url": image_url,
                    "mime": mime,
                    "width": image_info.get("thumbwidth") or image_info.get("width"),
                    "height": image_info.get("thumbheight") or image_info.get("height"),
                    "source": "commons",
                    "tags": [],
                }
            )

        return results

    def _score_candidate(self, product: dict, candidate: dict) -> float:
        title_tokens = set(tokenize(candidate["title"]))
        tag_tokens = set()
        for tag in candidate.get("tags", []):
            tag_tokens.update(tokenize(tag))
        name_tokens = set(tokenize(product["name"]))
        category_tokens = set(tokenize(product["categoryName"]))
        category_tokens.update(CATEGORY_HINTS.get(product["category"], []))
        brand = get_product_brand(product)
        brand_tokens = set(tokenize(brand)) if brand else set()
        searchable_tokens = title_tokens | tag_tokens

        score = 0.0
        normalized_name = normalize_text(product["name"])
        normalized_title = normalize_text(candidate["title"])

        if normalized_name and normalized_name in normalized_title:
            score += 8.0

        score += len(name_tokens & searchable_tokens) * 1.8
        score += len(category_tokens & searchable_tokens) * 0.9
        score += len(brand_tokens & searchable_tokens) * 2.5

        if brand_tokens and brand_tokens.issubset(searchable_tokens):
            score += 2.0

        if candidate.get("width", 0) and candidate.get("height", 0):
            if min(candidate["width"], candidate["height"]) >= 300:
                score += 0.5

        if any(token in searchable_tokens for token in BANNED_IMAGE_TOKENS):
            score -= 4.0

        if product["category"] != "books" and "cover" in title_tokens:
            score -= 1.5

        return score

    def _download_candidate(self, product: dict, candidate: dict) -> str | None:
        if not self.network_enabled:
            return None

        cached_download = self.cache["downloads"].get(candidate["url"])
        if cached_download and relative_path_exists(
            self.repo_root, cached_download["relative_path"]
        ):
            return cached_download["relative_path"]

        suffix = hashlib.sha1(candidate["url"].encode("utf-8")).hexdigest()[:10]
        extension = extension_from_mime(candidate["mime"], candidate["url"])
        filename = (
            f"{product['category']}-{slugify(product['name'])}-{suffix}{extension}"
        )
        target_path = self.assets_dir / filename
        relative_path = get_relative_product_asset_path(filename)

        if not target_path.exists():
            try:
                binary = self._fetch_binary(candidate["url"])
            except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError):
                return None
            target_path.write_bytes(binary)
            self.downloaded_count += 1

        self.cache["downloads"][candidate["url"]] = {
            "relative_path": relative_path,
            "source_title": candidate["title"],
        }
        return relative_path

    def _fallback_relative_path(self, category_slug: str) -> str:
        return get_fallback_relative_path(category_slug)

    def _ensure_fallback_assets(self) -> None:
        fallback_dir = self.assets_dir / FALLBACK_DIR
        fallback_dir.mkdir(parents=True, exist_ok=True)

        for category_slug, svg in FALLBACK_SVGS.items():
            fallback_path = fallback_dir / f"fallback-{category_slug}.svg"
            if not fallback_path.exists():
                fallback_path.write_text(svg, encoding="utf-8")

    def _fetch_json(self, url: str) -> dict:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "NeonRetroProductImageResolver/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)

    def _fetch_search_json(self, url: str) -> dict:
        for attempt, delay in enumerate((0.0, *SEARCH_RETRY_DELAYS_SECONDS), start=1):
            self._throttle_search_requests()
            try:
                return self._fetch_json(url)
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt > len(SEARCH_RETRY_DELAYS_SECONDS):
                    raise
                time.sleep(delay or SEARCH_RETRY_DELAYS_SECONDS[0])

        raise urllib.error.HTTPError(url, 429, "Too Many Requests", None, None)

    def _fetch_binary(self, url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "NeonRetroProductImageResolver/1.0"},
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read()

    def _throttle_search_requests(self) -> None:
        elapsed = time.monotonic() - self.last_search_request_at
        if elapsed < SEARCH_MIN_INTERVAL_SECONDS:
            time.sleep(SEARCH_MIN_INTERVAL_SECONDS - elapsed)
        self.last_search_request_at = time.monotonic()


def build_products(csv_path: Path, image_resolver: ProductImageResolver | None = None) -> list[dict]:
    products = []
    seen_names = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            raw_category = row["Product Category"].strip()
            product_name = row["Product Name"].strip()

            if raw_category not in CATEGORY_MAP or product_name in seen_names:
                continue

            slug, category_name = CATEGORY_MAP[raw_category]
            product_id = len(products) + 1
            price = round(float(row["Unit Price"]), 2)

            product = {
                "id": product_id,
                "category": slug,
                "categoryName": category_name,
                "name": product_name,
                "price": price,
                "image": "",
                "discount": 0,
                "salesCount": (product_id * 37) % 950 + 50,
                "description": (
                    f"{category_name} product: {product_name}. "
                    "High quality item with fast shipping and easy returns."
                ),
                "stock": (product_id * 13) % 46 + 5,
                "rating": round(3.5 + (product_id % 16) * 0.1, 1),
                "attributes": build_attributes(slug, product_name),
            }

            if image_resolver is None:
                product["image"] = get_fallback_relative_path(slug)
            else:
                product["image"] = image_resolver.resolve_image(product)

            products.append(product)
            seen_names.add(product_name)

    return products


def main() -> None:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    csv_path = resolve_csv_path(repo_root)
    output_path = repo_root / "frontend" / "data" / "products.json"

    image_resolver = ProductImageResolver(repo_root)
    products = build_products(csv_path, image_resolver=image_resolver)
    output_path.write_text(
        json.dumps(products, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    image_resolver.save_cache()

    counts = Counter(product["categoryName"] for product in products)
    print(f"Total products: {len(products)}")
    for category_name in [
        "Electronics",
        "Clothing",
        "Beauty",
        "Home Appliances",
        "Books",
        "Sports",
    ]:
        print(f"{category_name}: {counts.get(category_name, 0)}")

    print(f"Downloaded images: {image_resolver.downloaded_count}")
    print(f"Product cache hits: {image_resolver.product_cache_hits}")
    print(f"Search cache hits: {image_resolver.search_cache_hits}")
    print(f"Fallback images used: {image_resolver.fallback_count}")


if __name__ == "__main__":
    main()
