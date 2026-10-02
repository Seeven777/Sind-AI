from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class ConnectorItem:
    external_id:str
    item_type:str
    title:str
    content:str=''
    occurred_at:str|None=None
    source_uri:str|None=None
    priority:int=50
    metadata:dict=field(default_factory=dict)


@dataclass(slots=True)
class SyncResult:
    items:list[ConnectorItem]=field(default_factory=list)
    metadata:dict=field(default_factory=dict)


class Connector(Protocol):
    connector_id:str
    connector_kind:str
    name:str
    read_only:bool

    def health(self)->dict: ...
    def sync(self)->SyncResult: ...


class ConnectorRegistry:
    def __init__(self):
        self._items:dict[str,Connector]={}

    def register(self,connector:Connector)->None:
        self._items[connector.connector_id]=connector

    def get(self,connector_id:str)->Connector:
        return self._items[connector_id]

    def all(self)->tuple[Connector,...]:
        return tuple(self._items.values())

    def health(self)->dict:
        result={}
        for key,value in self._items.items():
            try: result[key]=value.health()
            except Exception as exc:
                result[key]={'status':'error','error':str(exc)}
        return result
