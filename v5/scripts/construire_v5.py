"""DECIMO_ESQ_V4.ifc (existant) -> v5/DECIMO_ESQ_V5.ifc (IFC4, aménagement seul).

Règle : la V4 est l'existant. Le fichier est migré en IFC4 (GlobalId, placements et géométries
conservés), puis on AJOUTE uniquement : dalle haute manquante (hypothèse), faux-plafonds,
revêtements, cloisons légères, menuiseries dans les baies existantes, mobilier, éclairage,
équipements techniques, réservations, espaces. Aucune entité V4 n'est modifiée géométriquement,
déplacée ou supprimée ; les seules écritures sur la V4 sont l'ajout d'un pset « KDEMI_Existant »
et la correction des textures cassées par la migration (attribut URLReference).

Usage : python3 v5/scripts/construire_v5.py
"""
import os, sys, time, importlib, warnings
import numpy as np
import ifcopenshell, ifcopenshell.guid, ifcpatch
import ifcopenshell.util.element as ue
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import *  # noqa

warnings.filterwarnings("ignore")
CM = 100.0
INDICE = "V5"


def api(path, *a, **kw):
    mod, fn = path.rsplit(".", 1)
    return getattr(importlib.import_module("ifcopenshell.api." + mod), fn)(*a, **kw)


# ============================ 0. migration IFC2X3 -> IFC4 ===========================
src = ifcopenshell.open(V4_IFC)
src_tex = {t[4] for t in src.by_type("IfcImageTexture")}
import logging
logging.disable(logging.WARNING)
f = ifcpatch.execute({"input": V4_IFC, "file": src, "recipe": "Migrate", "arguments": ["IFC4"]})
logging.disable(logging.NOTSET)
V4_IDS = {e.id() for e in f}

# textures : la migration range le chemin dans « Parameter » au lieu de « URLReference »
for t in f.by_type("IfcImageTexture"):
    url = "".join(t.Parameter) if t.Parameter else None
    assert url in src_tex, url
    t.Parameter = None
    t.URLReference = "../" + url

OH = f.by_type("IfcOwnerHistory")[0]
CORRECTIONS = [f"IfcImageTexture x{len(src_tex)} : chemin replacé dans URLReference (défaut de migration), relatif à v5/"]

# conformité IFC4 de données V4, sans effet géométrique
for w in f.by_type("IfcWallStandardCase"):
    rels = [a for a in w.HasAssociations if a.is_a("IfcRelAssociatesMaterial")]
    if len(rels) > 1:
        for a in rels:
            if a.RelatingMaterial.is_a("IfcMaterialLayerSet") and len(a.RelatedObjects) == 1:
                CORRECTIONS.append(f"{w.GlobalId} ({w.Name}) : association redondante au IfcMaterialLayerSet retirée "
                                   "(le IfcMaterialLayerSetUsage du même jeu de couches est conservé)")
                f.remove(a)
for st in list(f.by_type("IfcDoorStyle")):
    dt = f.createIfcDoorType(st.GlobalId, st.OwnerHistory, st.Name, st.Description, st.ApplicableOccurrence,
                             st.HasPropertySets, st.RepresentationMaps, st.Tag, None, "DOOR", "NOTDEFINED", st.ParameterTakesPrecedence, None)
    for inv in f.get_inverse(st):
        for i, v in enumerate(inv):
            if v == st:
                inv[i] = dt
    f.remove(st)
    CORRECTIONS.append(f"{dt.GlobalId} ({dt.Name}) : IfcDoorStyle (IFC2X3) converti en IfcDoorType, même GlobalId et mêmes RepresentationMaps")

rdc = next(s for s in f.by_type("IfcBuildingStorey") if "RDC" in s.Name)
body = next(c for c in f.by_type("IfcGeometricRepresentationSubContext") if c.ContextIdentifier == "Body")
app = f.by_type("IfcApplication")[0]


def by_tag(tag):
    r = [e for e in f.by_type("IfcProduct") if (e.Name or "").split(":")[-1] == tag and not e.is_a("IfcOpeningElement")]
    assert len(r) == 1, (tag, r)
    return r[0]


def by_name(name):
    r = [e for e in f.by_type("IfcProduct") if e.Name == name]
    assert len(r) == 1, (name, r)
    return r[0]


# ============================ 1. styles et matériaux ================================
STYLES = {s.Name: s for s in f.by_type("IfcSurfaceStyle")}


def new_style(name, hexc, transparency=0.0, method="NOTDEFINED", spec=None):
    rgb = [int(hexc[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    ren = f.createIfcSurfaceStyleRendering(
        f.createIfcColourRgb(None, *rgb), transparency, None, None, None, None,
        f.createIfcColourRgb(None, *([spec] * 3)) if spec else None,
        f.createIfcSpecularRoughness(0.3) if spec else None, method)
    s = f.createIfcSurfaceStyle(name, "BOTH", [ren])
    STYLES[name] = s
    return s


for nm, hexc, kw in [
    ("KDEMI - Terrazzo sable", "#D8CCB6", {}),
    ("KDEMI - Enduit terre", "#B98A62", {}),
    ("KDEMI - Indigo", INDIGO, {}),
    ("KDEMI - Acoustique laine de bois sable", "#E2D5C0", {}),
    ("KDEMI - Plâtre blanc", "#F1EEE8", {}),
    ("KDEMI - Tissu indigo", "#34416F", {}),
    ("KDEMI - Lumière chaude 2700 K", "#FFE3B0", {"method": "FLAT"}),
    ("KDEMI - Équipement blanc", "#ECEBE7", {"method": "PLASTIC", "spec": 0.2}),
    ("KDEMI - Équipement gris", "#8E8A86", {"method": "PLASTIC", "spec": 0.2}),
    ("KDEMI - PVC gris", "#9C9A97", {}),
    ("KDEMI - Réservation (repère)", "#D2452F", {"transparency": 0.35}),
]:
    new_style(nm, hexc, **kw)

K = {  # clés courtes -> noms de style
    "iroko": "KDEMI - Bois iroko huilé", "acier": "KDEMI - Acier noir mat", "claustra": "KDEMI - Claustra terre cuite",
    "terre_cuite": "KDEMI - Enduit terre cuite", "vitre": "KDEMI - Vitrage clair", "livres": "KDEMI - Livres",
    "tissu": "KDEMI - Tissu terre cuite", "sable": "KDEMI - Enduit chaux sable", "blanc": "KDEMI - Enduit chaux blanc",
    "terrazzo": "KDEMI - Terrazzo sable", "terre": "KDEMI - Enduit terre", "indigo": "KDEMI - Indigo",
    "acoustique": "KDEMI - Acoustique laine de bois sable", "platre": "KDEMI - Plâtre blanc",
    "tissu_indigo": "KDEMI - Tissu indigo", "lumiere": "KDEMI - Lumière chaude 2700 K",
    "equip": "KDEMI - Équipement blanc", "equip_gris": "KDEMI - Équipement gris", "pvc": "KDEMI - PVC gris",
    "resa": "KDEMI - Réservation (repère)", "vegetal": "KDEMI - Végétal",
}
MATS = {}


def material_rel(key):
    if key not in MATS:
        name = K[key]
        m = next((m for m in f.by_type("IfcMaterial") if m.Name == name), None)
        if m is None:
            m = f.createIfcMaterial(name, None, None)
            si = f.createIfcStyledItem(None, [STYLES[name]], None)
            f.createIfcMaterialDefinitionRepresentation(None, None, [f.createIfcStyledRepresentation(body, "Style", "Material", [si])], m)
        MATS[key] = f.createIfcRelAssociatesMaterial(ifcopenshell.guid.new(), OH, None, None, [], m)
    return MATS[key]


# ============================ 2. helpers géométriques (m -> cm) ======================
P3 = lambda x, y, z: f.createIfcCartesianPoint((float(x) * CM, float(y) * CM, float(z) * CM))
P2 = lambda x, y: f.createIfcCartesianPoint((float(x) * CM, float(y) * CM))
D3 = lambda *v: f.createIfcDirection(tuple(float(a) for a in v))
DZ = D3(0, 0, 1)


def styled(items, key):
    for it in items:
        f.createIfcStyledItem(it, [STYLES[K[key]]], None)
    return items


def placement_z(z0, axis=None, ref=None, origin=(0, 0)):
    return f.createIfcAxis2Placement3D(P3(origin[0], origin[1], z0), axis, ref)


def box(x0, y0, x1, y1, z0, z1):
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    prof = f.createIfcRectangleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2((x0 + x1) / 2, (y0 + y1) / 2), None),
                                          (x1 - x0) * CM, (y1 - y0) * CM)
    return f.createIfcExtrudedAreaSolid(prof, placement_z(z0), DZ, (z1 - z0) * CM)


def cyl(cx, cy, r, z0, z1):
    prof = f.createIfcCircleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(cx, cy), None), r * CM)
    return f.createIfcExtrudedAreaSolid(prof, placement_z(z0), DZ, (z1 - z0) * CM)


