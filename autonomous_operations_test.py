import json
import tempfile
from pathlib import Path

from actions.hub import ActionHub
from approvals.engine import ApprovalEngine
from automations.engine import AutomationEngine
from connectors.gateway import ConnectorGateway
from monitors.engine import MonitorEngine
from notifications.engine import NotificationEngine
from team_assistant.engine import TeamAssistantEngine


BASE=Path(__file__).resolve().parent


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print(f"[OK] {name}")


def load_catalog(path,key):
    data=json.loads(path.read_text(encoding="utf-8"))
    return data.get(key,[]) if isinstance(data,dict) else data


def main():
    with tempfile.TemporaryDirectory() as raw:
        td=Path(raw)

        notifications=NotificationEngine(td/"notifications.db")
        approvals=ApprovalEngine(td/"approvals.db")
        connectors=ConnectorGateway(td/"connectors.db")
        team=TeamAssistantEngine(td/"team.db")
        monitors=MonitorEngine(td/"monitors.db")

        # Notifications
        n=notifications.add("Teste","Alerta local",category="test",severity="info")
        check("Notification add",n["ok"],n)
        nid=n["data"]["id"]
        check("Notification unread",notifications.unread()["count"]==1)
        check("Notification read",notifications.mark_read(nid)["ok"])
        check("Notification stats","read" in notifications.stats()["statuses"])

        # Team roles/users/passwords/grants/gaps/feedback
        role=team.role_create("Comunicação","Equipe de comunicação")
        check("Team role",role["ok"],role)
        role_id=role["data"]["id"]
        user=team.user_create("teste","Pessoa Teste",role_id=role_id,password="SenhaLocal#123")
        check("Team user",user["ok"],user)
        uid=user["data"]["id"]
        auth=team.authenticate("teste","SenhaLocal#123")
        check("Team auth",auth["ok"],auth)
        check("Wrong password rejected",not team.authenticate("teste","errada")["ok"])
        check("Collection grant",team.collection_grant_set(role_id,"sindpetshop")["ok"])
        check("Track grant",team.track_grant_set(role_id,1)["ok"])
        check("Feedback",team.feedback_add(uid,5,"teste","Q","A","OK")["ok"])
        gap=team.gap_add("Como localizar a CCT correta?","cct")
        check("Knowledge gap",gap["ok"],gap)
        gap2=team.gap_add("Como localizar a CCT correta?","cct")
        check("Gap occurrence increments",gap2["data"]["occurrences"]==2,gap2)

        # Connector profiles/endpoints & safe preview without secrets.
        cp=connectors.create(
            "Teste API","https://example.com/api/",
            auth_type="bearer",description="Connector de teste",enabled=False
        )
        check("Connector create",cp["ok"],cp)
        cid=cp["data"]["id"]
        ep=connectors.endpoint_create(
            cid,"listar","GET","items/{{id}}",
            params={"limit":"{{limit}}"},risk="read"
        )
        check("Connector endpoint",ep["ok"],ep)
        eid=ep["data"]["id"]
        preview=connectors.preview(eid,{"id":5,"limit":10})
        check("Connector preview works without secret",preview["ok"],preview)
        check("Connector preview masks secret",preview["headers"].get("Authorization")=="<secret>",preview)

        # File monitor detects change.
        watched=td/"watched.txt"
        watched.write_text("A",encoding="utf-8")
        m=monitors.create("arquivo_teste","file",{"path":str(watched),"mode":"hash"})
        check("Monitor create",m["ok"],m)
        mid=m["data"]["id"]
        first=monitors.check(mid)
        check("First monitor baseline",first["ok"] and not first["changed"],first)
        watched.write_text("B",encoding="utf-8")
        second=monitors.check(mid)
        check("Monitor detects file change",second["ok"] and second["changed"],second)
        check("Monitor event generated",monitors.events(monitor_id=mid,acknowledged=False)["count"]==1)

        # Approvals with executor callback.
        executed=[]
        approvals.set_executor(lambda item: executed.append(item["id"]) or {"ok":True,"done":True})
        ar=approvals.create(
            "Publicar teste","action","x","wordpress.posts.publish",
            {"id":12},risk="high",description="Teste de aprovação"
        )
        check("Approval create",ar["ok"],ar)
        aid=ar["data"]["id"]
        ap=approvals.approve(aid,note="Teste")
        check("Approval execution",ap["ok"] and executed==[aid],ap)

        # Scheduler with deterministic fake executor.
        automation=AutomationEngine(td/"automations.db",poll_seconds=2)
        calls=[]
        automation.set_executor(
            lambda job: calls.append((job["target_type"],job["target_id"],job["params"]))
            or {"ok":True,"value":"executed"}
        )
        job=automation.create(
            "job_teste","interval","action","notification.stats",
            schedule={"interval_seconds":60},params={"x":1}
        )
        check("Automation create",job["ok"],job)
        jid=job["data"]["id"]
        run=automation.run_now(jid)
        check("Automation run_now",run["ok"] and len(calls)==1,run)
        check("Automation history",automation.history(job_id=jid)["count"]==1)
        check("Automation next run",automation.get(jid)["data"]["next_run"] is not None)

        # Rejected approval should not strand a recurring automation forever.
        job2=automation.create(
            "job_aprovacao","daily","action","connector.execute",
            schedule={"hour":8,"minute":0},params={}
        )
        check("Automation approval test job",job2["ok"],job2)
        jid2=job2["data"]["id"]
        approval2=approvals.create(
            "Execução agendada sensível","automation",str(jid2),"connector.execute",
            {"job_id":jid2},risk="high"
        )
        approvals.set_resolution_callback(
            lambda item: automation.reject_approval(
                int((item.get("payload") or {}).get("job_id") or item.get("source_id")),
                reason=item.get("resolution_note") or "Rejeitada"
            ) if item.get("source_type")=="automation" else {"ok":True}
        )
        rejected=approvals.reject(approval2["data"]["id"],note="Teste de rejeição")
        check("Approval reject callback",rejected["ok"],rejected)
        after_reject=automation.get(jid2)["data"]
        check("Recurring automation rescheduled after rejection",
              after_reject["status"]=="enabled" and after_reject["next_run"] is not None,
              after_reject)

        # ActionHub includes and executes new engines.
        hub=ActionHub(
            BASE/"actions"/"catalog.json",
            {
                "automations":automation,
                "monitors":monitors,
                "approvals":approvals,
                "connectors":connectors,
                "team":team,
                "notifications":notifications,
            }
        )
        stats=hub.stats()
        check("Action Hub >= 600 actions",stats["actions"]>=600,stats)
        check("New engine actions searchable",
              any(x["id"]=="automation.stats" for x in hub.search("automação estatísticas",20)["items"]))
        hr=hub.execute("team.stats",{})
        check("Action Hub team execution",hr["ok"],hr)

        # Catalog integrity and workflow references.
        actions=load_catalog(BASE/"actions"/"catalog.json","actions")
        workflows=load_catalog(BASE/"workflows"/"catalog.json","workflows")
        caps=load_catalog(BASE/"capabilities"/"catalog.json","capabilities")
        action_ids=[x["id"] for x in actions]
        check("Action IDs unique",len(action_ids)==len(set(action_ids)))
        action_set=set(action_ids)
        missing=[]
        for wf in workflows:
            for step in wf.get("steps",[]):
                aid_ref=step.get("action") or step.get("action_id")
                if aid_ref and aid_ref not in action_set:
                    missing.append((wf.get("id"),aid_ref))
        check("Workflow action references valid",not missing,missing[:20])
        check("Release adds >= 100 possibilities",len(actions)>=580 and len(workflows)>=450)
        check("Combined brokered possibilities >= 1300",len(actions)+len(workflows)+len(caps)>=1300)

        # Engines remain functional, but technical modules are secondary infrastructure.
        html=(BASE/"ui"/"web"/"index.html").read_text(encoding="utf-8")
        js=(BASE/"ui"/"web"/"app.js").read_text(encoding="utf-8")
        habitat=(BASE/"ui"/"habitat.py").read_text(encoding="utf-8")
        check("Control Center exists",'id="controlOverlay"' in html)
        check("Conversation-first shell",'id="conversation"' in html and 'id="conversationList"' in html)
        check("Old Actions page removed",'id="view-actions"' not in html)
        check("Control Center renderer","renderControlCenter" in js)
        for slot in ("runAutomation","approvalDecision","checkMonitor","markNotificationRead","testConnector"):
            check(f"Bridge {slot}",f"def {slot}" in habitat)

        summary={
            "public_capabilities":len(caps),
            "actions":len(actions),
            "workflows":len(workflows),
            "combined":len(caps)+len(actions)+len(workflows),
            "new_engine_counts":{
                name:sum(1 for a in actions if a.get("engine")==name)
                for name in ("automations","monitors","approvals","connectors","team","notifications")
            }
        }
        print("\nResumo:")
        print(json.dumps(summary,indent=2,ensure_ascii=False))
        print("\nAutonomous Operations offline test concluído.")


if __name__=="__main__":
    main()
