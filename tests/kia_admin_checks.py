"""Admin Kia formatting checks. Run: python -m tests.kia_admin_checks"""

from app.services.kia_admin import _inr_indian, format_admin_reply


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_inr_indian() -> None:
    _assert(_inr_indian(249000) == "₹2,49,000", _inr_indian(249000))
    _assert(_inr_indian(188400) == "₹1,88,400", _inr_indian(188400))
    _assert(_inr_indian(0) == "₹0", "zero")


def test_format_admin_reply_currency_and_links() -> None:
    raw = (
        "There are 21 circles. Total contributions are $249,000. "
        "Review circle ops at /dashboard/circle-ops."
    )
    out = format_admin_reply(raw)
    _assert("₹2,49,000" in out, f"expected INR, got: {out}")
    _assert("$" not in out, f"dollar leaked: {out}")
    _assert("[Circle ops](/dashboard/circle-ops)" in out, f"link missing: {out}")


def main() -> None:
    test_inr_indian()
    test_format_admin_reply_currency_and_links()
    print("All Admin Kia checks passed.")


if __name__ == "__main__":
    main()
