import asyncio
import json
import os
import platform
import re
import subprocess
import webbrowser
from datetime import datetime

import psutil
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from groq_ai import ask_tommy
from speech import TommySpeech


app = FastAPI(title="Tommy AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

speech = TommySpeech()
connected_clients = set()

# ─── Utility helpers ──────────────────────────────────────────────────────────

def get_system_status() -> dict:
    """Return CPU, RAM, disk, battery, OS info."""
    battery = psutil.sensors_battery()
    disk = psutil.disk_usage("/")

    return {
        "cpu": psutil.cpu_percent(interval=0.5),
        "ram": psutil.virtual_memory().percent,
        "disk_used": round(disk.used / (1024 ** 3), 1),
        "disk_total": round(disk.total / (1024 ** 3), 1),
        "battery": round(battery.percent) if battery else None,
        "charging": battery.power_plugged if battery else None,
        "os": f"{platform.system()} {platform.release()}",
        "time": datetime.now().strftime("%I:%M %p"),
        "date": datetime.now().strftime("%A, %d %B %Y"),
    }


def get_weather(city: str = "Meerut") -> dict:
    """Fetch weather using Open-Meteo (free, no key needed) after geocoding."""
    try:
        geo_url = (
            f"https://geocoding-api.open-meteo.com/v1/search"
            f"?name={city}&count=1&language=en&format=json"
        )
        geo = requests.get(geo_url, timeout=5).json()
        if not geo.get("results"):
            return {"error": f"City '{city}' not found."}

        result = geo["results"][0]
        lat, lon = result["latitude"], result["longitude"]
        name = result.get("name", city)

        wx_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,"
            f"apparent_temperature,weather_code,wind_speed_10m"
            f"&timezone=auto"
        )
        wx = requests.get(wx_url, timeout=5).json()
        cur = wx["current"]

        codes = {
            0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy",
            3: "Overcast", 45: "Foggy", 48: "Icy Fog",
            51: "Light Drizzle", 61: "Slight Rain", 63: "Moderate Rain",
            65: "Heavy Rain", 71: "Slight Snow", 80: "Showers",
            95: "Thunderstorm",
        }
        code = cur.get("weather_code", 0)
        desc = codes.get(code, "Unknown")

        return {
            "city": name,
            "temp": round(cur["temperature_2m"]),
            "feels_like": round(cur["apparent_temperature"]),
            "humidity": cur["relative_humidity_2m"],
            "wind": round(cur["wind_speed_10m"]),
            "condition": desc,
        }
    except Exception as e:
        return {"error": str(e)}


def open_url(url: str):
    """Open a URL in the default browser."""
    webbrowser.open(url)


# ─── Intent detection for special commands ────────────────────────────────────

INTENT_PATTERNS = [
    # Chrome search
    (r"(?:search|google|chrome search|look up|find)\s+(?:for\s+)?(.+)", "chrome_search"),
    # YouTube
    (r"(?:open|play|search|find)\s+(?:on\s+)?youtube\s*(?:for\s+)?(.+)?", "youtube"),
    (r"youtube\s+(.+)", "youtube"),
    # Weather
    (r"weather\s+(?:in|of|for)?\s*(.+)?", "weather"),
    (r"(?:what(?:'s| is) the weather)(?:\s+in\s+(.+))?", "weather"),
    # System status
    (r"system\s+(?:status|info|stats|health)", "system_status"),
    (r"(?:cpu|ram|memory|battery|disk)\s+(?:usage|status|info)", "system_status"),
    # Time / Date
    (r"(?:what(?:'s| is) the |current )?(?:time|date|day)", "datetime"),
]


def detect_intent(text: str):
    """Return (intent, param) or (None, None) if no special intent."""
    lower = text.lower().strip()
    for pattern, intent in INTENT_PATTERNS:
        m = re.search(pattern, lower)
        if m:
            param = m.group(1).strip() if m.lastindex and m.group(1) else ""
            return intent, param
    return None, None


# ─── Event helpers ────────────────────────────────────────────────────────────

async def send_event(event, data=None):
    message = {"event": event, "data": data}
    disconnected = set()

    for client in list(connected_clients):
        try:
            await client.send_text(json.dumps(message))
        except Exception:
            disconnected.add(client)

    for client in disconnected:
        connected_clients.discard(client)


async def speak_answer(answer):
    await send_event("speaking_start", {"text": answer})

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, speech.speak, answer)

    await send_event("speaking_end")


# ─── Intent handlers ─────────────────────────────────────────────────────────

async def handle_chrome_search(query: str):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    open_url(url)
    msg = f"🔍 Searching Google for: **{query}**"
    await send_event("answer", {"text": msg, "mode": "NORMAL", "action": "chrome_search", "query": query, "url": url})
    await speak_answer(f"Searching Google for {query}")
    await send_event("ready")


