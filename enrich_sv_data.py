#!/usr/bin/env python3
"""Augment an EXISTING build_sv_data.py snapshot, without broadening game-availability claims.
Downloads upstream PokéAPI CSV at build time. Does not auto-certify mechanics.
"""
import argparse, csv, io, json, time, urllib.request
from pathlib import Path

CSV_ROOT = 'https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/'

def rows_from_csv(name, local_csv_dir=None):
    if local_csv_dir:
        data=(Path(local_csv_dir)/f'{name}.csv').read_text(encoding='utf-8-sig')
    else:
        last=None
        for attempt in range(3):
            try:
                req=urllib.request.Request(CSV_ROOT+name+'.csv',headers={'User-Agent':'Pokemon-SV-Guide/1.2.2 data-audit'})
                with urllib.request.urlopen(req,timeout=40) as r: data=r.read().decode('utf-8-sig')
                break
            except Exception as e:
                last=e
                time.sleep(attempt+1)
        else:
            raise RuntimeError(f'Failed to download {name}.csv: {last}')
    return list(csv.DictReader(io.StringIO(data)))

def integer(s):
    try: return int(s)
    except (TypeError,ValueError): return None

def enrich(snapshot, moves, flavors=None, version_groups=None):
    assert snapshot.get('schema')==1 and len(snapshot.get('pokemon',[]))>=500
    catalog=snapshot['moves']
    move_by_id={integer(row.get('id')):row for row in moves}
    move_by_en={r.get('identifier'):r for r in moves}
    sv_id=None
    if version_groups:
        sv_id=next((integer(g.get('id')) for g in version_groups if g.get('identifier')=='scarlet-violet'),None)
    # Only localized text, NEVER pretend that a short flavor line is exact mechanics.
    flavor_map={}
    if flavors:
        for row in flavors:
            if integer(row.get('language_id'))!=12: continue
            move_id=integer(row.get('move_id'))
            vg_id=integer(row.get('version_group_id'))
            if move_id is None: continue
            text=' '.join((row.get('flavor_text') or '').split())
            if not text: continue
            if sv_id is not None and vg_id==sv_id:
                flavor_map[move_id]=(100,text)
            elif move_id not in flavor_map or flavor_map[move_id][0]< (vg_id or 0):
                # Only fallback if no exact SV line exists.
                flavor_map[move_id]=(vg_id or 0,text)
    enhanced=0; localized=0
    for en,record in catalog.items():
        row=move_by_en.get(en)
        if not row: continue
        pp=integer(row.get('pp'))
        if pp is not None: record['pp']=pp;enhanced+=1
        priority=integer(row.get('priority'))
        if priority is not None: record['priority']=priority
        # PokeAPI CSV empty accuracy means 'not applicable/always hits under usual conditions'.
        # Do NOT relabel it as 100%.
        accuracy=integer(row.get('accuracy'))
        record['accuracy']=accuracy
        move_id=integer(row.get('id'))
        entry=flavor_map.get(move_id)
        if entry:
            record['flavorZh']=entry[1]
            record['flavorVersion']='scarlet-violet' if sv_id is not None and entry[0]==100 else 'other-generation-needs-review'
            localized+=1
    coverage=snapshot.setdefault('coverage',{})
    coverage['movePpEntries']=enhanced
    coverage['moveFlavorZhEntries']=localized
    coverage['moveMechanicsVerified']='curated-only; no automated battle-mechanics claims'
    return enhanced,localized

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--coverage',required=True)
    parser.add_argument('--csv-dir',default=None,help='offline fixture directory for testing')
    args=parser.parse_args()
    path=Path(args.input)
    snapshot=json.loads(path.read_text('utf-8'))
    moves=rows_from_csv('moves',args.csv_dir)
    # Optional description source: failures are reported but do not block PP enhancement.
    flavors=groups=None
    try:
        flavors=rows_from_csv('move_flavor_text',args.csv_dir)
        groups=rows_from_csv('version_groups',args.csv_dir)
    except (OSError,RuntimeError,UnicodeError) as e:
        print('WARNING: localized flavor descriptions unavailable:',str(e))
    enhanced,localized=enrich(snapshot,moves,flavors,groups)
    if enhanced<350:
        raise ValueError('PP coverage gate failed: fewer than 350 existing moves enriched; refusing to publish')
    path.write_text(json.dumps(snapshot,ensure_ascii=False,separators=(',',':')),'utf-8')
    cpath=Path(args.coverage)
    coverage=json.loads(cpath.read_text('utf-8')) if cpath.exists() else {}
    coverage.update({'movePpEntries':enhanced,'moveFlavorZhEntries':localized,'moveMechanicsVerified':'curated-only'})
    cpath.write_text(json.dumps(coverage,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({'baseMoveEntries':len(snapshot['moves']),'ppEnriched':enhanced,'zhFlavor':localized},ensure_ascii=False))
if __name__=='__main__':main()
