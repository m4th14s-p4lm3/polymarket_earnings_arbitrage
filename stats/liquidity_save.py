from pathlib import Path
import requests
import json
import time
from datetime import datetime

from polymarket_api import DataFeed

DEFAULT_INTERVAL_SECONDS = 10
__all__ = ["run_liquidity_logger"]


def fetch_order_book(token_id):
    """Fetches the order book for a specific token from Polymarket CLOB."""
    url = "https://clob.polymarket.com/book"
    params = {"token_id": token_id}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def save_to_jsonl(data, filename: Path):
    """Appends data as a single line JSON object."""
    with open(filename, "a") as f:
        data["local_timestamp"] = datetime.now().isoformat()
        f.write(json.dumps(data) + "\n")


def build_targets_for_slug(slug):
    outcome_addresses = DataFeed.get_slug_outcome_addresses(slug)
    targets = []
    for label, token_id in outcome_addresses.items():
        targets.append({"label": label, "id": token_id})
    return targets


def run_liquidity_logger(
    slug: str,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    output_file: Path | None = None,
):
    targets = build_targets_for_slug(slug)
    output_path = output_file or Path(f"polymarket_liquidity_{slug}.jsonl")

    print("Starting Liquidity Logger...")
    print(f"Market slug: {slug}")
    print(f"Tracking: {[t['label'] for t in targets]}")
    print(f"Saving to: {output_path}")
    print("Press Ctrl+C to stop.\n")

    while True:
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp_str}] Cycle starting...")

        for target in targets:
            label = target["label"]
            token_id = target["id"]

            book_data = fetch_order_book(token_id)

            if book_data:
                book_data["outcome_side"] = label
                book_data["token_id"] = token_id
                book_data["slug"] = slug

                save_to_jsonl(book_data, output_path)
                print(f"   > {label}: Saved.")
            else:
                print(f"   > {label}: Failed.")

        print(f"   Waiting {interval_seconds}s...")
        time.sleep(interval_seconds)
