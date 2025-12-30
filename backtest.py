import json
import logging
from model import Oracle, Resolution
from dataclasses import dataclass
from time import perf_counter
import numpy as np
from tqdm import tqdm


@dataclass
class BacktestCase:
    sec_url: str
    true_resolution: Resolution
    description: str = ""


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

        pbar = tqdm(self.data, desc="Backtesting", unit="case")

        for i, case in enumerate(pbar, start=1):
            start = perf_counter()
            oracle_result = self.oracle.resolve(case.sec_url, description=case.description)
            duration = perf_counter() - start

            is_correct = oracle_result == case.true_resolution

            total += 1
            if oracle_result == Resolution.UNK:
                unks += 1
            if is_correct:
                correct += 1

            durations.append(duration)
            total_time += duration
            self.results.append((case, oracle_result, is_correct, duration))

            avg_time = total_time / total
            remaining = avg_time * (len(self.data) - total)
            resolved = total - unks
            acc = correct / resolved if resolved > 0 else 0.0

            pbar.set_postfix(
                acc=f"{acc:.3f}",
                unk=unks,
                avg=f"{avg_time:.2f}s",
                eta=f"{remaining:.1f}s",
            )
        durations = np.array(durations)
        acc = correct / total
        logging.info(f"Backtest Summary:")
        logging.info(f"Total cases: {correct}/{total}, Total Acc: {acc:.3f}")
        logging.info(f"Unknown cases: {unks}")
        if total - unks > 0:
            logging.info(f"Resolved cases: {correct}/{total - unks} correct, Resolved acc: {correct / (total - unks):.3f}")
        logging.info(f"Average oracle resolution time: {durations.mean():.3f} seconds")
        logging.info(f"min: {durations.min():.3f} seconds, max: {durations.max():.3f} seconds, std: {durations.std():.3f} seconds")


if __name__ == "__main__":
    from edgar_api import EDGAR
    # read json
    with open("backtest_data/data.json", "r") as f:
        data = json.load(f)
    backtest_data = [
        BacktestCase(row["sec_link"], Resolution(row["target"].lower()), row["description"])
        for row in data[:10]
    ]
    print(f"Loaded {len(backtest_data)} backtest cases.")

    # logging.basicConfig(level=logging.INFO)
    # logger = logging.getLogger(__name__)

    # (1) Define a random oracle for testing
    # import time
    # class RandOracle(Oracle):
    #     def resolve(self, sec_url: str, description: str = "") -> Resolution:
    #         # wait for ~2 sec
    #         sleep_time = 1 + np.random.rand() * 2
    #         time.sleep(sleep_time)
    #         return np.random.choice([Resolution.YES, Resolution.NO, Resolution.UNK], p=[0.4, 0.4, 0.2])

    # oracle = RandOracle(EDGAR())

    # (2) Use the real oracle
    oracle = Oracle(EDGAR())

    # Run backtest
    backtest = Backtest(oracle, backtest_data)
    backtest.run()

