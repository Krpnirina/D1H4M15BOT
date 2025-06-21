import asyncio
import websockets
import json
import aiohttp
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()  # Maka variables avy amin'ny .env

API_TOKEN = os.getenv("API_TOKEN")
APP_ID = int(os.getenv("APP_ID"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["R_10", "R_25", "R_50", "R_75", "R_100",
           "1HZ10V", "1HZ25V", "1HZ50V", "1HZ75V", "1HZ100V"]

DURATION = timedelta(hours=1)
active_trades = {}

async def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    async with aiohttp.ClientSession() as session:
        await session.post(url, data=payload)

def now():
    return datetime.now(timezone.utc)

async def send_ping(ws):
    while True:
        await asyncio.sleep(30)
        await ws.send(json.dumps({"ping": 1}))

async def authorize(ws):
    await ws.send(json.dumps({"authorize": API_TOKEN}))

async def subscribe_ticks(ws, symbol):
    await ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
    print(f"🚀 Manomboka amin'ny symbol: {symbol}")
    await send_telegram(f"🚀 Fanombohana fanangonana tick ho an'ny {symbol}")

async def buy_contract(ws, symbol):
    contract_request = {
        "buy": 1,
        "parameters": {
            "amount": 0.35,
            "basis": "stake",
            "contract_type": "CALL",
            "currency": "USD",
            "duration": 5,
            "duration_unit": "m",
            "symbol": symbol
        }
    }
    print(f"🔁 Sending buy contract request for {symbol}...")
    await ws.send(json.dumps(contract_request))

async def handle_messages(ws, symbol):
    start_time = now()
    data_collector = []

    async for message in ws:
        data = json.loads(message)

        if "error" in data:
            err_msg = data["error"]["message"]
            print(f"⛔ ERROR: {err_msg}")
            await send_telegram(f"⛔ ERROR amin'ny {symbol}: {err_msg}")
            break

        msg_type = data.get("msg_type")

        if msg_type == "authorize":
            print("✅ Authorized successfully!")

        elif msg_type == "tick":
            tick = data.get("tick", {})
            if tick.get("symbol") == symbol:
                data_collector.append(tick["quote"])
                print(f"📊 Tick {symbol}: {tick['quote']}")

                # Rehefa feno 1 ora ny fanangonana
                if now() - start_time >= DURATION:
                    await send_telegram(f"⏱ Vita ny 1 ora fanangonana ho an'ny {symbol}")

                    if symbol not in active_trades:
                        active_trades[symbol] = True
                        await buy_contract(ws, symbol)
                    break

        elif msg_type == "buy":
            symbol_buy = data.get('echo_req', {}).get('parameters', {}).get('symbol', 'unknown')
            trade_id = data['buy'].get('transaction_id', 'unknown')
            print(f"✅ Trade purchased. ID: {trade_id} Symbol: {symbol_buy}")
            await send_telegram(f"✅ Trade purchased for {symbol_buy}. ID: {trade_id}")

async def collect_and_trade(symbol):
    uri = f"wss://ws.binaryws.com/websockets/v3?app_id={APP_ID}"
    async with websockets.connect(uri) as ws:
        await authorize(ws)
        asyncio.create_task(send_ping(ws))
        await subscribe_ticks(ws, symbol)
        await handle_messages(ws, symbol)

async def monitor_symbols():
    print("⏳ Miandry 1 ora voalohany ho an'ny fanangonana data...")
    await send_telegram("⏳ Miandry 1 ora voalohany ho an'ny fanangonana data...")
    await asyncio.sleep(3600)
    await send_telegram("⏳ Vita ny 1 ora voalohany. Manomboka ny fanaraha-maso mitohy.")

    while True:
        tasks = []
        for symbol in SYMBOLS:
            if symbol not in active_trades:
                tasks.append(collect_and_trade(symbol))
        if tasks:
            await asyncio.gather(*tasks)
        await asyncio.sleep(60)

async def main():
    print("🚀 Manomboka fanangonana tick ho an'ny symbol rehetra")
    await asyncio.gather(*[collect_and_trade(symbol) for symbol in SYMBOLS])
    await monitor_symbols()

if __name__ == "__main__":
    asyncio.run(main())