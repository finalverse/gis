#!/usr/bin/env python3
"""Admit reviewed FWD into the existing SpatialDB authored-asset pipeline.

This is an authored presentation publication. Its advisory navigation anchor does
not transform projected grid north to true ENU or establish a MutSea association.
The exact source FWD/CRS/provenance remains hash-pinned alongside the publication.
"""
import argparse,hashlib,json,pathlib,re,shutil,subprocess,time,uuid

def conjunctive_license(expressions):
    """Canonicalize AND-only expressions without changing their obligations.

    Preserve every original source expression in the pinned FWD. Unsupported
    OR/WITH expressions refuse rather than being flattened or relicensed.
    """
    atoms=set()
    for expression in expressions:
        if not isinstance(expression,str) or not 0<len(expression)<=8192:
            raise ValueError('License expression byte budget')
        tokens=re.findall(r'[A-Za-z0-9.+-]+|[()]|\S',expression)
        if len(tokens)>512:raise ValueError('License expression token budget')
        index=0
        def term(depth):
            nonlocal index
            if depth>24 or index>=len(tokens):raise ValueError('Invalid license expression')
            token=tokens[index];index+=1
            if token=='(':
                sequence(depth+1)
                if index>=len(tokens) or tokens[index]!=')':raise ValueError('License parentheses')
                index+=1
            elif re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+-]*',token) and token not in ['AND','OR','WITH']:
                atoms.add(token)
            else:raise ValueError('Only conjunctive source license expressions are supported')
        def sequence(depth):
            nonlocal index
            term(depth)
            while index<len(tokens) and tokens[index]=='AND':index+=1;term(depth)
        sequence(0)
        if index!=len(tokens):raise ValueError('Unsupported source license operator')
    result=' AND '.join(sorted(atoms))
    if not result or len(result)>128:raise ValueError('Canonical license exceeds SpatialDB profile')
    return result

def run(args,cwd=None):
    p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError('SpatialDB stage failed: '+p.stderr[-1600:])
    return p.stdout

def stage(definition,cas,validator,spatialdb,output,reviewed=False):
    if not reviewed:raise ValueError('A reviewed geographic export is required')
    definition,cas,spatialdb,output=map(lambda p:pathlib.Path(p).resolve(),[definition,cas,spatialdb,output])
    if output.exists():raise ValueError('Use a new stage directory')
    raw=definition.read_bytes();d=json.loads(raw)
    validation=json.loads(run([validator,'validate',definition,cas]))
    if len(d['assets'])!=1:raise ValueError('Initial connector admits one static geographic scene')
    a=d['assets'][0];t=a['transform'];frame=next(f for f in d['frames'] if f['id']==a['frame_id'])
    if frame['units']!='metre' or frame['kind']!='local_cartesian' or frame['axes'] not in ['east,north,up','east,grid_north,up']:raise ValueError('Unsupported source frame')
    if t!={'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}:raise ValueError('Initial connector requires an identity placement')
    if d.get('simulation_bindings'):raise ValueError('Cannot publish a simulation binding through the asset connector')
    output.mkdir(parents=True);shutil.copyfile(definition,output/'source.fwd.json');shutil.copyfile(cas/a['sha256'],output/'scene.glb')
    ns=uuid.UUID(d['definition_id']);key=hashlib.sha256(raw).hexdigest()
    uid=lambda suffix:str(uuid.uuid5(ns,suffix))
    fictional=a['classification']=='fictional';license=conjunctive_license(s['license'] for s in d['sources'])
    attribution=('FinalGIS/Studio derivative. '+('Imaginary Aetheria terrain.' if fictional else 'Ville de Montréal roof/road subsets (CC BY4.0), NRCan terrain (OGL-Canada2.0). Estimated heights, colors and widths; not surveyed architecture.')+' Exact CRS and provenance: FWD SHA256 '+key+'. Anchor advisory only; no world binding.')
    description={'schema_version':'spatialdb.authored-scene/v1','graph_id':uid('spatialdb-graph'),'root_entity_id':uid('presentation-root'),'owner_id':'alice','dataset_id':'finalgis-'+d['definition_id'],'label':'FinalGIS '+('Aetheria fictional geography' if fictional else 'Montréal derived geography')+' (authored presentation)','anchor':{'longitude':0 if fictional else -73.55350350168884,'latitude':0 if fictional else 45.507201203216475,'height_metres':0},'world_binding':None,'collision_tolerance_metres':0.1,'subtree_depth':6,'license':license,'attribution':attribution[:512],'packages':[{'id':'finalgis','path':'scene.glb','package_id':'finalgis.geography','version':str(d['version']),'license':license,'sha256':a['sha256']}],'placements':[{'name':'geography','package':'finalgis','translation':[0,0,0],'yaw_degrees':0,'scale':1}]}
    path=output/'spatialdb-scene.json';path.write_text(json.dumps(description))
    started=time.perf_counter()
    run(['node','--max-old-space-size=256',spatialdb/'workers/authored/ingest-gltf.mjs',path,output/'ingested'])
    compiled=json.loads(run(['node','--max-old-space-size=256',spatialdb/'workers/authored/scene-compiler.generated.mjs',output/'ingested/job.json',output/'store']))
    document=output/'store/scene-publications'/(compiled['graph']['version']+'.json')
    seal=json.loads(run(['cargo','run','--locked','--quiet','-p','spatialdb-types','--example','seal_publication','--',document,output/'store/objects','alice'],cwd=spatialdb))
    receipt={'schema':'finalgis.spatialdb-exchange/1','source_fwd_sha256':key,'source_world_id':d['world']['id'],'validation':validation,'graph_id':compiled['graph']['graph_id'],'version':compiled['graph']['version'],'document':str(document),'objects':str(output/'store/objects'),'seal_sha256':hashlib.sha256(json.dumps(seal,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'elapsed_ms':(time.perf_counter()-started)*1000,'publication':'offline_validated_spatialdb_asset_store','geographic_placement':'advisory_anchor_only; exact projected origin remains in source FWD; no geodesy conversion claimed','world_binding':None,'world_mutated':False}
    (output/'exchange.json').write_text(json.dumps(receipt,indent=2));return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--definition',required=True);p.add_argument('--cas',required=True);p.add_argument('--validator',required=True);p.add_argument('--spatialdb',required=True);p.add_argument('--output',required=True);p.add_argument('--reviewed',action='store_true');a=p.parse_args()
    print(json.dumps(stage(a.definition,a.cas,a.validator,a.spatialdb,a.output,a.reviewed)))
