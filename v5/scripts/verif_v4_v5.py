"""Compare DECIMO_ESQ_V4.ifc (existant) et v5/DECIMO_ESQ_V5.ifc.

Pour CHAQUE produit de la V4 (murs, poteaux, dalles et ouvertures en premier lieu) :
GlobalId présent, même classe, mêmes attributs, même conteneur, même placement absolu,
même représentation (arbre d'entités canonique), mêmes sommets et même boîte englobante
une fois la géométrie calculée (ouvertures déduites). Vérifie aussi que les relations
ouvertures / remplissages des éléments V4 sont inchangées, qu'aucun ajout ne pénètre la
structure (poteaux, voiles, dalle haute) et contrôle les règles techniques (plénum, placard,
tableau, splits, réservations, coffrages).

Usage : python3 v5/scripts/verif_v4_v5.py [--v5 FICHIER.ifc] [rapport.md]
        (code retour 0 si tous les écarts sont nuls ; par défaut FICHIER = v5/DECIMO_ESQ_V5.ifc)
"""
import os, sys, logging
import numpy as np
import ifcopenshell, ifcopenshell.geom
import ifcopenshell.util.placement as up
import ifcopenshell.util.element as ue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import RACINE, V4_IFC, V5_IFC, Z_DALLE_SOUS, PLACARD_NET, DEGAGEMENT_TD, TABLEAU  # noqa

logging.disable(logging.WARNING)
ARGS = sys.argv[1:]
if "--v5" in ARGS:
    k = ARGS.index("--v5")
    V5_IFC = os.path.abspath(ARGS[k + 1])
    del ARGS[k:k + 2]
V5_REL = os.path.relpath(V5_IFC, RACINE)
TOL = 1e-6           # m
v4 = ifcopenshell.open(V4_IFC)
v5 = ifcopenshell.open(V5_IFC)
S = ifcopenshell.geom.settings()
S.set("use-world-coords", True)


def unit_scale(f):
    u = next(u for u in f.by_type("IfcSIUnit") if u.UnitType == "LENGTHUNIT")
    return {"CENTI": 0.01, "MILLI": 0.001, None: 1.0}[u.Prefix]


SC4, SC5 = unit_scale(v4), unit_scale(v5)


def body(p):
    if p.Representation is None:
        return None
    reps = p.Representation.Representations
    return next((r for r in reps if r.RepresentationIdentifier == "Body"), reps[0])


def mesh(p):
    rep = body(p)
    if rep is None:
        return None
    g = ifcopenshell.geom.create_shape(S, p, rep).geometry
    return np.array(g.verts).reshape(-1, 3), np.array(g.faces).reshape(-1, 3)


def canon(e, seen=None, depth=0):
    """Arbre d'attributs directs, indépendant des numéros d'entité et du schéma."""
    if isinstance(e, ifcopenshell.entity_instance):
        if e.is_a("IfcOwnerHistory") or e.is_a("IfcRepresentationContext"):
            return "_"
        if depth > 40:
            return e.is_a()
        return e.is_a() + "(" + ",".join(canon(a, seen, depth + 1) for a in e) + ")"
    if isinstance(e, (tuple, list)):
        return "[" + ",".join(canon(a, seen, depth + 1) for a in e) + "]"
    if isinstance(e, float):
        return f"{e:.6f}"
    return repr(e)


def category(p):
    if p.is_a("IfcWall"):
        return "Mur"
    if p.is_a("IfcColumn") or (p.Name or "").endswith("4351026"):
        return "Poteau"
    if p.is_a("IfcSlab"):
        return "Dalle"
    if p.is_a("IfcOpeningElement"):
        return "Ouverture"
    return "Autre"


