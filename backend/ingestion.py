import json
import asyncio
from datetime import datetime, timezone

import websockets

from backend.db import get_db, init_db, insert_tick


async def listen_to_binance(symbol: str):
    url = f"wss://fstream.binance.com/ws/{symbol}@trade"

    print(f"Connecting to Binance for {symbol.upper()}...")

    db = get_db()
    init_db(db)
    print("Database connected. Storing live ticks...\n")

    async with websockets.connect(url) as websocket:
        print("Connected to Binance. Waiting for trades...\n")

        while True:
            message = await websocket.recv()
            data = json.loads(message)

            if data.get("e") == "trade":
                price = float(data["p"])
                qty = float(data["q"])
                ts = datetime.fromtimestamp(data["T"] / 1000, tz=timezone.utc)

                insert_tick(
                    db=db,
                    symbol=symbol,
                    price=price,
                    qty=qty,
                    ts=ts,
                )

                print(
                    f"STORED | {data['s']} | "
                    f"price={price:.2f} | "
                    f"qty={qty:.6f} | "
                    f"time={ts.isoformat()}"
                )


if __name__ == "__main__":
    asyncio.run(listen_to_binance("btcusdt"))
