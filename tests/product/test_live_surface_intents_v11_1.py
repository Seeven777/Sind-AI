from jarvis.brain.intent import IntentRouter


def test_weather_natural_language_routes_to_research():
    router=IntentRouter()
    for text in (
        "Qual a previsão do clima para hoje?",
        "Abra o gadget da previsão do clima",
        "Como está o tempo agora?",
    ):
        assert router.classify(text).name == "research", text


def test_live_news_routes_to_research():
    router=IntentRouter()
    for text in ("Quais são as últimas notícias?", "Abra o gadget de notícias de hoje"):
        assert router.classify(text).name == "research", text
