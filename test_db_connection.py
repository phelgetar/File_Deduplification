#!/usr/bin/env python3
"""Test database connection and configuration."""

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus, unquote_plus

# Load environment variables
load_dotenv()

print("=" * 60)
print("DATABASE CONNECTION TEST")
print("=" * 60)

# Get variables
raw_url = os.getenv("DATABASE_URL")
db_password = os.getenv("DB_PASSWORD")

print(f"\n1. Raw DATABASE_URL from .env:")
print(f"   {raw_url}")

print(f"\n2. DB_PASSWORD from .env:")
print(f"   {db_password}")

print(f"\n3. Password appears URL-encoded: {('%' in db_password) if db_password else 'N/A'}")

if db_password:
    if '%' in db_password:
        decoded = unquote_plus(db_password)
        print(f"\n4. Decoded password:")
        print(f"   {decoded}")

        encoded = quote_plus(decoded)
        print(f"\n5. Re-encoded password:")
        print(f"   {encoded}")
    else:
        encoded = quote_plus(db_password)
        print(f"\n4. Encoded password:")
        print(f"   {encoded}")

    # Build final URL
    if raw_url:
        final_url = raw_url.replace("${DB_PASSWORD}", encoded)

        print(f"\n6. Final DATABASE_URL:")
        masked_url = final_url.replace(encoded, "***MASKED***")
        print(f"   {masked_url}")

        print(f"\n7. Placeholder replaced: {('${DB_PASSWORD}' not in final_url)}")

        # Try connection
        print(f"\n8. Testing connection...")
        try:
            from sqlalchemy import create_engine
            engine = create_engine(final_url, echo=False)

            # Test connection
            with engine.connect() as conn:
                result = conn.execute("SELECT 1")
                print("   ✅ Connection successful!")
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
    else:
        print("\n❌ DATABASE_URL not found in .env file")
else:
    print("\n❌ DB_PASSWORD not found in .env file")

print("\n" + "=" * 60)
