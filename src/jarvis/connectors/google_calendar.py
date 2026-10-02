from __future__ import annotations

from datetime import datetime,timezone,timedelta
import urllib.parse

from .base import ConnectorItem,SyncResult
from .google_oauth import google_json_request


class GoogleCalendarConnector:
    connector_id="google.calendar"
    connector_kind="google_calendar"
    name="Google Calendar"
    read_only=True

    def __init__(self,oauth,days_ahead=14,max_results=50):
        self.oauth=oauth
        self.days_ahead=days_ahead
        self.max_results=max_results

    def health(self):
        result=self.oauth.status()
        result.update({"read_only":True})
        return result

    def sync(self):
        status=self.oauth.status()
        if status["status"]!="healthy":
            return SyncResult([],{**status,"skipped":True})
        start=datetime.now(timezone.utc)
        end=start+timedelta(days=self.days_ahead)
        params=urllib.parse.urlencode({
            "timeMin":start.isoformat().replace("+00:00","Z"),
            "timeMax":end.isoformat().replace("+00:00","Z"),
            "singleEvents":"true",
            "orderBy":"startTime",
            "maxResults":self.max_results,
        })
        raw=google_json_request(
            self.oauth,
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events?{params}"
        )
        items=[]
        for event in raw.get("items",[])[:self.max_results]:
            start_obj=event.get("start") or {}
            occurred=start_obj.get("dateTime") or start_obj.get("date")
            title=event.get("summary") or "(evento sem título)"
            description=event.get("description","")
            location=event.get("location","")
            content="\n".join(x for x in (
                description,
                f"Local: {location}" if location else "",
            ) if x)
            items.append(ConnectorItem(
                external_id=event.get("id") or event.get("iCalUID"),
                item_type="calendar_event",
                title=title,
                content=content,
                occurred_at=occurred,
                source_uri=event.get("htmlLink"),
                priority=70,
                metadata={
                    "location":location,
                    "status":event.get("status"),
                    "organizer":event.get("organizer"),
                    "attendees":event.get("attendees"),
                },
            ))
        return SyncResult(items,{"events_seen":len(items),"days_ahead":self.days_ahead})