def ring(cx, cy, r, t, z0, z1):
    prof = f.createIfcCircleHollowProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(cx, cy), None), r * CM, t * CM)
    return f.createIfcExtrudedAreaSolid(prof, placement_z(z0), DZ, (z1 - z0) * CM)


def polyline2(pts):
    pts = [tuple(map(float, p)) for p in pts]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return f.createIfcPolyline([P2(x, y) for x, y in pts])


def profile_from_polygon(poly):
    poly = poly.buffer(0)
    ext = list(poly.exterior.coords)
    if poly.interiors:
        return f.createIfcArbitraryProfileDefWithVoids("AREA", None, polyline2(ext), [polyline2(list(i.coords)) for i in poly.interiors])
    return f.createIfcArbitraryClosedProfileDef("AREA", None, polyline2(ext))


def slab_from_polygon(poly, z0, z1):
    """Extrusion verticale d'un polygone shapely (ou multipolygone) en plan."""
    polys = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
    return [f.createIfcExtrudedAreaSolid(profile_from_polygon(p), placement_z(z0), DZ, (z1 - z0) * CM)
            for p in polys if p.area > 1e-6]


def xz_extrude(poly, y0, y1):
    """Polygone dans le plan vertical XZ (coordonnées x, z), extrudé de y0 à y1."""
    pos = f.createIfcAxis2Placement3D(P3(0, y1, 0), D3(0, -1, 0), D3(1, 0, 0))
    polys = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
    return [f.createIfcExtrudedAreaSolid(profile_from_polygon(p), pos, DZ, (y1 - y0) * CM) for p in polys if p.area > 1e-7]


def yz_extrude(poly, x0, x1):
    """Polygone dans le plan vertical YZ (coordonnées y, z), extrudé de x0 à x1."""
    pos = f.createIfcAxis2Placement3D(P3(x0, 0, 0), D3(1, 0, 0), D3(0, 1, 0))
    return [f.createIfcExtrudedAreaSolid(profile_from_polygon(poly), pos, DZ, (x1 - x0) * CM)]


def xz_disc(cx, cz, r, y0, y1, hollow=None):
    pos2 = f.createIfcAxis2Placement2D(P2(cx, cz), None)
    prof = (f.createIfcCircleHollowProfileDef("AREA", None, pos2, r * CM, hollow * CM) if hollow
            else f.createIfcCircleProfileDef("AREA", None, pos2, r * CM))
    pos = f.createIfcAxis2Placement3D(P3(0, y1, 0), D3(0, -1, 0), D3(1, 0, 0))
    return f.createIfcExtrudedAreaSolid(prof, pos, DZ, (y1 - y0) * CM)


def xz_rect(x0, z0, x1, z1, y0, y1):
    return xz_extrude(sbox(x0, z0, x1, z1), y0, y1)[0]


def tube(points, r):
    """Liaison/fourreau : IfcSweptDiskSolid le long d'une polyligne 3D."""
    pl = f.createIfcPolyline([P3(*p) for p in points])
    return f.createIfcSweptDiskSolid(pl, r * CM, None, None, None)


def run_boxes(points, w, h):
    """Chemin de câbles : une boîte par tronçon orthogonal (w largeur, h hauteur, centrée)."""
    out = []
    for (x0, y0, z0), (x1, y1, z1) in zip(points[:-1], points[1:]):
        if abs(z1 - z0) > 1e-6:
            out.append(box(x0 - w / 2, y0 - w / 2, x0 + w / 2, y0 + w / 2, min(z0, z1) - h / 2, max(z0, z1) + h / 2))
        elif abs(x1 - x0) > 1e-6:
            out.append(box(min(x0, x1) - w / 2, y0 - w / 2, max(x0, x1) + w / 2, y0 + w / 2, z0 - h / 2, z0 + h / 2))
        else:
            out.append(box(x0 - w / 2, min(y0, y1) - w / 2, x0 + w / 2, max(y0, y1) + w / 2, z0 - h / 2, z0 + h / 2))
    return out


