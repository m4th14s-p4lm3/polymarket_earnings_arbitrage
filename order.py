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
    # time.sleep(1)
    
    # kfy_url = "https://polymarket.com/event/kfy-quarterly-earnings-nongaap-eps-12-04-2025-1pt31"
    # kfy_em = EarningsMarket(kfy_url, edgar_sentinel)




    # 10/12/2025
    orcl_url = "https://polymarket.com/event/orcl-quarterly-earnings-nongaap-eps-12-08-2025-1pt64"

    chwy_url = "https://polymarket.com/event/chwy-quarterly-earnings-nongaap-eps-12-10-2025-0pt3"
    adbe_url = "https://polymarket.com/event/adbe-quarterly-earnings-nongaap-eps-12-10-2025-5pt4"
    mnt_url = "https://polymarket.com/event/mtn-quarterly-earnings-gaap-eps-12-10-2025-neg5pt24"

    orcl_em = EarningsMarket(orcl_url, edgar_sentinel)
    
    chwy_em = EarningsMarket(chwy_url, edgar_sentinel)
    adbe_em = EarningsMarket(adbe_url, edgar_sentinel)
    mnt_em = EarningsMarket(mnt_url, edgar_sentinel)

    # 11/12/2025
    cost_url = "https://polymarket.com/event/cost-quarterly-earnings-gaap-eps-12-11-2025-4pt28"
    avgo_url = "https://polymarket.com/event/avgo-quarterly-earnings-nongaap-eps-12-11-2025-1pt87"
    rh_url = "https://polymarket.com/event/rh-quarterly-earnings-nongaap-eps-12-11-2025-2pt16"
    lulu_url = "https://polymarket.com/event/lulu-quarterly-earnings-gaap-eps-12-11-2025-2pt21"

    cost_em = EarningsMarket(cost_url, edgar_sentinel)
    avgo_em = EarningsMarket(avgo_url, edgar_sentinel)
    rh_em = EarningsMarket(rh_url, edgar_sentinel)
    lulu_em = EarningsMarket(lulu_url, edgar_sentinel)



    # pcb_url = "https://polymarket.com/event/cpb-quarterly-earnings-nongaap-eps-12-09-2025-0pt73?tid=1765226600660"
    # azo_url = "https://polymarket.com/event/azo-quarterly-earnings-gaap-eps-12-09-2025-32pt58?tid=1765226611220"
    # dbi_url = "https://polymarket.com/event/dbi-quarterly-earnings-nongaap-eps-12-09-2025-0pt16?tid=1765226624433"
    # aso_url = "https://polymarket.com/event/aso-quarterly-earnings-nongaap-eps-12-09-2025-1pt06?tid=1765226633644"
    
    

    # pcb_em = EarningsMarket(pcb_url, edgar_sentinel)
    # azo_em = EarningsMarket(azo_url, edgar_sentinel)
    # dbi_em = EarningsMarket(dbi_url, edgar_sentinel)
    # aso_em = EarningsMarket(aso_url, edgar_sentinel)


    print("Market is runnning...")
    
    edgar_sentinel.run()
    print("Sentinel is running...")

    # pass