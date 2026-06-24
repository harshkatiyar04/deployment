"""Post-signup contact read/update helpers (IN / GB locales)."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.signup_locales import (
    build_contact_display,
    resolve_country_code,
    validate_signup_contact_address,
)
from app.schemas.signup import SignupContactDisplay
from app.models.enums import KycStatus
from app.models.signup import SignupRequest

_EDITABLE_KYC = frozenset({KycStatus.pending, KycStatus.info_required})


def contact_editable_for(user: SignupRequest) -> bool:
    return user.kyc_status in _EDITABLE_KYC


def session_contact_extras(user: SignupRequest) -> dict:
    """Extra /auth/me fields for locale-aware contact display."""
    display = build_contact_display(
        mobile=user.mobile,
        guardian_mobile=user.guardian_mobile,
        country=user.country,
        pincode=user.pincode,
    )
    return {
        "country": resolve_country_code(user.country),
        "address_line1": user.address_line1 or "",
        "address_line2": user.address_line2 or "",
        "city": user.city or "",
        "state": user.state or "",
        "pincode": user.pincode or "",
        "mobile_display": display["mobile_display"],
        "contact_display": SignupContactDisplay(**display),
        "contact_editable": contact_editable_for(user),
    }


async def update_signup_contact(
    db: AsyncSession,
    user: SignupRequest,
    *,
    mobile: str,
    address_line1: str,
    address_line2: str,
    city: str,
    state: str,
    pincode: str,
    country: str,
) -> SignupRequest:
    if not contact_editable_for(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contact details can only be updated while your application is under review. Contact support after approval.",
        )

    (
        mobile_norm,
        country_norm,
        pincode_norm,
        state_norm,
        city_norm,
        line1,
        line2,
    ) = validate_signup_contact_address(
        mobile=mobile,
        country=country,
        pincode=pincode,
        state=state,
        city=city,
        address_line1=address_line1,
        address_line2=address_line2,
    )

    user.mobile = mobile_norm
    user.country = country_norm
    user.pincode = pincode_norm
    user.state = state_norm
    user.city = city_norm
    user.address_line1 = line1
    user.address_line2 = line2
    user.updated_at = datetime.utcnow()
    await db.flush()
    return user