def circle_poly(cx, cy, r, n=64):
    return Point(cx, cy).buffer(r, resolution=n // 4)


def arch(x0, x1, z0, zs, n=24):
    r = (x1 - x0) / 2; c = (x0 + x1) / 2
    return Polygon([(x0, z0), (x1, z0), (x1, zs)] + [(c + r * np.cos(a), zs + r * np.sin(a)) for a in np.linspace(0, np.pi, n)[1:-1]] + [(x0, zs)])


def pill(x0, x1, z0, z1, n=20):
    r = (x1 - x0) / 2; c = (x0 + x1) / 2
    return Polygon([(c + r * np.cos(a), z1 - r + r * np.sin(a)) for a in np.linspace(0, np.pi, n)]
                   + [(c + r * np.cos(a), z0 + r + r * np.sin(a)) for a in np.linspace(np.pi, 2 * np.pi, n)[:-1]])


# baies V4 (mêmes définitions que scripts/maj_ifc_v4.py)
BAIES = {"A": arch(0.55, 1.75, 0.45, 1.95), "B": pill(2.00, 2.70, 0.90, 2.40), "C": pill(5.15, 6.25, 0.60, 2.50)}
PORTE = arch(3.35, 4.85, 0.0, 2.05)

# ============================ 3. création d'éléments ================================
REPERES = []  # (n°, libellé) pour les légendes des dessins


def repere(label):
    for n, l in REPERES:
        if l == label:
            return n
    REPERES.append((len(REPERES) + 1, label))
    return len(REPERES)


def new(ifc_class, name, items, mat=None, predefined_type=None, description=None, rep_type="SweptSolid",
        lot="Aménagement", rep_label=None, props=None, psets=None, container=rdc, **attrs):
    p = api("root.create_entity", f, ifc_class=ifc_class, name=name, predefined_type=predefined_type)
    p.OwnerHistory = OH
    p.Description = description
    for k, v in attrs.items():
        setattr(p, k, v)
    if container is not None:
        api("spatial.assign_container", f, products=[p], relating_structure=container)
    api("geometry.edit_object_placement", f, product=p, matrix=np.eye(4), is_si=True)
    if items:
        if any(i.is_a("IfcSweptDiskSolid") for i in items):
            rep_type = "AdvancedSweptSolid"
        rep = f.createIfcShapeRepresentation(body, "Body", rep_type, items)
        api("geometry.assign_representation", f, product=p, representation=rep)
    ps = api("pset.add_pset", f, product=p, name="KDEMI_Esquisse")
    vals = {"Indice": INDICE, "Lot": lot, "Origine": "Aménagement V5 sur existant V4"}
    if rep_label:
        vals["Repere"] = str(repere(rep_label))
    vals.update(props or {})
    api("pset.edit_pset", f, pset=ps, properties=vals)
    for nm, pr in (psets or {}).items():
        q = api("pset.add_pset", f, product=p, name=nm)
        api("pset.edit_pset", f, pset=q, properties=pr)
    if mat:
        rel = material_rel(mat)
        rel.RelatedObjects = list(rel.RelatedObjects) + [p]
    return p


HYP = {"KDEMI_Hypothese": {"Statut": "À relever sur site", "Source": "Hypothèse ESQ Ahoua"}}

# ============================ 4. marquage de l'existant ===============================
PORTEURS = ["4350587", "4350588", "4350589", "4350590", "4350606", "4350607", "4350608", "4351026"]
for t in PORTEURS:
    e = by_tag(t)
    ps = api("pset.add_pset", f, product=e, name="KDEMI_Existant")
    api("pset.edit_pset", f, pset=ps, properties={
        "Statut": "Existant porteur - ne pas toucher", "Source": "DECIMO_ESQ_V4.ifc",
        "Remarque": ("Refend agglo : statut porteur supposé, à confirmer par le BET" if t in ("4350606", "4350607", "4350608")
                     else "Poteau / pilier existant (proxy V4)" if t == "4351026" else "Mur de façade / mitoyen / arrière")})
for t in ("4350620", "4350621"):
    ps = api("pset.add_pset", f, product=by_tag(t), name="KDEMI_Existant")
    api("pset.edit_pset", f, pset=ps, properties={"Statut": "Existant non porteur - conserver", "Source": "DECIMO_ESQ_V4.ifc"})
for nm in ("Cloison rangement / dégagement", "Cloison pleine salle de réunion"):
    ps = api("pset.add_pset", f, product=by_name(nm), name="KDEMI_Existant")
    api("pset.edit_pset", f, pset=ps, properties={"Statut": "Cloison V4 non porteuse - conserver", "Source": "DECIMO_ESQ_V4.ifc"})

# ============================ 5. dalle haute (absente de la V4) =======================
EMPRISE = sbox(-0.09, -0.09, 6.69, 7.59)     # = enveloppe extérieure des murs V4 4350587/88/89/90
dalle = new("IfcSlab", "Dalle haute existante (plancher des logements) - hypothèse",
            styled(slab_from_polygon(EMPRISE, Z_DALLE_SOUS, Z_DALLE_DESSUS), "platre"), predefined_type="FLOOR",
            description="Élément structurel absent de la V4, ajouté sur l'emprise exacte des murs V4 ; sous-face +3,30 = arase des murs ; ép. 20 cm supposée",
            lot="Existant (complément)", rep_label="Dalle haute existante (ajoutée, hypothèse ép. 0,20)",
            psets={"KDEMI_Existant": {"Statut": "Existant porteur - ne pas toucher", "Source": "Ajout V5 : absent de la V4",
                                      "Remarque": "Épaisseur, retombées et réseaux à relever sur site ; aucun percement"}, **HYP})
api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=dalle, name="Pset_SlabCommon"),
    properties={"LoadBearing": True, "IsExternal": False, "Status": "EXISTING"})

# ============================ 6. espaces ==============================================
import ifcopenshell.geom
_gs = ifcopenshell.geom.settings()
_gs.set("use-world-coords", True)


def _footprint(p):
    rep = next(r for r in p.Representation.Representations if r.RepresentationIdentifier == "Body")
    v = np.array(ifcopenshell.geom.create_shape(_gs, p, rep).geometry.verts).reshape(-1, 3)
    return sbox(v[:, 0].min(), v[:, 1].min(), v[:, 0].max(), v[:, 1].max())


MURS_V4 = unary_union([_footprint(w) for w in f.by_type("IfcWall") if w.id() in V4_IDS] + [_footprint(by_tag("4351026"))])
PILIER = sbox(5.61, 3.30, 6.51, 4.20)
CAISSON = sbox(3.09, 0.09, 3.23, 0.99)
NICHES = [sbox(3.20, 7.06, 4.10, 7.41), sbox(4.18, 7.06, 5.43, 7.41), sbox(5.51, 7.06, 6.41, 7.41)]
COFF = {k: sbox(*v) for k, v in COFFRAGES.items()}
PLAC_EXT = sbox(*PLACARD_EXT)
ZONES = {
    "01": ("Salle de lecture", unary_union([sbox(3.09, 0.09, 6.51, 7.06), sbox(3.04, 2.82, 3.09, 5.04)] + NICHES).difference(PILIER).difference(CAISSON), "SPACE"),
    "02": ("Coin lecture / vitrine", sbox(0.09, 0.09, 2.91, 2.46), "SPACE"),
    "03": ("Salle de réunion", sbox(0.09, 2.52, 2.96, 5.04), "SPACE"),
    "04": ("Rangement", sbox(0.09, 5.16, 1.76, 6.24).difference(COFF["EU/EV 2 (rangement)"]).difference(PLAC_EXT), "SPACE"),
    "05": ("Placard technique", sbox(*PLACARD_NET), "SPACE"),
    "06": ("Dégagement", sbox(1.88, 5.16, 2.91, 6.24), "SPACE"),
    "07": ("WC", sbox(0.09, 6.36, 2.91, 7.41).difference(COFF["EU/EV 1 (WC)"]), "SPACE"),
    "08": ("Terrasse couverte (pergola V4)", sbox(0.0, -2.75, 6.6, -0.09).difference(sbox(0.35, -0.49, 2.95, -0.09))
           .difference(sbox(5.05, -0.49, 6.45, -0.09)).difference(sbox(3.20, -0.21, 5.00, -0.09)), "EXTERNAL"),
}
ZONES = {k: (n, p.difference(MURS_V4), t) for k, (n, p, t) in ZONES.items()}
SPACES = {}
for num, (nom, poly, ptype) in ZONES.items():
    h = 2.90 if ptype == "EXTERNAL" else (Z_FP_SOUS if num != "05" else Z_FP_SOUS)
    sp = api("root.create_entity", f, ifc_class="IfcSpace", name=num, predefined_type=ptype)
    sp.OwnerHistory = OH
    sp.LongName = nom
    sp.CompositionType = "ELEMENT"
    api("aggregate.assign_object", f, products=[sp], relating_object=rdc)
    api("geometry.edit_object_placement", f, product=sp, matrix=np.eye(4), is_si=True)
    api("geometry.assign_representation", f, product=sp,
        representation=f.createIfcShapeRepresentation(body, "Body", "SweptSolid", slab_from_polygon(poly, 0.0, h)))
    q = api("pset.add_qto", f, product=sp, name="Qto_SpaceBaseQuantities")
    api("pset.edit_qto", f, qto=q, properties={"NetFloorArea": round(poly.area, 2), "GrossFloorArea": round(poly.area, 2),
                                                "NetPerimeter": round(poly.length * CM, 1), "Height": round(h * CM, 1),
                                                "FinishCeilingHeight": round(h * CM, 1)})
    ps = api("pset.add_pset", f, product=sp, name="Pset_SpaceCommon")
    api("pset.edit_pset", f, pset=ps, properties={"Reference": num, "IsExternal": ptype == "EXTERNAL", "PubliclyAccessible": num in ("01", "02", "07", "08")})
    ps = api("pset.add_pset", f, product=sp, name="KDEMI_Esquisse")
    api("pset.edit_pset", f, pset=ps, properties={"Indice": INDICE, "Surface_m2": round(poly.area, 2),
                                                  "HSP_sous_faux_plafond_m": h if ptype != "EXTERNAL" else None})
    SPACES[num] = sp


