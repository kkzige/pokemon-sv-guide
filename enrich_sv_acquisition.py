#!/usr/bin/env python3
"""Offline-only curated SV acquisition overlay for an already-generated snapshot.

This script imports a small self-contained, versioned JSON source with provenance.
No network call, no blanket 'both versions', no inferred wild spawn or held item.
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path


def enrich(snapshot: dict, source: dict, *, strict=True) -> dict:
    if snapshot.get('schema') != 1 or source.get('schema') != 1:
        raise ValueError('Unexpected snapshot/acquisition schema')
    if not isinstance(snapshot.get('pokemon'), list):
        raise ValueError('Missing pokemon list')
    exclusive = source['exclusives']; habitats = source['habitats']; materials = source['tmMaterials']
    known_species={p.get('speciesEn',p.get('en')) for p in snapshot['pokemon']}
    known_forms={p['en'] for p in snapshot['pokemon']}
    if set(exclusive)&set(habitats) and any(exclusive[k]['native'] != habitats[k]['native'] for k in set(exclusive)&set(habitats) if 'native' in habitats[k]):
        raise ValueError('Contradictory habitat and version exclusive')
    for key,val in exclusive.items():
        if val.get('native') not in ('scarlet','violet') or val.get('scope') not in ('species','form'):
            raise ValueError('Bad version-exclusivity entry: '+key)
    for key,val in habitats.items():
        if not val.get('areas') or not val.get('source'):
            raise ValueError('Habitat lacks locations/source: '+key)
    inverted=defaultdict(list)
    for ident,record in materials.items():
        if not record.get('sources') or not record.get('source') or record.get('scope')!='sv-tm-crafting':
            raise ValueError('Bad TM material: '+ident)
        for species in record['sources']:
            inverted[species].append({'id':ident,'en':record['en'], 'zh':record.get('zh'), 'source':record['source'], 'purpose':record.get('purpose','tm-category')})
    extra_exclusive=0; extra_habitat=0; extra_material_species=set(); extra_material_links=0
    for p in snapshot['pokemon']:
        en=p['en']; sp=p.get('speciesEn',en)
        # Tauros family form and region are not interchangable. Exact form takes precedence.
        tag=exclusive.get(en)
        if tag and tag['scope']=='form':
            version=tag
        elif en==sp:
            version=exclusive.get(en)
        else:
            version=None
        habitat=habitats.get(en)
        # Exclude non-default regional forms from species-only drop claims.
        ds=inverted.get(en,[])
        if en=='wooper-paldea':ds=inverted.get('wooper-paldea',[])
        if en=='tauros':ds=[]
        if en.startswith('tauros-paldea-'):ds=inverted.get('tauros-paldea-combat-breed',[]) or inverted.get('tauros-paldea',[]) or inverted.get('tauros',[])
        if version or habitat or ds:
            p['svAcquisition']={'version':version,'habitat':habitat,'tmMaterials':ds}
            if version:extra_exclusive+=1
            if habitat:extra_habitat+=1
            if ds:extra_material_species.add(en);extra_material_links+=len(ds)
    cover=snapshot.setdefault('coverage',{})
    cover.update({'svNativeExclusiveForms':extra_exclusive, 'svVerifiedHabitatRecords':extra_habitat,
                  'svTmMaterialTypes':len(materials), 'svTmMaterialSpecies':len(extra_material_species),
                  'svTmMaterialLinks':extra_material_links,
                  'svAcquisitionNote':'Version native exclusivity, sampled wild sites and TM material sources are separate datasets; unverified entries remain unknown.'})
    if strict and (len(exclusive)<60 or len(materials)<170 or extra_exclusive<48 or len(extra_material_species)<250 or extra_habitat<20):
        raise ValueError('Acquisition coverage gate failed: '+str({k:cover[k] for k in ('svNativeExclusiveForms','svVerifiedHabitatRecords','svTmMaterialTypes','svTmMaterialSpecies')}))
    return cover


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--coverage',required=True);ap.add_argument('--data',default='sv_acquisition_data.json');ap.add_argument('--no-strict',action='store_true');args=ap.parse_args()
    f=Path(args.input); c=Path(args.coverage)
    s=json.loads(f.read_text(encoding='utf-8'))
    d=json.loads(Path(args.data).read_text(encoding='utf-8'))
    cv=enrich(s,d,strict=not args.no_strict)
    f.write_text(json.dumps(s,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    old=json.loads(c.read_text(encoding='utf-8')) if c.exists() else {}
    old.update({k:v for k,v in cv.items() if k.startswith('sv')})
    c.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in old.items() if k.startswith('sv')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
