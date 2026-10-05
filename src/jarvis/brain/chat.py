from __future__ import annotations


class ChatService:
    def __init__(self, conversations, orchestrator):
        self.conversations = conversations
        self.orchestrator = orchestrator

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
    def _history_for_model(messages, limit=24):
        rows=[]
        for msg in messages[-limit:]:
            role=msg.get('role') or 'user'
            content=str(msg.get('content') or '').strip()
            if content:
                rows.append({'role':role,'content':content})
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
        self.conversations.add_message(
            conversation_id,'assistant',result['content'],
            {
                'kind':result.get('kind'),'agent':result.get('agent'),
                'agents':result.get('agents'),'task_id':result.get('task_id'),
                'mission_id':result.get('mission_id'),'artifact_id':result.get('artifact_id'),
                'provider':result.get('provider'),'model':result.get('model'),
                'mode':result.get('mode',mode),
            }
        )
        convo=self.conversations.get(conversation_id)
        if convo and convo['title']=='Nova conversa':
            first_user=next((m for m in convo['messages'] if m['role']=='user'),None)
            if first_user:
                self.conversations.rename(conversation_id,self._title_from_first_message(first_user['content']))
        return result

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
        self.conversations.add_message(
            conversation_id,'assistant',result['content'],
            {
                'kind':result.get('kind'),'agent':result.get('agent'),
                'agents':result.get('agents'),'task_id':result.get('task_id'),
                'mission_id':result.get('mission_id'),'artifact_id':result.get('artifact_id'),
                'provider':result.get('provider'),'model':result.get('model'),
                'regenerated':True,'mode':result.get('mode',mode),
            }
        )
        return result
