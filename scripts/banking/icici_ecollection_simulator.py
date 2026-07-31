"""
Local ICICI eCollection simulator — mimics bank Validation (+ retries) then Credit Confirm.

Usage (uvicorn running on :8000):
  python scripts/banking/icici_ecollection_simulator.py
  python scripts/banking/icici_ecollection_simulator.py --base http://127.0.0.1:8000 --van ABBCDEMO001
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime


def post(url: str, payload: dict, auth: tuple[str, str] | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if auth and auth[0]:
        import base64

        token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return exc.code, parsed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--client-code", default="ABBC")
    p.add_argument("--van", default="ABBCDEMO001")
    p.add_argument("--amount", default="100.00")
    p.add_argument("--utr", default=None)
    p.add_argument("--user", default="")
    p.add_argument("--password", default="")
    p.add_argument("--retries", type=int, default=2)
    args = p.parse_args()

    utr = args.utr or f"SIM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    auth = (args.user, args.password) if args.user else None
    validate_url = f"{args.base.rstrip('/')}/webhooks/icici/ecollection/validate"
    confirm_url = f"{args.base.rstrip('/')}/webhooks/icici/ecollection/credit-confirm"

    payload = {
        "CUSTOMER CODE": args.client_code,
        "VIRTUAL ACCOUNT NUMBER": args.van,
        "TRANSACTION AMOUNT": args.amount,
        "CURRENCY CODE": "INR",
        "PAYMENT MODE": "NEFT",
        "UTR": utr,
        "DATE": datetime.utcnow().strftime("%d-%m-%Y"),
        "SENDER NAME": "SIM REMITTER",
        "SENDER ACCOUNT NUMBER": "1234567890",
        "SENDER IFSC": "ICIC0000001",
    }

    print("Health:", f"{args.base}/webhooks/icici/ecollection/health")
    for i in range(1 + max(0, args.retries)):
        code, resp = post(validate_url, payload, auth)
        print(f"Validate attempt {i + 1}: HTTP {code} -> {resp}")

    confirm_payload = {
        "CUSTOMER_CODE": args.client_code,
        "VAN": args.van,
        "AMOUNT": args.amount,
        "CURRENCY_CODE": "INR",
        "PAYMENT_MODE": "NEFT",
        "UTR": utr,
        "TRAN_DATE": datetime.utcnow().strftime("%d-%m-%Y"),
        "REMITTERNAME": "SIM REMITTER",
        "REMITTER_ACCNO": "1234567890",
        "REMITTER_IFSC": "ICIC0000001",
    }
    code, resp = post(confirm_url, confirm_payload, auth)
    print(f"Credit confirm: HTTP {code} -> {resp}")

    # Duplicate confirm (idempotency)
    code2, resp2 = post(confirm_url, confirm_payload, auth)
    print(f"Credit confirm retry: HTTP {code2} -> {resp2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
