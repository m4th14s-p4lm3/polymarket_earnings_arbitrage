import requests
import json
import time
from datetime import datetime

# --- CONFIGURATION ---
TOKEN_NO = (
    "62722005233739912694837180623567401979223102173730324524176457919194513939892"
)
TOKEN_YES = (
    "97537118540221875348319481740286935565220077047612494324842299539638592514493"
)

# List of targets to track
TARGETS = [{"label": "NO", "id": TOKEN_NO}, {"label": "YES", "id": TOKEN_YES}]

OUTPUT_FILE = "polymarket_liquidity.jsonl"


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


def save_to_jsonl(data, filename):
    """Appends data as a single line JSON object."""
    with open(filename, "a") as f:
        # Add a local timestamp for when we saved it
        data["local_timestamp"] = datetime.now().isoformat()

        # Write as a single line of JSON
        f.write(json.dumps(data) + "\n")


def main():
    print(f"Starting Liquidity Logger...")
    print(f"Tracking: {[t['label'] for t in TARGETS]}")
    print(f"Saving to: {OUTPUT_FILE}")
    print("Press Ctrl+C to stop.\n")

    while True:
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp_str}] Cycle starting...")

        for target in TARGETS:
            label = target["label"]
            token_id = target["id"]

            # 1. Fetch
            book_data = fetch_order_book(token_id)

            if book_data:
                # 2. Inject Context (Label & ID)
                # This ensures we know which token this data belongs to later
                book_data["outcome_side"] = label
                book_data["token_id"] = token_id

                # 3. Save
                save_to_jsonl(book_data, OUTPUT_FILE)
                print(f"   > {label}: Saved.")
            else:
                print(f"   > {label}: Failed.")

        # 4. Wait
        print("   Waiting 10s...")
        time.sleep(10)


if __name__ == "__main__":
    main()
