def snapshot(agent):
    try: browser=agent.browser_agent.status()
    except Exception: browser={'running':False}
    try: selected=agent.deep_access.snapshot()
    except Exception: selected={'selected':False}
    try: kb=agent.knowledge.stats()
    except Exception: kb={}
    try: observe=agent.observe.status()
    except Exception: observe={}
    try: institutional=agent.institutional.execute('stats')
    except Exception: institutional={}
    try: ik=agent.institutional_knowledge.execute('stats')
    except Exception: ik={}
    try: training=agent.training.execute('stats')
    except Exception: training={}
    try: governance=agent.governance.execute('stats')
    except Exception: governance={}
    try: automations=agent.automations.stats()
    except Exception: automations={}
    try: monitors=agent.monitors.stats()
    except Exception: monitors={}
    try: approvals=agent.approvals.stats()
    except Exception: approvals={}
    try: notifications=agent.notifications.stats()
    except Exception: notifications={}
    try: connectors=agent.connectors.stats()
    except Exception: connectors={}
    try: team=agent.team.stats()
    except Exception: team={}
    return {
        'browser':{'running':browser.get('running',False),'url':browser.get('url'),'title':browser.get('title'),'pages':browser.get('pages',0)},
        'desktop_window':{'selected':selected.get('selected',False),'title':selected.get('title')},
        'knowledge':{'collections':kb.get('collections',0),'documents':kb.get('documents',0)},
        'institutional':{
            'profile_fields':institutional.get('profile_fields',0),
            'policies':institutional.get('policies',0),
            'style_rules':institutional.get('style_rules',0),
            'ccts':ik.get('ccts',0),
            'clauses':ik.get('clauses',0),
        },
        'training':{'tracks':training.get('tracks',0),'learners':training.get('learners',0)},
        'governance':{'safe_mode':(governance.get('modes') or {}).get('safe_mode','on'),'connectors':governance.get('connectors',0)},
        'autonomy':{
            'jobs':automations.get('jobs',0),
            'automation_statuses':automations.get('statuses',{}),
            'monitors':monitors.get('monitors',0),
            'monitor_events_pending':monitors.get('pending_events',0),
            'approvals_pending':(approvals.get('statuses') or {}).get('pending',0),
            'notifications_unread':(notifications.get('statuses') or {}).get('unread',0),
        },
        'external_connectors':{'configured':connectors.get('connectors',0),'enabled':connectors.get('enabled',0),'endpoints':connectors.get('endpoints',0)},
        'team_assistant':{'users':team.get('users',0),'active_users':team.get('active_users',0),'knowledge_gaps_open':team.get('knowledge_gaps_open',0)},
        'observation':{'active':observe.get('active',False),'session_id':observe.get('session_id')},
    }
