from pathlib import Path
from jarvis.skills import SkillRegistry,SkillRepository,SkillManager,SkillRunner
from jarvis.storage import Database,MigrationEngine


def test_skill_scaffold_test_install_and_run(tmp_path:Path):
    db=Database(tmp_path/"jarvis.db")
    conn=db.open()
    MigrationEngine(conn,Path(__file__).resolve().parents[2]/"migrations").apply_pending()
    registry=SkillRegistry()
    repo=SkillRepository(conn)
    manager=SkillManager(
        root=tmp_path/"skills",staging=tmp_path/"staging",
        repository=repo,registry=registry
    )
    scaffold=manager.create_scaffold("demo.echo","Echo skill",("echo",))
    result=manager.test(Path(scaffold["path"]))
    assert result["passed"] is True
    installed=manager.install(Path(scaffold["path"]))
    assert installed["skill_id"]=="demo.echo"
    runner=SkillRunner(registry)
    output=runner.execute("demo.echo",{"hello":"world"})
    assert output["success"] is True
    assert output["output"]["hello"]=="world"
    db.close()
