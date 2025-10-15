import asyncio
import websockets
import json
import random
from datetime import datetime
import os

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8765))  # ใช้ PORT จาก Re

CONNECTED = set()
USERNAME_COLOR = {}
COLOR_POOL = [
    "#e6194b","#3cb44b","#ffe119","#0082c8","#f58231",
    "#911eb4","#46f0f0","#f032e6","#fabebe","#46f0f0",
    "#008080","#e6beff","#aa6e28","#fffac8","#800000",
]

async def broadcast(msg):
    if CONNECTED:
        data = json.dumps(msg, ensure_ascii=False)
        await asyncio.gather(*(ws.send(data) for ws in list(CONNECTED)), return_exceptions=True)

async def register(ws, username):
    CONNECTED.add(ws)
    # เลือกสีสุ่มที่ยังไม่ถูกใช้
    used_colors = set(USERNAME_COLOR.values())
    available = [c for c in COLOR_POOL if c not in used_colors]
    color = random.choice(available) if available else "#000000"
    USERNAME_COLOR[username] = color
    await broadcast({"type":"join","user":username,"color":color,"ts":datetime.utcnow().isoformat()})
    return color

async def unregister(ws, username):
    CONNECTED.remove(ws)
    USERNAME_COLOR.pop(username, None)
    await broadcast({"type":"leave","user":username,"ts":datetime.utcnow().isoformat()})

async def handler(ws):
    username = None
    try:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("type") != "join":
            await ws.send(json.dumps({"type":"error","message":"First message must be join"}))
            return
        username = msg.get("user","Anonymous")
        color = await register(ws, username)
        await ws.send(json.dumps({"type":"joined","user":username,"color":color,"ts":datetime.utcnow().isoformat()}))
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("type")=="chat":
                await broadcast({
                    "type":"chat",
                    "user":username,
                    "text":msg.get("text",""),
                    "color":color,
                    "ts":datetime.utcnow().isoformat()
                })
    except websockets.ConnectionClosed:
        pass
    finally:
        if username:
            await unregister(ws, username)

async def main():
    async with websockets.serve(handler, HOST, PORT):
        print(f"Server running on {HOST}:{PORT}")
        await asyncio.Future()  # run forever

if __name__=="__main__":
    asyncio.run(main())
