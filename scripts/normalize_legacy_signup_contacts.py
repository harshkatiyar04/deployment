"""One-time backfill: normalize legacy signup mobiles and UK postcodes in DB."""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.signup_locales import (
    coerce_stored_mobile,
    format_postcode_display,
    resolve_country_code,
    validate_and_normalize_mobile,
)
from app.db.session import AsyncSessionLocal
from app.models.signup import SignupRequest


async def run(*, dry_run: bool) -> None:
    updated_mobile = 0
    updated_postcode = 0
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(SignupRequest))
        rows = res.scalars().all()
        for signup in rows:
            country = resolve_country_code(signup.country)
            mobile_next = coerce_stored_mobile(signup.mobile, signup.country)
            if mobile_next and mobile_next != (signup.mobile or "").strip():
                try:
                    mobile_next = validate_and_normalize_mobile(mobile_next, country)
                except Exception:
                    continue
                if mobile_next != signup.mobile:
                    print(f"mobile {signup.id}: {signup.mobile!r} -> {mobile_next!r}")
                    if not dry_run:
                        signup.mobile = mobile_next
                    updated_mobile += 1

            if signup.guardian_mobile:
                guardian_next = coerce_stored_mobile(signup.guardian_mobile, signup.country)
                if guardian_next and guardian_next != signup.guardian_mobile:
                    try:
                        guardian_next = validate_and_normalize_mobile(guardian_next, country)
                    except Exception:
                        guardian_next = None
                    if guardian_next and guardian_next != signup.guardian_mobile:
                        print(
                            f"guardian {signup.id}: {signup.guardian_mobile!r} -> {guardian_next!r}"
                        )
                        if not dry_run:
                            signup.guardian_mobile = guardian_next
                        updated_mobile += 1

            if signup.pincode and country == "GB":
                postcode_next = format_postcode_display(signup.pincode, signup.country)
                if postcode_next != "—" and postcode_next != signup.pincode:
                    print(f"postcode {signup.id}: {signup.pincode!r} -> {postcode_next!r}")
                    if not dry_run:
                        signup.pincode = postcode_next
                    updated_postcode += 1

            if country in {"IN", "GB"} and signup.country != country:
                print(f"country {signup.id}: {signup.country!r} -> {country!r}")
                if not dry_run:
                    signup.country = country

        if not dry_run:
            await db.commit()

    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"{mode}: updated {updated_mobile} mobile field(s), {updated_postcode} postcode(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize legacy signup contact fields")
    parser.add_argument("--apply", action="store_true", help="Write changes (default is dry run)")
    args = parser.parse_args()
    asyncio.run(run(dry_run=not args.apply))


if __name__ == "__main__":
    main()
