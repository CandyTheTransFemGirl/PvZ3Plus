import json,zipfile,struct,base64,sys,collections,pathlib
def var(b,p):
 v=0
 for i in range(10):
  x=b[p];p+=1;v|=(x&127)<<(7*i)
  if x<128:return v,p
 raise ValueError('varint overflow')
def wire(b):
 p=0
 while p<len(b):
  k,p=var(b,p);n,w=k>>3,k&7
  if not n:raise ValueError('zero field')
  if w==0:v,p=var(b,p)
  elif w in (1,2,5):
   if w==2:l,p=var(b,p)
   else:l={1:8,5:4}[w]
   if p+l>len(b):raise ValueError('truncated')
   v=b[p:p+l];p+=l
  else:raise ValueError('wire '+str(w))
  yield n,w,v
def run(schema,source,out):
 s=json.loads(pathlib.Path(schema).read_text());types=s['types']
 def raw(w,v):return v if w==0 else {'base64':base64.b64encode(v).decode()}
 def value(k,t,e,w,v):
  if k=='message' and w==2:return msg(t,v)
  if k=='enum' and w==0:return {'number':v,'name':next((x['name'] for x in types[t]['values'] if x['number']==v),None)}
  if k=='scalar':
   if e=='string' and w==2:return v.decode('utf8')
   if e=='ByteString' and w==2:return raw(w,v)
   if e in ('float','double') and w==({'float':5,'double':1}[e]):return struct.unpack('<f' if e=='float' else '<d',v)[0]
   if w==0 and e in ('int','long','uint','ulong','bool'):
    if e=='bool':return bool(v)
    if e in ('int','long'):
     bits=32 if e=='int' else 64;v&=(1<<bits)-1
     if v>>(bits-1):v-=1<<bits
    return v
  raise ValueError('type/wire mismatch')
 def msg(t,b):
  fs={f['number']:f for f in types[t]['fields']};d={}
  for n,w,v in wire(b):
   f=fs[n];k,e,r=f['type_kind'],f['element_type'],f['type_ref'];name=f['name'];repeated=f['cardinality']!='singular'
   if k=='map' and w==2:
    a={}
    for i,j,u in wire(v):
     side='key' if i==1 else 'value';a[side]=value(f['map_'+side+'_type_kind'],f['map_'+side+'_type_ref'],f[side+'_type'],j,u)
    vals=[a]
   elif repeated and w==2 and (k=='enum' or k=='scalar' and e not in ('string','ByteString')):
    vals=[];p=0;pw=5 if e=='float' else 1 if e=='double' else 0
    while p<len(v):
     if pw:l=4 if pw==5 else 8;u=v[p:p+l];p+=l
     else:u,p=var(v,p)
     vals.append(value(k,r,e,pw,u))
   else:vals=[value(k,r,e,w,v)]
   if repeated:d.setdefault(name,[]).extend(vals)
   else:d[name]=vals[0]
  return d
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);report={}
 files=sorted(pathlib.Path(source).glob('*.data'))
 if len(files)!=14:raise ValueError('Expected 14 databases')
 for p in files:
  d=msg(s['unique_message_roots'][p.stem],p.read_bytes())
  (out/(p.stem+'.json')).write_text(json.dumps(d,ensure_ascii=False,allow_nan=False))
  report[p.stem]={k:len(v) for k,v in d.items() if isinstance(v,list)}
  print(p.stem,report[p.stem])
 (out/'report.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':run(*sys.argv[1:])