def covers(space_num, covering):
    f.createIfcRelCoversSpaces(ifcopenshell.guid.new(), OH, None, None, SPACES[space_num], [covering])


# ============================ 7. cloisons légères ======================================
def cloison(name, items, desc, rep_label="Cloison légère / retombée BA13 (ajout V5)"):
    w = new("IfcWall", name, styled(items, "platre"), predefined_type="PARTITIONING", description=desc,
            rep_label=rep_label, lot="Cloisons légères", mat="platre")
    api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=w, name="Pset_WallCommon"),
        properties={"LoadBearing": False, "IsExternal": False, "Status": "NEW", "AcousticRating": "Rw ≥ 40 dB (hyp.)"})
    return w


cloison("Retombée BA13 au-dessus de la cloison vitrée coin lecture / réunion", [box(0.09, 2.46, 2.91, 2.52, 2.60, Z_FP_SOUS)],
        "Ferme le vide +2,60 / +3,00 entre la cloison vitrée V4 (4350609) et le faux-plafond ; plénum continu au-dessus")
cloison("Retombée BA13 au-dessus du passage à galandage", [box(2.91, 0.90, 3.09, 1.80, 2.10, Z_FP_SOUS)],
        "Imposte au droit du passage coin lecture / salle de lecture, au-dessus de la porte à galandage V4 (h 2,08)")

# placard technique : 2 joues + façade (porte pleine 0,60 x 2,04)
x0, y0, x1, y1 = PLACARD_EXT
nx0, ny0, nx1, ny1 = PLACARD_NET
cloison("Placard technique - joue ouest", [box(x0, y0, nx0, y1, 0.0, Z_FP_DESSUS)], "BA13 sur ossature, 7 cm", "Placard technique 0,60 x 0,40 net")
cloison("Placard technique - joue est", [box(nx1, y0, x1, y1, 0.0, Z_FP_DESSUS)], "BA13 sur ossature, 7 cm", "Placard technique 0,60 x 0,40 net")
facade_pl = cloison("Placard technique - façade", [box(nx0, ny1, nx1, y1, 0.0, Z_FP_DESSUS)],
                    "Façade BA13 avec baie de porte pleine 0,60 x 2,04 ; tête ouverte sur le plénum (passage des câbles)",
                    "Placard technique 0,60 x 0,40 net")
op = new("IfcOpeningElement", "Baie porte placard technique", [box(nx0, ny1 - 0.01, nx1, y1 + 0.01, 0.0, 2.04)],
         predefined_type="OPENING", container=None, lot="Cloisons légères")
api("feature.add_feature", f, feature=op, element=facade_pl)
porte_pl = new("IfcDoor", "Porte pleine placard technique 0,60", styled([box(nx0 + 0.005, ny1 + 0.015, nx1 - 0.005, ny1 + 0.055, 0.005, 2.035)], "iroko"),
               predefined_type="DOOR", description="Porte pleine iroko, ferme-porte, serrure à clé (accès technique)",
               rep_label="Placard technique 0,60 x 0,40 net", lot="Menuiseries intérieures", mat="iroko",
               OverallHeight=204.0, OverallWidth=60.0, OperationType="SINGLE_SWING_LEFT")
api("feature.add_filling", f, opening=op, element=porte_pl)

# ============================ 8. faux-plafonds, oculus, sols, murs ======================
OCULUS = circle_poly(*ARBRE, R_OCULUS, 96)
TROUS = unary_union(list(COFF.values()) + [PLAC_EXT, sbox(*HABILLAGE_TD)])
CEIL = {
    "01": ZONES["01"][1].difference(unary_union(NICHES)).difference(OCULUS).difference(TROUS).union(CAISSON).difference(OCULUS),
    "02": ZONES["02"][1].difference(TROUS),
    "03": ZONES["03"][1],
    "04": ZONES["04"][1],
    "06": ZONES["06"][1],
    "07": ZONES["07"][1],
}
for num, poly in CEIL.items():
    wet = num == "07"
    c = new("IfcCovering", f"Faux-plafond {'hydrofuge' if wet else 'acoustique'} - {ZONES[num][0]}",
            styled(slab_from_polygon(poly, Z_FP_SOUS, Z_FP_DESSUS), "platre" if wet else "acoustique"),
            predefined_type="CEILING", lot="Faux-plafonds", mat="platre" if wet else "acoustique",
            description=("Plaque BA13 H1 peinte" if wet else "Panneaux laine de bois 40 mm sur ossature suspendue, αw ≥ 0,85")
                        + f" ; sous-face +{Z_FP_SOUS:.2f}, plénum {PLENUM:.2f} m sous dalle",
            rep_label="Faux-plafond acoustique (+3,00, plénum 0,26)" if not wet else "Faux-plafond hydrofuge WC (+3,00)",
            psets={"Pset_CoveringCommon": {"Status": "NEW", "AcousticRating": "αw 0,85" if not wet else "-",
                                           "NominalThickness": 4.0}})
    covers(num, c)

ocu = new("IfcCovering", "Oculus de l'arbre à livres - bandeau iroko et sous-face indigo",
          styled([ring(*ARBRE, R_OCULUS + 0.02, 0.02, Z_FP_SOUS, Z_FP_SOUS + 0.12)], "iroko")
          + styled(slab_from_polygon(OCULUS.buffer(0.10).intersection(sbox(3.09, 0.09, 6.51, 7.06)), Z_DALLE_SOUS - 0.004, Z_DALLE_SOUS), "indigo"),
          predefined_type="CEILING", lot="Faux-plafonds", mat="indigo",
          description="Trémie Ø 2,80 dans le faux-plafond : la canopée V4 (+3,28) monte jusqu'à la dalle ; sous-face de dalle peinte indigo (peinture seule, sans fixation)",
          rep_label="Oculus Ø 2,80 : bandeau iroko, sous-face de dalle indigo")
covers("01", ocu)

FLOORS = {"01": ("terrazzo", "Terrazzo coulé sable, granulats terre cuite et noir, joints laiton", "Sol terrazzo sable"),
          "02": ("iroko", "Parquet iroko huilé, lames 14 cm", "Sol parquet iroko"),
          "03": ("iroko", "Parquet iroko huilé, lames 14 cm", "Sol parquet iroko")}
for num, (key, desc, lab) in FLOORS.items():
    poly = ZONES[num][1].difference(unary_union(NICHES)) if num == "01" else ZONES[num][1]
    c = new("IfcCovering", f"Revêtement de sol - {ZONES[num][0]}", styled(slab_from_polygon(poly, 0.0, 0.004), key),
            predefined_type="FLOORING", lot="Revêtements", mat=key, rep_label=lab,
            description=desc + " ; posé sur le sol V4 conservé (géométrie de finition 4 mm)")
    covers(num, c)

