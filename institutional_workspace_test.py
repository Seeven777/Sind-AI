import json
import tempfile
from pathlib import Path

from attachments.manager import AttachmentManager
from cognitive.conversation_store import ConversationStore
from cognitive.project_store import ProjectStore
from institutional.services import InstitutionalServices
from knowledge.base import KnowledgeBase


BASE=Path(__file__).resolve().parent


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


def main():
    with tempfile.TemporaryDirectory() as raw:
        td=Path(raw)

        # Institutional tabs adapter
        services=InstitutionalServices(BASE/"data"/"institutional_services.json")
        opened=[]
        actions=[]
        services.set_tab_adapter(
            opener=lambda sid: opened.append(sid) or {"ok":True},
            action=lambda sid,op,payload: actions.append((sid,op,payload)) or {
                "ok":True,"title":"Teste","text":"conteúdo da aba","url":"https://example.local/"
            }
        )
        result=services.open("instagram")
        check("Instagram opens embedded",result["ok"] and result.get("embedded") is True,result)
        check("Embedded opener called",opened==["instagram"],opened)
        inspected=services.tab_action("dashboard","inspect",max_chars=5000)
        check("Dashboard inspect uses tab adapter",inspected["ok"] and actions[-1][0]=="insights_dashboard",inspected)

        # Conversations + attachments cleanup.
        conversations=ConversationStore(td/"conversations.db")
        first=conversations.current_session_id
        conversations.append("user","Conversa descartável",session_id=first)
        second=conversations.new_session("Conversa útil")["session_id"]
        conversations.append("user","Manter esta conversa",session_id=second)

        knowledge=KnowledgeBase(td/"knowledge.db",td/"storage")
        projects=ProjectStore(td/"projects.db")
        attachments=AttachmentManager(td/"attachments.db",knowledge,projects)

        file1=td/"exclusive.txt";file1.write_text("arquivo exclusivo",encoding="utf-8")
        a1=attachments.add_files([str(file1)],session_id=first)
        check("Conversation attachment indexed",a1["ok"],a1)

        project=projects.create("Projeto")[ "data" ]["id"]
        file2=td/"project.txt";file2.write_text("arquivo de projeto",encoding="utf-8")
        a2=attachments.add_files([str(file2)],session_id=first,project_id=project)
        check("Project attachment indexed",a2["ok"],a2)

        purge=attachments.purge_session(first)
        check("Exclusive attachment removed",purge["removed"]>=1,purge)
        check("Project attachment preserved",purge["preserved_project_attachments"]>=1,purge)

        deleted=conversations.delete_session(first)
        check("Conversation deleted",deleted["ok"] and deleted["deleted_session_id"]==first,deleted)
        remaining=conversations.list_sessions(limit=20)["items"]
        check("Useful conversation remains",any(x["id"]==second for x in remaining),remaining)
        check("Deleted conversation absent",all(x["id"]!=first for x in remaining),remaining)

        # Source validation: every supplied daily service has a tab label mapping in Habitat.
        habitat=(BASE/"ui"/"habitat.py").read_text(encoding="utf-8")
        for service in services.list(daily=True)["items"]:
            check(f"Service tab registered: {service['id']}", f'"{service["id"]}"' in habitat, service["id"])

        check("Chat delete UI exists",'data-delete-session' in (BASE/"ui/web/app.js").read_text(encoding="utf-8"))
        check("Persistent browser profile exists","JarvisInstitutional" in habitat and "ForcePersistentCookies" in habitat)

        print("\nInstitutional workspace + chat deletion test concluído.")


if __name__=="__main__":
    main()
