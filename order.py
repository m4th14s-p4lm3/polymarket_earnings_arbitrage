# from multiprocessing import Process, Event
from threading import Thread, Event
from datetime import datetime, timedelta, timezone
import time
import json

import polymarket_api
from edgar_sentinel import EdgarSentinel
from edgar_api import EDGAR

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
    def __init__(self, url:str, edgar_sentinel:EdgarSentinel, init_run = True):
        self.url:str = url
        self.slug:str = polymarket_api.Utils.extract_slug_from_url(url)
        self.ticker:str = polymarket_api.Utils.extract_ticker_from_slug(self.slug)
        self.cik:str = str(EDGAR().get_cik_by_ticker(self.ticker))
        
        self.description = polymarket_api.DataFeed.get_slug_description(self.slug)
        self.outcome_addresses:dict = polymarket_api.DataFeed.get_slug_outcome_addresses(self.slug)
        # print(self.outcome_addresses)

        self.expected_release_date:datetime = polymarket_api.Utils.extract_expected_release_date(self.slug)
        self.sec_url:str = None

        self.edgar_sentinel:EdgarSentinel = edgar_sentinel
        # if not edgar_sentinel.running:
        #     raise "ERROR: Edgar sentinel is not running!"

        self.thred:Thread = None
        self.alert:Event = Event()

        self.resolution:str = None
        self.oracle_time = None

        if init_run:
            self.run()

    def set_sec_url(self, url):
        self.sec_url = url

    def trigger_alert(self):
        self.alert.set()

    def run(self):
        self.edgar_sentinel.set_alert(self.cik, self)
        self.thred = Thread(target=self.trade)
        self.thred.start()
        
    def trade(self):
        # while True:
            # self.alert.clear()
        self.alert.wait()
        print("ALERT TRIGGERED!!!!")
        logger.info(f"Trigger sent to slug: {self.slug}")

        timer_start = time.perf_counter()
        resolution = get_resolution(self.description, self.sec_url)
        self.oracle_time = time.perf_counter() - timer_start

        resolution = json.loads(resolution)
        resolution = resolution["resolution"]
        if resolution != "not enough informations":
            resolution = resolution[0].upper() + resolution[1:].lower()
            # resolution = "Yes"
            address = self.outcome_addresses[resolution]
            price = polymarket_api.DataFeed.get_market_price_for_token(address)
            telegram_bot.send_message(f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price: {price}, oracle time: {self.oracle_time}")
            logger.info(f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price: {price}, oracle time: {self.oracle_time}")
        else:
            price_yes = polymarket_api.DataFeed.get_market_price_for_token(self.outcome_addresses["Yes"])
            price_no = polymarket_api.DataFeed.get_market_price_for_token(self.outcome_addresses["No"])
            logger.info(f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price_yes {price_yes}, price_no: {price_no}, oracle time: {self.oracle_time}")
            telegram_bot.send_message(f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price_yes {price_yes}, price_no: {price_no}, oracle time: {self.oracle_time}")

        # self.thred.join()


    def __str__(self)->str:
        return self.cik

if __name__ == "__main__":
    edgar_sentinel = EdgarSentinel()
    time.sleep(1)
    
    # kfy_url = "https://polymarket.com/event/kfy-quarterly-earnings-nongaap-eps-12-04-2025-1pt31"
    # kfy_em = EarningsMarket(kfy_url, edgar_sentinel)

    orcl_url = "https://polymarket.com/event/orcl-quarterly-earnings-nongaap-eps-12-08-2025-1pt64"
    orcl_em = EarningsMarket(orcl_url, edgar_sentinel)


    print("Market is runnning...")
    # print(mcd_em.slug)
    
    edgar_sentinel.run()
    print("Sentinel is running...")

    # pass