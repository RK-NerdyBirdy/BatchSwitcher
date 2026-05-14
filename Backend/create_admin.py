#!/usr/bin/env python3
"""CLI utility to create admin users."""

import asyncio
import sys
from getpass import getpass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.crud.admin import get_admin_by_email
from app.models.admin import Admin


async def create_admin_cli():
    """Interactively create an admin user."""
    print("\n=== Batch Switcher Admin Registration ===\n")

    admin_name = input("Admin Name: ").strip()
    if not admin_name:
        print("ERROR: Admin name cannot be empty")
        sys.exit(1)

    admin_email = input("Admin Email: ").strip().lower()
    if "@" not in admin_email:
        print("ERROR: Invalid email format")
        sys.exit(1)

    password = getpass("Password (min 8 chars): ")
    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters")
        sys.exit(1)

    password_confirm = getpass("Confirm Password: ")
    if password != password_confirm:
        print("ERROR: Passwords do not match")
        sys.exit(1)

    async with async_session_maker() as db:
        existing = await get_admin_by_email(db, admin_email)
        if existing:
            print(f"ERROR: Admin with email {admin_email} already exists")
            sys.exit(1)

        password_hash = get_password_hash(password)
        admin = Admin(
            admin_name=admin_name,
            admin_email=admin_email,
            password_hash=password_hash,
            password_initial_change=False,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        print(f"\n✓ Admin created successfully!")
        print(f"  Admin ID: {admin.admin_id}")
        print(f"  Name: {admin.admin_name}")
        print(f"  Email: {admin.admin_email}")
        print(f"\nYou can now login with:")
        print(f"  POST /api/auth/admin/login")
        print(f"  {{'admin_email': '{admin.admin_email}', 'password': '...'}}\n")


if __name__ == "__main__":
    asyncio.run(create_admin_cli())