# enduit terre : mur est (hors pilier) et face intérieure de la façade côté salle de lecture
est = new("IfcCovering", "Enduit terre - mur est salle de lecture",
          styled([box(6.495, 0.09, 6.51, 3.30, 0.004, Z_FP_SOUS), box(6.495, 4.20, 6.51, 7.06, 0.004, Z_FP_SOUS)], "terre"),
          predefined_type="CLADDING", lot="Revêtements", mat="terre", rep_label="Enduit terre (argile locale) 15 mm",
          description="Enduit terre 15 mm sur mur existant (sans saignée) ; pilier existant laissé brut, peint")
covers("01", est)
fac_int = sbox(3.23, 0.004, 6.51, Z_FP_SOUS).difference(PORTE).difference(BAIES["C"])
fi = new("IfcCovering", "Enduit terre - face intérieure de la façade", styled(xz_extrude(fac_int, 0.09, 0.105), "terre"),
         predefined_type="CLADDING", lot="Revêtements", mat="terre", rep_label="Enduit terre (argile locale) 15 mm",
         description="Enduit terre 15 mm, retour en tableau non traité ; baies V4 non modifiées")
covers("01", fi)
lam = new("IfcCovering", "Lambris iroko - refend 4350608 (côté salle de lecture)",
          styled([box(3.09, 5.04, 3.11, 5.30, 0.004, Z_FP_SOUS), box(3.09, 6.14, 3.11, 7.06, 0.004, Z_FP_SOUS),
                  box(3.09, 5.30, 3.11, 6.14, 2.10, Z_FP_SOUS)], "iroko"),
          predefined_type="CLADDING", lot="Revêtements", mat="iroko", rep_label="Lambris iroko à claire-voie",
          description="Lambris iroko collé/vissé sur tasseaux ; contourne la baie libre V4 (y 5,30 - 6,14)")
covers("01", lam)

# ============================ 9. devanture : menuiseries dans les baies V4 ===============
def frame(shape, inset, y0, y1, bars=()):
    inner = shape.buffer(-inset, join_style=2)
    items = xz_extrude(shape.difference(inner), y0, y1)
    for b in bars:
        items += xz_extrude(b.intersection(inner), y0, y1)
    return items


A = BAIES["A"]
new("IfcMember", "Vitrine en arche - châssis acier noir (baie A)",
    styled(frame(A, 0.045, 0.012, 0.052, [sbox(0.935, 0, 0.965, 3), sbox(1.335, 0, 1.365, 3), sbox(0, 1.935, 3, 1.965)]), "acier"),
    predefined_type="MULLION", lot="Devanture", mat="acier", rep_label="Vitrine en arche, châssis acier noir",
    description="Dormant et petits bois acier noir 45 x 40 posés en tableau derrière le vitrage V4 conservé")
for k in ("B", "C"):
    sh = BAIES[k]
    zc = (sh.bounds[1] + sh.bounds[3]) / 2
    new("IfcMember", f"Châssis fixe acier noir (baie {k})", styled(frame(sh, 0.035, 0.012, 0.052, [sbox(0, zc - 0.015, 9, zc + 0.015)]), "acier"),
        predefined_type="MULLION", lot="Devanture", mat="acier", rep_label="Châssis fixes acier noir (baies B, C)",
        description="Dormant acier noir 35 x 40 en tableau, derrière le vitrage et le claustra V4 conservés")


# motifs Adinkra ajoutés dans les claustras V4 (les anneaux V4 restent en place)
def claustra_rings(prod):
    rings = []
    for it in prod.Representation.Representations[0].Items:
        if it.is_a("IfcExtrudedAreaSolid") and it.SweptArea.is_a("IfcCircleHollowProfileDef"):
            c = it.SweptArea.Position.Location.Coordinates
            rings.append((c[0] / CM, c[1] / CM, it.SweptArea.Radius / CM, it.SweptArea.WallThickness / CM))
    return rings


for k in ("A", "B", "C"):
    rings = claustra_rings(by_name(f"Claustra terre cuite baie {k}"))
    assert rings, k
    S_ = 0.20
    cx0, cz0 = min(r[0] for r in rings), min(r[1] for r in rings)
    grid = {(round((r[0] - cx0) / S_), round((r[1] - cz0) / S_)): r for r in rings}
    items = []
    for (i, j), (cx, cz, ro, t) in grid.items():
        ri = ro - t                                    # vide intérieur de l'anneau V4
        items.append(xz_disc(cx, cz, 0.036, -0.08, -0.04, hollow=0.010))      # cercle intermédiaire
        items.append(xz_disc(cx, cz, 0.013, -0.08, -0.04))                    # cœur
        items.append(xz_rect(cx - ri - 0.002, cz - 0.004, cx - 0.012, cz + 0.004, -0.08, -0.04))
        items.append(xz_rect(cx + 0.012, cz - 0.004, cx + ri + 0.002, cz + 0.004, -0.08, -0.04))
        if all(n in grid for n in ((i + 1, j), (i, j + 1), (i + 1, j + 1))):
            mx, mz, a = cx + S_ / 2, cz + S_ / 2, 0.048
            sq = sbox(mx - a, mz - a, mx + a, mz + a)
            items += xz_extrude(sq.difference(sq.buffer(-0.012, join_style=2)), -0.08, -0.04)
            items.append(xz_rect(mx - a + 0.01, mz - 0.005, mx + a - 0.01, mz + 0.005, -0.08, -0.04))
            items.append(xz_rect(mx - 0.005, mz - a + 0.01, mx + 0.005, mz + a - 0.01, -0.08, -0.04))
    new("IfcBuildingElementProxy", f"Inserts Adinkra terre cuite - claustra baie {k}", styled(items, "claustra"),
        lot="Devanture", mat="claustra", rep_label="Claustras terre cuite : inserts Adinkrahene et Eban",
        description="Inserts terre cuite scellés dans le claustra V4 conservé : cercles concentriques (Adinkrahene, grandeur) "
                    "dans chaque anneau ; carrés « clôture » (Eban, sécurité du foyer) dans les interstices. Pas de Gye Nyame.",
        predefined_type="USERDEFINED", ObjectType="Claustra - inserts")

# marquise acier noir au-dessus de la porte (sous la poutre de pergola V4 à +2,90)
marq = [box(3.25, -0.81, 4.95, -0.21, 2.83, 2.85), box(3.25, -0.81, 4.95, -0.79, 2.78, 2.85),
        box(3.25, -0.81, 3.27, -0.21, 2.78, 2.85), box(4.93, -0.81, 4.95, -0.21, 2.78, 2.85)]
for xb in (3.25, 4.93):
    marq += yz_extrude(Polygon([(-0.21, 2.55), (-0.21, 2.83), (-0.70, 2.83)]), xb, xb + 0.02)
new("IfcBuildingElementProxy", "Marquise acier noir", styled(marq, "acier"), lot="Devanture", mat="acier",
    rep_label="Marquise acier noir (débord 0,60)", predefined_type="USERDEFINED", ObjectType="Marquise",
    description="Tôle acier 20 mm, rive 70 mm, 2 consoles chevillées dans le portail enduit V4 ; dessous +2,78 (porte V4 : +2,80 en clé)")

