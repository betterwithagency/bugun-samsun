"""Today's Samsun conditions from Open-Meteo (free, no key): forecast + sea temperature + sun times."""
import requests

FORECAST = ("https://api.open-meteo.com/v1/forecast?latitude=41.2867&longitude=36.33"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,"
            "precipitation_probability_max,wind_speed_10m_max"
            "&timezone=Europe%2FIstanbul&forecast_days=1")
MARINE = ("https://marine-api.open-meteo.com/v1/marine?latitude=41.32&longitude=36.36"
          "&current=sea_surface_temperature&timezone=Europe%2FIstanbul")


def describe(code: int):
    """WMO weather code -> (Turkish text, icon name)."""
    if code == 0:
        return "Açık", "sun"
    if code == 1:
        return "Az bulutlu", "sun"
    if code == 2:
        return "Parçalı bulutlu", "cloud"
    if code == 3:
        return "Çok bulutlu", "cloud"
    if code in (45, 48):
        return "Sisli", "fog"
    if 51 <= code <= 57:
        return "Çisenti", "rain"
    if 61 <= code <= 67:
        return "Yağmurlu", "rain"
    if 71 <= code <= 77:
        return "Karlı", "snow"
    if 80 <= code <= 82:
        return "Sağanak yağışlı", "rain"
    if code in (85, 86):
        return "Kar sağanağı", "snow"
    if code >= 95:
        return "Gök gürültülü", "storm"
    return "Bulutlu", "cloud"


def today():
    """Return a dict for the 'Gün rehberi' slide, or None if the service is down."""
    try:
        d = requests.get(FORECAST, timeout=15).json()["daily"]
        text, icon = describe(int(d["weather_code"][0]))
        out = {
            "max": round(d["temperature_2m_max"][0]),
            "min": round(d["temperature_2m_min"][0]),
            "text": text,
            "icon": icon,
            "rain": d["precipitation_probability_max"][0],
            "wind": round(d["wind_speed_10m_max"][0]),
            "sunrise": d["sunrise"][0][-5:].replace(":", "."),
            "sunset": d["sunset"][0][-5:].replace(":", "."),
            "sea": None,
        }
    except Exception as exc:  # weather is a nice-to-have; never block the bulletin
        print(f"[weather] skipped: {exc}")
        return None
    try:
        sea = requests.get(MARINE, timeout=15).json()["current"]["sea_surface_temperature"]
        out["sea"] = round(sea) if sea is not None else None
    except Exception as exc:
        print(f"[weather] sea temperature skipped: {exc}")
    return out
