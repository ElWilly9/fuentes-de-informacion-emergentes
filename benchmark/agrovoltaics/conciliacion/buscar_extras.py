"""Busca qué artículos de la unión (79) no estarían en el conjunto del Word (77)."""
import runpy, itertools, io, contextlib
from collections import Counter
with contextlib.redirect_stdout(io.StringIO()):
    g=runpy.run_path("benchmark/agrovoltaics/conciliacion/union_wos_scopus.py")
U,pairs,sc,wo=g["U"],g["pairs"],g["sc"],g["wo"]
only_s=[k for k in sc.key if k not in set(wo.key)]; only_w=[k for k in wo.key if k not in set(sc.key)]
def stats(rem):
    keep=[k for k in U.index if k not in rem]
    cc=Counter(c for k,c in pairs if k not in rem)
    china=sum(U.loc[k].c_max for k in {k for k,c in pairs if c=="CHINA"} if k not in rem)
    return len(keep),cc["INDIA"],cc["UNITED STATES OF AMERICA"],int(china),int((U.loc[keep].year==2024).sum())
print("objetivo Word: 77 art | INDIA 10 | USA 5 | citas China 266 | 2024: 15")
ok=[]
for s,w in itertools.product(only_s,only_w):
    r=stats({s,w})
    if r==(77,10,5,266,15): ok.append((s,w))
print("pares (Scopus-solo, WoS-solo) que reproducen TODO:",len(ok))
for s,w in ok[:6]:
    print(" S:",U.loc[s].year,U.loc[s].title[:80],"| W:",U.loc[w].year,U.loc[w].title[:80])
# si ningún par: probar singles
if not ok:
    for k in U.index:
        r=stats({k}); 
        if r[1]==10 or r[2]==5: print("single",r,U.loc[k].year,U.loc[k].title[:70])