# ============================ 10. mobilier ==============================================
pod = styled([box(0.58, 0.105, 1.58, 0.45, 0.0, 0.43), box(0.58, 0.105, 1.58, 0.45, 0.43, 0.45)], "iroko")
pod += styled([box(0.66 + 0.30 * k, 0.16, 0.86 + 0.30 * k, 0.30, 0.45, 0.45 + 0.24 + 0.04 * (k % 2)) for k in range(3)], "livres")
new("IfcFurniture", "DECIMO_V05_Podium_vitrine:ESQ - sur mesure", pod, predefined_type="USERDEFINED", ObjectType="Podium vitrine",
    mat="iroko", lot="Mobilier", rep_label="Podium de vitrine iroko (h 0,45 = allège baie A)",
    description="Podium iroko sous la vitrine en arche, présentation des nouveautés")
agent = styled([cyl(6.05, 1.30, 0.26, 0.0, 0.06), cyl(6.05, 1.30, 0.03, 0.06, 0.42)], "acier")
agent += styled([cyl(6.05, 1.30, 0.24, 0.42, 0.50), box(6.27, 1.08, 6.33, 1.52, 0.50, 0.90)], "tissu_indigo")
new("IfcFurniture", "DECIMO_C05_Siege_accueil:ESQ", agent, predefined_type="CHAIR", mat="tissu_indigo", lot="Mobilier",
    rep_label="Siège agent d'accueil (tissu indigo)", description="Siège pivotant derrière la banque d'accueil V4")
new("IfcFurniture", "DECIMO_P05_Pouf_indigo:ESQ", styled([cyl(0.85, 2.05, 0.21, 0.0, 0.42)], "tissu_indigo"),
    predefined_type="CHAIR", mat="tissu_indigo", lot="Mobilier", rep_label="Pouf de lecture indigo",
    description="Pouf Ø 42 tissu indigo, coin lecture")

# habillage menuisé du tableau divisionnaire (en applique : aucune saignée dans le refend)
hx0, hy0, hx1, hy1 = HABILLAGE_TD
tx0, ty0, tx1, ty1, tz0, tz1 = TABLEAU
hab = [box(hx0, hy0, hx1, hy1, 0.004, tz0 - 0.05), box(hx0, hy0, hx1, hy1, tz1 + 0.10, Z_FP_SOUS),
       box(hx0, hy0, hx1, ty0, tz0 - 0.05, tz1 + 0.10), box(hx0, ty1, hx1, hy1, tz0 - 0.05, tz1 + 0.10),
       box(hx0, ty0, hx0 + 0.02, ty1, tz0 - 0.05, tz1 + 0.10)]
new("IfcFurniture", "Habillage menuisé du tableau divisionnaire", styled(hab, "iroko"), predefined_type="USERDEFINED",
    ObjectType="Habillage technique", mat="iroko", lot="Mobilier", rep_label="Tableau divisionnaire encastré dans habillage iroko",
    description="Colonne iroko 0,64 x 0,27 en applique sur le refend 4350606 jusqu'au plafond (gaine de descente des câbles), porte iroko devant le tableau")

# ============================ 11. éclairage (2700 K) ======================================
LTYPES = {}


def light_type(name, watt, flux, kind):
    if name not in LTYPES:
        t = api("root.create_entity", f, ifc_class="IfcLightFixtureType", name=name, predefined_type=kind)
        t.OwnerHistory = OH
        ps = api("pset.add_pset", f, product=t, name="Pset_LightFixtureTypeCommon")
        api("pset.edit_pset", f, pset=ps, properties={"TotalWattage": float(watt), "NumberOfSources": 1})
        ps = api("pset.add_pset", f, product=t, name="KDEMI_Eclairage")
        api("pset.edit_pset", f, pset=ps, properties={"TemperatureCouleur_K": 2700, "IRC": "≥ 90", "Flux_lm": int(flux), "Gradable": True})
        LTYPES[name] = t
    return LTYPES[name]


def light(name, items, tname, watt, flux, kind="POINTSOURCE", desc=None, label=None, space=None):
    p = new("IfcLightFixture", name, items, predefined_type=kind, lot="Éclairage", description=desc,
            rep_label=label or "Luminaire LED 2700 K", psets={"KDEMI_Eclairage": {"TemperatureCouleur_K": 2700, "Flux_lm": int(flux)}})
    api("type.assign_type", f, related_objects=[p], relating_type=light_type(tname, watt, flux, kind))
    return p


def suspension(cx, cy, r, zb, h, ztop):
    return styled([cyl(cx, cy, 0.004, zb + h, ztop)], "acier") + styled([ring(cx, cy, r, 0.012, zb, zb + h)], "terre_cuite") \
        + styled([cyl(cx, cy, r - 0.02, zb + h - 0.02, zb + h)], "terre_cuite") + styled([cyl(cx, cy, r * 0.55, zb + 0.01, zb + 0.02)], "lumiere")


light("Suspension terre cuite - table coin lecture", suspension(1.62, 1.06, 0.22, 1.95, 0.20, Z_FP_SOUS),
      "Suspension terre cuite Ø 44", 12, 900, desc="Suspension abat-jour terre cuite, LED 2700 K", label="Suspension terre cuite 2700 K")
light("Suspension terre cuite - salon de lecture", suspension(4.725, 3.47, 0.25, 1.95, 0.22, Z_FP_SOUS),
      "Suspension terre cuite Ø 50", 14, 1100, desc="Suspension abat-jour terre cuite, LED 2700 K", label="Suspension terre cuite 2700 K")
light("Linéaire suspendu - table de réunion",
      styled([box(0.62, 3.83, 1.78, 3.87, 2.38, 2.43)], "acier") + styled([box(0.64, 3.835, 1.76, 3.865, 2.375, 2.38)], "lumiere")
      + styled([cyl(0.70, 3.85, 0.003, 2.43, 2.85), cyl(1.70, 3.85, 0.003, 2.43, 2.85)], "acier"),
      "Linéaire suspendu 1,20 m", 24, 2600, kind="DIRECTIONSOURCE", desc="Linéaire acier noir suspendu sous le panneau V4 4350696",
      label="Linéaire suspendu acier noir 2700 K")
DL = {"01": [(3.75, 0.75), (4.45, 0.75), (5.30, 0.75), (6.05, 0.75), (5.30, 1.75), (6.05, 1.75), (3.75, 2.30), (4.40, 2.20),
             (3.75, 3.60), (5.30, 2.90), (6.10, 4.70), (6.10, 6.70), (3.45, 6.70)],
      "02": [(0.90, 0.70), (2.05, 1.90), (0.80, 1.70)], "04": [(1.30, 5.95)], "06": [(2.40, 5.70)], "07": [(1.40, 6.90)]}
for num, pts in DL.items():
    for k, (x, y) in enumerate(pts, 1):
        assert Point(x, y).distance(Point(*ARBRE)) > R_OCULUS + 0.08 or num != "01"
        light(f"Downlight encastré {ZONES[num][0]} {k}",
              styled([ring(x, y, 0.045, 0.008, Z_FP_SOUS - 0.004, Z_FP_SOUS + 0.08)], "acier") + styled([cyl(x, y, 0.037, Z_FP_SOUS - 0.002, Z_FP_SOUS)], "lumiere"),
              "Downlight encastré Ø 90 orientable", 7, 550, desc="Downlight LED encastré dans le faux-plafond, UGR < 19",
              label="Downlight encastré Ø 90, 2700 K")
light("Anneau LED indirect de l'oculus", styled([ring(*ARBRE, R_OCULUS + 0.045, 0.02, Z_FP_SOUS + 0.12, Z_FP_SOUS + 0.13)], "lumiere"),
      "Ruban LED 2700 K", 40, 4000, kind="DIRECTIONSOURCE", desc="Ruban LED posé sur le bandeau, éclaire la sous-face indigo",
      label="Anneau LED indirect de l'oculus")
