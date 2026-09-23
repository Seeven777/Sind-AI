import json
import tempfile
from pathlib import Path

from experience.engine import AdaptiveExperienceEngine
from experience.commands import parse_experience_command
from long_horizon.engine import LongHorizonEngine
from workplace.engine import WorkplaceIntelligence


BASE=Path(__file__).resolve().parent


def check(name,cond,detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]",name)


class DummyServices:
    def __init__(self):
        self.opened=[]
    def open(self,sid):
        self.opened.append(sid)
        return {"ok":True,"service":sid,"embedded":True}


def main():
    with tempfile.TemporaryDirectory() as raw:
        td=Path(raw)
        services=DummyServices()
        lh=LongHorizonEngine(td/"long.db",{
            "long_horizon_poll_seconds":1,
            "long_horizon_max_retries":1,
            "long_horizon_max_steps":8,
        })
        workplace=WorkplaceIntelligence(
            BASE/"workplace"/"playbooks.json",
            td/"workplace.db",
            services=services,
            long_horizon=lh,
            config={
                "workplace_auto_context":True,
                "workplace_max_context_playbooks":3,
                "workplace_preopen_services":2,
            },
            user_registry_path=td/"custom_playbooks.json",
        )
        exp=AdaptiveExperienceEngine(
            td/"experience.db",
            workplace=workplace,
            long_horizon=lh,
            config={
                "experience_auto_soft_rules":True,
                "experience_candidate_failure_threshold":2,
                "experience_max_context_rules":6,
            },
        )
        workplace.set_adapters(experience=exp)

        pid="workplace.content.carousel_rights"

        # Real outcome updates competence.
        e1=exp.record_playbook_outcome(pid,"completed","entrega aprovada",query="carrossel")
        check("Successful outcome recorded",e1["ok"],e1)
        profiles=exp.competence_map(kind="playbook")["items"]
        prof=next(x for x in profiles if x["label"]==pid)
        check("Success updates competence",prof["successes"]==1 and prof["uses"]==1,prof)

        # Explicit correction becomes safe rule immediately.
        workplace._record_start(pid,"carrossel sobre direitos")
        fb=exp.observe_feedback("Da próxima vez, deixe o texto mais curto e direto.")
        check("Explicit correction recognized",fb["recognized"],fb)
        rules=exp.rules(pid)["items"]
        check("Correction installed as playbook rule",any("mais curto" in x["rule_text"].lower() for x in rules),rules)
        guidance=exp.guidance(pid)["text"]
        check("Guidance is retrievable","mais curto" in guidance.lower(),guidance)

        # Guidance reaches actual Long-Horizon job metadata.
        started=workplace.start_long_horizon(pid,request="Criar novo carrossel",project_id=1,session_id=1)
        check("Playbook starts with experience guidance",started["ok"],started)
        job=started["data"]
        check("Guidance persisted in job metadata","mais curto" in (job.get("metadata",{}).get("experience_guidance","").lower()),job.get("metadata"))

        # Repeated failure proposes structural adaptation.
        exp.record_playbook_outcome(pid,"failed","fonte errada",query="carrossel")
        exp.record_playbook_outcome(pid,"failed","fonte errada novamente",query="carrossel")
        candidates=exp.candidates("proposed")["items"]
        check("Repeated failures create supervised adaptation",len(candidates)>=1,candidates)

        cid=candidates[0]["id"]
        approved=exp.approve_candidate(cid)
        check("Candidate can be approved/installed",approved["ok"],approved)
        check("Installed candidate adds active rule",exp.stats()["active_rules"]>=2,exp.stats())

        # Ranking bonus reacts to observed experience.
        bonus=exp.ranking_bonus(pid)
        check("Experience ranking bonus exists",isinstance(bonus,float),bonus)

        agent_result=exp.record_agent_outcome("content",success=True,source_id="swarm-1")
        check("Agent outcome learned",agent_result["ok"],agent_result)
        check("Agent routing bonus exists",exp.agent_bonus("content")>0,exp.agent_bonus("content"))

        rated=exp.rate_response(
            "Crie um carrossel sobre direito trabalhista",
            positive=True,
            project_id=1,
        )
        check("Message rating is recorded",rated["ok"],rated)

        # Completed job can become update-safe custom playbook.
        job_payload={
            "id":77,
            "goal":"Preparar relatório semanal do sindicato",
            "status":"completed",
            "metadata":{"services":["insights_dashboard"],"agents":["analyst","reviewer"]},
            "steps":[
                {"title":"Ler dashboard","instruction":"Use o dashboard de insights.","retry_safe":True},
                {"title":"Comparar","instruction":"Compare com a semana anterior.","retry_safe":True},
                {"title":"Revisar","instruction":"Revise os números e entregue o resumo.","retry_safe":True},
            ],
        }
        created=workplace.create_from_job(job_payload)
        check("Completed job becomes custom playbook",created["ok"],created)
        custom_id=created["id"]
        check("Custom playbook persisted",custom_id.startswith("custom.") and (td/"custom_playbooks.json").exists(),custom_id)

        # Reload proves it survives application/release restart.
        workplace2=WorkplaceIntelligence(
            BASE/"workplace"/"playbooks.json",
            td/"workplace2.db",
            services=services,
            long_horizon=lh,
            config={},
            user_registry_path=td/"custom_playbooks.json",
            experience=exp,
        )
        check("Custom playbook reloads after restart",workplace2.get(custom_id)["ok"],workplace2.stats())

        # Natural commands.
        check("Retrospective command",parse_experience_command("Faça uma retrospectiva de aprendizado")["action"]=="retrospective")
        check("Competence map command",parse_experience_command("Mostre o mapa de competências")["action"]=="competence_map")
        check("Approve adaptation command",parse_experience_command("Aprove a adaptação #12")=={"action":"approve_candidate","id":12})
        check("Job to playbook command",parse_experience_command("Transforme o job #77 em uma rotina")=={"action":"job_to_playbook","job_id":77})

        retro=exp.retrospective()
        check("Retrospective exposes success/failure",retro["successes"]>=1 and retro["failures"]>=2,retro)
        check("Experience stats available",exp.stats()["events"]>=4,exp.stats())

        # Product integration source assertions.
        agent=(BASE/"core"/"agent.py").read_text(encoding="utf-8")
        ui=(BASE/"ui"/"web"/"app.js").read_text(encoding="utf-8")
        habitat=(BASE/"ui"/"habitat.py").read_text(encoding="utf-8")
        check("System prompt contains experience context","EXPERIÊNCIA ACUMULADA RELEVANTE" in agent)
        check("Agent routes experience commands","parse_experience_command(user_text)" in agent)
        check("Long-Horizon receives experience guidance","APRENDIZADOS ACUMULADOS PARA ESTA ROTINA" in agent)
        check("Desktop renders experience map","experienceMap" in ui)
        check("Desktop can approve adaptations","experienceCandidateAction" in habitat)
        check("Desktop response rating bridge","rateExperience" in habitat)
        check("Completed jobs can become playbooks","jobToPlaybook" in habitat)
        mobile=(BASE/"mobile"/"companion.py").read_text(encoding="utf-8")
        check("Mobile response rating endpoint",'/api/experience/rate' in mobile)
        swarm=(BASE/"swarm"/"orchestrator.py").read_text(encoding="utf-8")
        check("Swarm supports adaptive experience","set_experience" in swarm and "agent_bonus" in swarm)

        rollback=exp.rollback_last_rule(pid)
        check("Adaptive rule can be rolled back",rollback["ok"],rollback)

        print("\nAdaptive Experience 1.9 test concluído.")


if __name__=="__main__":
    main()
