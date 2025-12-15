import json
from time import gmtime, strftime
from datetime import datetime
import logging
import os

# from multiprocessing import Process, Event
from threading import Thread, Event

from edgar_api import EDGAR
# from order import EarningsMarket

LOG_DIR = "logs"
if not os.path.isdir(LOG_DIR):
    os.mkdir(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=f"logs/sec_sentinel.log",
    filemode="a",
)


class EdgarSentinel:
    def __init__(self):
        self.edgar: EDGAR = EDGAR()
        self.logger: logging = logging.getLogger(__name__)
        self.thred: Thread = None
        self.running: bool = False
        self.cik_alerts: dict = {}  # {cik : Event}

    def set_alert(self, cik: str, earnings_market):
        self.cik_alerts.update({cik: earnings_market})

    def get_process(self):
        return self.process

    def get_process_status(self):
        return self.running

    def run(self):
        self.thread = Thread(target=self._watch)
        self.thread.start()

    def _watch(self):
        while True:  # watch dog
            try:
                self.running = True
                old_feed = set(self.edgar.get_rss_feed())
                # old_feed.pop()
                # old_feed.pop()

                while True:  # feed loop
                    feed = self.edgar.get_rss_feed()
                    for data in feed:
                        if data not in old_feed:
                            sec_url = data[1]
                            cik = str(sec_url.split("/")[6])
                            data = list(data)
                            data.append(cik)
                            # print(self.cik_alerts)
                            self.logger.info(
                                f"cik: {cik}, self.cik_alerts: {self.cik_alerts}"
                            )

                            # TODO: Add 8-K | 10-K | 10-Q in data[0] requirement!
                            if cik in self.cik_alerts:
                                self.logger.info(f"Alert sent to {cik}")
                                base_url = "/".join(
                                    data[1].split("/")[:-1]
                                )  # must remove the last part of url
                                self.cik_alerts[cik].set_sec_url(base_url)
                                self.cik_alerts[cik].trigger_alert()

                            # for c in self.cik_alerts:
                            #     self.logger.info(f"Alert sent to {c}")

                            #     print(c)
                            #     base_url = "/".join(data[1].split("/")[:-1]) # must remove the last part of url
                            #     # base_url = "https://www.sec.gov/Archives/edgar/data/1856437/000185643725000045/"
                            #     self.cik_alerts[c].set_sec_url(base_url)
                            #     self.cik_alerts[c].trigger_alert()

                            print(datetime.now(), end=" - ")
                            print(data)

                            self.logger.info(json.dumps(data))
                    old_feed = feed
            except Exception as e:
                self.running = False
                self.logger.error(f"Sentinel stopped with exception: {e}")


if __name__ == "__main__":
    edgar_sentinel = EdgarSentinel()
    edgar_sentinel.run()

    print("Sentinel is running...")