async def handle_youtube(query: str):
    if query:
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        msg = f"▶️ Opening YouTube search for: **{query}**"
        voice_msg = f"Opening YouTube for {query}"
    else:
        url = "https://www.youtube.com"
        msg = "▶️ Opening YouTube"
        voice_msg = "Opening YouTube"

    open_url(url)
    await send_event("answer", {"text": msg, "mode": "NORMAL", "action": "youtube", "query": query, "url": url})
    await speak_answer(voice_msg)
    await send_event("ready")


async def handle_weather(city: str):
    city = city or "Meerut"
    await send_event("thinking", {"text": f"Getting weather for {city}..."})

    data = await asyncio.to_thread(get_weather, city)

    if "error" in data:
        msg = f"Sorry, couldn't get weather for {city}. {data['error']}"
        await send_event("answer", {"text": msg, "mode": "NORMAL"})
        await speak_answer(msg)
    else:
        await send_event("weather_data", data)
        voice = (
            f"In {data['city']}, it's {data['temp']} degrees Celsius. "
            f"Condition: {data['condition']}. "
            f"Feels like {data['feels_like']} degrees. "
            f"Humidity is {data['humidity']} percent."
        )
        await speak_answer(voice)

    await send_event("ready")


async def handle_system_status():
    data = await asyncio.to_thread(get_system_status)
    await send_event("system_status", data)
    voice = (
        f"System report: CPU at {data['cpu']} percent, "
        f"RAM at {data['ram']} percent. "
        f"Disk used {data['disk_used']} of {data['disk_total']} GB."
    )
    if data["battery"] is not None:
        charge_word = "charging" if data["charging"] else "on battery"
        voice += f" Battery at {data['battery']} percent, {charge_word}."
    await speak_answer(voice)
    await send_event("ready")


async def handle_datetime():
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %d %B %Y")
    msg = f"🕒 It's {time_str} on {date_str}"
    await send_event("answer", {"text": msg, "mode": "NORMAL"})
    await speak_answer(f"It's {time_str} on {date_str}")
    await send_event("ready")


# ─── Main question processor ──────────────────────────────────────────────────

async def process_question(question: str):
    if not question:
        return

    # Check for special intents first
    intent, param = detect_intent(question)

    if intent == "chrome_search":
        await handle_chrome_search(param or question)
        return
    elif intent == "youtube":
        await handle_youtube(param)
        return
    elif intent == "weather":
        await handle_weather(param)
        return
    elif intent == "system_status":
        await handle_system_status()
        return
    elif intent == "datetime":
        await handle_datetime()
        return

    # Regular AI question
    await send_event("thinking", {"text": question})

    try:
        result = await asyncio.to_thread(ask_tommy, question)
        mode = result["mode"]
        answer = result["answer"]

        await send_event("answer", {"text": answer, "mode": mode})
        await speak_answer(answer)
        await send_event("ready")

    except Exception as error:
        print("AI error:", error)
        error_message = "Sorry bro, Tommy hit a server error. Please try again."
        await send_event("error", {"text": error_message})
        await speak_answer(error_message)
        await send_event("ready")


# ─── FastAPI routes ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    print("==================================")
    print("          TOMMY AI v5")
    print("==================================")
    await asyncio.to_thread(speech.calibrate)
    print("✅ Tommy ready.")
    print("🎤 Click the microphone button.")


@app.get("/system-status")
async def system_status_endpoint():
    return get_system_status()


@app.get("/weather")
async def weather_endpoint(city: str = "Meerut"):
    return get_weather(city)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print("🌐 Browser connected.")

    try:
        # Send initial ready + system info
        sys_data = await asyncio.to_thread(get_system_status)
        await websocket.send_text(json.dumps({"event": "ready", "data": {}}))
        await websocket.send_text(json.dumps({"event": "system_status", "data": sys_data}))

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            event = data.get("event")

            if event == "start_listening":
                await send_event("listening")
                question = await asyncio.to_thread(speech.listen, 8)

                if question:
                    await send_event("user_message", {"text": question})
                    await process_question(question)
                else:
                    await send_event("ready")

            elif event == "chat":
                text = data.get("text", "").strip()
                if text:
                    await send_event("user_message", {"text": text})
                    await process_question(text)

            elif event == "stop_speaking":
                speech.stop()

            elif event == "get_weather":
                city = data.get("city", "Meerut")
                await handle_weather(city)

            elif event == "get_system_status":
                await handle_system_status()

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        print("🌐 Browser disconnected.")

    except Exception as error:
        connected_clients.discard(websocket)
        print("WebSocket error:", error)
