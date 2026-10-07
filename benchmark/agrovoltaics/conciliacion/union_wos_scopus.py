"""Une Scopus + WoS (solo artículos principales) y compara con las cifras del Word. No modifica ninguna BD."""
import re, sys
import pandas as pd
from collections import Counter, defaultdict
RAW="data/sessions/Agrovoltaics/raw/"; WOS="benchmark/agrovoltaics/conciliacion/"
norm=lambda t: re.sub(r"[^a-z0-9]","",str(t).lower())
def load(f):
    xl=pd.ExcelFile(f if "conciliacion" in f else RAW+f)
    s={n:pd.read_excel(xl,sheet_name=n,dtype=str) for n in ("Article","Affiliation","ArticleAuthor","Author")}
    a=s["Article"]; a=a[a.ismainarticle=="True"].copy()
    a["key"]=a.apply(lambda r: str(r.doi).lower().strip() if pd.notna(r.doi) else "t:"+norm(r.title),axis=1)
    a["cited"]=pd.to_numeric(a.cited_by,errors="coerce").fillna(0)
    return a,s
sc,S=load("agrovoltaics_Scopus_data.xlsx"); wo,W=load("../../../benchmark/agrovoltaics/conciliacion/agrovoltaics_WoS_data.xlsx".replace("../../../",""),)
print("Scopus principales:",len(sc),"únicos por clave:",sc.key.nunique(),"| WoS:",len(wo),"únicos:",wo.key.nunique())
both=set(sc.key)&set(wo.key); print("en ambas (por DOI/título):",len(both))
# refuerzo: coincidencia solo por título normalizado
tk=set(sc.title.map(norm))&set(wo.title.map(norm)); print("en ambas por título normalizado:",len(tk))
union=set(sc.key)|set(wo.key); print("UNIÓN:",len(union),"(Word: 77)")
# tabla unificada
rows={}
for db,a in (("S",sc),("W",wo)):
    for r in a.itertuples():
        d=rows.setdefault(r.key,{"year":r.year,"title":r.title,"S":None,"W":None,"src":r.source_title}); d[db]=r.cited; d["year"]=d["year"] or r.year
U=pd.DataFrame(rows).T; U["year"]=U.year.astype(int)
print("\nAño | únicos | Scopus | WoS   (Word 2024: 15 / 12 / 9)")
ys=sorted(U.year.unique())
for y in ys:
    u=U[U.year==y]; print(f"{y} | {len(u):2d} | {u.S.notna().sum():2d} | {u.W.notna().sum():2d}")
def cites(mode):
    f={"max":lambda r:max(r.S or 0,r.W or 0),"scopus":lambda r:r.S or 0,"wos":lambda r:r.W or 0}[mode]
    return U.apply(f,axis=1)
for m in ("max","scopus","wos"):
    c=cites(m); U["c_"+m]=c
print("\nPeriodos (Word: 2007-12 → 5 art/46 citas; 2014 → 78; 2015 → 5 art/104)")
for lab,(a,b) in {"2007-2012":(2007,2012),"2014":(2014,2014),"2015":(2015,2015)}.items():
    u=U[(U.year>=a)&(U.year<=b)]; print(lab,len(u),"art | citas max/scopus/wos:",int(u.c_max.sum()),int(u.c_scopus.sum()),int(u.c_wos.sum()))
# países
def aff(sheets,a,keymap):
    af=sheets["Affiliation"]; af=af[af.SR.isin(a.SR)]; af=af[~af.Country.isin(["NO COUNTRY"])&af.Country.notna()]
    return {(keymap[sr],c) for sr,c in zip(af.SR,af.Country)}
ks=dict(zip(sc.SR,sc.key)); kw=dict(zip(wo.SR,wo.key))
pairs=aff(S,sc,ks)|aff(W,wo,kw)
cc=Counter(c for _,c in pairs)
print("\nPaíses unión (Word: CHINA 21, INDIA 10, GERMANY 8, USA 5, THAILAND 5, EGYPT 4, SPAIN 4, AUSTRALIA 3, BANGLADESH 3, CANADA 2):")
print(cc.most_common(12))
print("\nCitas totales China (Word 266), con max:",int(sum(U.loc[k].c_max for k in {k for k,c in pairs if c=='CHINA'})))
U.to_csv("benchmark/agrovoltaics/conciliacion/union_articulos.csv",index_label="key")