rows, fails = [], []
old = [p for p in v4.by_type("IfcProduct")]
for p in old:
    try:
        q = v5.by_guid(p.GlobalId)
    except RuntimeError:
        q = None
    r = {"guid": p.GlobalId, "cat": category(p), "classe": p.is_a(), "nom": p.Name or ""}
    if q is None:
        r["etat"] = "SUPPRIMÉ"
        fails.append(r); rows.append(r); continue
    r["classe_ok"] = q.is_a() == p.is_a()
    r["attr_ok"] = all(getattr(p, a, None) == getattr(q, a, None) for a in ("Name", "Description", "ObjectType", "Tag", "LongName"))
    c4, c5 = ue.get_container(p), ue.get_container(q)
    a4, a5 = ue.get_aggregate(p), ue.get_aggregate(q)
    r["conteneur_ok"] = (getattr(c4, "GlobalId", None), getattr(a4, "GlobalId", None)) == (getattr(c5, "GlobalId", None), getattr(a5, "GlobalId", None))
    if p.ObjectPlacement is not None:
        m4 = up.get_local_placement(p.ObjectPlacement).copy(); m4[:3, 3] *= SC4
        m5 = up.get_local_placement(q.ObjectPlacement).copy(); m5[:3, 3] *= SC5
        r["d_placement"] = float(np.abs(m4 - m5).max())
    else:
        r["d_placement"] = 0.0
    r["repr_ok"] = canon(body(p)) == canon(body(q))
    if p.Representation is not None:
        g4, g5 = mesh(p), mesh(q)
        r["nb_sommets"] = (len(g4[0]), len(g5[0]))
        r["d_sommets"] = float(np.abs(np.sort(g4[0], axis=0) - np.sort(g5[0], axis=0)).max()) if len(g4[0]) == len(g5[0]) else float("inf")
        r["d_bbox"] = float(max(np.abs(g4[0].min(0) - g5[0].min(0)).max(), np.abs(g4[0].max(0) - g5[0].max(0)).max()))
        r["bbox"] = (g5[0].min(0).round(3).tolist(), g5[0].max(0).round(3).tolist())
    else:
        r["nb_sommets"], r["d_sommets"], r["d_bbox"] = (0, 0), 0.0, 0.0
    if p.is_a("IfcElement"):
        o4 = sorted(x.RelatedOpeningElement.GlobalId for x in getattr(p, "HasOpenings", []))
        o5 = sorted(x.RelatedOpeningElement.GlobalId for x in getattr(q, "HasOpenings", []))
        f4 = sorted(x.RelatingOpeningElement.GlobalId for x in getattr(p, "FillsVoids", []))
        f5 = sorted(x.RelatingOpeningElement.GlobalId for x in getattr(q, "FillsVoids", []))
        r["ouvertures_ok"] = o4 == o5 and f4 == f5
    else:
        r["ouvertures_ok"] = True
    if p.is_a("IfcOpeningElement"):
        h4 = [x.RelatingBuildingElement.GlobalId for x in p.VoidsElements]
        h5 = [x.RelatingBuildingElement.GlobalId for x in q.VoidsElements]
        r["ouvertures_ok"] &= h4 == h5 and sorted(x.RelatedBuildingElement.GlobalId for x in p.HasFillings) == sorted(x.RelatedBuildingElement.GlobalId for x in q.HasFillings)
    ok = (r["classe_ok"] and r["attr_ok"] and r["conteneur_ok"] and r["repr_ok"] and r["ouvertures_ok"]
          and r["d_placement"] <= TOL and r["d_sommets"] <= TOL and r["d_bbox"] <= TOL and r["nb_sommets"][0] == r["nb_sommets"][1])
    r["etat"] = "identique" if ok else "ÉCART"
    if not ok:
        fails.append(r)
    rows.append(r)

# --- ajouts : aucune ouverture dans un élément V4, aucune pénétration de la structure -----------------
v4_ids = {p.GlobalId for p in old}
new = [p for p in v5.by_type("IfcProduct") if p.GlobalId not in v4_ids]
new_open_in_v4 = [o for o in v5.by_type("IfcOpeningElement") if o.GlobalId not in v4_ids
                  and any(x.RelatingBuildingElement.GlobalId in v4_ids for x in o.VoidsElements)]
porteurs = [p for p in v5.by_type("IfcProduct")
            if ue.get_psets(p).get("KDEMI_Existant", {}).get("Statut", "").startswith("Existant porteur")]
