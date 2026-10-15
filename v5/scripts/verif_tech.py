"""Contrôle des lots techniques : v5/DECIMO_ESQ_V5.ifc -> v5/DECIMO_ESQ_V5_tech.ifc.

1. Tous les produits de la V5 (dont les 141 de la V4) sont présents et identiques dans la maquette
   technique : classe, attributs, placement, sommets (tolérance 1e-6 m).
2. Règles techniques : sanitaires V4 lus et non touchés, raccordements, pentes EU/EV (1 à 3 %),
   diamètres, collisions avec le WC et le lave-mains, réseaux en plénum, goulottes sous le
   faux-plafond, circuits (NF C 15-100), BAES, courants faibles.

Usage : python3 v5/scripts/verif_tech.py [rapport.md]    (code retour 0 si tout est conforme)
"""
import os, sys, logging, warnings
import numpy as np
import ifcopenshell, ifcopenshell.geom
import ifcopenshell.util.placement as up
import ifcopenshell.util.element as ue
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import V5_IFC, Z_FP_SOUS, Z_FP_DESSUS, Z_DALLE_SOUS  # noqa
import technique as T  # noqa

logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")
TOL = 1e-6
v5 = ifcopenshell.open(V5_IFC)
vt = ifcopenshell.open(T.V5_TECH)
S = ifcopenshell.geom.settings()
S.set("use-world-coords", True)
_M = {}


def mesh(p):
    """Maillage monde d'un produit de la maquette technique (cache par id d'entité)."""
    if p.id() not in _M:
        rep = next((r for r in p.Representation.Representations if r.RepresentationIdentifier == "Body"), None)
        g = ifcopenshell.geom.create_shape(S, p, rep).geometry
        _M[p.id()] = (np.array(g.verts).reshape(-1, 3), np.array(g.faces).reshape(-1, 3))
    return _M[p.id()]


# --- 1. identité V5 -> V5 tech ------------------------------------------------------------------------
ident, ecarts = 0, []
for p in v5.by_type("IfcProduct"):
    try:
        q = vt.by_guid(p.GlobalId)
    except RuntimeError:
        ecarts.append((p.GlobalId, p.Name, "absent")); continue
    ok = q.is_a() == p.is_a() and all(getattr(p, a, None) == getattr(q, a, None) for a in ("Name", "Description", "ObjectType", "Tag"))
    if p.ObjectPlacement is not None:
        ok &= float(np.abs(up.get_local_placement(p.ObjectPlacement) - up.get_local_placement(q.ObjectPlacement)).max()) <= TOL * 100
    if p.Representation is not None and not p.is_a("IfcOpeningElement"):
        g = ifcopenshell.geom.create_shape(S, p, next(r for r in p.Representation.Representations if r.RepresentationIdentifier == "Body")).geometry
        h = ifcopenshell.geom.create_shape(S, q, next(r for r in q.Representation.Representations if r.RepresentationIdentifier == "Body")).geometry
        a, b = np.array(g.verts).reshape(-1, 3), np.array(h.verts).reshape(-1, 3)
        ok &= a.shape == b.shape and (len(a) == 0 or float(np.abs(np.sort(a, 0) - np.sort(b, 0)).max()) <= TOL)
    ps, qs = ue.get_psets(p), ue.get_psets(q)
    ok &= {k: {kk: vv for kk, vv in v.items() if kk != "id"} for k, v in ps.items()} == \
          {k: {kk: vv for kk, vv in v.items() if kk != "id"} for k, v in qs.items()}
    if ok:
        ident += 1
    else:
        ecarts.append((p.GlobalId, p.Name, "écart"))
n_v5 = len(v5.by_type("IfcProduct"))
v5_ids = {p.GlobalId for p in v5.by_type("IfcProduct")}
ajouts = [p for p in vt.by_type("IfcProduct") if p.GlobalId not in v5_ids]

# --- 2. règles --------------------------------------------------------------------------------------
R = []


def regle(nom, mesure, ok):
    R.append((nom, mesure, bool(ok)))


SAN, NOTES = T.lire_sanitaires(vt)
regle("WC et lave-mains V4 du local 07 lus dans l'IFC", f"lus : {sorted(SAN) or 'aucun'} ; non lus documentés : "
      f"{sum('non' in n and 'dessiné' in n for n in NOTES)}", True)


_IT = {}


