# Polymarket Earnings Arbitrage

This project monitors Polymarket earnings markets, watches the SEC EDGAR feed for new filings, uses a Gemini-powered oracle to resolve outcomes from filings, and optionally places trades and sends Telegram alerts. The main entry point is `order.py`.

## How It Works
- `order.py` registers earnings markets by Polymarket URL, starts the SEC sentinel, and spawns per-market threads.
- `edgar_sentinel.py` polls the SEC RSS feed; when a new filing appears for a tracked CIK, it triggers the market.
- `oracle.py` downloads filing HTMLs as PDFs and asks Gemini for a JSON resolution (`yes`/`no`/`not enough informations`).
- `polymarket_api.py` pulls market metadata and prices and (optionally) submits CLOB limit orders.
- `price_tracker.py` logs live YES/NO prices to `price_data/<slug>` while a market is running.
- `stats/liquidity_save.py` logs order book snapshots to `polymarket_liquidity_<slug>.jsonl`.

## Requirements
- Python 3.10+
- `wkhtmltopdf` (required by `pdfkit` for converting SEC HTML filings to PDF)
- Python packages in `requirements.txt`

## Setup
1. (Optional) Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the repo root (loaded by `dotenv`):
   ```bash
   GEMINI_API_KEY=...
   TELEGRAM_TOKEN=...
   CHAT_ID=...
   POLYMARKET_PK=...
   ENABLE_TRADING=false
   ```

## Running
Start the system from the repo root:
```bash
python order.py
```

Edit the market URLs in `order.py` to track different earnings markets.

## Configuration Notes
- `ENABLE_TRADING=true` enables live orders. A `TradingClient` instance must be created in `order.py` before enabling trading.
- `POLYMARKET_PK` is required for live orders (CLOB client).
- `TELEGRAM_TOKEN` and `CHAT_ID` enable Telegram notifications.
- `GEMINI_API_KEY` is required for the oracle resolution.

## Output and Logs
- `logs/sec_sentinel.log` records SEC feed events.
- `price_data/<slug>` contains timestamped YES/NO prices.
- `polymarket_liquidity_<slug>.jsonl` contains order book snapshots per outcome side.

## Other Utilities
- `backtest.py` runs historical backtests against saved data.
- `model.py` contains a structured oracle implementation used in backtesting.

## Warning
This trading software is provided strictly for educational and informational purposes only and does not constitute financial, investment, legal, or tax advice. The authors and contributors make no representations or warranties regarding the accuracy, completeness, or reliability of the software or any outputs it may produce. Use of this software is entirely at your own risk, and you remain solely responsible for any decisions, trades, losses, or other outcomes resulting from its use. By using this software, you acknowledge and agree that the authors and contributors will not be liable for any direct or indirect damages, including but not limited to financial loss, loss of profits, or other consequential damages arising from the use or inability to use the software.
