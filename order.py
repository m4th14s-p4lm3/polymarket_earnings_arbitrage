# from multiprocessing import Process, Event
from threading import Thread, Event
from datetime import datetime, timedelta, timezone
import time
import json

from prometheus_client import start_http_server

from metrics import ORACLE_RESOLUTION, ORACLE_RESOLUTION_TIME, POLYMARKET_MARKET_VOLUME_USD, POLYMARKET_TOKEN_PRICE_USD, POLYMARKET_USD_EARNED, POLYMARKET_WATCHED_MARKETS
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

        self.thread:Thread = None
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
        self.thread = Thread(target=self.trade)
        self.thread.start()
        
    def trade(self):
        POLYMARKET_WATCHED_MARKETS.labels(cik=self.cik, ticker=self.ticker).inc()
        
        # while True:
            # self.alert.clear()
        self.alert.wait()
        print("ALERT TRIGGERED!!!!")
        logger.info(f"Trigger sent to slug: {self.slug}")

        # get prices before oracle
        price_yes = polymarket_api.DataFeed.get_market_price_for_token(self.outcome_addresses["Yes"])
        price_no = polymarket_api.DataFeed.get_market_price_for_token(self.outcome_addresses["No"])
        logger.info(f"Price after trigger - slug: {self.slug}, ticker: {self.ticker}, price_yes {price_yes}, price_no: {price_no}")
        try:
            POLYMARKET_TOKEN_PRICE_USD.labels(cik=self.cik, ticker=self.ticker, slug=self.slug, event='edgar_alert', outcome='Yes').set(float(price_yes))
            POLYMARKET_TOKEN_PRICE_USD.labels(cik=self.cik, ticker=self.ticker, slug=self.slug, event='edgar_alert', outcome='No').set(float(price_no))
        except (ValueError, TypeError):
            pass

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
            telegram_bot.send_message(f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price: {price}, oracle time: {self.oracle_time}")
            logger.info(f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price: {price}, oracle time: {self.oracle_time}")
            try:
                POLYMARKET_TOKEN_PRICE_USD.labels(cik=self.cik, ticker=self.ticker, slug=self.slug, event='oracle_resolution', outcome=resolution).set(float(price))
            except (ValueError, TypeError):
                pass
        else:
            price_yes = polymarket_api.DataFeed.get_market_price_for_token(self.outcome_addresses["Yes"])
            price_no = polymarket_api.DataFeed.get_market_price_for_token(self.outcome_addresses["No"])
            logger.info(f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price_yes {price_yes}, price_no: {price_no}, oracle time: {self.oracle_time}")
            telegram_bot.send_message(f"slug: {self.slug}, ticker: {self.ticker}, resolution: {resolution}, price_yes {price_yes}, price_no: {price_no}, oracle time: {self.oracle_time}")
            try:
                POLYMARKET_TOKEN_PRICE_USD.labels(cik=self.cik, ticker=self.ticker, slug=self.slug, event='oracle_resolution', outcome='Yes').set(float(price_yes))
                POLYMARKET_TOKEN_PRICE_USD.labels(cik=self.cik, ticker=self.ticker, slug=self.slug, event='oracle_resolution', outcome='No').set(float(price_no))
            except (ValueError, TypeError):
                pass
        # self.thred.join()
        ORACLE_RESOLUTION_TIME.labels(cik=self.cik, ticker=self.ticker, slug=self.slug).set(self.oracle_time)
        ORACLE_RESOLUTION.labels(cik=self.cik, ticker=self.ticker, slug=self.slug, outcome=resolution).inc()


    def __str__(self)->str:
        return self.cik

if __name__ == "__main__":
    LOG_DIR = "logs"
    if not os.path.isdir(LOG_DIR):
        os.mkdir(LOG_DIR)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=f'logs/sec_sentinel.log',
        filemode='a'
    )

    edgar_sentinel = EdgarSentinel()
    urls = os.environ.get("POLYMARKET_URLS")
    if urls == None:
        logger.error("No markets supplied with POLYMARKET_URLS, stopping...")
        exit(1)
    markets = [EarningsMarket(url, edgar_sentinel) for url in urls.splitlines()]
    logger.info("Watching markets " + ", ".join(urls.splitlines()))
    logger.info("Market is runnning...")
    
    start_http_server(9090)
    logger.info("Prometheus HTTP server running...")
    
    edgar_sentinel.run()
    logger.info("Sentinel is running...")
