from .base import ModelResponse
class MockModelProvider:
    provider_id='mock'
    def __init__(self,response='Resposta simulada do modelo.'): self.response=response; self.default_model='mock-model'
    def health(self): return {'status':'healthy','provider':'mock','models':['mock-model']}
    def list_models(self): return ['mock-model']
    def chat(self,messages,*,model=None,system=None):
        prompt=messages[-1].content if messages else ''; return ModelResponse(self.response.replace('{{PROMPT}}',prompt),model or self.default_model,self.provider_id)
