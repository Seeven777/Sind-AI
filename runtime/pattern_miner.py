import json
from collections import Counter, defaultdict
from pathlib import Path


class PatternMiner:
    def __init__(self, action_log):
        self.action_log = Path(action_log)

    def _load(self, limit=500):
        if not self.action_log.exists():
            return []
        out=[]
        for line in self.action_log.read_text(encoding='utf-8', errors='replace').splitlines()[-int(limit):]:
            try:
                item=json.loads(line)
            except Exception:
                continue
            if not item.get('ok'):
                continue
            source=str(item.get('source',''))
            if source.startswith('skill:'):
                continue
            tool=item.get('tool')
            if not tool:
                continue
            # Diferencia ações brokered para que padrões como
            # browser.navigate -> website.seo_summary não virem apenas
            # execute_action -> execute_action.
            if tool == "execute_action":
                action_id = (item.get("args") or {}).get("action_id")
                if action_id:
                    item = dict(item)
                    item["pattern_tool"] = f"action:{action_id}"
            out.append(item)
        return out

    def suggest(self, min_repeats=2, min_length=2, max_length=5, limit=10):
        actions=self._load()
        if len(actions) < min_length * min_repeats:
            return {'ok': True, 'patterns': []}
        tool_seq=[a.get('pattern_tool') or a['tool'] for a in actions]
        counts=Counter()
        positions=defaultdict(list)
        for n in range(int(min_length), int(max_length)+1):
            for i in range(0, len(tool_seq)-n+1):
                seq=tuple(tool_seq[i:i+n])
                counts[seq]+=1
                positions[seq].append(i)
        candidates=[]
        for seq,count in counts.items():
            if count < int(min_repeats):
                continue
            # Avoid trivial repetitions of a single tool type only.
            if len(set(seq)) == 1:
                continue
            start=positions[seq][-1]
            example=actions[start:start+len(seq)]
            candidates.append({
                'tools': list(seq),
                'occurrences': count,
                'example_args': [x.get('args',{}) for x in example],
                'suggested_name': '_'.join(seq)[:80],
            })
        candidates.sort(key=lambda x:(-x['occurrences']*len(x['tools']), -len(x['tools'])))
        return {'ok': True, 'patterns': candidates[:int(limit)]}
