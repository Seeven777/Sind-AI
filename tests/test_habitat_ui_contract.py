from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class HabitatUIContractTests(unittest.TestCase):
    def test_habitat_loads_procedural_orb_and_theme(self):
        html = (ROOT / "ui" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="jarvisOrb"', html)
        self.assertIn('src="orb.js"', html)
        self.assertIn('href="habitat.css"', html)
        self.assertIn('id="historyToggle"', html)

    def test_orb_supports_complete_agent_state_contract(self):
        js = (ROOT / "ui" / "web" / "orb.js").read_text(encoding="utf-8")
        for state in (
            "idle", "listening", "thinking", "planning", "executing",
            "observing", "verifying", "speaking", "success", "error",
        ):
            self.assertIn(f"{state}:", js)
        self.assertIn("requestAnimationFrame", js)
        self.assertIn("prefers-reduced-motion", js)
        self.assertIn("jarvis-visual-quality", js)

    def test_backend_maps_observable_runtime_phases(self):
        source = (ROOT / "ui" / "habitat.py").read_text(encoding="utf-8")
        for state in ("listening", "planning", "observing", "verifying", "speaking", "thinking", "executing"):
            self.assertIn(f'return "{state}"', source)

    def test_ui_uses_backend_state_instead_of_fake_timer_sequence(self):
        js = (ROOT / "ui" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("bridge.statusChanged.connect", js)
        self.assertIn("setAgentState(String(state", js)
        self.assertIn("bridge.commandFinished.connect", js)

    def test_voice_conversation_is_local_and_drives_the_orb(self):
        helper = (ROOT / "scripts" / "jarvis_voice_input.py").read_text(encoding="utf-8")
        habitat = (ROOT / "ui" / "habitat.py").read_text(encoding="utf-8")
        app = (ROOT / "ui" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("VoiceSession().get_stt_backend()", helper)
        self.assertIn('language="pt"', helper)
        self.assertIn("voiceLevelChanged", habitat)
        self.assertIn("QTextToSpeech", habitat)
        self.assertIn("orb.setAudioLevel", app)
        self.assertIn("bridge.voiceTranscript.connect", app)

    def test_orb_has_direct_pointer_interaction(self):
        orb = (ROOT / "ui" / "web" / "orb.js").read_text(encoding="utf-8")
        self.assertIn("pointerdown", orb)
        self.assertIn("pointermove", orb)
        self.assertIn("wheel", orb)
        self.assertIn("dblclick", orb)

    def test_elevenlabs_voice_is_backend_only_with_local_fallback(self):
        helper = (ROOT / "scripts" / "jarvis_elevenlabs_tts.py").read_text(encoding="utf-8")
        habitat = (ROOT / "ui" / "habitat.py").read_text(encoding="utf-8")
        config = (ROOT / "data" / "config.json").read_text(encoding="utf-8")
        self.assertIn("ELEVENLABS_API_KEY", helper)
        self.assertNotIn("ELEVENLABS_API_KEY", (ROOT / "ui" / "web" / "app.js").read_text(encoding="utf-8"))
        self.assertIn("_speak_elevenlabs", habitat)
        self.assertIn('"2CECaLAGTS5NRGxgbcxr"', config)
        self.assertIn('"voice_fallback_local": true', config)

    def test_weather_fast_path_avoids_llm_and_builds_widget(self):
        from core.weather_fast_path import matches, query

        class Hub:
            def execute(self, capability, _params, timeout=8):
                if capability == "weather.geocode":
                    return {"ok": True, "data": {"results": [{"name": "São Paulo", "admin1": "São Paulo", "latitude": -23.55, "longitude": -46.63}]}}
                if capability == "weather.current":
                    return {"ok": True, "url": "https://api.open-meteo.com/test", "data": {"current": {"temperature_2m": 24.3, "apparent_temperature": 25.1, "relative_humidity_2m": 61, "wind_speed_10m": 8.2, "weather_code": 2, "time": "2026-10-02T10:00"}, "current_units": {"temperature_2m": "°C"}}}
                return {"ok": True, "data": {"daily": {"time": ["2026-10-02"], "weather_code": [2], "temperature_2m_max": [27], "temperature_2m_min": [18], "precipitation_probability_max": [15]}}}

        self.assertTrue(matches("Jarvis, como está o tempo hoje?"))
        self.assertFalse(matches("Não tenho tempo hoje para isso"))
        result = query(Hub(), "Como está o tempo hoje?", "São Paulo")
        self.assertTrue(result["ok"])
        self.assertEqual(result["widget"]["type"], "weather")
        self.assertEqual(result["widget"]["temperature"], 24.3)

    def test_context_widget_contract_is_rendered_from_verified_metadata(self):
        app = (ROOT / "ui" / "web" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "ui" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="contextWidgets"', html)
        self.assertIn("if(meta.widget)showContextWidget(meta.widget)", app)
        self.assertIn("weather-widget", app)


if __name__ == "__main__":
    unittest.main()
