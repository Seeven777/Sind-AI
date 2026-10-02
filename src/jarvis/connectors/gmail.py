from __future__ import annotations

import base64
import urllib.parse

from .base import ConnectorItem,SyncResult
from .google_oauth import GoogleAuthError,google_json_request


def _headers(payload):
    return {
        h.get("name","").lower():h.get("value","")
        for h in (payload or {}).get("headers",[])
    }


class GmailConnector:
    connector_id="google.gmail"
    connector_kind="gmail"
    name="Gmail"
    read_only=True

    def __init__(self,oauth,query="is:unread newer_than:14d",max_results=25):
        self.oauth=oauth
        self.query=query
        self.max_results=max_results

    def health(self):
        result=self.oauth.status()
        result.update({"read_only":True,"query":self.query})
        return result

    def sync(self):
        status=self.oauth.status()
        if status["status"]!="healthy":
            return SyncResult([],{**status,"skipped":True})
        params=urllib.parse.urlencode({
            "q":self.query,
            "maxResults":self.max_results,
        })
        listing=google_json_request(
            self.oauth,
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages?{params}"
        )
        items=[]
        for row in listing.get("messages",[])[:self.max_results]:
            msg=google_json_request(
                self.oauth,
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/"
                +urllib.parse.quote(row["id"])
                +"?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date"
            )
            headers=_headers(msg.get("payload"))
            subject=headers.get("subject") or "(sem assunto)"
            sender=headers.get("from","")
            snippet=msg.get("snippet","")
            labels=set(msg.get("labelIds") or [])
            priority=85 if "IMPORTANT" in labels else 60
            items.append(ConnectorItem(
                external_id=msg["id"],
                item_type="email",
                title=subject,
                content=f"De: {sender}\n{snippet}".strip(),
                occurred_at=None,
                source_uri=f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
                priority=priority,
                metadata={
                    "from":sender,
                    "date":headers.get("date",""),
                    "thread_id":msg.get("threadId"),
                    "labels":sorted(labels),
                },
            ))
        return SyncResult(items,{"messages_seen":len(items),"query":self.query})