import trimesh
_TM = {}


def tm(p):
    if p.GlobalId not in _TM:
        v, fc = mesh(p)
        _TM[p.GlobalId] = trimesh.Trimesh(v, fc, process=True)
    return _TM[p.GlobalId]


def depth_between(ma, mb, tol):
    lo, hi = np.maximum(ma.bounds[0], mb.bounds[0]), np.minimum(ma.bounds[1], mb.bounds[1])
    if np.any(hi - lo <= tol):
        return 0.0
    try:
        inter = trimesh.boolean.intersection([ma, mb], engine="manifold")
        return float((inter.bounds[1] - inter.bounds[0]).min()) if inter.volume > 1e-9 else 0.0
    except Exception:  # noqa  solide non fermé : boîte englobante commune (majorant)
        return float((hi - lo).min())


_IT = {}


def items(p):
    """Un maillage par item de représentation (les items d'un même produit peuvent se toucher)."""
    if p.GlobalId not in _IT:
        g = ifcopenshell.geom.create_shape(S, p, body(p)).geometry
        v, fc, ids = np.array(g.verts).reshape(-1, 3), np.array(g.faces).reshape(-1, 3), np.array(g.item_ids)
        _IT[p.GlobalId] = [trimesh.Trimesh(v, fc[ids == k], process=True) for k in np.unique(ids)]
    return _IT[p.GlobalId]


def penetrations(set_a, set_b, tol):
    """Intersections booléennes (manifold) composante par composante ;
    profondeur = plus petite dimension du volume commun."""
    out = []
    for a in set_a:
        parts = items(a)
        for b in set_b:
            mb = tm(b)
            depth = max((depth_between(pa, mb, tol) for pa in parts), default=0.0)
            if depth > tol:
                out.append((a.GlobalId, a.Name, b.Name, round(depth, 4)))
    return out


def aabb_gap(a, b):
    ma, mb = tm(a), tm(b)
    d = np.maximum(0, np.maximum(ma.bounds[0] - mb.bounds[1], mb.bounds[0] - ma.bounds[1]))
    return float(np.linalg.norm(d))


cand = [p for p in new if not p.is_a("IfcOpeningElement") and not p.is_a("IfcSpace") and p.Representation is not None
        and ue.get_psets(p).get("KDEMI_Existant") is None]
clash_list = sorted(penetrations(cand, porteurs, 0.002), key=lambda t: -t[3])
_dalle = [p for p in v5.by_type("IfcSlab") if p.GlobalId not in v4_ids]
_logts = [p for p in v5.by_type("IfcBuildingElementProxy") if (p.Name or "").endswith("4350698")]
autotest = penetrations(_dalle, _logts, 0.002)

# --- règles techniques --------------------------------------------------------------------------------
def by_name(prefix):
    return [p for p in v5.by_type("IfcProduct") if (p.Name or "").startswith(prefix)]


def bb(p):
    v = mesh(p)[0]
    return v.min(0), v.max(0)


tech = []
fp = [p for p in v5.by_type("IfcCovering") if p.PredefinedType == "CEILING" and (p.Name or "").startswith("Faux-plafond")]
top = max(bb(p)[1][2] for p in fp)
low = min(bb(p)[0][2] for p in fp)
tech.append(("Plénum sous dalle haute ≥ 0,25 m", f"{Z_DALLE_SOUS - top:.3f} m (faux-plafond +{low:.2f} / +{top:.2f}, dalle +{Z_DALLE_SOUS:.2f})", Z_DALLE_SOUS - top >= 0.25 - 1e-9))
pl = PLACARD_NET
tech.append(("Placard technique 0,60 x 0,40 net, porte pleine", f"{pl[2] - pl[0]:.2f} x {pl[3] - pl[1]:.2f} m ; porte : {by_name('Porte pleine placard')[0].is_a()}",
             abs(pl[2] - pl[0] - 0.60) < 1e-6 and abs(pl[3] - pl[1] - 0.40) < 1e-6))
