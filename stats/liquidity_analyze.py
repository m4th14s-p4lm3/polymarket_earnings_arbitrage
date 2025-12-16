import argparse
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
DEFAULT_INPUT_FILE = "polymarket_liquidity.jsonl"


def parse_order_book(bids, asks):
    """
    Parses raw bid/ask lists into usable float data and calculates stats.
    Returns: best_bid, best_ask, bid_shares, ask_shares, bid_usdc, ask_usdc
    """
    parsed_bids = [(float(x["price"]), float(x["size"])) for x in bids]
    parsed_asks = [(float(x["price"]), float(x["size"])) for x in asks]

    # 1. Best Price
    best_bid = max([b[0] for b in parsed_bids]) if parsed_bids else 0.0
    best_ask = min([a[0] for a in parsed_asks]) if parsed_asks else 0.0

    # 2. Share Volume
    bid_shares = sum([b[1] for b in parsed_bids])
    ask_shares = sum([a[1] for a in parsed_asks])

    # 3. USDC Liquidity (Price * Size)
    bid_usdc = sum([b[0] * b[1] for b in parsed_bids])
    ask_usdc = sum([a[0] * a[1] for a in parsed_asks])

    return best_bid, best_ask, bid_shares, ask_shares, bid_usdc, ask_usdc


def print_table(title, records):
    """Helper function to print a formatted table for a list of records."""
    if not records:
        print(f"\n--- {title} (No Data Found) ---")
        return

    print(f"\n{'=' * 25} {title} {'=' * 25}")
    header = (
        f"{'TIMESTAMP':<10} | "
        f"{'BID':<5} | {'ASK':<5} | "
        f"{'SPREAD':<6} | "
        f"{'B_SHARES':<8} | {'B_$':<7} | "
        f"{'A_SHARES':<8} | {'A_$':<7} | "
        f"{'TOT_LIQ_$':<9}"
    )

    print("-" * len(header))
    print(header)
    print("-" * len(header))

    count = 0
    for data in records:
        try:
            ts_raw = data.get("local_timestamp", "")
            ts_display = ts_raw.split("T")[1].split(".")[0] if "T" in ts_raw else ts_raw

            bids = data.get("bids", [])
            asks = data.get("asks", [])

            best_bid, best_ask, bid_sh, ask_sh, bid_val, ask_val = parse_order_book(
                bids, asks
            )
            spread = best_ask - best_bid
            total_liq_usdc = bid_val + ask_val

            print(
                f"{ts_display:<10} | "
                f"{best_bid:<5.3f} | {best_ask:<5.3f} | "
                f"{spread:<6.3f} | "
                f"{bid_sh:<8.0f} | {bid_val:<7.0f} | "
                f"{ask_sh:<8.0f} | {ask_val:<7.0f} | "
                f"{total_liq_usdc:<9.0f}"
            )
            count += 1
        except (json.JSONDecodeError, KeyError):
            continue

    print("-" * len(header))
    print(f"Total Rows: {count}")


def main(files=None):
    paths = files or [DEFAULT_INPUT_FILE]

    yes_records = []
    no_records = []

    for path in paths:
        if not os.path.exists(path):
            print(f"Warning: File '{path}' not found. Skipping.")
            continue

        print(f"Reading stats from: {path}...")

        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    side = data.get("outcome_side", "UNKNOWN").upper()

                    if side == "YES":
                        yes_records.append(data)
                    elif side == "NO":
                        no_records.append(data)
                    else:
                        # You can add a list for 'unknown' if you have old data
                        pass
                except json.JSONDecodeError:
                    continue

    if not yes_records and not no_records:
        print("No data found in provided files.")
        return

    print_table("YES TOKEN LIQUIDITY", yes_records)
    print_table("NO TOKEN LIQUIDITY", no_records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze logged Polymarket liquidity JSONL files."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="One or more JSONL files to analyze. Defaults to polymarket_liquidity.jsonl",
    )

    args = parser.parse_args()
    main(args.files if args.files else None)