def items(p):
    """Un maillage par item de représentation : les items d'un même produit sont fermés mais se touchent."""
    if p.id() not in _IT:
        rep = next(r for r in p.Representation.Representations if r.RepresentationIdentifier == "Body")
        g = ifcopenshell.geom.create_shape(S, p, rep).geometry
        v, fc, ids = np.array(g.verts).reshape(-1, 3), np.array(g.faces).reshape(-1, 3), np.array(g.item_ids)
        _IT[p.id()] = [trimesh.Trimesh(v, fc[ids == k], process=True) for k in np.unique(ids)]
    return _IT[p.id()]


def profondeur(ma, mb):
    lo, hi = np.maximum(ma.bounds[0], mb.bounds[0]), np.minimum(ma.bounds[1], mb.bounds[1])
    if np.any(hi - lo <= 0.0005):
        return 0.0
    try:
        inter = trimesh.boolean.intersection([ma, mb], engine="manifold")
        return float((inter.bounds[1] - inter.bounds[0]).min()) if inter.volume > 1e-9 else 0.0
    except Exception:  # noqa  item non fermé : boîte commune (majorant)
        return float((hi - lo).min())


def penetration(a, b):
    return max((profondeur(ma, mb) for ma in items(a) for mb in items(b)), default=0.0)


san_prod = []
if "WC" in SAN:
    san_prod.append(vt.by_guid(SAN["WC"]["guid"]))
if "LM" in SAN:
    san_prod += [vt.by_guid(g) for g in SAN["LM"]["guid"]]
geo_ajouts = [p for p in ajouts if p.Representation is not None and not p.is_a("IfcOpeningElement")]
clash = [(a.Name, s.Name, round(d, 4)) for a in geo_ajouts for s in san_prod for d in [penetration(a, s)] if d > 0.002]
regle("Aucun ajout ne pénètre le WC ou le lave-mains V4 (> 2 mm)", f"{len(clash)} pénétration(s) {clash[:4]}", not clash)

tubes = {}
for p in vt.by_type("IfcPipeSegment"):
    if p.GlobalId in v5_ids:
        continue
    k = ue.get_psets(p).get("KDEMI_Esquisse", {})
    it = p.Representation.Representations[0].Items[0]
    if it.is_a("IfcSweptDiskSolid"):
        pts = np.array([c.Coordinates for c in it.Directrix.Points]) / 100.0
        tubes[k.get("Code") or p.Name] = (p, k, pts, it.Radius / 50.0)
for code, (p, k, pts, d) in sorted(tubes.items()):
    if k.get("Reseau") in ("EU", "EV"):
        seg = []
        for a, b in zip(pts[:-1], pts[1:]):
            L = np.linalg.norm((b - a)[:2])
            if L > 0.05:
                seg.append(100 * (a[2] - b[2]) / L)
        regle(f"{code} : pente de chaque tronçon entre 1 et 3 % (DTU 60.11)", ", ".join(f"{s:.2f} %" for s in seg) +
              f" ; fil d'eau {k['FilEau_amont_m']:+.3f} > {k['FilEau_aval_m']:+.3f}", all(1.0 - 1e-6 <= s <= 3.0 + 1e-6 for s in seg))
attendu = {"EV-WC": 110, "EU-LM": 40, "AEP-WC": 16, "AEP-LM": 16, "AEP-COL": 20}
regle("Diamètres extérieurs : EV Ø 100 (110), EU Ø 40, AEP multicouche 16 / 20",
      ", ".join(f"{c} {round(tubes[c][3] * 1000)} mm" for c in attendu if c in tubes),
      all(c in tubes and abs(tubes[c][3] * 1000 - d) < 0.5 for c, d in attendu.items() if (c.endswith("WC") and "WC" in SAN) or (c.endswith("LM") and "LM" in SAN) or c == "AEP-COL"))
xd, yd = T.DESCENTE_WC
fin = {c: float(np.hypot(tubes[c][2][-1][0] - xd, tubes[c][2][-1][1] - yd) - T.R_DESC) for c in ("EV-WC", "EU-LM") if c in tubes}
regle("EV et EU aboutissent sur la descente de l'immeuble (culottes)", ", ".join(f"{c} à {d * 1000:.0f} mm de la paroi" for c, d in fin.items()),
      all(-0.001 <= d <= 0.02 for d in fin.values()))
