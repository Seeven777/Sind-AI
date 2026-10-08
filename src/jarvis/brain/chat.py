from __future__ import annotations

import time


class ChatService:
    def __init__(self, conversations, orchestrator, performance=None, surface_service=None):
        self.conversations = conversations
        self.orchestrator = orchestrator
        self.performance = performance
        self.surface_service = surface_service

    def _apply_surfaces(self, query, result):
        if self.surface_service is None or not isinstance(result, dict):
            return result
        try:
            surfaces = self.surface_service.build(query, result)
        except Exception:
            surfaces = []
        if surfaces:
            result['surfaces'] = surfaces
        return result

    @staticmethod
    def _persist_assistant(result):
        # UI-owned cinematic actions are not prose replies. Persisting their
        # placeholder text makes the history look as if Jarvis only answered
        # "Briefing interativo do dia" even when the browser owns the sequence.
        return not (isinstance(result, dict) and result.get('ui_action') == 'morning_sequence')

    def new_conversation(self, title='Nova conversa'):
        return self.conversations.create(title)

    def list_conversations(self, *, search='', limit=100, include_archived=False):
        return self.conversations.list(search=search, limit=limit, include_archived=include_archived)

    def get_conversation(self, conversation_id):
        return self.conversations.get(conversation_id)

    def rename_conversation(self, conversation_id, title):
        return self.conversations.rename(conversation_id, title)

    def set_conversation_flags(self, conversation_id, *, pinned=None, archived=None):
        return self.conversations.set_flags(conversation_id, pinned=pinned, archived=archived)

    def delete_conversation(self, conversation_id):
        if not self.conversations.delete(conversation_id):
            raise KeyError(conversation_id)
        return {'conversation_id': conversation_id, 'deleted': True}

    def export_conversation(self, conversation_id, fmt='json'):
        if fmt == 'md':
            return self.conversations.export_markdown(conversation_id)
        if fmt == 'json':
            return self.conversations.export_json(conversation_id)
        raise ValueError('Formato de exportação inválido.')

    @staticmethod
    def _history_for_model(messages, limit=16, max_chars=18000):
        # Recent context matters most. Bound prompt size so long conversations do
        # not make every new response progressively slower.
        rows=[]
        used=0
        for msg in reversed(messages[-max(limit*2, limit):]):
            role=msg.get('role') or 'user'
            content=str(msg.get('content') or '').strip()
            if not content:
                continue
            remaining=max_chars-used
            if remaining<=0:
                break
            if len(content)>remaining:
                content=content[-remaining:]
            rows.append({'role':role,'content':content})
            used+=len(content)
            if len(rows)>=limit:
                break
        rows.reverse()
        return rows

    @staticmethod
    def _title_from_first_message(text):
        compact=' '.join(str(text).split()).strip()
        if not compact:
            return 'Nova conversa'
        return compact[:56] + ('…' if len(compact)>56 else '')

    @staticmethod
    def _compose_attachment_prompt(text, attachments):
        valid=[]
        for item in attachments or []:
            if not isinstance(item, dict):
                continue
            name=str(item.get('name') or 'arquivo')[:160]
            content=str(item.get('content') or '')
            if not content:
                continue
            valid.append(f"[ARQUIVO ANEXADO: {name}]\n{content}")
        if not valid:
            return text
        return text + "\n\n" + "\n\n".join(valid)

    async def send(self, conversation_id, text, *, mode='auto', attachments=None):
        started=time.perf_counter()
        history=self._history_for_model(self.conversations.recent_messages(conversation_id, limit=24))
        prompt = self._compose_attachment_prompt(text, attachments)
        metadata_attachments=[
            {'name':str(x.get('name') or 'arquivo')[:160], 'size':len(str(x.get('content') or ''))}
            for x in (attachments or []) if isinstance(x, dict)
        ]
        stored_content = prompt
        self.conversations.add_message(
            conversation_id,'user',stored_content,
            {'attachments':metadata_attachments} if metadata_attachments else {},
        )
        result=await self.orchestrator.handle(prompt, conversation_history=history, mode=mode)
        self._apply_surfaces(text, result)
        if self._persist_assistant(result):
            self.conversations.add_message(
                conversation_id,'assistant',result['content'],
                {
                    'kind':result.get('kind'),'agent':result.get('agent'),
                    'agents':result.get('agents'),'task_id':result.get('task_id'),
                    'mission_id':result.get('mission_id'),'artifact_id':result.get('artifact_id'),
                    'provider':result.get('provider'),'model':result.get('model'),
                    'mode':result.get('mode',mode),'surfaces':result.get('surfaces') or [],
                }
            )
        convo=self.conversations.get(conversation_id)
        if convo and convo['title']=='Nova conversa':
            first_user=next((m for m in convo['messages'] if m['role']=='user'),None)
            if first_user:
                self.conversations.rename(conversation_id,self._title_from_first_message(first_user['content']))
        if self.performance is not None:
            metric=self.performance.record(
                kind='chat',total_ms=(time.perf_counter()-started)*1000,
                provider=result.get('provider'),model=result.get('model'),route=result.get('kind')
            )
            result.setdefault('performance',metric)
        return result

    async def send_stream_to_queue(self, conversation_id, text, out_queue, *, mode='auto', attachments=None):
        """Run a chat request while pushing NDJSON-friendly events to a thread-safe queue."""
        started=time.perf_counter()
        first_token=[None]
        if self.performance is not None:self.performance.begin_interactive()
        history=self._history_for_model(self.conversations.recent_messages(conversation_id, limit=32))
        prompt=self._compose_attachment_prompt(text,attachments)
        metadata_attachments=[
            {'name':str(x.get('name') or 'arquivo')[:160],'size':len(str(x.get('content') or ''))}
            for x in (attachments or []) if isinstance(x,dict)
        ]
        self.conversations.add_message(
            conversation_id,'user',prompt,
            {'attachments':metadata_attachments} if metadata_attachments else {},
        )
        def emit_delta(delta):
            delta=str(delta or '')
            if not delta:
                return
            if first_token[0] is None:
                first_token[0]=time.perf_counter()
            out_queue.put({'type':'delta','text':delta})
        def emit_status(stage):
            out_queue.put({'type':'status','stage':str(stage or 'working')})
        try:
            result=await self.orchestrator.handle_stream(
                prompt,conversation_history=history,mode=mode,
                on_delta=emit_delta,on_status=emit_status,
            )
            self._apply_surfaces(text, result)
            total_ms=(time.perf_counter()-started)*1000
            ttft_ms=((first_token[0]-started)*1000) if first_token[0] is not None else total_ms
            if self.performance is not None:
                metric=self.performance.record(
                    kind='chat_stream',total_ms=total_ms,ttft_ms=ttft_ms,
                    provider=result.get('provider'),model=result.get('model'),route=result.get('kind'),
                    extra={'mode':mode},
                )
                result['performance']=metric
            if self._persist_assistant(result):
                self.conversations.add_message(
                    conversation_id,'assistant',result['content'],
                    {
                        'kind':result.get('kind'),'agent':result.get('agent'),
                        'agents':result.get('agents'),'task_id':result.get('task_id'),
                        'mission_id':result.get('mission_id'),'artifact_id':result.get('artifact_id'),
                        'provider':result.get('provider'),'model':result.get('model'),
                        'mode':result.get('mode',mode),'streamed':True,
                        'performance':result.get('performance'),'surfaces':result.get('surfaces') or [],
                    }
                )
            convo=self.conversations.get(conversation_id)
            if convo and convo['title']=='Nova conversa':
                first_user=next((m for m in convo['messages'] if m['role']=='user'),None)
                if first_user:
                    self.conversations.rename(conversation_id,self._title_from_first_message(first_user['content']))
            out_queue.put({'type':'done','result':result})
            return result
        except Exception as exc:
            out_queue.put({'type':'error','error':str(exc)})
            raise
        finally:
            if self.performance is not None:self.performance.end_interactive()

    async def regenerate(self, conversation_id, *, mode='auto'):
        convo=self.conversations.get(conversation_id)
        if not convo:
            raise KeyError(conversation_id)
        if not convo['messages'] or convo['messages'][-1]['role']!='assistant':
            raise ValueError('Não existe uma resposta do Jarvis para regenerar.')
        user_messages=[m for m in convo['messages'] if m['role']=='user']
        if not user_messages:
            raise ValueError('Não existe uma mensagem do usuário para regenerar.')
        target=user_messages[-1]['content']
        self.conversations.delete_last_assistant(conversation_id)
        history=self._history_for_model(self.conversations.recent_messages(conversation_id, limit=24))
        if history and history[-1]['role']=='user':
            history=history[:-1]
        result=await self.orchestrator.handle(target, conversation_history=history, mode=mode)
        self._apply_surfaces(target, result)
        self.conversations.add_message(
            conversation_id,'assistant',result['content'],
            {
                'kind':result.get('kind'),'agent':result.get('agent'),
                'agents':result.get('agents'),'task_id':result.get('task_id'),
                'mission_id':result.get('mission_id'),'artifact_id':result.get('artifact_id'),
                'provider':result.get('provider'),'model':result.get('model'),
                'regenerated':True,'mode':result.get('mode',mode),'surfaces':result.get('surfaces') or [],
            }
        )
        return result
