from prometheus_client import Gauge, Counter

EDGAR_RSS_FEED_SUBMITIONS = Counter(
    'edgar_rss_feed_submitions_total', 
    'Total tracked submitions to EDGAR RSS feed', 
    ['cik']
)

POLYMARKET_WATCHED_MARKETS = Counter(
    'polymarket_watched_markets_total',
    'Total watched markets in Polymarket',
    ['cik', 'ticker']
)

POLYMARKET_USD_EARNED = Gauge(
    'polymarket_usd_earned_total',
    'Total USD earned in Polymarket trades',
    ['cik', 'ticker', 'slug']
)

POLYMARKET_TOKEN_PRICE_USD = Gauge(
    'polymarket_token_price_usd',
    'Price of yes/no tokens in Polymarket',
    ['cik', 'ticker', 'slug', 'event', 'outcome']
)

POLYMARKET_MARKET_VOLUME_USD = Gauge(
    'polymarket_market_volume_usd_total',
    'Total USD in Polymarket markets after oracle resolution and buying tokens',
    ['cik', 'ticker', 'slug']
)

ORACLE_RESOLUTION_TIME = Gauge(
    'oracle_resolution_time_seconds',
    'Time in seconds it took the Oracle to find the Polymarket market resolution',
    ['cik', 'ticker', 'slug']
)

ORACLE_RESOLUTION = Counter(
    'oracle_resolution_total',
    'The total amount of yes/no resolutions of Oracle',
    ['cik', 'ticker', 'slug', 'outcome']
)
