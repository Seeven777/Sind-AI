from __future__ import annotations

import argparse
import asyncio
import getpass
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path

from jarvis.app.lifecycle import run_forever,run_once
from jarvis.app.product_runtime import start_product_runtime
from jarvis.hq.server import serve_hq
from jarvis.distributed.worker_server import serve_worker
from jarvis.tasks import TaskStatus


def parser():
    p=argparse.ArgumentParser(prog='jarvis')
    p.add_argument('--data-dir',type=Path,default=None)
    sub=p.add_subparsers(dest='command')

    for name in (
        'foundation','once','doctor','model-probe','hq','chat','curate-memory',
        'sync','connectors','briefing','inbox','scheduler-tick','watchers',
        'system-status','google-auth','google-disconnect','inventory',
        'skills','projects','browser-doctor','windows-doctor','voice-doctor',
        'agency-status','agency-runbooks',
    ):
        sub.add_parser(name)

    u=sub.add_parser('ui');u.add_argument('--no-open',action='store_true')
    h=sub.add_parser('hq-web');h.add_argument('--no-open',action='store_true')

    d=sub.add_parser('demo-agent')
    d.add_argument('--prompt',default='Pesquise como tornar agentes confiáveis.')

    t=sub.add_parser('demo-team')
    t.add_argument('--prompt',default='Crie uma missão completa para planejar uma campanha educativa.')

    o=sub.add_parser('operator')
    o.add_argument('tool',choices=['time','list','read','write'])
    o.add_argument('--path',default='')
    o.add_argument('--content',default='')

    cap=sub.add_parser('capability')
    cap.add_argument('name')

    ss=sub.add_parser('secret-set')
    ss.add_argument('key')
    sd=sub.add_parser('secret-delete')
    sd.add_argument('key')

    sc=sub.add_parser('skill-scaffold')
    sc.add_argument('skill_id')
    sc.add_argument('--description',default='Skill criada pelo Jarvis')
    sc.add_argument('--capability',action='append',default=[])

    sg=sub.add_parser('skill-generate')
    sg.add_argument('skill_id')
    sg.add_argument('--description',required=True)

    st=sub.add_parser('skill-test')
    st.add_argument('path',type=Path)

    si=sub.add_parser('skill-install')
    si.add_argument('path',type=Path)

    pc=sub.add_parser('project-create')
    pc.add_argument('name')
    pc.add_argument('--objective',default='')

    ac=sub.add_parser('agent-create')
    ac.add_argument('agent_id')
    ac.add_argument('name')
    ac.add_argument('--mission',required=True)
    ac.add_argument('--department',default='Custom')
    ac.add_argument('--capability',action='append',default=[])
    sub.add_parser('agents')

    aa=sub.add_parser('agency-agents')
    aa.add_argument('--limit',type=int,default=50)

    ar=sub.add_parser('agency-route')
    ar.add_argument('objective')
    ar.add_argument('--limit',type=int,default=5)

    an=sub.add_parser('agency-run')
    an.add_argument('slug')
    an.add_argument('objective')
    an.add_argument('--all-groups',action='store_true')
    an.add_argument('--max-agents',type=int,default=8)

    rem=sub.add_parser('reminder')
    rem.add_argument('--minutes',type=int,required=True)
    rem.add_argument('--message',required=True)

    wf=sub.add_parser('watch-file')
    wf.add_argument('path',type=Path)
    wf.add_argument('--name',default='Arquivo monitorado')

    worker=sub.add_parser('worker')
    worker.add_argument('--host',default='127.0.0.1')
    worker.add_argument('--port',type=int,default=4770)

    na=sub.add_parser('node-add')
    na.add_argument('node_id')
    na.add_argument('name')
    na.add_argument('endpoint')
    na.add_argument('--capability',action='append',default=[])

    nd=sub.add_parser('dispatch')
    nd.add_argument('capability')
    nd.add_argument('objective')

    return p


