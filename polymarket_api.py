import requests
import time
import datetime
import json
import numpy as np
from datetime import datetime, timedelta, timezone

# --- TRADING PART -------------------------------------------------

import os
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY, SELL


class TradingClient:
    """
    Jednoduchý wrapper kolem Polymarket CLOB klienta.

    - připojí se k účtu přes privátní klíč
    - umí poslat limitní order na konkrétní token_id (YES/NO outcome)
    """

    def __init__(
        self,
        private_key: str | None = None,
        host: str = "https://clob.polymarket.com",
        chain_id: int = POLYGON,
        funder: str | None = None,
    ) -> None:
        """
        private_key – privátní klíč účtu, který má USDC na Polymarketu
        funder      – adresa, ze které se bere balance (u EOA můžeš nechat None)
        """
        if private_key is None:
            private_key = os.getenv("POLYMARKET_PK")
        if not private_key:
            raise RuntimeError("Missing private key. Set POLYMARKET_PK env var.")

        self.client = ClobClient(
            host,
            key=private_key,
            chain_id=chain_id,
            funder=funder,
        )

        # L1 -> L2: vygeneruje nebo odvodí API key/secret/passphrase
        self.client.set_api_creds(self.client.create_or_derive_api_creds())

    def place_limit_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str = "BUY",
    ) -> dict:
        """
        Pošle limit order (bet) na daný outcome token.

        token_id – clobTokenId z Gamma API (to, co už máš v self.outcome_addresses)
        price    – limitní cena 0.01–0.99
        size     – kolik "shares" (viz docs – v praxi kolik kontraktů)
        side     – "BUY" nebo "SELL"
        """
        side_const = BUY if side.upper() == "BUY" else SELL

        order_args = OrderArgs(
            price=price,
            size=size,
            side=side_const,
            token_id=token_id,
        )

        # convenience: create + sign + post jedním call-em
        resp = self.client.create_and_post_order(order_args)
        return resp

class Utils:
    @staticmethod
    def extract_ticker_from_slug(slug) -> str:
        return slug.split("-")[0].upper()

    @staticmethod
    def extract_slug_from_url(url) -> str:
        return url.split("/")[-1]

    @staticmethod
    def extract_expected_release_date(slug) -> datetime:
        slug_split = slug.split("-")

        if len(slug_split[5]) == 4:
            y = int(slug_split[5])
            m = int(slug_split[6])
            d = int(slug_split[7])
        else:
            m = int(slug_split[5])
            d = int(slug_split[6])
            y = int(slug_split[7])
        dt = datetime(y, m, d, tzinfo=timezone.utc)
        return dt


class DataFeed:
    @staticmethod
    def get_slug_description(slug):
        url = "https://gamma-api.polymarket.com/markets/slug/" + slug
        resp = requests.get(url)
        resp.raise_for_status()
        resp_json = json.loads(resp.text)
        description = resp_json["description"]
        return description

    @staticmethod
    def get_slug_outcome_addresses(slug) -> dict:
        url = "https://gamma-api.polymarket.com/markets/slug/" + slug
        resp = requests.get(url)
        resp.raise_for_status()
        resp_json = json.loads(resp.text)

        description = resp_json["description"]
        outcomes = json.loads(resp_json["outcomes"])
        outcome_prices = json.loads(resp_json["outcomePrices"])
        clobTokenIds = json.loads(resp_json["clobTokenIds"])

        closed = resp_json["closed"]
        created_at = resp_json["createdAt"]

        outcome_addresses = {outcomes[0]: clobTokenIds[0], outcomes[1]: clobTokenIds[1]}
        return outcome_addresses

    @staticmethod
    def get_slug_data(slug) -> dict:
        url = "https://gamma-api.polymarket.com/markets/slug/" + slug
        resp = requests.get(url)
        resp.raise_for_status()
        resp_json = json.loads(resp.text)

        description = resp_json["description"]
        outcomes = json.loads(resp_json["outcomes"])
        outcome_prices = json.loads(resp_json["outcomePrices"])
        clobTokenIds = json.loads(resp_json["clobTokenIds"])

        closed = resp_json["closed"]
        created_at = resp_json["createdAt"]

        outcome_addresses = {outcomes[0]: clobTokenIds[0], outcomes[1]: clobTokenIds[1]}

        return {
            "description": description,
            "outcome_prices": outcome_prices,
            "outcome_addresses": outcome_addresses,
            "closed": closed,
            "created_at": created_at,
        }

    @staticmethod
    def get_price_history_for_token(token_id, start_dt, end_dt) -> list:
        HOST = "https://clob.polymarket.com"

        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())

        resp = requests.get(
            f"{HOST}/prices-history",
            params={
                "market": token_id,
                "startTs": start_ts,
                "endTs": end_ts,
            },
        )

        resp.raise_for_status()
        data = resp.json()
        history = data.get("history", [])

        prices = []
        for point in history:
            prices.append((point["t"], point["p"]))
        # prices = np.array(prices)
        return prices

    @staticmethod
    def get_market_price_for_token(token_id):
        HOST = "https://clob.polymarket.com/"
        resp = requests.get(
            f"{HOST}/price", params={"token_id": token_id, "side": "SELL"}
        )
        return resp.text


if __name__ == "__main__":
    # slug = "ccl-quarterly-earnings-nongaap-eps-2025-09-29-1pt32"
    slug = "dltr-quarterly-earnings-nongaap-eps-12-03-2025-1pt08"
    slug_data = DataFeed.get_slug_data(slug)

    resolve = None
    if (
        float(slug_data["outcome_prices"][0]) == 1.0
        and float(slug_data["outcome_prices"][1]) == 0.0
    ):
        resolve = "Yes"
    if (
        float(slug_data["outcome_prices"][0]) == 0.0
        and float(slug_data["outcome_prices"][1]) == 1.0
    ):
        resolve = "No"

    print(slug_data)
    # print(slug_data["outcome_prices"][0])
    # 16, 6, 57

    if resolve is None:
        print("NOT RESOLVED YET")
        exit()

    start_dt = datetime.datetime.fromisoformat("2025-10-21T05:00:00+00:00")
    end_dt = datetime.datetime.fromisoformat("2025-10-21T22:40:00+00:00")

    address = slug_data["outcome_addresses"][resolve]
    prices = DataFeed.get_price_history_for_token(address, start_dt, end_dt)
    # print(address)
    # print(res)
    dt_release = datetime.datetime(
        2025, 10, 21, 6, 53, 12, tzinfo=datetime.timezone.utc
    )
    unix_ts = dt_release.timestamp()
    # print(prices)

    for p in prices:
        if int(p[0]) > unix_ts:
            print(p)

    # print(get_market_price_for_token(address))
