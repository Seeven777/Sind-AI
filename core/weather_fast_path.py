"""Fast, deterministic weather lookup backed by the existing Open-Meteo catalog."""

from __future__ import annotations

import re
import unicodedata


WEATHER_CODES = {
    0: "céu limpo", 1: "predominantemente limpo", 2: "parcialmente nublado",
    3: "nublado", 45: "neblina", 48: "neblina com geada",
    51: "garoa leve", 53: "garoa", 55: "garoa intensa",
    61: "chuva leve", 63: "chuva", 65: "chuva forte",
    71: "neve leve", 73: "neve", 75: "neve forte",
    80: "pancadas leves", 81: "pancadas de chuva", 82: "pancadas fortes",
    95: "trovoadas", 96: "trovoadas com granizo", 99: "trovoadas fortes com granizo",
}


def _plain(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn").lower()


def matches(text: str) -> bool:
    value = _plain(str(text or ""))
    if re.search(r"\b(clima|previsao do tempo|temperatura|vai chover|chuva hoje)\b", value):
        return True
    return bool(
        re.search(r"\b(como|qual|veja|mostre|diga|consult[ea]|previsao)\b.{0,28}\btempo\b", value)
        or re.search(r"\btempo\s+(?:esta|vai|faz|em)\b", value)
        or re.search(r"\btempo\s+(?:hoje|agora|amanha)\s*[?!.]*$", value)
    )


def location_from(text: str, default: str) -> str:
    value = str(text or "").strip().rstrip("?.!")
    match = re.search(r"\b(?:em|para)\s+([\wÀ-ÿ][\wÀ-ÿ .'-]{1,55})$", value, re.I)
    if match:
        location = re.sub(r"\b(?:hoje|agora|amanhã|amanha)$", "", match.group(1), flags=re.I).strip()
        if location:
            return location
    return default


def _number(value, digits=0):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def query(capabilities, text: str, default_location: str = "São Paulo") -> dict:
    if not matches(text):
        return {"matched": False}
    requested = location_from(text, default_location)
    geo = capabilities.execute("weather.geocode", {
        "name": requested, "count": 1, "language": "pt",
    }, timeout=8)
    results = (geo.get("data") or {}).get("results") or [] if geo.get("ok") else []
    if not results:
        return {"matched": True, "ok": False, "error": f"Não encontrei a localidade {requested}."}
    place = results[0]
    latitude, longitude = place.get("latitude"), place.get("longitude")
    current_result = capabilities.execute("weather.current", {
        "latitude": latitude, "longitude": longitude, "timezone": "auto",
    }, timeout=8)
    daily_result = capabilities.execute("weather.daily.basic", {
        "latitude": latitude, "longitude": longitude, "timezone": "auto",
    }, timeout=8)
    if not current_result.get("ok"):
        return {"matched": True, "ok": False, "error": current_result.get("error") or "Clima indisponível."}

    current = (current_result.get("data") or {}).get("current") or {}
    daily = (daily_result.get("data") or {}).get("daily") or {}
    units = (current_result.get("data") or {}).get("current_units") or {}
    code = int(current.get("weather_code") or 0)
    location = ", ".join(x for x in (place.get("name"), place.get("admin1")) if x)
    days = []
    dates = daily.get("time") or []
    for index, date in enumerate(dates[:5]):
        def at(key):
            values = daily.get(key) or []
            return values[index] if index < len(values) else None
        day_code = int(at("weather_code") or 0)
        days.append({
            "date": date,
            "condition": WEATHER_CODES.get(day_code, "condição variável"),
            "code": day_code,
            "max": _number(at("temperature_2m_max")),
            "min": _number(at("temperature_2m_min")),
            "rain_probability": _number(at("precipitation_probability_max")),
        })

    temperature = _number(current.get("temperature_2m"), 1)
    apparent = _number(current.get("apparent_temperature"), 1)
    humidity = _number(current.get("relative_humidity_2m"))
    wind = _number(current.get("wind_speed_10m"), 1)
    condition = WEATHER_CODES.get(code, "condição variável")
    answer = (
        f"Em {location}, agora faz {temperature} graus, com {condition}. "
        f"A sensação térmica é de {apparent} graus, a umidade está em {humidity}% "
        f"e o vento em {wind} quilômetros por hora."
    )
    return {
        "matched": True, "ok": True, "answer": answer,
        "source": current_result.get("url"),
        "widget": {
            "type": "weather", "title": location, "condition": condition, "code": code,
            "temperature": temperature, "temperature_unit": units.get("temperature_2m", "°C"),
            "apparent": apparent, "humidity": humidity, "wind": wind, "days": days,
            "updated_at": current.get("time"), "provider": "Open-Meteo",
        },
    }
