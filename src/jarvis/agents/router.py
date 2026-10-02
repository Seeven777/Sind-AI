from __future__ import annotations


class AgentRouter:
    """Routes objectives to registered specialist agents without granting permissions.

    Core role selection remains in MissionPlanner. This router is the extension
    point for large specialist catalogs (currently Agency Agents/Codex TOMLs).
    """

    def __init__(self, *, registry, agency_catalog=None):
        self.registry = registry
        self.agency_catalog = agency_catalog

    def route(self, objective: str, limit: int = 3):
        if limit <= 0 or self.agency_catalog is None:
            return ()
        available = {card.agent_id for card in self.registry.available()}
        routes = self.agency_catalog.route(objective, limit=max(limit * 3, limit))
        selected = []
        for route in routes:
            if route.agent_id not in available:
                continue
            selected.append(route)
            if len(selected) >= limit:
                break
        return tuple(selected)

    def status(self) -> dict:
        catalog_status = self.agency_catalog.status() if self.agency_catalog is not None else {
            "status": "unavailable", "agents": 0, "runbooks": 0
        }
        return {
            "status": "healthy" if catalog_status.get("agents", 0) else "unavailable",
            "specialists": int(catalog_status.get("agents", 0)),
            "runbooks": int(catalog_status.get("runbooks", 0)),
        }
