
import json,uuid,urllib.request,urllib.parse,urllib.error
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from kp_engine.core import calculate,ruling_planets,transit_comparison,drill_dasha,horary_chart,zodiac_nakshatra_reference
B=Path(__file__).parent;app=FastAPI(title="KP Local Testing Tool")

DATA_DIR=B/"data";DATA_DIR.mkdir(exist_ok=True)
KUNDALI_FILE=DATA_DIR/"kundalis.json"
def _load_kundalis():
 if KUNDALI_FILE.exists():
  try:return json.loads(KUNDALI_FILE.read_text(encoding="utf-8"))
  except Exception:return []
 return []
def _save_kundalis(items):
 KUNDALI_FILE.write_text(json.dumps(items,indent=2),encoding="utf-8")

CONFIG_FILE=DATA_DIR/"config.json"
def _load_config():
 if CONFIG_FILE.exists():
  try:return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
  except Exception:return {}
 return {}
def _save_config(cfg):
 CONFIG_FILE.write_text(json.dumps(cfg,indent=2),encoding="utf-8")

def geocode_search(query,limit=8):
 """Looks up a place name via OpenStreetMap Nominatim and returns candidate
 locations with name/district/state/country and coordinates. Requires internet
 access at search time (unlike the offline KP calculations)."""
 url="https://nominatim.openstreetmap.org/search?"+urllib.parse.urlencode(
  {"q":query,"format":"jsonv2","addressdetails":1,"limit":limit,"accept-language":"en"})
 req=urllib.request.Request(url,headers={"User-Agent":"KP-Local-Testing-Tool/2.3 (local desktop app)"})
 with urllib.request.urlopen(req,timeout=8) as resp:
  data=json.loads(resp.read().decode("utf-8"))
 out=[]
 for item in data:
  addr=item.get("address",{})
  primary=(addr.get("village") or addr.get("town") or addr.get("city") or addr.get("municipality")
    or addr.get("suburb") or addr.get("county") or item.get("display_name","").split(",")[0]).strip()
  district=addr.get("state_district") or (addr.get("county") if addr.get("county")!=primary else None)
  state=addr.get("state");country=addr.get("country")
  sub_parts=[p for p in [district,state,country] if p and p!=primary]
  seen=[];sub_label=[]
  for p in sub_parts:
   if p not in seen:seen.append(p);sub_label.append(p)
  out.append({"name":primary,"district":district,"state":state,"country":country,
    "sub_label":", ".join(sub_label),"display_name":item.get("display_name"),
    "latitude":float(item["lat"]),"longitude":float(item["lon"])})
 return out
class Birth(BaseModel):
 name:str="";date:str;time:str;latitude:float;longitude:float;timezone:float=5.5
class Moment(BaseModel):
 date:str;time:str;latitude:float;longitude:float;timezone:float=5.5
class TransitReq(BaseModel):
 birth:Birth;transit:Moment
class DrillReq(BaseModel):
 birth:Birth;chain:list[str];levels:int=1
@app.post("/api/calculate")
def calc(b:Birth):
 try:return calculate(b.model_dump())
 except Exception as e:raise HTTPException(400,str(e))
@app.post("/api/ruling_planets")
def rp(m:Moment):
 try:return ruling_planets(m.model_dump())
 except Exception as e:raise HTTPException(400,str(e))
@app.post("/api/transit")
def tr(t:TransitReq):
 try:return transit_comparison(t.birth.model_dump(),t.transit.model_dump())
 except Exception as e:raise HTTPException(400,str(e))
@app.post("/api/dasha_drill")
def dd(d:DrillReq):
 try:
  r=calculate(d.birth.model_dump())
  utc=datetime.fromisoformat(r["utc"].replace("Z",""))
  moon_lon=r["planets"]["Moon"]["longitude"]
  return {"periods":drill_dasha(d.chain,utc,moon_lon,d.levels)}
 except Exception as e:raise HTTPException(400,str(e))
@app.get("/api/geocode")
def geocode(q:str=""):
 q=(q or "").strip()
 if len(q)<2:return {"results":[]}
 try:return {"results":geocode_search(q)}
 except Exception as e:raise HTTPException(400,f"Place search failed (needs internet): {e}")
class KundaliReq(BaseModel):
 name:str="";date:str;time:str;latitude:float;longitude:float;timezone:float=5.5
@app.get("/api/kundalis")
def list_kundalis():
 return {"kundalis":_load_kundalis()}
