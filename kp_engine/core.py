
from datetime import datetime,timedelta
from collections import Counter
SIGNS=["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_LORDS={"Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon","Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars","Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"}
NAKS=["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
ORDER=["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]; YEARS={"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,"Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}
SPAN=360/27
def norm(x): return x%360
def dms(x):
 x=norm(x);d=int(x);m=int((x-d)*60);s=((x-d)*60-m)*60;return f"{d:03d}°{m:02d}′{s:05.2f}″"
def stellar(lon):
 lon=norm(lon);si=int(lon//30);ni=min(26,int(lon//SPAN));inside=lon-ni*SPAN;star=(ORDER*3)[ni]
 def sub(off,span,start):
  idx=ORDER.index(start);cur=0
  for k in range(9):
   lord=ORDER[(idx+k)%9];w=span*YEARS[lord]/120
   if off<cur+w or k==8:return lord,off-cur,w
   cur+=w
 sl,off,w=sub(inside,SPAN,star);ssl,_,_=sub(off,w,sl)
 return {"longitude":lon,"dms":dms(lon),"sign":SIGNS[si],"degree_in_sign":lon-si*30,"sign_lord":SIGN_LORDS[SIGNS[si]],"nakshatra":NAKS[ni],"pada":min(4,int(inside//(SPAN/4))+1),"star_lord":star,"sub_lord":sl,"sub_sub_lord":ssl}
def calculate(p):
 import swisseph as swe
 y,m,d=map(int,p["date"].split("-"));parts=list(map(int,p["time"].split(":")));hh,mm=parts[:2];sec=parts[2] if len(parts)>2 else 0
 utc=datetime(y,m,d,hh,mm,sec)-timedelta(hours=float(p.get("timezone",5.5)));hour=utc.hour+utc.minute/60+utc.second/3600
 jd=swe.julday(utc.year,utc.month,utc.day,hour);lat=float(p["latitude"]);lon=float(p["longitude"]);swe.set_sid_mode(swe.SIDM_LAHIRI)
 flags=swe.FLG_SWIEPH|swe.FLG_SIDEREAL|swe.FLG_SPEED
 ids={"Sun":swe.SUN,"Moon":swe.MOON,"Mars":swe.MARS,"Mercury":swe.MERCURY,"Jupiter":swe.JUPITER,"Venus":swe.VENUS,"Saturn":swe.SATURN,"Rahu":swe.MEAN_NODE}
 planets={}
 for name,pid in ids.items():
  res=swe.calc_ut(jd,pid,flags);xx=res[0]
  planets[name]={**stellar(xx[0]),"speed":xx[3],"retrograde":xx[3]<0}
 kl=norm(planets["Rahu"]["longitude"]+180);planets["Ketu"]={**stellar(kl),"speed":planets["Rahu"]["speed"],"retrograde":True}
 hres=swe.houses_ex(jd,lat,lon,b'P',0);tropical=hres[0];ay=swe.get_ayanamsa_ut(jd)
 # pysweph >=2.10.3.4 returns house cusps with an empty/index-0 entry.
 # Older pyswisseph returned exactly 12 cusps. Normalize both layouts.
 tropical=list(tropical)
 if len(tropical)==13:
  tropical=tropical[1:]
 if len(tropical)!=12:
  raise ValueError(f"Swiss Ephemeris returned {len(tropical)} house cusps; expected 12")
 cusps=[{"house":i,**stellar(norm(c-ay))} for i,c in enumerate(tropical,1)]
 dasha=vimshottari_dasha(planets["Moon"]["longitude"],utc)
 sequence=significator_sequence(planets,cusps)
 aspects=aspect_hits(planets,cusps)
 for name,node in sequence.items():
  star_lord=planets[name]["star_lord"]
  if star_lord==name:
   status="Self"
  else:
   # Tenanted (T): this planet is the star lord (nakshatra lord) of at least one
   # OTHER PLANET (house cusps are not counted). Untenanted (UT): it is not the
   # star lord of any other planet.
   is_tenanted=any(pn!=name and pl["star_lord"]==name for pn,pl in planets.items())
   status="T" if is_tenanted else "UT"
  planets[name]["tenancy"]=status
  planets[name]["signifies_houses"]=node["planet_houses"]
 asc_sign_idx=int(norm(cusps[0]["longitude"])//30)
 for name,pl in planets.items():
  pl["house_d1"]=whole_sign_house(pl["longitude"],asc_sign_idx)
  pl["house_kp"]=house_of(pl["longitude"],cusps)
 pnch=panchang(planets["Sun"]["longitude"],planets["Moon"]["longitude"],utc,lat,lon,float(p.get("timezone",5.5)))
 gemstone=gemstone_analysis(planets,asc_sign_idx)
 predictions=predictions_for_chart(dasha,sequence,utc,planets["Moon"]["longitude"])
 house_narratives=house_lord_narratives(planets,asc_sign_idx)
 vastu=vastu_directions(asc_sign_idx)
 hit_remedies=hit_theory_remedies(planets,aspects,dasha,utc)
 return {"input":p,"utc":utc.isoformat()+"Z","julian_day":jd,"ayanamsa":ay,"ayanamsa_dms":dms(ay),"ascendant":cusps[0],"planets":planets,"cusps":cusps,"dasha":dasha,"sequence":sequence,"aspects":aspects,"panchang":pnch,"gemstone":gemstone,"predictions":predictions,"house_narratives":house_narratives,"vastu":vastu,"hit_remedies":hit_remedies}

YEAR_DAYS=365.2425
def _level(start_lord,start_date,total_years,elapsed_fraction,depth):
 idx0=ORDER.index(start_lord);cursor=start_date;out=[]
 for k in range(9):
  lord=ORDER[(idx0+k)%9];yrs=total_years*YEARS[lord]/120
  if k==0 and elapsed_fraction>0: yrs=yrs*(1-elapsed_fraction)
  end=cursor+timedelta(days=yrs*YEAR_DAYS)
  node={"lord":lord,"start":cursor.date().isoformat(),"end":end.date().isoformat(),"years":round(yrs,4)}
  if depth>1: node["antardasha"]=_level(lord,cursor,yrs,0,depth-1)
  out.append(node);cursor=end
 return out

def vimshottari_dasha(moon_lon,birth_dt,depth=2):
 moon_lon=norm(moon_lon);ni=min(26,int(moon_lon//SPAN));star_lord=(ORDER*3)[ni]
 frac_elapsed=(moon_lon-ni*SPAN)/SPAN
 mahadasha=_level(star_lord,birth_dt,120,frac_elapsed,depth)
 return {"birth_nakshatra_lord":star_lord,"mahadasha":mahadasha}

def drill_dasha(chain,birth_dt,moon_lon,levels=2):
 """chain: list of lords already chosen e.g. ['Saturn','Mars'] (Mahadasha->Antardasha lord already known).
 Returns the next `levels` of sub-periods, computed fresh from the top so dates line up exactly
 with vimshottari_dasha()."""
 moon_lon=norm(moon_lon);ni=min(26,int(moon_lon//SPAN));star_lord=(ORDER*3)[ni]
 frac_elapsed=(moon_lon-ni*SPAN)/SPAN
 nodes=_level(star_lord,birth_dt,120,frac_elapsed,1)
 cur=next(n for n in nodes if n["lord"]==chain[0])
 cur_start=datetime.fromisoformat(cur["start"]);cur_years=cur["years"];cur_lord=cur["lord"]
 for lord in chain[1:]:
  sub=_level(cur_lord,cur_start,cur_years,0,1)
  cur=next(n for n in sub if n["lord"]==lord)
  cur_start=datetime.fromisoformat(cur["start"]);cur_years=cur["years"];cur_lord=cur["lord"]
 return _level(cur_lord,cur_start,cur_years,0,levels)

# ---------------- Significator Sequence ----------------
ASPECT_HOUSES={"Mars":[4,7,8],"Jupiter":[5,7,9],"Saturn":[3,7,10]}  # classical Vedic special drishti (from-house counted)

def house_of(lon,cusps):
 lon=norm(lon);n=len(cusps)
 for i in range(n):
  a=cusps[i]["longitude"];b=cusps[(i+1)%n]["longitude"]
  if a<b:
   if a<=lon<b: return cusps[i]["house"]
  else:
   if lon>=a or lon<b: return cusps[i]["house"]
 return cusps[-1]["house"]

def significator_sequence(planets,cusps):
 occ={name:house_of(p["longitude"],cusps) for name,p in planets.items()}
 owned={name:[c["house"] for c in cusps if c["sign_lord"]==name] for name in planets}

 def simple_houses(pname):
  return sorted(set([occ[pname]])|set(owned.get(pname,[])))

 def node_sources(name):
  sign=planets[name]["sign"];rashi_lord=SIGN_LORDS[sign]
  sources=[{"type":"Own house","via":name,"houses":[occ[name]]},
           {"type":"Rashi lord","via":rashi_lord,"houses":simple_houses(rashi_lord)}]
  for other in planets:
   if other!=name and occ[other]==occ[name]:
    sources.append({"type":"Conjunct","via":other,"houses":simple_houses(other)})
  my_sign_idx=int(norm(planets[name]["longitude"])//30)
  for aspector in planets:
   if aspector==name or aspector in ("Rahu","Ketu"): continue
   houses_from=ASPECT_HOUSES.get(aspector,[7])
   asp_sign_idx=int(norm(planets[aspector]["longitude"])//30)
   target_signs=[(asp_sign_idx+h-1)%12 for h in houses_from]
   if my_sign_idx in target_signs:
    sources.append({"type":"Vedic aspect","via":aspector,"houses":simple_houses(aspector)})
  return sources

 def base_signif(pname):
  if pname in ("Rahu","Ketu"):
   return sorted(set(sum([s["houses"] for s in node_sources(pname)],[])))
  return simple_houses(pname)

 seq={}
 for name in planets:
  star_lord=planets[name]["star_lord"];sub_lord=planets[name]["sub_lord"]
  star_of_sub=planets[sub_lord]["star_lord"] if sub_lord in planets else sub_lord
  own_houses=base_signif(name)
  sl_houses=base_signif(star_lord)
  subl_houses=base_signif(sub_lord)
  ssl_houses=base_signif(star_of_sub)
  combined=sorted(set(own_houses+sl_houses+subl_houses+ssl_houses))
  # Fruitful Significators: a house number that repeats across more than one of the
  # 4 significator sub-lists (Planet / Star Lord / Sub Lord / Star of Sub) is treated
  # as a stronger, "fruitful" signification for that planet.
  counts=Counter(own_houses+sl_houses+subl_houses+ssl_houses)
  fruitful=sorted([h for h,c in counts.items() if c>1])
  node={"planet":name,"planet_houses":own_houses,"star_lord":star_lord,"star_lord_houses":sl_houses,
        "sub_lord":sub_lord,"sub_lord_houses":subl_houses,"star_of_sub":star_of_sub,"star_of_sub_houses":ssl_houses,
        "combined":combined,"fruitful":fruitful}
  if name in ("Rahu","Ketu"):
   node["signification_sources"]=node_sources(name)
  seq[name]=node
 return seq

# ---------------- Aspect Hit System ----------------
# Both positive and negative hits are named by which classical angle they sit
# near: ~30/60/120 deg (positive) and ~45/90/180 deg (negative).
POS_RANGES=[(27,33,"Semi-Sextile Hit"),(55,65,"Sextile Hit"),(112,128,"Trine Hit")]
NEG_RANGES=[(42,48,"Minor Hit"),(85,95,"Major Hit"),(172,188,"Killer Hit")]

def _classify(diff):
 d=diff%360
 if d>180: d=360-d
 for lo,hi,band in POS_RANGES:
  if lo<=d<=hi: return "+",round(d,2),band
 for lo,hi,band in NEG_RANGES:
  if lo<=d<=hi: return "-",round(d,2),band
 return None,round(d,2),None

def aspect_hits(planets,cusps):
 order=[n for n in sorted(planets.keys(),key=lambda n:planets[n]["longitude"]) if n!="Rahu"]
 pp=[];ph=[]
 for i in range(len(order)):
  for j in range(i+1,len(order)):
   a,b=order[i],order[j]
   diff=planets[b]["longitude"]-planets[a]["longitude"]
   hit,d,band=_classify(diff)
   if hit: pp.append({"from":a,"to":b,"from_deg":round(planets[a]["longitude"],2),"to_deg":round(planets[b]["longitude"],2),"diff":d,"hit":hit,"band":band})
 for name in planets:
  for c in cusps:
   diff=c["longitude"]-planets[name]["longitude"]
   hit,d,band=_classify(diff)
   if hit: ph.append({"planet":name,"house":c["house"],"planet_deg":round(planets[name]["longitude"],2),"cusp_deg":round(c["longitude"],2),"diff":d,"hit":hit,"band":band})
 return {"planet_planet":pp,"planet_house":ph}

# ---------------- Panchang ----------------
TITHI_NAMES=["Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi"]
YOGA_NAMES=["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti","Shoola","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"]
KARAN_MOVABLE=["Bava","Balava","Kaulava","Taitila","Gara","Vanija","Vishti"]
VAAR=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]  # Python weekday(): Mon=0

def tithi_info(sun_lon,moon_lon):
 diff=norm(moon_lon-sun_lon)
 idx=int(diff//12)  # 0..29
 paksha="Shukla" if idx<15 else "Krishna"
 local_idx=idx if idx<15 else idx-15
 name="Purnima" if idx==14 else ("Amavasya" if idx==29 else TITHI_NAMES[local_idx])
 return {"paksha":paksha,"tithi":name,"tithi_number":idx+1,"degrees_elapsed":round(diff-idx*12,2)}

def yoga_info(sun_lon,moon_lon):
 total=norm(sun_lon+moon_lon)
 span=800/60  # 13.3333 deg
 idx=int(total//span)
 return {"yoga":YOGA_NAMES[idx%27],"degrees_elapsed":round(total-idx*span,2)}

def karan_info(sun_lon,moon_lon):
 diff=norm(moon_lon-sun_lon)
 k=int(diff//6)+1  # 1..60
 if k==1: name="Kimstughna"
 elif k>=58: name=["Shakuni","Chatushpada","Naga"][k-58]
 else: name=KARAN_MOVABLE[(k-2)%7]
 return {"karan":name,"karan_number":k}

def sun_rise_set(y,m,d,lat,lon,tz):
 import swisseph as swe
 jd0=swe.julday(y,m,d,0.0)-tz/24.0
 geopos=(lon,lat,0)
 def _event(rsmi):
  rflag,tret=swe.rise_trans(jd0,swe.SUN,rsmi,geopos,0,0,swe.FLG_SWIEPH)
  if rflag<0: return None
  yy,mm,dd,hh=swe.revjul(tret[0]);local_h=hh+tz
  hh2=int(local_h)%24;mm2=int((local_h-int(local_h))*60);ss2=int((((local_h-int(local_h))*60)-mm2)*60)
  return f"{hh2:02d}:{mm2:02d}:{ss2:02d}"
 return {"sunrise":_event(swe.CALC_RISE),"sunset":_event(swe.CALC_SET)}

def panchang(sun_lon,moon_lon,utc_dt,lat,lon,tz):
 out={}
 out.update({"tithi_details":tithi_info(sun_lon,moon_lon)})
 out.update({"yoga_details":yoga_info(sun_lon,moon_lon)})
 out.update({"karan_details":karan_info(sun_lon,moon_lon)})
 out["vaar"]=VAAR[utc_dt.weekday()]
 try:
  out.update(sun_rise_set(utc_dt.year,utc_dt.month,utc_dt.day,lat,lon,tz))
 except Exception as e:
  out["sunrise"]=None;out["sunset"]=None;out["sun_error"]=str(e)
 return out

WEEKDAY_LORDS={0:"Moon",1:"Mars",2:"Mercury",3:"Jupiter",4:"Venus",5:"Saturn",6:"Sun"}  # Python Mon=0

def ruling_planets(p):
 """p: {date,time,latitude,longitude,timezone} for the MOMENT of judgement (not birth)."""
 r=calculate(p)
 asc=r["ascendant"];moon=r["planets"]["Moon"]
 y,m,d=map(int,p["date"].split("-"));wd=datetime(y,m,d).weekday()
 day_lord=WEEKDAY_LORDS[wd]
 return {"day_lord":day_lord,
         "ascendant_sign_lord":asc["sign_lord"],"ascendant_star_lord":asc["star_lord"],"ascendant_sub_lord":asc["sub_lord"],
         "moon_sign_lord":moon["sign_lord"],"moon_star_lord":moon["star_lord"],"moon_sub_lord":moon["sub_lord"],
         "ascendant_sign":asc["sign"],"ascendant_nakshatra":asc["nakshatra"],
         "moon_sign":moon["sign"],"moon_nakshatra":moon["nakshatra"],
         "ruling_planets_set":sorted(set([day_lord,asc["sign_lord"],asc["star_lord"],asc["sub_lord"],moon["sign_lord"],moon["star_lord"],moon["sub_lord"]]))}

def whole_sign_house(planet_lon,asc_sign_index):
 sign_idx=int(norm(planet_lon)//30)
 return ((sign_idx-asc_sign_index)%12)+1

# ---------------- Gemstone Suggestion (Trikona-lord method) ----------------
# Step 1: the lords of the 1st, 5th and 9th houses (Trikona / trine houses) are
#         shortlisted as candidate gemstone planets.
# Step 2: a candidate is dropped if it sits in a dusthana house (6th/8th/12th).
# Step 3: a candidate is dropped if it is debilitated (neecha) in its own sign.
# Whatever survives both checks is recommended.
DEBILITATION_SIGN={"Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces","Jupiter":"Capricorn",
  "Venus":"Virgo","Saturn":"Aries","Rahu":"Scorpio","Ketu":"Taurus"}
GEMSTONE_INFO={
 "Sun":{"gem":"Ruby (Manik)","metal":"Gold","finger":"Ring finger","day":"Sunday","mantra":"Om Suryaya Namah","mantra_count":7000},
 "Moon":{"gem":"Pearl (Moti)","metal":"Silver","finger":"Little finger","day":"Monday","mantra":"Om Chandraya Namah","mantra_count":11000},
 "Mars":{"gem":"Red Coral (Moonga)","metal":"Gold or Copper","finger":"Ring finger","day":"Tuesday","mantra":"Om Mangalaya Namah","mantra_count":10000},
 "Mercury":{"gem":"Emerald (Panna)","metal":"Gold","finger":"Little finger","day":"Wednesday","mantra":"Om Budhaya Namah","mantra_count":9000},
 "Jupiter":{"gem":"Yellow Sapphire (Pukhraj)","metal":"Gold","finger":"Index finger","day":"Thursday","mantra":"Om Brihaspataye Namah","mantra_count":19000},
 "Venus":{"gem":"Diamond or White Sapphire (Heera)","metal":"Silver or Platinum","finger":"Middle finger","day":"Friday","mantra":"Om Shukraya Namah","mantra_count":16000},
 "Saturn":{"gem":"Blue Sapphire (Neelam)","metal":"Silver or Iron","finger":"Middle finger","day":"Saturday","mantra":"Om Shanicharaya Namah","mantra_count":23000},
 "Rahu":{"gem":"Hessonite (Gomed)","metal":"Silver","finger":"Middle finger","day":"Saturday","mantra":"Om Rahave Namah","mantra_count":18000},
 "Ketu":{"gem":"Cat's Eye (Lehsunia)","metal":"Silver or Gold","finger":"Ring finger","day":"Tuesday","mantra":"Om Ketave Namah","mantra_count":17000},
}
def gemstone_analysis(planets,asc_sign_idx):
 trikona=[]
 for house in (1,5,9):
  sign_idx=(asc_sign_idx+house-1)%12
  sign=SIGNS[sign_idx]
  trikona.append({"house":house,"sign":sign,"sign_number":sign_idx+1,"lord":SIGN_LORDS[sign]})
 shortlist=[]
 for t in trikona:
  if t["lord"] not in shortlist: shortlist.append(t["lord"])
 results=[]
 for lord in shortlist:
  pl=planets.get(lord)
  if not pl: continue
  house=pl["house_d1"];sign=pl["sign"]
  dusthana=house in (6,8,12)
  deb_sign=DEBILITATION_SIGN.get(lord)
  debilitated=(sign==deb_sign)
  recommended=(not dusthana) and (not debilitated)
  reasons=[]
  if dusthana: reasons.append(f"placed in house {house}, a dusthana (6th/8th/12th)")
  if debilitated: reasons.append(f"debilitated in {sign}")
  if recommended: reasons.append(f"trikona lord, not in a dusthana house, and not debilitated")
  info=GEMSTONE_INFO[lord]
  results.append({"planet":lord,"house":house,"sign":sign,"dusthana":dusthana,"debilitated":debilitated,
    "recommended":recommended,"reason":"; ".join(reasons),**info})
 return {"trikona":trikona,"shortlist":shortlist,"results":results}

# ---------------- House-by-House Lord Placement Narratives ----------------
def _ordinal(n):
 suf="th" if 10<=n%100<=20 else {1:"st",2:"nd",3:"rd"}.get(n%10,"th")
 return f"{n}{suf}"

HOUSE_INFO={
 1:{"title":"Self & Vitality","keywords":"personality, health and how you present yourself to the world"},
 2:{"title":"Wealth & Family","keywords":"savings, family circle, speech and food habits"},
 3:{"title":"Courage & Communication","keywords":"siblings, courage, short journeys and communication skills"},
 4:{"title":"Home & Comfort","keywords":"mother, home, property, vehicles and inner peace"},
 5:{"title":"Creativity & Children","keywords":"children, intellect, romance and speculative gains"},
 6:{"title":"Health & Service","keywords":"health, competition, debts and daily work"},
 7:{"title":"Partnerships","keywords":"marriage, business partners and public dealings"},
 8:{"title":"Transformation","keywords":"longevity, sudden change, inheritance and hidden matters"},
 9:{"title":"Fortune & Higher Learning","keywords":"father, luck, higher education and long journeys"},
 10:{"title":"Career & Status","keywords":"profession, reputation and public standing"},
 11:{"title":"Gains & Networks","keywords":"income, elder siblings, friendships and wish-fulfillment"},
 12:{"title":"Release & Expenses","keywords":"expenses, foreign connections, spirituality and rest"},
}
PLACEMENT_THEMES={
 1:{"theme":"a strong, self-driven energy — you tend to take charge and act on your own instincts here",
   "action":"trust your own initiative here rather than waiting for others to move first"},
 2:{"theme":"a financial and family-oriented energy — resources, savings and home-grown relationships shape the outcome",
   "action":"keep a steady side income going and stay close to family for support"},
 3:{"theme":"an energy of effort and communication — outcomes come through your own hustle, networking and willingness to speak up",
   "action":"invest in communication skills, short courses or sales-oriented work"},
 4:{"theme":"a home-and-comfort energy — matters here are tied closely to your mother, your residence and your need for emotional stability",
   "action":"home-based work, real estate or property investment suits you well"},
 5:{"theme":"a creative and speculative energy — intelligence, planning and calculated risk-taking play a big role",
   "action":"use your strategic thinking in planning, education or speculative ventures"},
 6:{"theme":"a service-and-competition energy — routine, discipline and problem-solving determine the result",
   "action":"a structured daily routine and consistent service turns this into a strength"},
 7:{"theme":"a partnership energy — other people, spouse or business partners have a direct hand in the outcome",
   "action":"choose partners and collaborators carefully; joint ventures work in your favour"},
 8:{"theme":"a transformative, behind-the-scenes energy — sudden shifts and deep research or introspection are involved",
   "action":"avoid impulsive decisions here; deeper research or professional guidance pays off"},
 9:{"theme":"a fortunate, higher-learning energy — sustained effort combined with faith and education brings the best results",
   "action":"keep learning and stay consistent — fortune supports sustained effort"},
 10:{"theme":"a career-and-status energy — public reputation, authority and professional recognition come into play",
   "action":"focus on visible, quality-driven work — this area rewards public effort"},
 11:{"theme":"a gains-and-network energy — friendships, communities and multiple income streams support this area strongly",
   "action":"lean on your network and diversify income streams to make progress here"},
 12:{"theme":"a releasing, low-profile energy — quiet effort, letting go and sometimes distance from the usual setting brings results",
   "action":"be comfortable working away from the spotlight, and avoid overspending here"},
}
def house_lord_narratives(planets,asc_sign_idx):
 out=[]
 for h in range(1,13):
  sign_idx=(asc_sign_idx+h-1)%12;sign=SIGNS[sign_idx];lord=SIGN_LORDS[sign]
  placement=planets[lord]["house_d1"]
  info=HOUSE_INFO[h];dest=PLACEMENT_THEMES[placement]
  text=(f"{_ordinal(h)} House ({info['title']}) is ruled by {lord}, currently placed in your {_ordinal(placement)} house. "
        f"This brings {dest['theme']}, directly touching your {info['keywords']}.")
  action=dest["action"];suggestion=action[0].upper()+action[1:]+"."
  out.append({"house":h,"sign":sign,"title":info["title"],"lord":lord,"lord_house":placement,
    "text":text,"suggestion":suggestion})
 return out

# ---------------- Vastu Direction Mapping (Rashi -> Direction) ----------------
RASHI_DIRECTIONS={"Aries":"East","Taurus":"NW","Gemini":"NNW","Cancer":"NNE","Leo":"ENE","Virgo":"North",
 "Libra":"WSW/SW","Scorpio":"SSW","Sagittarius":"NE","Capricorn":"SSE/South","Aquarius":"West","Pisces":"SE"}
OFFICE_PRIORITY=[(10,"Career"),(2,"Wealth"),(7,"Business"),(11,"Gains")]
BEDROOM_PRIORITY=[(4,"Home"),(2,"Family"),(11,"Gains"),(5,"Children"),(7,"Spouse")]
def vastu_directions(asc_sign_idx):
 def house_sign(h):return SIGNS[(asc_sign_idx+h-1)%12]
 def build(priority):
  rows=[]
  for i,(h,label) in enumerate(priority):
   sign=house_sign(h)
   rows.append({"priority":i+1,"house":h,"sign":sign,"direction":RASHI_DIRECTIONS[sign],"use_for":label})
  return rows
 avoid=[{"house":h,"sign":house_sign(h),"direction":RASHI_DIRECTIONS[house_sign(h)]} for h in (6,8,12)]
 return {"office":build(OFFICE_PRIORITY),"bedroom":build(BEDROOM_PRIORITY),"avoid":avoid}

# ---------------- Hit Theory Remedies (currently active Dasha planets) ----------------
# "Active" planets = the current Mahadasha lord + its Nakshatra(star) lord, and the
# current Antardasha lord + its Nakshatra(star) lord. For each of these, any negative
# aspect "hit" (see Aspect Hit System) landing ON them from another planet, or that they
# throw onto a house cusp, is treated as an obstruction needing a remedy.
BODY_ZONES={"Aries":"Head","Taurus":"Face","Gemini":"Arms & Shoulders","Cancer":"Chest","Leo":"Heart",
 "Virgo":"Abdomen","Libra":"Lower Back / Kidneys","Scorpio":"Reproductive Area","Sagittarius":"Thighs",
 "Capricorn":"Knees","Aquarius":"Calves","Pisces":"Feet"}
OIL_NAMES={"Sun":"Surya Tel (Sun Oil)","Moon":"Chandra Tel (Moon Oil)","Mars":"Mangal Tel (Mars Oil)",
 "Mercury":"Budh Tel (Mercury Oil)","Jupiter":"Guru Tel (Jupiter Oil)","Venus":"Shukra Tel (Venus Oil)",
 "Saturn":"Shani Tel (Saturn Oil)","Rahu":"Rahu Tel (Rahu Oil)","Ketu":"Ketu Tel (Ketu Oil)"}
SYMBOL_COLORS={"Sun":"Orange/Red","Moon":"White","Mars":"Red","Mercury":"Green","Jupiter":"Yellow",
 "Venus":"Pink/White","Saturn":"Black/Blue","Rahu":"Smoky Grey","Ketu":"Multi-colour/Grey"}
SEVERITY_BY_BAND={"Killer Hit":"SEVERE","Major Hit":"MODERATE","Minor Hit":"MILD"}

def _build_remedy(cause,target_type,target,diff,band,planets):
 sign=planets[cause]["sign"];info=GEMSTONE_INFO[cause]
 return {"cause":cause,"cause_sign":sign,"target_type":target_type,"target":target,
   "degree":diff,"band":band,"severity":SEVERITY_BY_BAND.get(band,"MILD"),
   "body_zone":BODY_ZONES[sign],"oil":OIL_NAMES[cause],"symbol_color":SYMBOL_COLORS[cause],
   "direction":RASHI_DIRECTIONS[sign],"mantra":info["mantra"],"day":info["day"]}

def hit_theory_remedies(planets,aspects,dasha,utc):
 # NOTE: "today" must be the real current date, not the birth moment (utc is the
 # birth instant, kept only for signature symmetry with other dasha helpers).
 today=datetime.utcnow().date().isoformat()
 def in_range(s,e):return s<=today<e
 mahas=dasha["mahadasha"]
 md=next((m for m in mahas if in_range(m["start"],m["end"])),mahas[0])
 adlist=md.get("antardasha") or []
 ad=next((a for a in adlist if in_range(a["start"],a["end"])),adlist[0] if adlist else None)
 active=[]
 for lord in [md["lord"],planets[md["lord"]]["star_lord"]]+([ad["lord"],planets[ad["lord"]]["star_lord"]] if ad else []):
  if lord and lord not in active: active.append(lord)
 remedies=[];seen=set()
 for hit in aspects["planet_planet"]:
  if hit["hit"]!="-": continue
  a,b=hit["from"],hit["to"]
  if b in active and a not in active: cause,target=a,b
  elif a in active and b not in active: cause,target=b,a
  else: continue
  key=(cause,"planet",target)
  if key in seen: continue
  seen.add(key);remedies.append(_build_remedy(cause,"planet",target,hit["diff"],hit["band"],planets))
 for hit in aspects["planet_house"]:
  if hit["hit"]!="-" or hit["planet"] not in active: continue
  key=(hit["planet"],"house",hit["house"])
  if key in seen: continue
  seen.add(key);remedies.append(_build_remedy(hit["planet"],"house",hit["house"],hit["diff"],hit["band"],planets))
 remedies.sort(key=lambda r:{"SEVERE":0,"MODERATE":1,"MILD":2}.get(r["severity"],3))
 return {"active_planets":active,"remedies":remedies}

# ---------------- Prediction Engine (Dasha + Significators method) ----------------
# Rule-based, transparent by design: for the currently running Mahadasha, Antardasha
# and Pratyantardasha, we take the lord's already-computed combined significator
# houses (planet -> star lord -> sub lord -> star of sub) and map them onto four
# life themes. Favorable/challenging house classification follows standard
# kendra-trikona-upachaya vs dusthana groupings.
LIFE_THEMES={
 "Career & Finance":[2,6,10,11],
 "Marriage & Relationships":[2,5,7,11],
 "Health":[1,6,8,12],
 "General & Family":[1,3,4,9,12],
}
FAVORABLE_HOUSES={1,2,3,5,9,10,11}
CHALLENGING_HOUSES={6,8,12}
THEME_CLAUSES={
 "Career & Finance":{"supportive":"favorable for income growth, career progress or new opportunities",
   "testing":"may bring work pressure, financial caution or delays worth planning for",
   "mixed":"a mixed period for career and money matters — steady effort recommended"},
 "Marriage & Relationships":{"supportive":"a good phase for relationships, partnerships or marriage-related developments",
   "testing":"relationships may need extra patience and communication during this period",
   "mixed":"relationship matters look mixed — no major shifts expected either way"},
 "Health":{"supportive":"generally supportive for health and vitality",
   "testing":"suggests extra care for health — avoid overexertion and keep up routine checkups",
   "mixed":"health looks stable with no strong indication either way"},
 "General & Family":{"supportive":"favorable for family matters, education, travel or spiritual pursuits",
   "testing":"family or domestic matters may need more attention and patience",
   "mixed":"a fairly neutral period for family and general life matters"},
}
def _period_theme(theme,houses):
 fav=sum(1 for h in houses if h in FAVORABLE_HOUSES);chal=sum(1 for h in houses if h in CHALLENGING_HOUSES)
 tone="supportive" if fav>chal else ("testing" if chal>fav else "mixed")
 return {"theme":theme,"houses":sorted(houses),"tone":tone,"text":theme+" (houses "+", ".join(str(h) for h in sorted(houses))+"): "+THEME_CLAUSES[theme][tone]}

def _classify_period(lord,seq_node,start,end):
 houses=seq_node["combined"]
 fav=sum(1 for h in houses if h in FAVORABLE_HOUSES);chal=sum(1 for h in houses if h in CHALLENGING_HOUSES)
 total=len(houses) or 1;score=round((fav-chal)/total,2)
 sentiment="Favorable" if score>0.25 else ("Challenging" if score<-0.25 else "Mixed")
 themes=[]
 for theme,theme_houses in LIFE_THEMES.items():
  hit=[h for h in houses if h in theme_houses]
  if hit: themes.append(_period_theme(theme,hit))
 if sentiment=="Favorable":
  summary=f"{lord}'s period looks generally favorable, with houses {houses} in focus — a good window to pursue growth and take initiative."
 elif sentiment=="Challenging":
  summary=f"{lord}'s period calls for some caution, with challenging houses {houses} in focus — a good time to be measured, avoid big risks, and consolidate rather than expand."
 else:
  summary=f"{lord}'s period is mixed, with houses {houses} in focus — outcomes will likely depend on effort and the underlying chart strength rather than the period alone."
 return {"lord":lord,"start":start,"end":end,"houses":houses,"score":score,"sentiment":sentiment,"themes":themes,"summary":summary}

def predictions_for_chart(dasha,sequence,utc,moon_lon):
 # NOTE: "today" must be the real current date, not the birth moment (utc is the
 # birth instant, still needed below to seed drill_dasha's chain from the right root).
 today=datetime.utcnow().date().isoformat()
 def in_range(s,e):return s<=today<e
 mahas=dasha["mahadasha"]
 md=next((m for m in mahas if in_range(m["start"],m["end"])),mahas[0])
 out={"mahadasha":_classify_period(md["lord"],sequence[md["lord"]],md["start"],md["end"])}
 adlist=md.get("antardasha") or []
 ad=next((a for a in adlist if in_range(a["start"],a["end"])),adlist[0] if adlist else None)
 if ad:
  out["antardasha"]=_classify_period(ad["lord"],sequence[ad["lord"]],ad["start"],ad["end"])
  pdlist=drill_dasha([md["lord"],ad["lord"]],utc,moon_lon,1)
  pd=next((x for x in pdlist if in_range(x["start"],x["end"])),pdlist[0] if pdlist else None)
  if pd:
   out["pratyantardasha"]=_classify_period(pd["lord"],sequence[pd["lord"]],pd["start"],pd["end"])
 return out

# ---------------- Static Reference: Zodiac + Nakshatra + Naming Letters ----------------
# Classical, ubiquitous reference tables (not chart-specific). Nakshatra-pada naming
# syllables (Devanagari) and rashi naming letters are cross-verified against a
# published Hindi namkaran reference (gaurbrahmansamaj.com naam-rashi-akshar, itself
# derived from the standard nakshatra-pada table) before shipping, since these get
# used for real baby-naming decisions. Roman transliterations kept alongside for
# readability; Devanagari is the source of truth.
NAKS_HI=["अश्विनी","भरणी","कृत्तिका","रोहिणी","मृगशिरा","आर्द्रा","पुनर्वसु","पुष्य","आश्लेषा","मघा",
 "पूर्वाफाल्गुनी","उत्तराफाल्गुनी","हस्त","चित्रा","स्वाति","विशाखा","अनुराधा","ज्येष्ठा","मूल","पूर्वाषाढ़ा",
 "उत्तराषाढ़ा","श्रवण","धनिष्ठा","शतभिषा","पूर्वाभाद्रपद","उत्तराभाद्रपद","रेवती"]
SIGNS_HI={"Aries":"मेष","Taurus":"वृषभ","Gemini":"मिथुन","Cancer":"कर्क","Leo":"सिंह","Virgo":"कन्या",
 "Libra":"तुला","Scorpio":"वृश्चिक","Sagittarius":"धनु","Capricorn":"मकर","Aquarius":"कुम्भ","Pisces":"मीन"}
NAKSHATRA_PADA_SYLLABLES=[
 ["Chu","Che","Cho","La"],["Li","Lu","Le","Lo"],["A","Ee","U","Ae"],["O","Va","Vi","Vu"],
 ["Ve","Vo","Ka","Ki"],["Ku","Gha","Na","Chha"],["Ke","Ko","Ha","Hi"],["Hu","He","Ho","Da"],
 ["Di","Du","De","Do"],["Ma","Mi","Mu","Me"],["Mo","Ta","Ti","Tu"],["Te","To","Pa","Pi"],
 ["Pu","Sha","Na","Tha"],["Pe","Po","Ra","Ri"],["Ru","Re","Ro","Ta"],["Ti","Tu","Te","To"],
 ["Na","Ni","Nu","Ne"],["No","Ya","Yi","Yu"],["Ye","Yo","Bha","Bhi"],["Bhu","Dha","Pha","Dhha"],
 ["Bhe","Bho","Ja","Ji"],["Khi","Khu","Khe","Kho"],["Ga","Gi","Gu","Ge"],["Go","Sa","Si","Su"],
 ["Se","So","Da","Di"],["Du","Tha","Jha","Nya"],["De","Do","Cha","Chi"],
]
# Devanagari pada syllables — verified against gaurbrahmansamaj.com nakshatra-pada
# breakdown; 3 corrections made vs. the earlier Roman-only table: Ardra pada3 (ङ, not
# ना), Hasta pada3 (ण, not ना), Uttara Bhadrapada pada4 (ञ, not त्र).
NAKSHATRA_PADA_SYLLABLES_HI=[
 ["चू","चे","चो","ला"],["ली","लू","ले","लो"],["आ","ई","ऊ","ए"],["ओ","वा","वी","वू"],
 ["वे","वो","का","की"],["कू","घ","ङ","छ"],["के","को","हा","ही"],["हू","हे","हो","डा"],
 ["डी","डू","डे","डो"],["मा","मी","मू","मे"],["मो","टा","टी","टू"],["टे","टो","पा","पी"],
 ["पू","ष","ण","ठ"],["पे","पो","रा","री"],["रू","रे","रो","ता"],["ती","तू","ते","तो"],
 ["ना","नी","नू","ने"],["नो","या","यी","यू"],["ये","यो","भा","भी"],["भू","धा","फा","ढा"],
 ["भे","भो","जा","जी"],["खी","खू","खे","खो"],["गा","गी","गू","गे"],["गो","सा","सी","सू"],
 ["से","सो","दा","दी"],["दू","थ","झ","ञ"],["दे","दो","चा","ची"],
]
RASHI_NAAM_AKSHAR={
 "Aries":["A","L","I"],"Taurus":["B","V","U"],"Gemini":["K","Chh","Gh"],"Cancer":["D","H"],
 "Leo":["M","T"],"Virgo":["P","Th","N"],"Libra":["R","T"],"Scorpio":["N","Y"],
 "Sagittarius":["Bh","Dh","Ph","Fa"],"Capricorn":["Kh","J"],"Aquarius":["G","S","Sh"],"Pisces":["D","Ch","Jh","Th"],
}
# Full 9-letter-per-rashi Devanagari naming set (2.25 nakshatras' worth of padas per
# rashi = 9 syllables) — matches gaurbrahmansamaj.com's detailed rashi-wise breakdown.
RASHI_NAAM_AKSHAR_HI={
 "Aries":["चू","चे","चो","ला","ली","लू","ले","लो","आ"],
 "Taurus":["ई","ऊ","ए","ओ","वा","वी","वू","वे","वो"],
 "Gemini":["का","की","कू","घ","ङ","छ","के","को","हा"],
 "Cancer":["ही","हू","हे","हो","डा","डी","डू","डे","डो"],
 "Leo":["मा","मी","मू","मे","मो","टा","टी","टू","टे"],
 "Virgo":["टो","पा","पी","पू","ष","ण","ठ","पे","पो"],
 "Libra":["रा","री","रू","रे","रो","ता","ती","तू","ते"],
 "Scorpio":["तो","ना","नी","नू","ने","नो","या","यी","यू"],
 "Sagittarius":["ये","यो","भा","भी","भू","धा","फा","ढा","भे"],
 "Capricorn":["भो","जा","जी","खी","खू","खे","खो","गा","गी"],
 "Aquarius":["गू","गे","गो","सा","सी","सू","से","सो","दा"],
 "Pisces":["दी","दू","थ","झ","ञ","दे","दो","चा","ची"],
}
def zodiac_nakshatra_reference():
 signs=[{"sign":s,"sign_hi":SIGNS_HI[s],"lord":SIGN_LORDS[s],"from_deg":i*30,"to_deg":(i+1)*30,
   "naam_akshar":RASHI_NAAM_AKSHAR[s],"naam_akshar_hi":RASHI_NAAM_AKSHAR_HI[s]} for i,s in enumerate(SIGNS)]
 nakshatras=[]
 for ni in range(27):
  nakshatras.append({"number":ni+1,"nakshatra":NAKS[ni],"nakshatra_hi":NAKS_HI[ni],"lord":(ORDER*3)[ni],
    "from_deg":round(ni*SPAN,4),"to_deg":round((ni+1)*SPAN,4),
    "pada_syllables":NAKSHATRA_PADA_SYLLABLES[ni],"pada_syllables_hi":NAKSHATRA_PADA_SYLLABLES_HI[ni]})
 return {"signs":signs,"nakshatras":nakshatras}

# ---------------- KP Horary (1-249 number system) ----------------
# Same nakshatra -> 9-part Vimshottari sub-lord subdivision used everywhere else in
# this file (see stellar()/sub()), just walked continuously across the whole 0-360
# zodiac instead of resetting display per nakshatra. Classical KP horary additionally
# splits any sub-lord segment that straddles a 30-degree sign boundary into two
# separate numbers (this is what turns the raw 27*9=243 subdivisions into the
# standard 249 KP horary numbers) — verified against the published 1-249 KP horary
# table (JyotishPortal) before shipping.
def _build_horary_table():
 segments=[]
 for ni in range(27):
  nak_start=ni*SPAN;star=(ORDER*3)[ni];idx0=ORDER.index(star);cur=nak_start
  for k in range(9):
   lord=ORDER[(idx0+k)%9];w=SPAN*YEARS[lord]/120
   segments.append([cur,cur+w,NAKS[ni],star,lord]);cur=cur+w
 table=[];num=1
 for s,e,nak,star,sub in segments:
  cur_start=s;b=(int(s//30)+1)*30
  while b<e-1e-9:
   table.append({"number":num,"from_deg":cur_start,"to_deg":b,"nakshatra":nak,"star_lord":star,"sub_lord":sub})
   num+=1;cur_start=b;b+=30
  table.append({"number":num,"from_deg":cur_start,"to_deg":e,"nakshatra":nak,"star_lord":star,"sub_lord":sub})
  num+=1
 assert len(table)==249,f"expected 249 KP horary numbers, got {len(table)} — subdivision logic changed unexpectedly"
 assert abs(table[-1]["to_deg"]-360)<1e-6,"horary table does not close at 360 degrees"
 return table
HORARY_TABLE=_build_horary_table()

def horary_ascendant_degree(number):
 row=HORARY_TABLE[number-1]
 return (row["from_deg"]+row["to_deg"])/2

def _ascendant_for_time(y,m,d,hh_frac,lat,lon,tz):
 import swisseph as swe
 utc_dt=datetime(y,m,d)+timedelta(hours=hh_frac)-timedelta(hours=tz)
 jd=swe.julday(utc_dt.year,utc_dt.month,utc_dt.day,utc_dt.hour+utc_dt.minute/60+utc_dt.second/3600)
 swe.set_sid_mode(swe.SIDM_LAHIRI)
 hres=swe.houses_ex(jd,lat,lon,b'P',0);tropical=list(hres[0])
 if len(tropical)==13: tropical=tropical[1:]
 ay=swe.get_ayanamsa_ut(jd)
 return norm(tropical[0]-ay)

def _ang_dist(a,b):
 d=abs(a-b)%360
 return min(d,360-d)

def solve_time_for_ascendant(target_deg,date_str,lat,lon,tz):
 """Reverse-solves for the clock time (on the given date, at this location) whose
 Ascendant lands on target_deg — a coarse-to-fine numeric search over swe.houses_ex,
 since the Ascendant sweeps through all 360 degrees roughly once every ~24h and there
 is no simple closed-form inverse for Placidus houses."""
 y,m,d=map(int,date_str.split("-"))
 N=144  # coarse: every 10 minutes across the day
 samples=[(i*24.0/N,_ascendant_for_time(y,m,d,i*24.0/N,lat,lon,tz)) for i in range(N+1)]
 best_i=min(range(len(samples)),key=lambda i:_ang_dist(samples[i][1],target_deg))
 hh_lo=max(0.0,samples[best_i][0]-24.0/N);hh_hi=min(24.0,samples[best_i][0]+24.0/N)
 for _ in range(7):
  M=20
  fine=[hh_lo+(hh_hi-hh_lo)*i/M for i in range(M+1)]
  fine_asc=[(hh,_ascendant_for_time(y,m,d,hh,lat,lon,tz)) for hh in fine]
  bi=min(range(len(fine_asc)),key=lambda i:_ang_dist(fine_asc[i][1],target_deg))
  span=(hh_hi-hh_lo)/M
  hh_lo=max(0.0,fine[bi]-span);hh_hi=min(24.0,fine[bi]+span)
 hh_final=(hh_lo+hh_hi)/2
 total_seconds=int(round(hh_final*3600))
 hh=min(23,total_seconds//3600);mm=(total_seconds%3600)//60;ss=total_seconds%60
 return f"{hh:02d}:{mm:02d}:{ss:02d}"

def horary_chart(number,date,lat,lon,tz,label="Horary Query"):
 if not (1<=number<=249): raise ValueError("Horary number must be between 1 and 249")
 row=HORARY_TABLE[number-1]
 target=horary_ascendant_degree(number)
 time_str=solve_time_for_ascendant(target,date,lat,lon,tz)
 chart=calculate({"name":label,"date":date,"time":time_str,"latitude":lat,"longitude":lon,"timezone":tz})
 achieved=chart["ascendant"]["longitude"]
 chart["horary"]={"number":number,"nakshatra":row["nakshatra"],"star_lord":row["star_lord"],
   "sub_lord":row["sub_lord"],"from_deg":round(row["from_deg"],4),"to_deg":round(row["to_deg"],4),
   "target_ascendant":round(target,4),"solved_time":time_str,"achieved_ascendant":round(achieved,4),
   "error_deg":round(_ang_dist(achieved,target),4)}
 return chart

def transit_comparison(birth_p,transit_p):
 """Compares a birth chart to a transit (current-moment) chart using whole-sign houses
 (the simple Rasi-chart house count from the Ascendant sign, not the Placidus KP cusps)."""
 b=calculate(birth_p);t=calculate(transit_p)
 b_asc_idx=int(norm(b["ascendant"]["longitude"])//30);t_asc_idx=int(norm(t["ascendant"]["longitude"])//30)
 rows=[]
 for name in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]:
  bp=b["planets"][name];tp=t["planets"][name]
  bh=whole_sign_house(bp["longitude"],b_asc_idx);th=whole_sign_house(tp["longitude"],t_asc_idx)
  rows.append({"planet":name,"birth_sign":bp["sign"],"birth_house":bh,"transit_sign":tp["sign"],"transit_house":th,"movement":th-bh})
 return {"birth":b,"transit":t,"comparison":rows}