td = by_name("Tableau divisionnaire")[0]
x0, y0, x1, y1 = DEGAGEMENT_TD
gen = [p for p in v5.by_type("IfcProduct") if p.Representation is not None and not p.is_a("IfcSpace") and not p.is_a("IfcOpeningElement")
       and p.GlobalId != td.GlobalId and not (p.Name or "").startswith(("Revêtement de sol", "Habillage menuisé", "Faux-plafond", "Chemin de câbles"))
       and (p.Name or "").split(":")[-1] not in ("4350632",) and not ((p.Name or "").split(":")[-1].isdigit() and 4350636 <= int((p.Name or "0").split(":")[-1]) <= 4350657)]
obst = []
for p in gen:
    lo, hi = bb(p)
    if lo[0] < x1 - 1e-3 and hi[0] > x0 + 1e-3 and lo[1] < y1 - 1e-3 and hi[1] > y0 + 1e-3 and lo[2] < 2.0 and hi[2] > 0.01:
        obst.append(p.Name)
tech.append(("Tableau divisionnaire : 1,00 m dégagé devant", f"zone x {x0:.2f}-{x1:.2f}, y {y0:.2f}-{y1:.2f}, h 2,00 : {len(obst)} obstacle(s) {obst}", not obst))
d_eau = ue.get_psets(td)["KDEMI_Esquisse"].get("Distance_point_eau_m")
tech.append(("Tableau loin de l'eau", f"{d_eau} m du WC (lave-mains et WC dans le local 07)", d_eau and d_eau > 3))
tables = [p for p in v5.by_type("IfcFurnishingElement") if any(k in (p.Name or "") for k in ("_T01", "_T02", "Table_", "_C02"))]
for sp in by_name("Split mural"):
    lo, hi = bb(sp)
    over = [t.Name for t in tables if bb(t)[0][0] < hi[0] and bb(t)[1][0] > lo[0] and bb(t)[0][1] < hi[1] and bb(t)[1][1] > lo[1]]
    wall = [w.Name for w in porteurs if w.is_a("IfcWall") and aabb_gap(sp, w) <= 0.02]
    tech.append((f"{sp.Name} : sur mur plein, en hauteur, hors tables", f"+{lo[2]:.2f} / +{hi[2]:.2f} ; fixé sur {[w.split(':')[-1] for w in wall]} ; au-dessus de : {over or 'aucune table'}",
                 not over and lo[2] >= 2.2 and bool(wall)))
resa = [p for p in v5.by_type("IfcBuildingElementProxy") if p.PredefinedType == "PROVISIONFORVOID"]
rc = penetrations(resa, porteurs, 0.0005)
tech.append((f"Réservations hors structure ({len(resa)})", f"{len(rc)} intersection(s) avec poteaux / voiles / dalle", len(rc) == 0))
liais = by_name("Liaisons frigorifiques")
lc = penetrations(liais, porteurs, 0.0005)
tech.append(("Liaisons splits : faux-plafond puis baie arrière existante", f"{len(liais)} faisceaux, {len(lc)} intersection(s) avec la structure", len(lc) == 0 and len(liais) == 2))
cof = by_name("Coffrage acoustique")
dims = [tuple((bb(c)[1] - bb(c)[0])[:2].round(2)) for c in cof]
st = [ue.get_psets(c).get("KDEMI_Hypothese", {}).get("Statut") for c in cof]
tech.append(("Coffrages EU/EV 0,30 x 0,30 « À relever sur site »", f"{len(cof)} coffrages {[tuple(float(x) for x in d) for d in dims]} ; statut {sorted(set(st))}", all(abs(d[0] - 0.3) < 0.005 and abs(d[1] - 0.3) < 0.005 for d in dims) and set(st) == {"À relever sur site"}))
interdits = [p.Name for p in v5.by_type("IfcProduct") if p.is_a() in ("IfcRoof", "IfcStair", "IfcStairFlight") or "TGBT" in (p.Name or "") or "groupe électrogène" in (p.Name or "").lower()]
tech.append(("Pas de toiture, d'escalier, de TGBT ni de groupe électrogène", f"{len(interdits)} trouvé(s)", not interdits))

