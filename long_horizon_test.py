import tempfile
import time
from pathlib import Path

from long_horizon.engine import LongHorizonEngine


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


def main():
    with tempfile.TemporaryDirectory() as raw:
        db=Path(raw)/"long.db"
        cfg={
            "long_horizon_poll_seconds":1,
            "long_horizon_max_retries":2,
            "long_horizon_max_steps":6,
            "long_horizon_retry_base_seconds":2,
        }
        engine=LongHorizonEngine(db,cfg)
        engine.set_planner(lambda job: {"steps":[
            {"title":"Pesquisar","instruction":"Pesquisar contexto","retry_safe":True},
            {"title":"Executar","instruction":"Executar objetivo","retry_safe":True},
            {"title":"Verificar","instruction":"Verificar resultado","retry_safe":True},
        ]})
        calls=[]
        engine.set_executor(lambda job,step: calls.append(step["position"]) or {"ok":True,"output":f"feito-{step['position']}"})

        created=engine.create("Planejar campanha de outubro",auto_resume=True)
        check("Create job",created["ok"],created)
        jid=created["data"]["id"]

        for _ in range(4):
            engine.run_now(jid)
        job=engine.get(jid)["data"]
        check("Job completes by checkpoints",job["status"]=="completed",job)
        check("Three isolated executions",calls==[0,1,2],calls)
        check("Progress 100%",job["progress"]["percent"]==100,job["progress"])
        check("Checkpoints persisted",engine.checkpoints(jid)["count"]>=6,engine.checkpoints(jid))

        # Simulate crash during a retry-safe running step.
        recovered=engine.create("Job recuperável",plan=[
            {"title":"Leitura segura","instruction":"Ler dados","retry_safe":True},
            {"title":"Finalizar","instruction":"Verificar","retry_safe":True},
        ])
        rid=recovered["data"]["id"]
        with engine._connect() as c:
            c.execute("UPDATE long_jobs SET status='running',current_step=0 WHERE id=?",(rid,))
            c.execute("UPDATE long_job_steps SET status='running' WHERE job_id=? AND position=0",(rid,))
        engine2=LongHorizonEngine(db,cfg)
        rec=engine2.recover_on_start()
        check("Safe interrupted step auto-recovers",rid in rec["recovered"],rec)
        check("Recovered job queued",engine2.get(rid)["data"]["status"]=="queued",engine2.get(rid))

        # Unsafe interrupted step must wait for human review.
        unsafe=engine2.create("Publicar algo",plan=[
            {"title":"Publicar","instruction":"Publicar conteúdo externo","retry_safe":False},
        ])
        uid=unsafe["data"]["id"]
        with engine2._connect() as c:
            c.execute("UPDATE long_jobs SET status='running',current_step=0 WHERE id=?",(uid,))
            c.execute("UPDATE long_job_steps SET status='running' WHERE job_id=? AND position=0",(uid,))
        engine3=LongHorizonEngine(db,cfg)
        rec2=engine3.recover_on_start()
        check("Unsafe interrupted step waits for review",uid in rec2["waiting_review"],rec2)
        check("Unsafe status waiting_user",engine3.get(uid)["data"]["status"]=="waiting_user",engine3.get(uid))

        print("\nLong-Horizon test concluído.")


if __name__=="__main__":
    main()
