from datetime import datetime, time
import json
import logging
import os
from model import Oracle, Resolution
from dataclasses import dataclass
from time import perf_counter, sleep
import numpy as np
from tqdm import tqdm
import argparse
import csv
import json
import logging
import numpy as np

import bisect

class LinearTimeSeries:
    def __init__(self, points):
        # assume points are sorted by timestamp
        self.timestamps = [t for t, _ in points]
        self.values = [v for _, v in points]

    def query(self, t):
        # handle boundaries explicitly
        if t <= self.timestamps[0]:
            return self.values[0]
        if t >= self.timestamps[-1]:
            return self.values[-1]

        i = bisect.bisect_right(self.timestamps, t) - 1

        t0, t1 = self.timestamps[i], self.timestamps[i + 1]
        v0, v1 = self.values[i], self.values[i + 1]

        # linear interpolation
        return v0 + (t - t0) * (v1 - v0) / (t1 - t0)



@dataclass
class BacktestCase:
    sec_url: str
    true_resolution: Resolution
    description: str = ""
    price_series: LinearTimeSeries | None = None
    resolution_time: float | None = None


class Backtest:
    def __init__(self, oracle: Oracle, data: list[BacktestCase]):
        self.oracle = oracle
        self.data = data
        self.results = []

    def run(self):
        self.results = []

        correct = 0
        unks = 0
        total = 0

        total_time = 0.0
        durations = []

        profits = []
        profits_pct = []

        profit_sum = 0.0
        profit_pct_sum = 0.0

        pbar = tqdm(self.data, desc="Backtesting", unit="case")

        for case in pbar:
            start = perf_counter()
            oracle_result = self.oracle.resolve(case.sec_url, description=case.description)
            duration = perf_counter() - start

            is_correct = oracle_result == case.true_resolution
            is_unknown = oracle_result == Resolution.UNK

            release_price = None
            trade_price = None
            profit = None
            profit_pct = None

            if case.price_series is not None and case.resolution_time is not None:
                release_price = case.price_series.query(case.resolution_time)
                trade_price = case.price_series.query(case.resolution_time + duration)

                if not is_unknown:
                    if is_correct:
                        profit = (1.0 - trade_price)
                    else:
                        profit = -trade_price

                    profit_pct = profit / trade_price

                    profits.append(profit)
                    profits_pct.append(profit_pct)

                    profit_sum += profit
                    profit_pct_sum += profit_pct

            total += 1
            total_time += duration
            durations.append(duration)

            if is_unknown:
                unks += 1
            if is_correct:
                correct += 1

            self.results.append(
                (
                    case,
                    oracle_result,
                    is_correct,
                    duration,
                    release_price,
                    trade_price,
                    profit,
                    profit_pct,
                )
            )

            avg_time = total_time / total
            remaining = avg_time * (len(self.data) - total)

            resolved = total - unks
            acc = correct / resolved if resolved > 0 else 0.0

            avg_profit = profit_sum / len(profits) if profits else 0.0
            avg_profit_pct = profit_pct_sum / len(profits_pct) if profits_pct else 0.0

            pbar.set_postfix(
                acc=f"{acc:.3f}",
                unk=unks,
                avg_t=f"{avg_time:.2f}s",
                eta=f"{remaining:.1f}s",
                avg_p=f"{avg_profit:.4f}",
                avg_p_pct=f"{avg_profit_pct:.2%}",
            )

    def print_results(self):
        total = len(self.results)

        correct = sum(r[2] for r in self.results)
        unks = sum(1 for r in self.results if r[1] == Resolution.UNK)

        durations = np.array([r[3] for r in self.results])

        profits = np.array([r[6] for r in self.results if r[6] is not None])
        profits_pct = np.array([r[7] for r in self.results if r[7] is not None])

        print("\nBacktest Summary")
        print("=" * 60)

        print(f"Total cases        : {total}")
        print(f"Correct            : {correct}")
        print(f"Unknown            : {unks}")
        print(f"Accuracy (total)   : {correct / total:.3f}")

        if total - unks > 0:
            print(f"Accuracy (resolved): {correct / (total - unks):.3f}")

        print("\nOracle timing (seconds)")
        print(f"  Mean : {durations.mean():.3f}")
        print(f"  Min  : {durations.min():.3f}")
        print(f"  Max  : {durations.max():.3f}")
        print(f"  Std  : {durations.std():.3f}")

        if len(profits) > 0:
            print("\nSimulated trading performance")
            print(f"  Total profit     : {profits.sum():.4f}")
            print(f"  Avg profit       : {profits.mean():.4f}")
            print(f"  Min / Max profit : {profits.min():.4f} / {profits.max():.4f}")
            print(f"  Profit std       : {profits.std():.4f}")
            print(f"  Avg profit %     : {profits_pct.mean():.4%}")
            print(f"  Profitable trades: {(profits > 0).sum()}/{len(profits)}")

        print("=" * 60)


def write_results_csv(results, output_path):
    fieldnames = [
        "sec_url",
        "true_resolution",
        "oracle_resolution",
        "is_correct",
        "is_unknown",
        "resolution_time",
        "oracle_latency_sec",
        "release_price",
        "trade_price",
        "profit",
        "profit_pct",
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for (
            case,
            oracle_result,
            is_correct,
            duration,
            release_price,
            trade_price,
            profit,
            profit_pct,
        ) in results:
            writer.writerow({
                "sec_url": case.sec_url,
                "true_resolution": case.true_resolution.value,
                "oracle_resolution": oracle_result.value,
                "is_correct": is_correct,
                "is_unknown": oracle_result == Resolution.UNK,
                "resolution_time": case.resolution_time,
                "oracle_latency_sec": duration,
                "release_price": release_price,
                "trade_price": trade_price,
                "profit": profit,
                "profit_pct": profit_pct,
            })


def main():
    parser = argparse.ArgumentParser(description="Run oracle backtests.")
    parser.add_argument(
        "-s", "--source",
        default="backtest_data/cases/time_series_data.json",
        help="Path to backtest source JSON file"
    )
    parser.add_argument(
        "-o", "--output",
        default="backtest_data/results/",
        help="Path to output CSV folder"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of test cases"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    args = parser.parse_args()
    output_dir = os.path.dirname(args.output)
    base_name = os.path.splitext(os.path.basename(args.output))[0]
    ext = os.path.splitext(args.output)[1] or ".csv"

    os.makedirs(output_dir, exist_ok=True)

    timestamped_output = os.path.join(
        output_dir,
        f"{base_name}_{timestamp}{ext}"
)

    with open(args.source, "r") as f:
        data = json.load(f)

    np.random.seed(args.seed)

    if args.limit is not None:
        data = np.random.choice(data, size=args.limit, replace=False)

    backtest_data = [
        BacktestCase(
            row["sec_link"],
            Resolution(row["target"].lower()),
            row.get("description", ""),
            LinearTimeSeries(row["price_series"]) if "price_series" in row else None,
            row.get("sec_time_stamp"),
        )
        for row in data
    ]

    from edgar_api import EDGAR
    oracle = Oracle(EDGAR())

    backtest = Backtest(oracle, backtest_data)

    try:
        backtest.run()
    except KeyboardInterrupt:
        print("\nBacktest interrupted by user.")
    except Exception as e:
        print(f"\nBacktest failed with error: {e}")
        raise
    finally:
        if backtest.results:
            write_results_csv(backtest.results, timestamped_output)
            backtest.print_results()
            print(f"\nResults written to {timestamped_output}")
        else:
            print("\nNo results to write.")


if __name__ == "__main__":
    main()

