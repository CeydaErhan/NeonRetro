"""CLI script to create an admin user in the database."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bcrypt
from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(description="Create an admin user.")
    parser.add_argument("email", help="Admin account email")
    parser.add_argument("password", help="Admin account password")
    return parser.parse_args()


def create_admin(email: str, password: str) -> None:
    """Create an admin user with a hashed password if it does not already exist."""
    with SessionLocal() as session:
        existing = session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"Admin user already exists: {email}")
            return

        user = User(
            email=email,
            password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            role="admin",
        )
        session.add(user)
        session.commit()
        print(f"Admin user created successfully: {user.email}")


def main() -> None:
    """Run the admin creation flow from CLI input."""
    args = parse_args()
    create_admin(args.email, args.password)


if __name__ == "__main__":
    main()
