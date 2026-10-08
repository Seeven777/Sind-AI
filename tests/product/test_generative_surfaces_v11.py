from pathlib import Path

from jarvis.surfaces import GenerativeSurfaceService


def test_weather_surface_is_structured_and_compact():
    service = GenerativeSurfaceService()
    result = {
        "kind": "delegated",
        "content": "Hoje a temperatura atual é 24°C, com chuva em 30%, umidade de 72% e vento de 12 km/h.",
        "metadata": {
            "sources": [
                {"title": "Previsão São Paulo", "url": "https://example.com/weather"}
            ]
        },
    }
    surfaces = service.build("Qual a previsão do tempo para hoje?", result)
    assert len(surfaces) == 1
    surface = surfaces[0]
    assert surface["surface"] == "weather"
    values = {row["label"]: row["value"] for row in surface["data"]["metrics"]}
    assert values["Temperatura"] == "24°C"
    assert values["Chuva"] == "30%"
    assert surface["data"]["sources"][0]["domain"] == "example.com"
    assert surface["presentation"] == "surface_primary"


def test_news_surface_exposes_sources_without_executable_markup():
    service = GenerativeSurfaceService()
    result = {
        "kind": "delegated",
        "content": "Encontrei três novidades importantes e organizei os principais impactos.",
        "metadata": {
            "sources": [
                {"title": "Notícia A", "url": "https://news.example/a"},
                {"title": "Notícia B", "url": "https://news.example/b"},
            ]
        },
    }
    [surface] = service.build("Quais são as últimas notícias?", result)
    assert surface["surface"] == "news"
    assert len(surface["data"]["items"]) == 2
    assert all("html" not in item for item in surface["data"]["items"])
    assert surface["data"]["items"][0]["url"].startswith("https://")


def test_surface_ui_is_loaded_on_desktop_and_mobile():
    root = Path(__file__).resolve().parents[2] / "src" / "jarvis" / "ui" / "hq_web"
    companion = (root / "companion.html").read_text(encoding="utf-8")
    mobile = (root / "mobile.html").read_text(encoding="utf-8")
    engine = (root / "surface-engine.js").read_text(encoding="utf-8")
    assert 'id="surface-layer"' in companion
    assert 'id="surface-layer"' in mobile
    assert '/surface-engine.js' in companion
    assert '/surface-engine.js' in mobile
    assert "class SurfaceManager" in engine
    assert "registry.register('weather'" in engine
    assert "registry.register('news'" in engine
    assert "safeUrl" in engine


def test_explicit_weather_gadget_opens_expanded():
    service = GenerativeSurfaceService()
    [surface] = service.build(
        "Abra o gadget da previsão do clima",
        {"kind":"delegated","content":"Temperatura atual 25°C e chuva em 20%.","metadata":{"sources":[]}},
    )
    assert surface["surface"] == "weather"
    assert surface["default_expanded"] is True


def test_weather_surface_prefers_structured_weather_metadata():
    service=GenerativeSurfaceService()
    [surface]=service.build("Abra o gadget do clima",{
        "kind":"delegated",
        "content":"Previsão consultada em fonte meteorológica.",
        "metadata":{
            "weather":{
                "location":"São Paulo, São Paulo, Brasil",
                "current":{"temperature":25,"humidity":62,"wind_speed":11.4},
                "today":{"precipitation_probability_max":35},
                "units":{"temperature":"°C","humidity":"%","wind_speed":"km/h","probability":"%"},
            },
            "sources":[{"title":"Open-Meteo","url":"https://open-meteo.com/"}],
        },
    })
    values={x["label"]:x["value"] for x in surface["data"]["metrics"]}
    assert values == {"Temperatura":"25°C","Chuva":"35%","Umidade":"62%","Vento":"11.4km/h"}
    assert surface["subtitle"].startswith("São Paulo")
