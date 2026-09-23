from collections import Counter


def _focus_sequence(events):
    sequence = []
    for event in events:
        if event.get("event_type") != "window_focus":
            continue
        app_id = (event.get("app_id") or "unknown").strip() or "unknown"
        if not sequence or sequence[-1] != app_id:
            sequence.append(app_id)
    return sequence


def detect_activity_patterns(events, min_count=2, max_pattern=4, limit=12):
    """Find repeated app-transition sequences without using an LLM.

    This is intentionally conservative in Phase 1: it discovers repeated context
    sequences but does not auto-create automations. Later phases can use the same
    output as evidence for procedural learning.
    """
    sequence = _focus_sequence(events)
    found = Counter()
    max_pattern = max(2, min(int(max_pattern), 6))

    for width in range(2, max_pattern + 1):
        for index in range(0, max(0, len(sequence) - width + 1)):
            chunk = tuple(sequence[index : index + width])
            if len(set(chunk)) == 1:
                continue
            found[chunk] += 1

    items = []
    for chunk, count in found.most_common():
        if count < int(min_count):
            continue
        items.append({
            "sequence": list(chunk),
            "count": int(count),
            "length": len(chunk),
        })
        if len(items) >= int(limit):
            break

    return {
        "ok": True,
        "focus_events": len(sequence),
        "patterns": items,
        "count": len(items),
    }
