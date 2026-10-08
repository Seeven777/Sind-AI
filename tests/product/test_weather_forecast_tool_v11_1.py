from jarvis.tools import WeatherForecastTool


def test_weather_forecast_tool_returns_structured_data(monkeypatch):
    tool=WeatherForecastTool()
    replies=iter([
        {"results":[{"name":"São Paulo","admin1":"São Paulo","country":"Brasil","latitude":-23.55,"longitude":-46.63}]},
        {
            "timezone":"America/Sao_Paulo",
            "current":{"temperature_2m":25.0,"apparent_temperature":26.1,"relative_humidity_2m":62,"precipitation":0.0,"rain":0.0,"weather_code":2,"wind_speed_10m":11.4,"time":"2026-10-07T15:00"},
            "current_units":{"temperature_2m":"°C","relative_humidity_2m":"%","precipitation":"mm","wind_speed_10m":"km/h"},
            "daily":{"temperature_2m_max":[27.5],"temperature_2m_min":[18.2],"precipitation_probability_max":[35],"weather_code":[2]},
            "daily_units":{"precipitation_probability_max":"%"},
        },
    ])
    monkeypatch.setattr(tool,"_json",lambda url: next(replies))
    result=tool.execute({"location":"São Paulo, SP"})
    assert result.success is True
    assert result.output["current"]["temperature"] == 25.0
    assert result.output["today"]["precipitation_probability_max"] == 35
    assert result.output["provider"] == "Open-Meteo"
