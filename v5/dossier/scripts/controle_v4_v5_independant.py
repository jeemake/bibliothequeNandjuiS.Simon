import ifcopenshell, ifcopenshell.geom, numpy as np, logging, sys
logging.disable(logging.WARNING)
v4=ifcopenshell.open(sys.argv[1]); v5=ifcopenshell.open(sys.argv[2])
def sc(f):
    u=next(u for u in f.by_type("IfcSIUnit") if u.UnitType=="LENGTHUNIT"); return {"CENTI":.01,"MILLI":.001,None:1.}[u.Prefix]
s4,s5=sc(v4),sc(v5)
S=ifcopenshell.geom.settings(); S.set("use-world-coords",True)
def bb(p,f):
    try:
        g=ifcopenshell.geom.create_shape(S,p).geometry; v=np.array(g.verts).reshape(-1,3)
        return v.min(0),v.max(0),len(v)
    except Exception as e: return None
prods=[p for p in v4.by_type("IfcProduct") if p.Representation]
mx=0;bad=[];allbb=[]
for p in prods:
    q=v5.by_guid(p.GlobalId) if True else None
    try: q=v5.by_guid(p.GlobalId)
    except RuntimeError: bad.append(("missing",p.GlobalId,p.Name)); continue
    a=bb(p,v4); b=bb(q,v5)
    if a is None or b is None: continue
    d=max(abs(a[0]-b[0]).max(),abs(a[1]-b[1]).max())  # world coords already in metres? check
    if a[2]!=b[2]: bad.append(("nverts",p.Name,a[2],b[2]))
    mx=max(mx,d)
    if d>1e-6: bad.append(("bbox",p.Name,d))
    if p.is_a("IfcWall"): allbb.append((a[0],a[1]))
print("V4 products w/ geometry:",len(prods),"max bbox dev (m):",mx,"issues:",bad[:10])
lo=np.min([x[0] for x in allbb],0);hi=np.max([x[1] for x in allbb],0)
print("wall envelope (m):",lo.round(3),hi.round(3),"=> %.2f x %.2f"%(hi[0]-lo[0],hi[1]-lo[1]))
for tag in ["4350629","4350630","4350631"]:
    for f,n in ((v4,"V4"),(v5,"V5")):
        e=[x for x in f.by_type("IfcProduct") if x.Name and tag in x.Name]
        print(n,tag,[(x.is_a(),x.Name,x.GlobalId) for x in e])
print("V4 walls",len(v4.by_type("IfcWall")),"V5 walls",len(v5.by_type("IfcWall")))
print("V5 storeys",[s.Name for s in v5.by_type("IfcBuildingStorey")],"stairs",len(v5.by_type("IfcStair")),"roofs",len(v5.by_type("IfcRoof")))
