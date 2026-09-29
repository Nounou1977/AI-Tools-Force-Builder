import json, hashlib, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT=Path(__file__).parent
DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
SEEN=DATA/"seen.json"; LATEST=DATA/"latest.json"

def load(p,d):
    try:return json.loads(p.read_text())
    except:return d

def fetch(url):
    r=Request(url,headers={"User-Agent":"Mozilla/5.0 RadarDemandes/1.0"})
    with urlopen(r,timeout=20) as x:return x.read()

def parse(url):
    root=ET.fromstring(fetch(url)); out=[]
    for item in root.findall(".//item"):
        out.append({
            "title":(item.findtext("title") or "").strip(),
            "link":(item.findtext("link") or "").strip(),
            "description":re.sub("<[^>]+>"," ",item.findtext("description") or "").strip(),
            "published":(item.findtext("pubDate") or "").strip()
        })
    return out

def score(x):
    t=(x["title"]+" "+x["description"]).lower()
    s=0
    groups=[
      (["urgent","asap","immediately","today","24 hours","right now"],25),
      (["budget","paid","pay","$","€","£"],15),
      (["automation","automate","workflow","agent","n8n","zapier","make.com","crm","integration"],25),
      (["freelance","project","hire","client","looking for","need"],15),
      (["invoice","report","data","lead","scraping","reconcile"],10)
    ]
    for words,pts in groups:
        if any(w in t for w in words): s+=pts
    return min(s,100)

seen=load(SEEN,{})
sources=load(ROOT/"sources.json",[])
new=[]
for src in sources:
    try:
        for x in parse(src["url"]):
            key=hashlib.sha256((x["link"] or x["title"]).encode()).hexdigest()
            if key in seen: continue
            x["source"]=src["name"]; x["score"]=score(x)
            x["detected_at"]=datetime.now(timezone.utc).isoformat()
            seen[key]=x["detected_at"]; new.append(x)
    except Exception as e:
        print("WARN",src["name"],e)

new.sort(key=lambda x:x["score"],reverse=True)
hot=[x for x in new if x["score"]>=85]
SEEN.write_text(json.dumps(seen,ensure_ascii=False,indent=2))
LATEST.write_text(json.dumps({"checked_at":datetime.now(timezone.utc).isoformat(),"new":len(new),"hot":hot[:20]},ensure_ascii=False,indent=2))
for x in hot[:10]:
    print(f"HOT|{x['score']}|{x['title']}|{x['link']}")
