class ChatService:
    def __init__(self,conversations,orchestrator):
        self.conversations=conversations; self.orchestrator=orchestrator
    def new_conversation(self,title='Conversa com Jarvis'):
        return self.conversations.create(title)
    async def send(self,conversation_id,text):
        self.conversations.add_message(conversation_id,'user',text)
        result=await self.orchestrator.handle(text)
        self.conversations.add_message(
            conversation_id,'assistant',result['content'],
            {
                'kind':result.get('kind'),'agent':result.get('agent'),
                'agents':result.get('agents'),'task_id':result.get('task_id'),
                'mission_id':result.get('mission_id'),'artifact_id':result.get('artifact_id')
            }
        )
        return result
