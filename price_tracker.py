import time
import polymarket_api 
from threading import Thread

import os
import json

PRICE_DATA_PATH = "price_data"

class PriceTracker:
    """
        This class creates a thred which track market prices for a market on polymarket.
        The ouput file structure is unix_time_stamp price_yes price_no separated by space
        and each entry is a new line.
    """
    def __init__(self, slug:str):
        self.slug:str = slug
        self.token_addresses:dict = polymarket_api.DataFeed.get_slug_outcome_addresses(slug)

        self.thread = None
        self.thread_running = False

        self.price_file_name = slug

        self.run() # start thread

    def run(self):
        self.thread = Thread(target=self.track_price)
        self.thread_running = True
        self.thread.start()
    
    def stop(self):
        self.thread_running = False
        
    def track_price(self):
        if not os.path.isdir(PRICE_DATA_PATH):
            os.mkdir(PRICE_DATA_PATH)

        open(os.path.join(PRICE_DATA_PATH, self.price_file_name), 'a').close() # create an empty file
        while self.thread_running:
            tokken_address_yes = self.token_addresses["Yes"]
            tokken_address_no = self.token_addresses["No"]

            time_stamp = time.time()
            price_yes = json.loads(polymarket_api.DataFeed.get_market_price_for_token(tokken_address_yes))["price"]
            price_no = json.loads(polymarket_api.DataFeed.get_market_price_for_token(tokken_address_no))["price"]
            with open(os.path.join(PRICE_DATA_PATH, self.price_file_name), "a") as f:
                f.write(f"{time_stamp} {price_yes} {price_no}\n")



if __name__ == "__main__":

    slug = "len-quarterly-earnings-gaap-eps-12-16-2025-2pt22"
    addresses = polymarket_api.DataFeed.get_slug_outcome_addresses(slug)
    print(addresses)
    price_tracker = PriceTracker(slug)

    price_tracker.run()
    time.sleep(3)
    price_tracker.stop()