light("Anneau LED sous la canopée de l'arbre à livres", styled([ring(*ARBRE, 0.47, 0.03, 2.355, 2.368)], "lumiere"),
      "Ruban LED 2700 K", 12, 1200, kind="DIRECTIONSOURCE", desc="Ruban LED sous l'anneau iroko V4 de la canopée",
      label="Anneau LED sous la canopée")
light("Réglette LED de vitrine (baie A)", styled([box(0.85, 0.055, 1.45, 0.085, 2.30, 2.33)], "lumiere"),
      "Réglette LED vitrine", 8, 700, kind="DIRECTIONSOURCE", desc="Réglette LED en tableau, éclaire le podium", label="Réglette LED de vitrine")
light("Liseuse niche banquette", styled([box(5.20, 7.30, 5.32, 7.38, 1.30, 1.36)], "acier") + styled([box(5.21, 7.30, 5.31, 7.31, 1.30, 1.36)], "lumiere"),
      "Liseuse orientable", 4, 250, desc="Liseuse orientable dans la niche banquette V4", label="Liseuse de lecture")
light("Spot encastré sous marquise", styled([cyl(4.10, -0.50, 0.04, 2.775, 2.83)], "acier") + styled([cyl(4.10, -0.50, 0.03, 2.772, 2.775)], "lumiere"),
      "Spot étanche IP65", 6, 450, desc="Spot étanche encastré dans la marquise, éclaire le seuil", label="Spot sous marquise IP65")

# ============================ 12. technique (hyp. ESQ Ahoua) =============================
TECH = "Technique (hyp. ESQ Ahoua)"
new("IfcElectricDistributionBoard", "Tableau divisionnaire (encastré dans l'habillage)",
    styled([box(tx0, ty0, tx1, ty1, tz0, tz1)], "equip"), predefined_type="DISTRIBUTIONBOARD", lot=TECH, mat="equip",
    rep_label="Tableau divisionnaire encastré dans habillage iroko",
    description="Coffret ~0,60 (l) x 0,25 (p) x 0,75 (h), organes de commande entre +1,00 et +1,75 ; 1,00 m dégagé devant ; loin des points d'eau",
    props={"Degagement_m": 1.00, "Distance_point_eau_m": round(Point(2.78, 0.44).distance(sbox(0.09, 6.36, 2.91, 7.41)), 2)}, psets=HYP)
new("IfcProtectiveDevice", "Coffret arrivée électrique immeuble (disjoncteur de branchement)",
    styled([box(0.58, 5.16, 0.83, 5.30, 1.30, 1.75)], "equip"), predefined_type="CIRCUITBREAKER", lot=TECH, mat="equip",
    rep_label="Placard technique 0,60 x 0,40 net",
    description="Arrivée depuis la colonne de l'immeuble ; cheminement d'arrivée à relever. Pas de TGBT ni de groupe électrogène.", psets=HYP)
new("IfcCommunicationsAppliance", "Baie informatique murale 9U", styled([box(0.555, 5.17, 1.105, 5.52, 0.30, 0.80)], "equip_gris"),
    predefined_type="NETWORKAPPLIANCE", lot=TECH, mat="equip_gris", rep_label="Placard technique 0,60 x 0,40 net",
    description="Baie 19\" 9U 0,55 x 0,35 : box opérateur, switch, onduleur", psets=HYP)
new("IfcJunctionBox", "Coffret liaisons clim (alimentation et bus des 2 splits)", styled([box(0.88, 5.16, 1.08, 5.26, 1.30, 1.55)], "equip"),
    predefined_type="POWER", lot=TECH, mat="equip", rep_label="Placard technique 0,60 x 0,40 net",
    description="Départs alimentation et liaison de commande des unités intérieures", psets=HYP)

for k, (sx0, sy0, sx1, sy1, sz0, sz1) in ((1, SPLIT1), (2, SPLIT2)):
    it = styled([box(sx0, sy0, sx1, sy1, sz0 + 0.03, sz1)], "equip") + styled([box(sx0, sy0, sx1, sy1, sz0, sz0 + 0.03)], "equip_gris")
    new("IfcUnitaryEquipment", f"Split mural 9 000 BTU/h - unité intérieure {k}", it, predefined_type="SPLITSYSTEM", lot=TECH, mat="equip",
        rep_label="Split mural 9 000 BTU/h (2,6 kW)",
        description=("Salle de lecture, mur est plein au-dessus des rayonnages" if k == 1 else "Salle de réunion, mur mitoyen plein au-dessus du tableau mural")
                    + " ; pas au-dessus d'une table ; liaisons en faux-plafond vers la baie arrière existante",
        props={"Puissance_BTU_h": 9000, "Puissance_kW": 2.6}, psets=HYP)
    pump_x = sx1 - 0.06 if k == 1 else sx0 + 0.03
    new("IfcPump", f"Mini-pompe de relevage des condensats - split {k}", styled([box(pump_x - 0.03, sy1 - 0.12, pump_x + 0.03, sy1 - 0.02, sz1, sz1 + 0.05)], "equip"),
        predefined_type="SUMPPUMP", lot=TECH, mat="equip", rep_label="Mini-pompe de relevage des condensats",
        description="Refoulement des condensats en plénum vers la descente EU/EV 2 (siphon sec) : relevage obligatoire", psets=HYP)

# liaisons frigorifiques + câble de commande (faisceau Ø 6 cm ; condensats séparés, voir lots_techniques) : plénum -> vide du doublage V4 -> baie arrière V4
L1 = [(6.43, 5.27, SPLIT1[5] + 0.05), (6.43, 5.27, Z_LIAISONS), (6.43, 6.90, Z_LIAISONS), (6.00, 6.90, Z_LIAISONS),
      (6.00, 7.22, Z_LIAISONS), (4.85, 7.22, Z_LIAISONS), (4.85, 7.22, 2.70), (4.85, 7.75, 2.70)]
L2 = [(0.13, 3.55, SPLIT2[5] + 0.05), (0.13, 3.55, Z_LIAISONS), (0.60, 3.55, Z_LIAISONS), (0.60, 1.35, Z_LIAISONS),
      (3.25, 1.35, Z_LIAISONS), (3.25, 7.22, Z_LIAISONS), (4.60, 7.22, Z_LIAISONS), (4.60, 7.22, 2.70), (4.60, 7.75, 2.70)]
for k, pts in ((1, L1), (2, L2)):
    new("IfcPipeSegment", f"Liaisons frigorifiques et câble de commande - split {k}", styled([tube(pts, 0.03)], "pvc"),
        predefined_type="FLEXIBLESEGMENT", lot=TECH, mat="pvc", rep_label="Liaisons split (faux-plafond -> doublage -> baie arrière)",
        description="Faisceau calorifugé sous fourreau : plénum (+3,15), vide technique du doublage V4, sortie par la baie arrière existante vers la courette",
        props={"Traverse_structure": False}, psets=HYP)
C1 = [(0.83, 5.40, Z_FP_DESSUS), (0.83, 5.40, Z_CABLES), (0.83, 3.60, Z_CABLES), (0.83, 0.44, Z_CABLES), (2.78, 0.44, Z_CABLES), (2.78, 0.44, TABLEAU[5])]
C1b = [(0.83, 3.60, Z_CABLES), (0.18, 3.60, Z_CABLES), (0.18, 3.60, SPLIT2[5])]
C2 = [(2.78, 0.44, Z_CABLES), (2.78, 1.10, Z_CABLES), (5.50, 1.10, Z_CABLES), (5.50, 4.30, Z_CABLES), (6.40, 4.30, Z_CABLES),
      (6.40, 4.95, Z_CABLES), (6.40, 4.95, SPLIT1[5])]
