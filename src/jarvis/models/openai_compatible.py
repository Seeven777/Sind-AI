from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Sequence

from .base import ChatMessage,ModelResponse,ModelUnavailableError


class OpenAICompatibleProvider:
    """Generic OpenAI-compatible Chat Completions provider.

    This adapter is optional and configured entirely outside the core.
    """

    def __init__(self,provider_id,base_url,api_key,default_model,timeout=120):
        self.provider_id=provider_id
        self.base_url=base_url.rstrip('/')
        self.api_key=api_key
        self.default_model=default_model
        self.timeout=timeout

    def _request(self,path,payload=None):
        url=self.base_url+'/'+path.lstrip('/')
        data=json.dumps(payload).encode('utf-8') if payload is not None else None
        headers={'Accept':'application/json'}
        if data is not None:headers['Content-Type']='application/json'
        if self.api_key:headers['Authorization']=f'Bearer {self.api_key}'
        req=urllib.request.Request(url,data=data,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            raise ModelUnavailableError(f'{self.provider_id} indisponível: {exc}') from exc

    def health(self):
        if not self.api_key:
            return {'status':'unconfigured','provider':self.provider_id}
        try:
            models=self.list_models()
            return {
                'status':'healthy','provider':self.provider_id,
                'base_url':self.base_url,'models':models[:50],
                'default_model':self.default_model,
            }
        except Exception as exc:
            return {'status':'unavailable','provider':self.provider_id,'error':str(exc)}

    def list_models(self):
        raw=self._request('/models')
        return [str(x.get('id')) for x in raw.get('data',[]) if x.get('id')]

    def chat(self,messages:Sequence[ChatMessage],*,model=None,system=None):
        wire=[]
        if system:wire.append({'role':'system','content':system})
        wire.extend({'role':m.role,'content':m.content} for m in messages)
        selected=model or self.default_model
        raw=self._request('/chat/completions',{
            'model':selected,'messages':wire,'temperature':0.2,
        })
        choices=raw.get('choices') or []
        if not choices:
            raise ModelUnavailableError(f'{self.provider_id} retornou zero choices.')
        message=choices[0].get('message') or {}
        content=str(message.get('content') or '').strip()
        if not content:
            raise ModelUnavailableError(f'{self.provider_id} retornou conteúdo vazio.')
        return ModelResponse(
            content,selected,self.provider_id,
            {
                'usage':raw.get('usage'),
                'finish_reason':choices[0].get('finish_reason'),
            }
        )
