# from multiprocessing import Process, Event
from threading import Thread, Event, Lock
from datetime import datetime, timedelta, timezone
from typing import Dict
import time
import json

import polymarket_api
from edgar_sentinel import EdgarSentinel
from edgar_api import EDGAR
from stats.liquidity_save import run_liquidity_logger
from price_tracker import PriceTracker

from oracle import get_resolution

from telegram_bot import TelegramBot
import logging

logger = logging.getLogger(__name__)
import os

from dotenv import load_dotenv

load_dotenv()


TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
telegram_bot = TelegramBot(TOKEN, CHAT_ID)


class EarningsMarket:
    _liquidity_logger_threads: Dict[str, Thread] = {}
    _liquidity_logger_lock: Lock = Lock()

    def __init__(self, url: str, edgar_sentinel: EdgarSentinel, init_run=True):
        self.url: str = url
        self.slug: str = polymarket_api.Utils.extract_slug_from_url(url)
        self.ticker: str = polymarket_api.Utils.extract_ticker_from_slug(self.slug)
        self.cik: str = str(EDGAR().get_cik_by_ticker(self.ticker))

        self.description = polymarket_api.DataFeed.get_slug_description(self.slug)
        self.outcome_addresses: dict = (
            polymarket_api.DataFeed.get_slug_outcome_addresses(self.slug)
        )
        # print(self.outcome_addresses)

        self.expected_release_date: datetime = (
            polymarket_api.Utils.extract_expected_release_date(self.slug)
        )
        self.sec_url: str = None

        self.edgar_sentinel: EdgarSentinel = edgar_sentinel
        
        self.price_tracker:PriceTracker = None
        
        # if not edgar_sentinel.running:
        #     raise "ERROR: Edgar sentinel is not running!"

        self.thread: Thread = None
        self.alert: Event = Event()

        self.resolution: str = None
        self.oracle_time = None

        if init_run:
            self.run()

    @classmethod
    def start_liquidity_logger(cls, slug: str):
        with cls._liquidity_logger_lock:
            existing = cls._liquidity_logger_threads.get(slug)
            if existing and existing.is_alive():
                return

            def _run_liquidity_logger():
                # Runs the order book logger without blocking the main process.
                try:
                    run_liquidity_logger(slug)
                except Exception:
                    logger.exception(
                        "Liquidity logger exited unexpectedly for slug %s", slug
                    )

            logger.info("Starting liquidity logger for slug %s", slug)
            th = Thread(target=_run_liquidity_logger, daemon=True)
            cls._liquidity_logger_threads[slug] = th
            th.start()

    def set_sec_url(self, url):
        self.sec_url = url

    def trigger_alert(self):
        self.alert.set()

    def run(self):
        self.edgar_sentinel.set_alert(self.cik, self)
        self.thread = Thread(target=self.trade)
        self.thread.start()
        # self.start_liquidity_logger(self.slug)
        self.price_tracker:PriceTracker = PriceTracker(self.slug)


    def trade(self):
        # while True:
        # self.alert.clear()
        self.alert.wait()
        print("ALERT TRIGGERED!!!!")
        logger.info(f"Trigger sent to slug: {self.slug}")

        # get prices before oracle
        price_yes = polymarket_api.DataFeed.get_market_price_for_token(self.outcome_addresses["Yes"])
        price_no = polymarket_api.DataFeed.get_market_price_for_token(self.outcome_addresses["No"])
        logger.info(f"Price after trigger - slug: {self.slug}, ticker: {self.ticker}, price_yes {price_yes}, price_no: {price_no}")

        timer_start = time.perf_counter()
        resolution = get_resolution(self.description, self.sec_url)
        self.oracle_time = time.perf_counter() - timer_start

        resolution = json.loads(resolution)
        resolution = resolution["resolution"]
        if resolution != "not enough informations":
            resolution = resolution[0].upper() + resolution[1:].lower()
            # resolution = "Yes"
            address = self.outcome_addresses[resolution]
            # get pricee after oracle
            price = polymarket_api.DataFeed.get_market_price_for_token(address)
            telegram_bot.send_message(
                f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price: {price}, oracle time: {self.oracle_time}"
            )
            logger.info(
                f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price: {price}, oracle time: {self.oracle_time}"
            )
        else:
            price_yes = polymarket_api.DataFeed.get_market_price_for_token(
                self.outcome_addresses["Yes"]
            )
            price_no = polymarket_api.DataFeed.get_market_price_for_token(
                self.outcome_addresses["No"]
            )
            logger.info(
                f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price_yes {price_yes}, price_no: {price_no}, oracle time: {self.oracle_time}"
            )
            telegram_bot.send_message(
                f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price_yes {price_yes}, price_no: {price_no}, oracle time: {self.oracle_time}"
            )

        # self.thred.join()

    def __str__(self) -> str:
        return self.cik


if __name__ == "__main__":
    edgar_sentinel = EdgarSentinel()
    time.sleep(1)

    # kfy_url = "https://polymarket.com/event/kfy-quarterly-earnings-nongaap-eps-12-04-2025-1pt31"
    # kfy_em = EarningsMarket(kfy_url, edgar_sentinel)

    len_url = "https://polymarket.com/event/len-quarterly-earnings-gaap-eps-12-16-2025-2pt22"
    len_em = EarningsMarket(len_url, edgar_sentinel)

    gis_url = "https://polymarket.com/event/gis-quarterly-earnings-nongaap-eps-12-17-2025-1pt02"
    gis_em = EarningsMarket(gis_url, edgar_sentinel)


    print("Market is runnning...")
    
    edgar_sentinel.run()
    print("Sentinel is running...")

    # pass
