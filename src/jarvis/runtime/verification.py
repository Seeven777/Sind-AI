from __future__ import annotations

from dataclasses import dataclass,field
from pathlib import Path
import hashlib


@dataclass(slots=True)
class VerificationResult:
    status:str
    passed:bool
    evidence:dict=field(default_factory=dict)
    error:str|None=None


class GoalVerifier:
    """Independent verification layer for completed actions."""

    def verify(self,expected:dict,evidence:dict)->VerificationResult:
        kind=expected.get('kind')

        if kind=='file_exists':
            path=Path(expected['path'])
            exists=path.is_file()
            return VerificationResult(
                'passed' if exists else 'failed',exists,
                {'path':str(path),'exists':exists},
                None if exists else 'Arquivo esperado não existe.'
            )

        if kind=='file_sha256':
            path=Path(expected['path'])
            if not path.is_file():
                return VerificationResult('failed',False,{'exists':False},'Arquivo não existe.')
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            ok=digest==expected.get('sha256')
            return VerificationResult(
                'passed' if ok else 'failed',ok,
                {'path':str(path),'sha256':digest},
                None if ok else 'Checksum não corresponde ao esperado.'
            )

        if kind=='contains':
            hay=str(evidence.get(expected.get('field','content'),''))
            needle=str(expected.get('value',''))
            ok=needle in hay
            return VerificationResult(
                'passed' if ok else 'failed',ok,
                {'field':expected.get('field','content'),'contains':needle},
                None if ok else 'Evidência não contém o valor esperado.'
            )

        if kind=='equals':
            field=expected.get('field')
            observed=evidence.get(field)
            ok=observed==expected.get('value')
            return VerificationResult(
                'passed' if ok else 'failed',ok,
                {'field':field,'observed':observed,'expected':expected.get('value')},
                None if ok else 'Valor observado diverge do esperado.'
            )

        if kind=='evidence_key':
            key=expected.get('key')
            ok=bool(evidence.get(key))
            return VerificationResult(
                'passed' if ok else 'failed',ok,
                {'key':key,'value':evidence.get(key)},
                None if ok else f'Evidência ausente: {key}'
            )

        return VerificationResult(
            'uncertain',False,evidence,
            f"Tipo de verificação não suportado: {kind}"
        )


class ObserveActVerifyRuntime:
    def __init__(self,*,tool_executor,verifier=None):
        self.tool_executor=tool_executor
        self.verifier=verifier or GoalVerifier()

    async def execute(self,tool_id,payload,*,task_id=None,expected=None,approval_granted=False):
        action=await self.tool_executor.execute(
            tool_id,payload,task_id=task_id,approval_granted=approval_granted
        )
        if not action.success:
            return {
                'status':action.status,
                'action':action,
                'verification':None,
            }
        if expected is None:
            return {
                'status':'completed',
                'action':action,
                'verification':VerificationResult(
                    'passed',True,action.evidence
                ),
            }
        verification=self.verifier.verify(expected,{
            **action.output,**action.evidence
        })
        return {
            'status':'completed' if verification.passed else verification.status,
            'action':action,
            'verification':verification,
        }
