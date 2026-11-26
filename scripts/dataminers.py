import json, random, datetime, pathlib, uuid
p=pathlib.Path("progress.json")
d=json.loads(p.read_text(encoding="utf-8"))
g=next(x for x in d["groups"]["list"] if x["id"]=="dataminer-group")
history="\n".join(x["body"].lower() for x in g["messages"])
clues=[]
def walk(v,path):
    if isinstance(v,dict):
        for k,x in v.items(): walk(x,path+[k])
    elif isinstance(v,list):
        for i,x in enumerate(v): walk(x,path+[str(i)])
    elif isinstance(v,str) and v and len(v)<350:
        key=path[-1]
        if key.startswith("ID_") or key in ("name","plantId","zombieId","releaseAt","deliverAt","id"):
            if v.lower() not in history and not v.startswith("candy-"):
                clues.append((".".join(path),v))
for k in ("hiddenReferences","releaseSchedule","upcomingUpdates","customZombiePlan","customRoster","plantPass","achievements"):
    walk(d.get(k,{}),[k])
if not clues or random.random()<0.25:
    print("Investigation completed; no new finding posted.")
    raise SystemExit(0)
path,value=random.choice(clues)
member=random.choice(g["members"])
body=random.choice(["Found something in {path}: {value}. Not sure what it means yet.","Interesting reference in {path}: {value}. This is file evidence, not an announcement.","Anyone seen this? {path} contains {value}."]) .format(path=path,value=value)
now=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")
g["messages"].append(dict(id="datamine-"+uuid.uuid4().hex,senderId=member["id"],sender=member["name"],body=body,createdAt=now,replyTo=None))
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