for nm, pts in (("placard technique -> tableau divisionnaire", C1), ("dérivation split 2", C1b), ("tableau -> salle de lecture / split 1", C2)):
    new("IfcCableCarrierSegment", f"Chemin de câbles {nm}", styled(run_boxes(pts, 0.08, 0.04), "equip_gris"),
        predefined_type="CABLETRAYSEGMENT", lot=TECH, mat="equip_gris", rep_label="Chemin de câbles 80 x 40 en plénum",
        description="Dalle marine 80 x 40 suspendue sous dalle (tiges filetées : chevillage à valider BET, aucun percement traversant)", psets=HYP)

# réservations Ø 0,10 : jamais dans la structure
RESAS = [("R1", "Entrée liaisons split 1 dans le doublage V4", (6.00, 7.06, Z_LIAISONS), "y", 0.18, "Doublage cintré V4 (non structurel)"),
         ("R2", "Entrée liaisons split 2 dans le doublage V4", (3.25, 7.06, Z_LIAISONS), "y", 0.18, "Doublage cintré V4 (non structurel)"),
         ("R3", "Sortie liaisons split 1 - baie arrière existante", (4.85, 7.41, 2.70), "y", 0.18, "Baie V4 #160 (ouverture existante)"),
         ("R4", "Sortie liaisons split 2 - baie arrière existante", (4.60, 7.41, 2.70), "y", 0.18, "Baie V4 #160 (ouverture existante)"),
         ("R5", "Passage câbles placard -> réunion (cloison placo 4350621)", (0.83, 5.04, Z_CABLES), "y", 0.12, "Cloison placo V4 non porteuse")]
for code, nm, (x, y, z), ax, depth, host in RESAS:
    r = 0.05
    solid = f.createIfcExtrudedAreaSolid(f.createIfcCircleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(0, 0), None), r * CM),
                                         f.createIfcAxis2Placement3D(P3(x, y, z), D3(0, 1, 0), D3(1, 0, 0)), DZ, depth * CM)
    new("IfcBuildingElementProxy", f"Réservation {code} Ø 0,10 - {nm}", styled([solid], "resa"), predefined_type="PROVISIONFORVOID",
        lot=TECH, mat="resa", rep_label="Réservation Ø 0,10 (hors structure)",
        description=f"Support : {host}. Ne traverse ni poteau, ni voile, ni dalle.",
        psets={"Pset_ProvisionForVoid": {"Shape": "Round", "Diameter": 10.0, "Depth": round(depth * CM, 1), "System": "CVC / courants forts"},
               "KDEMI_Reservation": {"Code": code, "Support": host, "Traverse_structure": False}, **HYP})

bx0, bx1, bz0, bz1 = BAIE_ARRIERE
panel = sbox(bx0, 2.55, bx1, bz1).difference(unary_union([Point(4.85, 2.70).buffer(0.05, 16), Point(4.60, 2.70).buffer(0.05, 16)]))
new("IfcPlate", "Panneau passe-liaisons dans la baie arrière existante", styled(xz_extrude(panel, 7.415, 7.455), "acier"),
    predefined_type="SHEET", lot=TECH, mat="acier", rep_label="Panneau passe-liaisons en imposte de la baie arrière",
    description="Tôle acier 4 cm en tableau de la baie V4 #160 (imposte +2,55 / +2,80), 2 passages Ø 0,10 ; l'imposte vitrée V4 4350595 est à adapter sur site",
    psets=HYP)

for nm, (cx0, cy0, cx1, cy1) in COFFRAGES.items():
    cx, cy = (cx0 + cx1) / 2, (cy0 + cy1) / 2
    prof = f.createIfcRectangleHollowProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(cx, cy), None), 30.0, 30.0, 5.0, None, None)
    c = new("IfcCovering", f"Coffrage acoustique descente {nm}",
            styled([f.createIfcExtrudedAreaSolid(prof, placement_z(0.004), DZ, (Z_DALLE_SOUS - 0.004) * CM)], "platre"),
            predefined_type="USERDEFINED", ObjectType="Coffrage acoustique", lot=TECH, mat="platre",
            rep_label="Coffrage acoustique 0,30 x 0,30 descente EU/EV (à relever)",
            description="Parement 2 BA13 hydro (25 mm) + laine minérale 25 mm (ép. 50), toute hauteur jusqu'à la dalle ; trappes de visite ; descente de l'immeuble supposée",
            psets={"KDEMI_Hypothese": {"Statut": "À relever sur site", "Source": "Descentes EU/EV de l'immeuble en hypothèse"}})
    covers("07" if "WC" in nm else "04", c)
    new("IfcPipeSegment", f"Descente {nm} Ø 100 (hypothèse)", styled([cyl(cx, cy, 0.055, 0.0, Z_DALLE_SOUS)], "pvc"),
        predefined_type="RIGIDSEGMENT", lot=TECH, mat="pvc", rep_label="Coffrage acoustique 0,30 x 0,30 descente EU/EV (à relever)",
        description="Descente EU/EV des logements, position et diamètre à relever sur site",
        psets={"KDEMI_Hypothese": {"Statut": "À relever sur site", "Source": "Descentes EU/EV de l'immeuble en hypothèse"}})

# ============================ 13. lots techniques (électricité, plomberie, fixations) ======
def bbox_monde(p):
    rep = next(r for r in p.Representation.Representations if r.RepresentationIdentifier == "Body")
    v = np.array(ifcopenshell.geom.create_shape(_gs, p, rep).geometry.verts).reshape(-1, 3)
    return v.min(0), v.max(0)


import lots_techniques  # noqa: E402
LOTS = lots_techniques.ajouter(globals())

# ============================ 14. finalisation =======================================
proj = f.by_type("IfcProject")[0]
f.header.file_name.name = os.path.basename(V5_IFC)
f.header.file_name.time_stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
f.header.file_name.originating_system = "IfcOpenShell " + ifcopenshell.version + " - v5/scripts/construire_v5.py"
f.header.file_description.description = ("ViewDefinition [DesignTransferView]", "Bibliotheque Decimo - V5 amenagement sur existant V4")
f.write(V5_IFC)

os.makedirs(RAPPORTS, exist_ok=True)
with open(os.path.join(RAPPORTS, "corrections_conformite_ifc4.txt"), "w", encoding="utf-8") as fh:
    fh.write("Corrections non géométriques appliquées aux données V4 pour la conformité IFC4\n")
    fh.write("".join(f"- {c}\n" for c in CORRECTIONS))
with open(os.path.join(RAPPORTS, "reperes.csv"), "w", encoding="utf-8") as fh:
    fh.write("repere;libelle\n")
    for n, l in REPERES:
        fh.write(f"{n};{l}\n")
with open(os.path.join(RAPPORTS, "espaces.csv"), "w", encoding="utf-8") as fh:
    fh.write("numero;nom;type;surface_m2;hsp_m\n")
    for num, (nom, poly, ptype) in ZONES.items():
        fh.write(f"{num};{nom};{ptype};{poly.area:.2f};{'2.90 (pergola)' if ptype == 'EXTERNAL' else f'{Z_FP_SOUS:.2f}'}\n")
new_ids = [e for e in f.by_type("IfcProduct") if e.id() not in V4_IDS]
print(f"ok {V5_IFC} : {len(new_ids)} produits ajoutés, {len(REPERES)} repères, plénum {PLENUM:.2f} m")