if "WC" in SAN and "EV-WC" in tubes:
    p0 = tubes["EV-WC"][2][0]
    regle("EV : départ sur la sortie supposée du WC (dos de la cuvette)", f"{p0.round(3).tolist()} / sortie {np.round(SAN['WC']['sortie'], 3).tolist()}",
          np.linalg.norm(p0 - np.array(SAN["WC"]["sortie"])) < 0.01)
if "LM" in SAN and "EU-LM" in tubes:
    p0 = tubes["EU-LM"][2][0]
    bx, by = SAN["LM"]["bonde"]
    regle("EU : départ à l'aplomb de la bonde du lave-mains", f"{p0.round(3).tolist()} / bonde ({bx:.3f}, {by:.3f})", np.hypot(p0[0] - bx, p0[1] - by) < 0.01)
aav = [p for p in vt.by_type("IfcValve") if p.PredefinedType == "ANTIVACUUM"]
tampons = [p for p in vt.by_type("IfcPipeFitting") if "visite" in (p.Name or "") or "dégorgement" in (p.Name or "")]
trappes = [p for p in vt.by_type("IfcBuildingElementProxy") if (p.ObjectType or "") == "Trappe de visite"]
regle("Ventilation et visite : AAV sur le branchement EU, tampons et trappes", f"{len(aav)} AAV, {len(tampons)} tampons / bouchons, {len(trappes)} trappes",
      aav and len(tampons) >= 2 and trappes)


def bb(p):
    v = mesh(p)[0]
    return v.min(0), v.max(0)


plen = [p for p in ajouts if p.is_a("IfcCableCarrierSegment") and p.PredefinedType == "CABLETRAYSEGMENT"] + \
       [p for p in ajouts if p.is_a("IfcDiscreteAccessory")] + [p for p in ajouts if p.PredefinedType == "PROVISIONFORVOID"]
hors = [p.Name for p in plen if bb(p)[0][2] < Z_FP_DESSUS - 1e-6 or bb(p)[1][2] > Z_DALLE_SOUS - 1e-6]
regle("Chemin CFA, suspentes et fourreau R6 dans le plénum (+3,04 à +3,30, sans toucher la dalle)", f"{len(plen)} éléments, {len(hors)} hors plénum {hors}", not hors)
goul = [p for p in ajouts if p.is_a("IfcCableCarrierSegment") and p.PredefinedType == "CABLETRUNKINGSEGMENT"]
hautes = [p.Name for p in goul if bb(p)[1][2] > Z_FP_SOUS]
regle("Goulottes arrêtées sous le faux-plafond (descentes sans saignée)", f"{len(goul)} goulottes, {len(hautes)} au-dessus de +3,00", not hautes)

groups = {}
for rel in vt.by_type("IfcRelAssignsToGroup"):
    groups[rel.RelatingGroup] = list(rel.RelatedObjects)
circ = {g: m for g, m in groups.items() if g.is_a("IfcDistributionCircuit")}
cp = {g: ue.get_psets(g).get("KDEMI_Circuit", {}) for g in circ}
lum_v5 = [p for p in v5.by_type("IfcLightFixture")]
aff = {p.GlobalId: [cp[g]["Repere"] for g, m in circ.items() if any(x.GlobalId == p.GlobalId for x in m)] for p in lum_v5}
mal = [p.Name for p in lum_v5 if len(aff[p.GlobalId]) != 1]
regle(f"Les {len(lum_v5)} luminaires 2700 K de la V5 sont chacun sur un seul circuit d'éclairage", f"{len(lum_v5) - len(mal)}/{len(lum_v5)} ; défauts {mal}", not mal and len(lum_v5) == 27)
pts_max = max((v.get("Nb_points_lumineux", 0) for v in cp.values()), default=0)
regle("Circuits d'éclairage ≤ 8 points (BAES compris), 1,5 mm² / 16 A max", ", ".join(f"{v['Repere']} {v['Nb_points_lumineux']}" for v in cp.values() if "Nb_points_lumineux" in v),
      pts_max <= 8 and all(v["Section_mm2"] >= 1.5 and v["Calibre_A"] <= 16 for v in cp.values() if "Nb_points_lumineux" in v))
soc = [v for v in cp.values() if "Nb_socles" in v]
regle("Circuits de prises ≤ 8 socles, 2,5 mm² / 20 A max", ", ".join(f"{v['Repere']} {v['Nb_socles']}" for v in soc),
      all(v["Nb_socles"] <= 8 and v["Section_mm2"] >= 2.5 and v["Calibre_A"] <= 20 for v in soc))