async def doctor(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        report={
            'foundation':rt.foundation.health.snapshot(),
            'models':rt.model_registry.health(),
            'active_agents':[c.agent_id for c in rt.agent_registry.available()],
            'tools':rt.tool_registry.list_ids(),
            'workspace':rt.workspace,
            'briefing':rt.briefing.snapshot()['summary'],
            'connectors':{
                'health':rt.connectors.health(),
                'counts':rt.connector_repository.counts(),
                'sources':rt.connector_repository.sources(),
            },
            'browser':rt.browser.health(),
            'windows':rt.windows.health(),
            'voice':rt.voice.health(),
            'skills':len(rt.skill_registry.all()),
            'agency':rt.agency_catalog.status(),
            'agent_router':rt.agent_router.status(),
            'scheduler':rt.scheduler_repository.all(),
            'watchers':rt.watcher_repository.enabled(),
            'mcp':rt.mcp.health(),
            'a2a':rt.a2a.health(),
            'nodes':rt.nodes.repository.list(),
            'hq':rt.hq.snapshot()['metrics'],
        }
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if report['foundation']['status']=='healthy' else 1
    finally:
        await rt.close()


async def model_probe(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        provider=rt.model_registry.get(rt.model_router.default_provider)
        probe=getattr(provider,'probe',None)
        result=probe(rt.model_router.default_model) if probe else provider.health()
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result.get('status')=='healthy' else 1
    finally:await rt.close()


async def demo_agent(data_dir,prompt):
    rt=await start_product_runtime(data_dir)
    try:
        print('JARVIS > Delegando para Research...')
        result=await rt.orchestrator.handle(prompt)
        print(f"\nAGENTE: {result.get('agent','Jarvis')}")
        print(f"TASK: {result.get('task_id','—')}")
        print(f"ARTIFACT: {result.get('artifact_path','—')}\n")
        print(result['content'])
        return 0
    finally:await rt.close()


async def demo_team(data_dir,prompt):
    rt=await start_product_runtime(data_dir)
    try:
        result=await rt.missions.run(prompt,title='Demo de equipe')
        print('MISSÃO:',result['mission_id'])
        print('TASK:',result['task_id'])
        print('AGENTES:',' → '.join(result['agents']))
        print('ENTREGA:',result['artifact_path'])
        print('\n=== ENTREGA ===\n'+result['content'])
        print('\n=== REVIEW ===\n'+result['review'])
        return 0
    finally:await rt.close()


async def operator_cli(data_dir,tool,path='',content=''):
    rt=await start_product_runtime(data_dir)
    try:
        operator=rt.agent_registry.runtime('operations.operator')
        task=await rt.foundation.task_service.create(
            'Operação via CLI',f'{tool} {path}',
            metadata={'agent':'operations.operator','source':'cli'}
        )
        await rt.foundation.task_service.transition(task.task_id,TaskStatus.READY)
        await rt.foundation.task_service.transition(task.task_id,TaskStatus.RUNNING)
        if tool=='time':
            tool_id='system.time';payload={}
        elif tool=='list':
            tool_id='files.list_directory';payload={'path':path}
        elif tool=='read':
            tool_id='files.read_text';payload={'path':path}
        else:
            tool_id='files.write_workspace_text';payload={'relative_path':path,'content':content}
        result=await operator.execute(tool_id,payload,task_id=task.task_id)
        print(result.summary)
        if result.metadata.get('approval_id'):
            print('APPROVAL:',result.metadata['approval_id'])
            await rt.foundation.task_service.transition(task.task_id,TaskStatus.BLOCKED)
        return 0 if result.success or result.metadata.get('approval_id') else 1
    finally:await rt.close()


async def curate_memory_cli(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        result=await rt.orchestrator.handle('Organize sua memória')
        print(result['content'])
        if result.get('artifact_path'):print('ARTIFACT:',result['artifact_path'])
        return 0
    finally:await rt.close()


async def sync_cli(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        result=await rt.connectors.sync_all()
        watch=await rt.watchers.check_all()
        print(json.dumps({'sync':result,'watchers':watch},ensure_ascii=False,indent=2))
        return 0
    finally:await rt.close()


async def connectors_cli(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        print(json.dumps({
            'health':rt.connectors.health(),
            'sources':rt.connector_repository.sources(),
            'counts':rt.connector_repository.counts(),
            'recent':rt.connector_repository.recent(10),
        },ensure_ascii=False,indent=2))
        return 0
    finally:await rt.close()


async def briefing_cli(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        print(rt.briefing.text());return 0
    finally:await rt.close()


async def inbox_cli(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        result=await rt.orchestrator.handle('Resuma minha caixa de entrada')
        print(result['content'])
        if result.get('artifact_path'):print('ARTIFACT:',result['artifact_path'])
        return 0
    finally:await rt.close()


async def scheduler_cli(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        print(json.dumps(await rt.scheduler.run_due(),ensure_ascii=False,indent=2));return 0
    finally:await rt.close()


async def watchers_cli(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        result=await rt.watchers.check_all()
        print(json.dumps({
            'watchers':rt.watcher_repository.enabled(),'result':result
        },ensure_ascii=False,indent=2));return 0
    finally:await rt.close()


async def interactive_chat(data_dir):
    rt=await start_product_runtime(data_dir)
    try:
        print('JARVIS NEXT')
        print('/sair encerra | /hq mostra escritório | /briefing mostra resumo')
        cid=rt.chat.new_conversation()
        while True:
            try:text=input('\nVOCÊ > ').strip()
            except (EOFError,KeyboardInterrupt):print();break
            if not text:continue
            if text.lower() in {'/sair','/exit','sair'}:break
            if text.lower()=='/hq':
                print(json.dumps(rt.hq.snapshot(),ensure_ascii=False,indent=2));continue
            if text.lower()=='/briefing':
                print(rt.briefing.text());continue
            try:
                result=await rt.chat.send(cid,text)
                print('\nJARVIS >',result['content'])
                if result.get('agents'):print('EQUIPE >',' → '.join(result['agents']))
                if result.get('artifact_path'):print('ARTIFACT >',result['artifact_path'])
                if result.get('approval_id'):print('APROVAÇÃO >',result['approval_id'])
            except Exception as exc:
                print('ERRO >',exc)
        return 0
    finally:await rt.close()


async def utility_command(args):
    rt=await start_product_runtime(args.data_dir)
    try:
        c=args.command
        if c=='google-auth':
            token=await asyncio.to_thread(rt.google_oauth.authenticate_interactive,True,240)
            print('Google autorizado.')
            print(json.dumps({
                'scope':token.get('scope'),
                'has_refresh_token':bool(token.get('refresh_token')),
            },ensure_ascii=False,indent=2))
            return 0
        if c=='google-disconnect':
            rt.google_oauth.token_store.delete()
            print('Token Google removido do armazenamento local.')
            return 0
        if c=='inventory':
            print(json.dumps(rt.capabilities.inventory(),ensure_ascii=False,indent=2));return 0
        if c=='capability':
            print(json.dumps(rt.capabilities.resolve(args.name),ensure_ascii=False,indent=2));return 0
        if c=='skills':
            print(json.dumps(rt.skill_manager.repository.list(),ensure_ascii=False,indent=2));return 0
        if c=='skill-scaffold':
            print(json.dumps(rt.skill_manager.create_scaffold(
                args.skill_id,args.description,args.capability
            ),ensure_ascii=False,indent=2));return 0
        if c=='skill-generate':
            result=await rt.skill_generator.generate(args.skill_id,args.description)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result.get('ready_for_install') else 1
        if c=='skill-test':
            print(json.dumps(rt.skill_manager.test(args.path),ensure_ascii=False,indent=2));return 0
        if c=='skill-install':
            print(json.dumps(rt.skill_manager.install(args.path),ensure_ascii=False,indent=2));return 0
        if c=='agency-status':
            print(json.dumps(rt.agency_catalog.status(),ensure_ascii=False,indent=2));return 0
        if c=='agency-agents':
            limit=max(1,args.limit)
            rows=[]
            for definition in rt.agency_catalog.definitions()[:limit]:
                rows.append({
                    'slug':definition.slug,'id':definition.agent_id,'name':definition.name,
                    'division':definition.division,'description':definition.description,
                })
            print(json.dumps({
                'status':rt.agency_catalog.status(),'showing':len(rows),'agents':rows
            },ensure_ascii=False,indent=2));return 0
        if c=='agency-runbooks':
            print(json.dumps({
                'status':rt.agency_catalog.status(),
                'runbooks':[
                    {
                        'slug':x.get('slug'),'title':x.get('title'),'mode':x.get('mode'),
                        'duration':x.get('duration'),'summary':x.get('summary')
                    } for x in rt.agency_catalog.runbooks()
                ]
            },ensure_ascii=False,indent=2));return 0
        if c=='agency-route':
            routes=rt.agent_router.route(args.objective,limit=max(1,args.limit))
            print(json.dumps({
                'objective':args.objective,
                'routes':[
                    {
                        'slug':r.slug,'agent_id':r.agent_id,'name':r.name,
                        'division':r.division,'score':r.score,'reason':r.reason
                    } for r in routes
                ]
            },ensure_ascii=False,indent=2));return 0
        if c=='agency-run':
            cap=None if args.max_agents<=0 else args.max_agents
            activation=None if args.all_groups else 'always'
            selected=rt.agency_catalog.runbook_agents(
                args.slug,activation=activation,max_agents=cap
            )
            if not selected:
                raise RuntimeError('Runbook não possui agentes instalados para esta seleção.')
            result=await rt.missions.run_with_agents(
                args.objective,agents=selected,
                title=f'Agency runbook: {args.slug}',
                reason=f'agency runbook {args.slug}; activation={activation or "all"}'
            )
            print(json.dumps({
                'mission_id':result['mission_id'],'task_id':result['task_id'],
                'agents':result['agents'],'review_passed':result['review_passed'],
                'artifact_path':result['artifact_path'],'content':result['content'],
                'review':result['review']
            },ensure_ascii=False,indent=2));return 0
        if c=='agents':
            print(json.dumps({
                'builtin_and_custom':[
                    {
                        'id':x.agent_id,'name':x.name,'department':x.department,
                        'capabilities':list(x.capabilities),
                        'active':x.agent_id in {a.agent_id for a in rt.agent_registry.available()}
                    } for x in rt.agent_registry.cards()
                ],
                'custom_definitions':rt.agent_factory.definitions()
            },ensure_ascii=False,indent=2));return 0
        if c=='agent-create':
            print(json.dumps(rt.agent_factory.create(
                agent_id=args.agent_id,name=args.name,mission=args.mission,
                department=args.department,capabilities=args.capability
            ),ensure_ascii=False,indent=2));return 0
        if c=='reminder':
            run_at=(datetime.now(timezone.utc)+timedelta(minutes=max(1,args.minutes))).isoformat()
            job_id=rt.scheduler_repository.create_once(
                args.message,'reminder',run_at,{'message':args.message}
            )
            print(json.dumps({'job_id':job_id,'run_at':run_at,'message':args.message},ensure_ascii=False,indent=2));return 0
        if c=='watch-file':
            watcher_id=rt.watcher_repository.ensure(
                args.name,'file.changed',{'path':str(args.path.resolve())}
            )
            print(json.dumps({'watcher_id':watcher_id,'path':str(args.path.resolve())},ensure_ascii=False,indent=2));return 0
        if c=='node-add':
            node=rt.nodes.register_remote(
                args.node_id,args.name,args.endpoint,args.capability
            )
            print(json.dumps({
                'node_id':node.node_id,'name':node.name,'endpoint':node.endpoint,
                'capabilities':list(node.capabilities),'status':node.status
            },ensure_ascii=False,indent=2));return 0
        if c=='dispatch':
            token=rt.secret_store.get(f'worker_token_{args.capability}')
            print(json.dumps(rt.dispatcher.dispatch(
                args.capability,args.objective,token=token
            ),ensure_ascii=False,indent=2));return 0
        if c=='projects':
            print(json.dumps(rt.projects.list(),ensure_ascii=False,indent=2));return 0
        if c=='project-create':
            print(json.dumps(rt.projects.create(
                args.name,args.objective,rt.workspace['workspace_id']
            ),ensure_ascii=False,indent=2));return 0
        if c=='browser-doctor':
            print(json.dumps(rt.browser.health(),ensure_ascii=False,indent=2));return 0
        if c=='windows-doctor':
            print(json.dumps(rt.windows.health(),ensure_ascii=False,indent=2));return 0
        if c=='voice-doctor':
            print(json.dumps(rt.voice.health(),ensure_ascii=False,indent=2));return 0
        if c=='secret-set':
            value=getpass.getpass(f'{args.key}: ')
            rt.secret_store.set(args.key,value)
            print('Secret armazenado localmente.')
            return 0
        if c=='secret-delete':
            rt.secret_store.delete(args.key);print('Secret removido.');return 0
        if c=='system-status':
            print(json.dumps({
                'foundation':rt.foundation.health.snapshot(),
                'models':rt.model_registry.health(),
                'connectors':rt.connectors.health(),
                'browser':rt.browser.health(),
                'windows':rt.windows.health(),
                'voice':rt.voice.health(),
                'mcp':rt.mcp.health(),
                'a2a':rt.a2a.health(),
                'nodes':rt.nodes.repository.list(),
                'agency':rt.agency_catalog.status(),
                'agent_router':rt.agent_router.status(),
                'capabilities':rt.capabilities.inventory(),
            },ensure_ascii=False,indent=2));return 0
        return 2
    finally:await rt.close()


async def amain(args):
    c=args.command or 'doctor'
    if c=='foundation':await run_forever(args.data_dir);return 0
    if c=='once':print(json.dumps(await run_once(args.data_dir),ensure_ascii=False,indent=2));return 0
    if c=='doctor':return await doctor(args.data_dir)
    if c=='model-probe':return await model_probe(args.data_dir)
    if c=='chat':return await interactive_chat(args.data_dir)
    if c=='demo-agent':return await demo_agent(args.data_dir,args.prompt)
    if c=='demo-team':return await demo_team(args.data_dir,args.prompt)
    if c=='operator':return await operator_cli(args.data_dir,args.tool,args.path,args.content)
    if c=='curate-memory':return await curate_memory_cli(args.data_dir)
    if c=='sync':return await sync_cli(args.data_dir)
    if c=='connectors':return await connectors_cli(args.data_dir)
    if c=='briefing':return await briefing_cli(args.data_dir)
    if c=='inbox':return await inbox_cli(args.data_dir)
    if c=='scheduler-tick':return await scheduler_cli(args.data_dir)
    if c=='watchers':return await watchers_cli(args.data_dir)
    if c=='hq':
        rt=await start_product_runtime(args.data_dir)
        try:print(json.dumps(rt.hq.snapshot(),ensure_ascii=False,indent=2));return 0
        finally:await rt.close()
    if c in {'ui','hq-web'}:
        await serve_hq(
            args.data_dir,start_page='/' if c=='ui' else '/hq',
            open_browser=not args.no_open
        );return 0
    if c=='worker':
        await serve_worker(args.data_dir,args.host,args.port);return 0
    return await utility_command(args)


def main():
    args=parser().parse_args()
    try:raise SystemExit(asyncio.run(amain(args)))
    except KeyboardInterrupt:print('\nEncerrado.')


if __name__=='__main__':
    main()
