import csv
import json
import re
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

CATEGORY_SEEDS = {
    "electronics": "tech",
    "clothing": "fashion",
    "beauty": "beauty",
    "home-appliances": "home",
    "books": "books",
    "sports": "sport",
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


def build_products(csv_path: Path) -> list[dict]:
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

            seed = f"{CATEGORY_SEEDS.get(slug, 'product')}-{product_id}"

            products.append(
                {
                    "id": product_id,
                    "category": slug,
                    "categoryName": category_name,
                    "name": product_name,
                    "price": price,
                    "image": f"https://picsum.photos/seed/{seed}/400/400",
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
            )
            seen_names.add(product_name)

    return products


def main() -> None:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    csv_path = resolve_csv_path(repo_root)
    output_path = repo_root / "frontend" / "data" / "products.json"

    products = build_products(csv_path)
    output_path.write_text(json.dumps(products, indent=2), encoding="utf-8")

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


if __name__ == "__main__":
    main()
