#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read a pinned SpatialDB authored publication into the canonical FWD profile.

Only finest, static, untextured leaf geometry is admitted. Bind verified material
factors into new derived GLBs; retain the received bytes and unchanged BIN hashes.
The exact source FWD frame is retained. No advisory Earth anchor is reinterpreted
as a geographic transform or permission to create a MutSea entity.
"""
import argparse,copy,hashlib,json,os,pathlib,re,stat,struct,subprocess,time,urllib.request,urllib.parse,uuid

def digest(data):return hashlib.sha256(data).hexdigest()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def bind_material(raw,material):
    if len(raw)<28 or struct.unpack_from('<III',raw)!=(0x46546c67,2,len(raw)):raise ValueError('Invalid GLB')
    length,kind=struct.unpack_from('<II',raw,12)
    if kind!=0x4e4f534a or length%4 or length+28>len(raw):raise ValueError('Invalid GLB JSON')
    doc=json.loads(raw[20:20+length]);tail=raw[20+length:]
    if len(tail)<8 or struct.unpack_from('<II',tail)!=(len(tail)-8,0x004e4942):raise ValueError('Invalid BIN chunk')
    if len(doc.get('meshes',[]))!=1 or len(doc['meshes'][0]['primitives'])!=1:raise ValueError('One primitive per published leaf required')
    if any(material.get(k) is not None for k in ['base_color_texture','normal_texture','metallic_roughness_texture','occlusion_texture','emissive_texture']):raise ValueError('Textured leaf requires another profile')
    doc['materials']=[{'pbrMetallicRoughness':{'baseColorFactor':material['base_color_factor'],'metallicFactor':material['metallic_factor'],'roughnessFactor':material['roughness_factor']},'doubleSided':material['double_sided'],'emissiveFactor':material['emissive_factor']}]
    doc['meshes'][0]['primitives'][0]['material']=0
    encoded=json.dumps(doc,separators=(',',':'),allow_nan=False).encode();encoded+=b' '*((-len(encoded))%4)
    derived=struct.pack('<III',0x46546c67,2,20+len(encoded)+len(tail))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+tail
    assert derived[-len(tail):]==tail
    return derived,digest(tail[8:])

def readback(endpoint,token_file,graph_id,version,expected_sha,source_fwd,validator,output):
    parsed=urllib.parse.urlsplit(endpoint)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ['', '/']:raise ValueError('Explicit loopback HTTP service required')
    graph_id=str(uuid.UUID(graph_id))
    if not re.fullmatch('[a-f0-9]{64}',version) or not re.fullmatch('[a-f0-9]{64}',expected_sha):raise ValueError('Publication digests required')
    token_file=pathlib.Path(token_file);s=token_file.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077 or s.st_size>4096:raise ValueError('Owned private token file required')
    token=token_file.read_text().strip()
    if not token or any(c in token for c in '\r\n\0'):raise ValueError('Invalid token file')
    source=pathlib.Path(source_fwd).read_bytes()
    if len(source)>1048576:raise ValueError('FWD size budget')
    fwd=json.loads(source);output=pathlib.Path(output)
    if output.exists():raise ValueError('New output directory required')
    base=endpoint.rstrip('/')+f'/v1/scene-graphs/{graph_id}/versions/{version}'
    opener=urllib.request.build_opener(NoRedirect)
    def get(suffix,expected,size=None):
        req=urllib.request.Request(base+suffix,headers={'Authorization':'Bearer '+token,'Accept-Encoding':'identity'})
        with opener.open(req,timeout=5) as response:
            if response.status!=200:raise ValueError('Unexpected HTTP response')
            raw=response.read(4194305)
        if len(raw)>4194304 or digest(raw)!=expected or (size is not None and len(raw)!=size):raise ValueError('Published object integrity failure')
        return raw
    start=time.perf_counter();graph_raw=get('/graph.json',expected_sha);graph=json.loads(graph_raw)
    if graph.get('schema_version')!='spatialdb.scene-graph/v2' or graph.get('world_binding') is not None or graph.get('unit')!='metre':raise ValueError('Unbound authored metre publication required')
    if graph.get('graph_id')!=graph_id or graph.get('version')!=version:raise ValueError('Publication identity mismatch')
    if any('subtree' in c for c in graph['cells']):raise ValueError('External subtrees require a subsequent streaming profile')
    if digest(source) not in graph.get('provenance',{}).get('source',''):raise ValueError('Original FWD provenance not bound by publication')
    if len(fwd['assets'])!=1 or fwd.get('simulation_bindings'):raise ValueError('Single source scene without simulation binding required')
    original=fwd['assets'][0];frame=next(f for f in fwd['frames'] if f['id']==original['frame_id'])
    if frame['kind']!='local_cartesian' or frame['units']!='metre' or frame['axes'] not in ['east,grid_north,up','east,north,up']:raise ValueError('Unsupported original frame')
    if original['transform']!={'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}:raise ValueError('Identity source placement required')
    leaves=[c for c in graph['cells'] if c.get('entity_id') and c['geometric_error']==0]
    if not 1<=len(leaves)<=64:raise ValueError('Finest leaf budget')
    materials={m['material_id']:m for m in graph['materials']}
    output.mkdir(parents=True);(output/'objects').mkdir();(output/'received').mkdir();assets=[];maps=[];total=0
    (output/'received/graph.json').write_bytes(graph_raw)
    for n,cell in enumerate(leaves):
        rep=next(r for r in cell['representations'] if r['family']=='visual' and r['geometric_error']==0)
        a=rep['asset'];sha=a['sha256']
        if not re.fullmatch('[a-f0-9]{64}',sha) or a['content_type']!='model/gltf-binary':raise ValueError('Static GLB reference required')
        raw=get('/assets/'+sha,sha,a['byte_length']);total+=len(raw)
        if total>64*1024*1024:raise ValueError('Scene byte budget')
        (output/'received'/sha).write_bytes(raw)
        derived,bin_sha=bind_material(raw,materials[rep['material_id']]);derived_sha=digest(derived);(output/'objects'/derived_sha).write_bytes(derived)
        # Re-publication retains earlier leaf provenance. Scope the new source
        # identity to this immutable publication/representation, not loop order.
        sid='spatialdb-leaf-'+digest((graph_id+':'+version+':'+rep['representation_id']).encode())[:40]
        if any(s['id']==sid for s in fwd['sources']):raise ValueError('Published leaf source identity collision')
        fwd['sources'].append({'id':sid,'uri':f'urn:spatialdb:{graph_id}:{version}:{sha}','sha256':sha,'license':graph['provenance']['license'],'version':version,'classification':'derived','attribution':graph['provenance']['source']})
        asset=copy.deepcopy(original);asset.update(id=str(uuid.uuid5(uuid.UUID(fwd['definition_id']),rep['representation_id'])),sha256=derived_sha,bytes=len(derived),source_ids=original['source_ids']+[sid],classification='derived');assets.append(asset)
        maps.append({'cell_id':cell['cell_id'],'representation_id':rep['representation_id'],'received_sha256':sha,'derived_material_glb_sha256':derived_sha,'unchanged_binary_sha256':bin_sha,'material_id':rep['material_id'],'triangles':rep['triangle_count']})
    fwd['assets']=assets;fwd['version']+=1;fwd.pop('semantics',None)
    fwd['generation']={'generator':'FinalGIS verified SpatialDB material binding','version':'0.1.0','seed':0,'operations':['read-pinned-authenticated-scene-graph','verify-finest-leaf-SHA-and-length','bind-published-scalar-materials-with-BIN-byte-preservation','preserve-original-FWD-projected-origin; ignore-advisory-Earth-anchor']}
    target=output/'world.fwd.json';target.write_text(json.dumps(fwd,indent=2,allow_nan=False)+'\n')
    checked=subprocess.run([str(validator),'validate',str(target),str(output/'objects')],check=True,capture_output=True,text=True,timeout=20)
    receipt={'schema':'finalgis.spatialdb-render-readback/1','graph_sha256':expected_sha,'source_fwd_sha256':digest(source),'materialized_fwd_sha256':digest(target.read_bytes()),'leaves':maps,'received_bytes':total,'elapsed_ms':(time.perf_counter()-start)*1000,'validation':json.loads(checked.stdout),'exact_frame_retained':True,'world_mutated':False,'scope':'authenticated publication readback; static presentation; advisory navigation anchor not used for placement'}
    (output/'readback.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();
    for k in ['endpoint','token-file','graph-id','version','expected-sha','source-fwd','validator','output']:p.add_argument('--'+k,required=True)
    a=p.parse_args();print(json.dumps(readback(a.endpoint,a.token_file,a.graph_id,a.version,a.expected_sha,a.source_fwd,a.validator,a.output)))
