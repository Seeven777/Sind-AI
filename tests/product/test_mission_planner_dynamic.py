from jarvis.missions import MissionPlanner


def test_software_team_is_dynamic():
    plan=MissionPlanner().build("Pesquise e implemente um script Python para analisar dados.")
    assert plan.agents==(
        "research.general",
        "intelligence.analyst",
        "engineering.developer",
        "review.verifier",
    )


def test_creative_team_is_dynamic():
    plan=MissionPlanner().build("Crie uma campanha de Instagram com análise de métricas.")
    assert plan.agents==(
        "research.general",
        "intelligence.analyst",
        "creative.creator",
        "review.verifier",
    )