# --- rapport -------------------------------------------------------------------------------------------
def fmt(x):
    return "0" if x == 0 else f"{x:.1e}"


out = ["# Comparaison V4 (existant) / V5", "",
       f"- V4 : `DECIMO_ESQ_V4.ifc` ({v4.schema}, {len(old)} produits) ; V5 : `{V5_REL}` ({v5.schema}, {len(v5.by_type('IfcProduct'))} produits)",
       f"- Tolérance : {TOL:g} m ; géométrie calculée par ifcopenshell.geom {ifcopenshell.version} (coordonnées monde, ouvertures déduites)", "",
       "| Catégorie | Éléments V4 | Retrouvés (GlobalId) | Identiques | Écart max placement (m) | Écart max sommets (m) | Écart max bbox (m) | Représentation identique | Ouvertures/remplissages identiques |",
       "|---|---|---|---|---|---|---|---|---|"]
for cat in ("Mur", "Poteau", "Dalle", "Ouverture", "Autre"):
    rs = [r for r in rows if r["cat"] == cat]
    if not rs:
        out.append(f"| {cat} | 0 | - | - | - | - | - | - | - |")
        continue
    found = [r for r in rs if r["etat"] != "SUPPRIMÉ"]
    out.append(f"| {cat} | {len(rs)} | {len(found)} | {sum(r['etat'] == 'identique' for r in rs)} | "
               f"{fmt(max(r['d_placement'] for r in found))} | {fmt(max(r['d_sommets'] for r in found))} | {fmt(max(r['d_bbox'] for r in found))} | "
               f"{sum(r['repr_ok'] for r in found)}/{len(found)} | {sum(r['ouvertures_ok'] for r in found)}/{len(found)} |")
out += ["", f"**Bilan : {len(rows) - len(fails)}/{len(rows)} produits V4 strictement identiques ; {len(fails)} écart(s).**", ""]
for r in fails:
    out.append(f"- ÉCART {r['guid']} {r['classe']} {r['nom']} : {r}")
out += ["", "## Détail murs, poteau, ouvertures (V5)", "", "| GlobalId | Classe | Nom | bbox min (m) | bbox max (m) | écart |", "|---|---|---|---|---|---|"]
for r in rows:
    if r["cat"] != "Autre":
        out.append(f"| `{r['guid']}` | {r['classe']} | {r['nom'][:60]} | {r.get('bbox', ('-',))[0]} | {r.get('bbox', ('-', '-'))[1]} | {fmt(max(r['d_placement'], r['d_sommets'], r['d_bbox']))} |")
out += ["", "## Ajouts V5", "",
        f"- {len(new)} produits ajoutés ; nouvelles ouvertures dans un élément V4 : **{len(new_open_in_v4)}**",
        f"- Éléments structurels contrôlés (pset KDEMI_Existant « Existant porteur - ne pas toucher ») : {len(porteurs)}",
        f"- Pénétrations > 2 mm d'un ajout dans la structure : **{len(clash_list)}**"]
for c in clash_list:
    out.append(f"  - {c}")
out.append(f"- Auto-contrôle du détecteur : dalle haute ajoutée / volume de contexte « logements » V4 (4350698) -> "
           f"recouvrement mesuré {autotest[0][3] if autotest else 0} m (attendu 0,20 : le volume V4 démarre à +3,30, signalé en point ouvert)")
out += ["", "## Règles techniques", "", "| Règle | Mesure | OK |", "|---|---|---|"]
for a, b, c in tech:
    out.append(f"| {a} | {b} | {'oui' if c else 'NON'} |")
good = not fails and not new_open_in_v4 and not clash_list and all(t[2] for t in tech) and bool(autotest)
out += ["", f"**Résultat global : {'CONFORME' if good else 'NON CONFORME'}**"]
txt = "\n".join(out)
print(txt)
if ARGS:
    open(ARGS[0], "w", encoding="utf-8").write(txt + "\n")
sys.exit(0 if good else 1)
