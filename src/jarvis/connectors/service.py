from __future__ import annotations

import asyncio

from jarvis.core.events import Event


class ConnectorService:
    def __init__(self,*,registry,repository,bus):
        self.registry=registry
        self.repository=repository
        self.bus=bus

    def register(self,connector,config=None):
        self.registry.register(connector)
        health=self._safe_health(connector)
        self.repository.register_source(connector,config=config)
        self.repository.set_source_status(
            connector.connector_id,
            health.get('status','configured'),
            health.get('error'),
        )

    def _safe_health(self,connector):
        try:
            return connector.health()
        except Exception as exc:
            return {'status':'error','error':str(exc)}

    async def sync_one(self,connector_id):
        connector=self.registry.get(connector_id)
        health=self._safe_health(connector)
        health_status=health.get('status','unknown')

        # Optional connectors must never make startup fail.
        if health_status in {'unconfigured','authorization_required','disabled','unavailable'}:
            self.repository.set_source_status(
                connector_id,health_status,health.get('error')
            )
            await self.bus.publish(Event(
                'connector.sync.skipped',
                severity='warning' if health_status=='unavailable' else 'info',
                payload={
                    'connector_id':connector_id,
                    'reason':health_status,
                    'health':health,
                }
            ))
            return {
                'connector_id':connector_id,
                'status':'skipped',
                'reason':health_status,
                'health':health,
            }

        sync_id=self.repository.start_sync(connector_id)
        await self.bus.publish(Event(
            'connector.sync.started',
            payload={'connector_id':connector_id,'sync_id':sync_id}
        ))
        try:
            result=await asyncio.to_thread(connector.sync)
            stored=0
            new_items=[]
            for item in result.items:
                item_id,is_new=self.repository.upsert_item(connector_id,item)
                stored+=1
                if is_new:
                    new_items.append(item_id)
                    await self.bus.publish(Event(
                        'connector.item.new',
                        payload={
                            'connector_id':connector_id,
                            'item_id':item_id,
                            'item_type':item.item_type,
                            'title':item.title,
                            'priority':item.priority,
                        }
                    ))
            self.repository.finish_sync(
                sync_id,connector_id,
                discovered=len(result.items),stored=stored
            )
            await self.bus.publish(Event(
                'connector.sync.completed',
                payload={
                    'connector_id':connector_id,
                    'sync_id':sync_id,
                    'discovered':len(result.items),
                    'stored':stored,
                    'new_items':len(new_items),
                }
            ))
            return {
                'connector_id':connector_id,
                'status':'completed',
                'discovered':len(result.items),
                'stored':stored,
                'new_items':len(new_items),
                'metadata':result.metadata,
            }
        except Exception as exc:
            self.repository.finish_sync(
                sync_id,connector_id,discovered=0,stored=0,error=str(exc)
            )
            await self.bus.publish(Event(
                'connector.sync.failed',severity='error',
                payload={
                    'connector_id':connector_id,
                    'sync_id':sync_id,
                    'error':str(exc),
                }
            ))
            return {
                'connector_id':connector_id,
                'status':'failed',
                'error':str(exc),
            }

    async def sync_all(self):
        results=[]
        for connector in self.registry.all():
            results.append(await self.sync_one(connector.connector_id))
        return results

    def health(self):
        return self.registry.health()