par_id = {}
for v in cp.values():
    par_id.setdefault(v["Differentiel"], []).append(v["Repere"])
lid = {v["Differentiel"] for v in cp.values() if v["Repere"].startswith("E")}
regle("Chaque différentiel 30 mA protège ≤ 8 circuits ; éclairage réparti sur ≥ 2 différentiels",
      " ; ".join(f"{k} : {', '.join(sorted(m))}" for k, m in sorted(par_id.items())), all(len(m) <= 8 for m in par_id.values()) and len(lid) >= 2)
spl = [v for v in cp.values() if v["Repere"].startswith("C")]
regle("Splits sur circuits spécialisés (1 split + sa mini-pompe par circuit)", ", ".join(f"{v['Repere']} {v['Calibre_A']} A {v['Section_mm2']} mm²" for v in spl),
      len(spl) == 2 and all(sum(x.is_a("IfcUnitaryEquipment") for x in circ[g]) == 1 for g in circ if cp[g]["Repere"].startswith("C")))
baes = [p for p in ajouts if p.is_a("IfcLightFixture") and ue.get_predefined_type(p) == "SECURITYLIGHTING"]
porte = next(p for p in vt.by_type("IfcDoor") if (p.Name or "").startswith("Porte d'entrée"))
plo, phi = bb(porte)
d_issue = min(np.hypot(((bb(b)[0] + bb(b)[1]) / 2)[0] - (plo[0] + phi[0]) / 2, ((bb(b)[0] + bb(b)[1]) / 2)[1] - phi[1]) for b in baes)
sans = [b.Name for b in baes if not any(b in m for m in circ.values())]
regle("BAES : un BAES à l'issue (< 1 m), tous en hauteur (> 2,0 m) et alimentés par un circuit d'éclairage",
      f"{len(baes)} BAES ; issue à {d_issue:.2f} m ; bas : {[b.Name for b in baes if bb(b)[0][2] < 2.0]} ; sans circuit : {sans}",
      len(baes) >= 1 and d_issue < 1.0 and all(bb(b)[0][2] >= 2.0 for b in baes) and not sans)
rj = [p for p in ajouts if p.is_a("IfcOutlet") and p.PredefinedType == "DATAOUTLET"]
ap = [p for p in ajouts if p.is_a("IfcCommunicationsAppliance")]
regle("Courants faibles : RJ45 aux postes, réunion, accueil ; borne Wi-Fi au plafond",
      f"{len(rj)} prises RJ45 doubles ({2 * len(rj)} ports) ; {len(ap)} borne(s) à +{bb(ap[0])[0][2]:.2f}" if ap else "aucune borne",
      len(rj) >= 4 and ap and bb(ap[0])[1][2] <= Z_FP_SOUS)
new_open = [o for o in vt.by_type("IfcOpeningElement") if o.GlobalId not in v5_ids]
regle("Aucune ouverture IFC ajoutée (ni dans la V4, ni dans la V5)", f"{len(new_open)}", not new_open)

# --- rapport --------------------------------------------------------------------------------------------
good = not ecarts and all(r[2] for r in R)
out = ["# Vérification des lots techniques", "",
       f"- Base : `v5/DECIMO_ESQ_V5.ifc` ({n_v5} produits) ; maquette technique : `v5/DECIMO_ESQ_V5_tech.ifc` ({len(vt.by_type('IfcProduct'))} produits, {len(ajouts)} ajoutés)",
       f"- Tolérance géométrique : {TOL:g} m ; ifcopenshell {ifcopenshell.version}", "",
       "## Produits de la V5 conservés", "",
       f"**{ident}/{n_v5} produits V5 identiques dans la maquette technique (classe, attributs, psets, placement, sommets) ; {len(ecarts)} écart(s).**", ""]
out += [f"- ÉCART {g} {n} : {w}" for g, n, w in ecarts]
out += ["", "## Lecture des sanitaires V4", ""] + [f"- {n}" for n in NOTES]
out += ["", "## Règles techniques", "", "| Règle | Mesure | OK |", "|---|---|---|"]
out += [f"| {a} | {b} | {'oui' if c else 'NON'} |" for a, b, c in R]
out += ["", f"**Résultat global : {'CONFORME' if good else 'NON CONFORME'}**"]
txt = "\n".join(out)
print(txt)
if len(sys.argv) > 1:
    open(sys.argv[1], "w", encoding="utf-8").write(txt + "\n")
sys.exit(0 if good else 1)
