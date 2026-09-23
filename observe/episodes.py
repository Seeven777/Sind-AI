from datetime import datetime


def _parse_ts(value):
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def build_work_episodes(events, gap_seconds=300, limit=20):
    """Group low-level context events into human-scale work episodes.

    Episodes are deterministic and derived from the activity ledger. They are not a
    claim about user intent; they simply summarize contiguous periods of observed work.
    """
    ordered = sorted(list(events or []), key=lambda x: str(x.get("ts") or ""))
    meaningful = [
        x for x in ordered
        if x.get("event_type") in {
            "window_focus", "window_heartbeat", "context_query", "app_event", "app_action"
        }
    ]
    groups = []
    current = []
    last_ts = None

    for item in meaningful:
        ts = _parse_ts(item.get("ts"))
        if current and ts and last_ts:
            gap = (ts - last_ts).total_seconds()
            if gap > max(30, int(gap_seconds)):
                groups.append(current)
                current = []
        current.append(item)
        if ts:
            last_ts = ts
    if current:
        groups.append(current)

    episodes = []
    for index, group in enumerate(groups[-max(1, int(limit)):], 1):
        apps = []
        documents = []
        event_types = {}
        sources = {}
        for item in group:
            app_id = str(item.get("app_id") or "unknown")
            if not apps or apps[-1] != app_id:
                apps.append(app_id)
            payload = item.get("payload") or {}
            hint = str(payload.get("document_hint") or "").strip()
            if hint and hint not in documents:
                documents.append(hint)
            event_type = str(item.get("event_type") or "event")
            event_types[event_type] = event_types.get(event_type, 0) + 1
            source = str(item.get("source") or "unknown")
            sources[source] = sources.get(source, 0) + 1

        start = _parse_ts(group[0].get("ts"))
        end = _parse_ts(group[-1].get("ts"))
        duration = 0
        if start and end:
            duration = max(0, int((end - start).total_seconds()))
        episodes.append(
            {
                "episode": index,
                "start": group[0].get("ts"),
                "end": group[-1].get("ts"),
                "duration_seconds": duration,
                "events": len(group),
                "apps": apps,
                "documents": documents[:12],
                "event_types": event_types,
                "sources": sources,
            }
        )

    return {"ok": True, "episodes": episodes, "count": len(episodes)}
