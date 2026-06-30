"""Unit checks for IN/GB signup locale validation."""
from __future__ import annotations

from fastapi import HTTPException

from app.core.signup_locales import (
    normalize_country_code,
    validate_and_normalize_mobile,
    validate_and_normalize_postcode,
    validate_signup_contact_address,
)


def _assert_raises(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except HTTPException:
        return
    raise AssertionError(f"expected HTTPException from {fn.__name__}")


def test_normalize_country_aliases():
    assert normalize_country_code("IN") == "IN"
    assert normalize_country_code("india") == "IN"
    assert normalize_country_code("UK") == "GB"
    assert normalize_country_code("United Kingdom") == "GB"


def test_normalize_country_accepts_us():
    assert normalize_country_code("US") == "US"


def test_normalize_country_rejects_unknown():
    _assert_raises(normalize_country_code, "ZZ")


def test_indian_mobile_e164():
    assert validate_and_normalize_mobile("9876543210", "IN") == "+919876543210"
    assert validate_and_normalize_mobile("+919876543210", "IN") == "+919876543210"


def test_indian_mobile_rejects_invalid():
    _assert_raises(validate_and_normalize_mobile, "5876543210", "IN")


def test_uk_mobile_e164():
    assert validate_and_normalize_mobile("07911123456", "GB") == "+447911123456"
    assert validate_and_normalize_mobile("7911123456", "GB") == "+447911123456"
    assert validate_and_normalize_mobile("+447911123456", "GB") == "+447911123456"


def test_indian_pincode():
    assert validate_and_normalize_postcode("110001", "IN") == "110001"


def test_uk_postcode_normalized():
    assert validate_and_normalize_postcode("sw1a1aa", "GB") == "SW1A 1AA"
    assert validate_and_normalize_postcode("SW1A 1AA", "GB") == "SW1A 1AA"


def test_validate_signup_bundle_india():
    result = validate_signup_contact_address(
        mobile="9876543210",
        country="IN",
        pincode="110001",
        state="Delhi",
        city="New Delhi",
        address_line1="1 Main St",
        address_line2="",
    )
    assert result[0] == "+919876543210"
    assert result[1] == "IN"
    assert result[2] == "110001"


def test_uk_state_optional():
    result = validate_signup_contact_address(
        mobile="07911123456",
        country="GB",
        pincode="SW1A 1AA",
        state="",
        city="London",
        address_line1="10 Downing St",
        address_line2="",
    )
    assert result[0] == "+447911123456"
    assert result[3] == ""


def test_legacy_india_mobile_display():
    from app.core.signup_locales import (
        build_contact_display,
        coerce_stored_mobile,
        format_mobile_display,
    )

    assert coerce_stored_mobile("9876543210", "India") == "+919876543210"
    assert format_mobile_display("9876543210", "IN") == "+91 98765 43210"
    contact = build_contact_display(mobile="9876543210", country="India", pincode="110001")
    assert contact["country_label"] == "India"
    assert contact["postcode_label"] == "PIN code"
    assert contact["mobile_e164"] == "+919876543210"


def test_uk_contact_display_labels():
    from app.core.signup_locales import build_contact_display

    contact = build_contact_display(
        mobile="+447911123456",
        country="GB",
        pincode="sw1a1aa",
    )
    assert contact["country_label"] == "United Kingdom"
    assert contact["postcode_label"] == "Postcode"
    assert contact["postcode_display"] == "SW1A 1AA"
    assert contact["state_label"] == "County / region"


def test_resubmit_allowed_for_rejected_and_info_required():
    from app.models.enums import KycStatus
    from app.services.signup_validation import (
        availability_flags_for_signup,
        signup_resubmit_allowed,
    )

    class _Rejected:
        kyc_status = KycStatus.rejected

    class _Info:
        kyc_status = KycStatus.info_required

    class _Pending:
        kyc_status = KycStatus.pending

    assert signup_resubmit_allowed(_Rejected()) is True
    assert signup_resubmit_allowed(_Info()) is True
    assert signup_resubmit_allowed(_Pending()) is False

    flags = availability_flags_for_signup(_Rejected())
    assert flags["resubmit_allowed"] is True
    assert flags["registered"] is False

    pending_flags = availability_flags_for_signup(_Pending())
    assert pending_flags["registered"] is True
    assert pending_flags["resubmit_allowed"] is False


def test_contact_editable_only_during_review():
    from app.models.enums import KycStatus
    from app.services.signup_contact import contact_editable_for

    class _User:
        kyc_status = KycStatus.pending

    assert contact_editable_for(_User()) is True

    class _Approved:
        kyc_status = KycStatus.approved

    assert contact_editable_for(_Approved()) is False


if __name__ == "__main__":
    test_normalize_country_aliases()
    test_normalize_country_accepts_us()
    test_normalize_country_rejects_unknown()
    test_indian_mobile_e164()
    test_indian_mobile_rejects_invalid()
    test_uk_mobile_e164()
    test_indian_pincode()
    test_uk_postcode_normalized()
    test_validate_signup_bundle_india()
    test_uk_state_optional()
    test_legacy_india_mobile_display()
    test_uk_contact_display_labels()
    test_resubmit_allowed_for_rejected_and_info_required()
    test_contact_editable_only_during_review()
    print("signup_locales checks OK")