@app.post("/api/kundalis")
def save_kundali(k:KundaliReq):
 items=_load_kundalis()
 rec={"id":str(uuid.uuid4()),"name":k.name,"date":k.date,"time":k.time,
   "latitude":k.latitude,"longitude":k.longitude,"timezone":k.timezone,
   "saved_at":datetime.utcnow().isoformat()+"Z"}
 items.append(rec);_save_kundalis(items)
 return rec
@app.delete("/api/kundalis/{kid}")
def delete_kundali(kid:str):
 items=_load_kundalis()
 items=[i for i in items if i["id"]!=kid]
 _save_kundalis(items)
 return {"ok":True}

class ConfigReq(BaseModel):
 api_key:str
@app.get("/api/config")
def get_config():
 cfg=_load_config()
 return {"has_key":bool(cfg.get("api_key"))}
@app.post("/api/config")
def set_config(c:ConfigReq):
 cfg=_load_config();cfg["api_key"]=c.api_key.strip();_save_config(cfg)
 return {"ok":True}

class AIInsightReq(BaseModel):
 name:str="";date:str;time:str;latitude:float;longitude:float;timezone:float=5.5;concerns:str=""
@app.post("/api/ai_insights")
def ai_insights(r:AIInsightReq):
 cfg=_load_config();api_key=cfg.get("api_key")
 if not api_key:
  raise HTTPException(400,"No Claude API key saved yet. Save one in the Full Report tab first (console.anthropic.com se milegi).")
 try:
  chart=calculate({"name":r.name,"date":r.date,"time":r.time,"latitude":r.latitude,"longitude":r.longitude,"timezone":r.timezone})
 except Exception as e:
  raise HTTPException(400,f"Could not calculate chart: {e}")
 md=chart["predictions"]["mahadasha"];ad=chart["predictions"].get("antardasha")
 lines=[f"Ascendant: {chart['ascendant']['sign']}",
   f"Moon: {chart['planets']['Moon']['sign']} ({chart['planets']['Moon']['nakshatra']})",
   f"Current Mahadasha: {md['lord']} ({md['sentiment']}, houses {md['houses']})"]
 if ad: lines.append(f"Current Antardasha: {ad['lord']} ({ad['sentiment']}, houses {ad['houses']})")
 if r.concerns.strip(): lines.append(f"Client's stated concerns: {r.concerns.strip()}")
 prompt=("You are a Vedic (KP) astrology assistant helping write one section of a client-facing report. "
   "Based on the chart summary below, write a warm, clear, 120-180 word paragraph of additional insight "
   "for the client in plain everyday language (avoid jargon dumps), connecting the current dasha period "
   "with the client's stated concerns if given. Interpret the data, don't just repeat it back.\n\n"+"\n".join(lines))
 try:
  body=json.dumps({"model":"claude-haiku-4-5-20251001","max_tokens":400,
    "messages":[{"role":"user","content":prompt}]}).encode("utf-8")
  req=urllib.request.Request("https://api.anthropic.com/v1/messages",data=body,headers={
    "x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"})
  with urllib.request.urlopen(req,timeout=30) as resp:
   data=json.loads(resp.read().decode("utf-8"))
  text="".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
  if not text: raise ValueError("Empty response from Claude API")
  return {"insight":text}
 except urllib.error.HTTPError as e:
  detail=e.read().decode("utf-8","ignore")
  raise HTTPException(400,f"Claude API error ({e.code}): {detail[:300]}")
 except Exception as e:
  raise HTTPException(400,f"Could not reach Claude API: {e}")

class HoraryReq(BaseModel):
 number:int;date:str;latitude:float;longitude:float;timezone:float=5.5;mode:str="manual";name:str=""
@app.post("/api/horary")
def horary(h:HoraryReq):
 if not (1<=h.number<=249):
  raise HTTPException(400,"Horary number must be between 1 and 249")
 try:
  r=horary_chart(h.number,h.date,h.latitude,h.longitude,h.timezone,label=h.name or "Horary Query")
  r["horary"]["mode"]=h.mode
  return r
 except Exception as e:
  raise HTTPException(400,str(e))

@app.get("/api/reference")
def reference():
 return zodiac_nakshatra_reference()

app.mount("/static",StaticFiles(directory=B/"static"),name="static")
@app.get("/")
def home():return FileResponse(B/"static/index.html")
