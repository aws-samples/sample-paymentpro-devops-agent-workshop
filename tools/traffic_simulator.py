#!/usr/bin/env python3
"""
PaymentPro Traffic Simulator

Generates realistic payment traffic against the Payment API.
Useful for populating dashboards with data and load testing.

Usage:
    # Generate 20 payments with mixed types, 3 seconds apart
    python traffic_simulator.py --count 20 --interval 3 --profile mixed

    # Burst mode: 50 payments as fast as possible
    python traffic_simulator.py --count 50 --interval 0 --profile burst

    # UPI-heavy traffic for 5 minutes
    python traffic_simulator.py --duration 300 --interval 5 --profile upi_heavy

    # Target a specific URL (default: production CloudFront)
    python traffic_simulator.py --url http://localhost:8001 --count 10
"""

import argparse
import asyncio
import json
import random
import time
from datetime import datetime

import httpx

# Default API base URL (CloudFront production)
DEFAULT_URL = "https://<your-cloudfront-domain>.cloudfront.net/api/v1"

# Payment profiles — weighted distribution
PROFILES = {
    "mixed": {"UPI": 40, "CREDIT_CARD": 30, "DEBIT_CARD": 20, "WALLET": 10},
    "cards_only": {"CREDIT_CARD": 50, "DEBIT_CARD": 50},
    "upi_heavy": {"UPI": 80, "CREDIT_CARD": 10, "DEBIT_CARD": 5, "WALLET": 5},
    "wallet_heavy": {"WALLET": 60, "UPI": 20, "CREDIT_CARD": 10, "DEBIT_CARD": 10},
    "burst": {"UPI": 25, "CREDIT_CARD": 25, "DEBIT_CARD": 25, "WALLET": 25},
}

# Test data for each payment type
VALID_CARDS = [
    "4111111111111111",  # Visa
    "4012888888881881",  # Visa
    "5500000000000004",  # Mastercard
    "5105105105105100",  # Mastercard
    "378282246310005",   # Amex
]

VALID_UPI_IDS = [
    "customer1@paytm",
    "buyer2@oksbi",
    "shopper3@ybl",
    "user4@hdfc",
    "payer5@icici",
    "client6@kotak",
    "member7@axl",
]

WALLET_IDS = [
    "wallet12345678",
    "wallet87654321",
    "walletABCD1234",
    "walletXYZW9876",
]

# Default merchant (demo) — will be overridden if merchants exist
DEFAULT_MERCHANT = "demo"


def pick_payment_type(profile: str) -> str:
    """Pick a random payment type based on profile weights."""
    weights = PROFILES[profile]
    types = list(weights.keys())
    probs = list(weights.values())
    return random.choices(types, weights=probs, k=1)[0]


def generate_payment_data(payment_type: str, merchant_id: str) -> dict:
    """Generate realistic payment data for the given type."""
    amount = round(random.uniform(10, 10000), 2)

    payload: dict = {
        "payment_type": payment_type,
        "amount": str(amount),
        "currency": "INR",
        "merchant_id": merchant_id,
    }

    if payment_type in ("CREDIT_CARD", "DEBIT_CARD"):
        card = random.choice(VALID_CARDS)
        payload["card_number"] = card
        payload["card_expiry"] = f"{random.randint(1,12):02d}/30"
        payload["cvv"] = "1234" if card.startswith("3") else "123"  # Amex=4, others=3

    elif payment_type == "UPI":
        payload["upi_id"] = random.choice(VALID_UPI_IDS)

    elif payment_type == "WALLET":
        payload["wallet_id"] = random.choice(WALLET_IDS)
        payload["wallet_balance"] = str(round(amount + random.uniform(100, 5000), 2))

    return payload


async def fetch_merchants(base_url: str) -> list[str]:
    """Fetch registered merchants from the API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/merchants/list")
            if resp.status_code == 200:
                merchants = resp.json()
                return [m["id"] for m in merchants] if merchants else [DEFAULT_MERCHANT]
    except Exception:
        pass
    return [DEFAULT_MERCHANT]


async def send_payment(client: httpx.AsyncClient, base_url: str, payload: dict) -> dict:
    """Send a single payment request."""
    try:
        resp = await client.post(f"{base_url}/payments", json=payload)
        return resp.json()
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


async def run_simulator(
    base_url: str,
    count: int,
    interval: float,
    duration: float,
    profile: str,
    verbose: bool,
) -> dict:
    """Run the traffic simulator."""
    print(f"\n{'='*60}")
    print(f"  PaymentPro Traffic Simulator")
    print(f"{'='*60}")
    print(f"  URL:      {base_url}")
    print(f"  Profile:  {profile} ({PROFILES[profile]})")
    print(f"  Count:    {count if count else 'unlimited'}")
    print(f"  Interval: {interval}s")
    print(f"  Duration: {duration}s" if duration else "  Duration: until count reached")
    print(f"{'='*60}\n")

    # Fetch available merchants
    merchants = await fetch_merchants(base_url)
    print(f"  Merchants found: {len(merchants)}")
    print(f"  Starting...\n")

    stats = {"total": 0, "success": 0, "failed": 0, "error": 0, "by_type": {}}
    start_time = time.time()

    async with httpx.AsyncClient(timeout=10.0) as client:
        i = 0
        while True:
            # Check termination conditions
            if count and i >= count:
                break
            if duration and (time.time() - start_time) >= duration:
                break

            # Generate and send payment
            payment_type = pick_payment_type(profile)
            merchant_id = random.choice(merchants)
            payload = generate_payment_data(payment_type, merchant_id)

            result = await send_payment(client, base_url, payload)
            status = result.get("status", "ERROR")

            # Track stats
            stats["total"] += 1
            if status == "SUCCESS":
                stats["success"] += 1
            elif status == "FAILED":
                stats["failed"] += 1
            else:
                stats["error"] += 1

            stats["by_type"][payment_type] = stats["by_type"].get(payment_type, 0) + 1

            # Log
            if verbose:
                emoji = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⚠️"
                print(f"  {emoji} #{i+1} {payment_type:12s} ₹{payload['amount']:>10s} → {status}")
            else:
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rps = stats["total"] / elapsed if elapsed > 0 else 0
                    print(f"  ... {stats['total']} payments sent ({rps:.1f}/s) — {stats['success']} success, {stats['failed']} failed")

            i += 1

            # Wait interval
            if interval > 0:
                await asyncio.sleep(interval)

    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Total:    {stats['total']} payments in {elapsed:.1f}s ({stats['total']/elapsed:.1f}/s)")
    print(f"  Success:  {stats['success']} ({stats['success']/stats['total']*100:.0f}%)" if stats['total'] > 0 else "")
    print(f"  Failed:   {stats['failed']}")
    print(f"  Errors:   {stats['error']}")
    print(f"  By Type:  {json.dumps(stats['by_type'])}")
    print(f"{'='*60}\n")

    return stats


def main():
    parser = argparse.ArgumentParser(description="PaymentPro Traffic Simulator")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"API base URL (default: {DEFAULT_URL})")
    parser.add_argument("--count", type=int, default=20, help="Number of payments to generate (default: 20)")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between payments (default: 2)")
    parser.add_argument("--duration", type=float, default=0, help="Max duration in seconds (0=unlimited)")
    parser.add_argument("--profile", choices=PROFILES.keys(), default="mixed", help="Payment type distribution")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show each payment result")
    args = parser.parse_args()

    asyncio.run(run_simulator(
        base_url=args.url,
        count=args.count,
        interval=args.interval,
        duration=args.duration,
        profile=args.profile,
        verbose=args.verbose,
    ))


if __name__ == "__main__":
    main()
