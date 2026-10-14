"""Bibliothèque Decimo — maquette d'esquisse V5 (IFC4, mm), générée de zéro.

Local en rez-de-chaussée d'un immeuble existant (logements aux étages) : un seul niveau,
emprise 6,78 × 7,68 m reprise de la V4 (même repère : x vers l'est, y depuis la devanture
sur rue (y = 0) vers le fond ; rue au sud, y < 0). Cotes saisies en mètres, écrites en mm.

Usage : python3 scripts/generer_ifc_v5.py v5/DECIMO_ESQ_V5.ifc
"""
import math, random, sys, uuid
import numpy as np
import ifcopenshell, ifcopenshell.guid
import ifcopenshell.api.root, ifcopenshell.api.unit, ifcopenshell.api.context, ifcopenshell.api.aggregate
import ifcopenshell.api.spatial, ifcopenshell.api.geometry, ifcopenshell.api.material, ifcopenshell.api.pset
import ifcopenshell.api.type, ifcopenshell.api.feature, ifcopenshell.api.project, ifcopenshell.api.style
from matplotlib.path import Path as MPath
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
from shapely.geometry.polygon import orient

OUT = sys.argv[1] if len(sys.argv) > 1 else "v5/DECIMO_ESQ_V5.ifc"
ROOT = __file__.rsplit("/scripts/", 1)[0]

# GUID déterministes : un fichier identique à chaque génération (mises à jour Revit stables)
_rng = random.Random(20261014)
ifcopenshell.guid.new = lambda: ifcopenshell.guid.compress(uuid.UUID(int=_rng.getrandbits(128), version=4).hex)

A = ifcopenshell.api
f = ifcopenshell.api.project.create_file("IFC4")
MM = 1000.0

# =============================================================================== projet
project = A.root.create_entity(f, ifc_class="IfcProject", name="Bibliothèque Decimo")
project.LongName = "Bibliothèque Decimo — Abidjan — esquisse V5 (RDC d'immeuble existant)"
project.Description = "Esquisse V5 K&Démi : local RDC un seul niveau, arbre à livres, claustra Adinkra, D.A. terre, ombre et bois"
project.Phase = "ESQ"
units = [A.unit.add_si_unit(f, unit_type="LENGTHUNIT", prefix="MILLI"),
         A.unit.add_si_unit(f, unit_type="AREAUNIT"), A.unit.add_si_unit(f, unit_type="VOLUMEUNIT"),
         A.unit.add_si_unit(f, unit_type="PLANEANGLEUNIT")]
A.unit.assign_unit(f, units=units)
model = A.context.add_context(f, context_type="Model")
BODY = A.context.add_context(f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model)
AXIS = A.context.add_context(f, context_type="Model", context_identifier="Axis", target_view="GRAPH_VIEW", parent=model)
plan = A.context.add_context(f, context_type="Plan")
ANNOT = A.context.add_context(f, context_type="Plan", context_identifier="Annotation", target_view="PLAN_VIEW", parent=plan)

site = A.root.create_entity(f, ifc_class="IfcSite", name="Abidjan — parcelle Decimo")
site.Description = "Rue, trottoir et arbres d'alignement : contexte indicatif (relevé à faire)"
site.RefLatitude, site.RefLongitude = (5, 20, 0, 0), (-4, -1, -30, 0)
site.RefElevation = 0.0
building = A.root.create_entity(f, ifc_class="IfcBuilding", name="Immeuble existant — RDC Bibliothèque Decimo")
building.Description = "Immeuble existant avec logements aux étages ; seul le local du RDC est dans le périmètre"
storey = A.root.create_entity(f, ifc_class="IfcBuildingStorey", name="RDC")
storey.LongName = "Rez-de-chaussée — local bibliothèque (niveau fini ±0,00)"
storey.Elevation = 0.0
A.aggregate.assign_object(f, products=[site], relating_object=project)
A.aggregate.assign_object(f, products=[building], relating_object=site)
A.aggregate.assign_object(f, products=[storey], relating_object=building)
for el in (site, building, storey):
    A.geometry.edit_object_placement(f, product=el)
SITE_LP, STOREY_LP = site.ObjectPlacement, storey.ObjectPlacement

f.header.file_description.description = ("ViewDefinition [DesignTransferView_V1.0]",)
f.header.file_name.name = OUT.rsplit("/", 1)[-1]
f.header.file_name.time_stamp = "2026-10-14T00:00:00"
f.header.file_name.author = ("K&Démi",)
f.header.file_name.organization = ("K&Démi architecture · intérieur",)
f.header.file_name.preprocessor_version = f"IfcOpenShell {ifcopenshell.version}"
f.header.file_name.originating_system = "scripts/generer_ifc_v5.py"

# ============================================================================ styles D.A.
def colour(hexc):
    return f.createIfcColourRgb(None, *[int(hexc[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])

STYLES, MATS = {}, {}
def material(name, hexc, category, transparency=0.0, method="NOTDEFINED", spec=None):
    st = f.create_entity("IfcSurfaceStyle", Name=name, Side="BOTH", Styles=[f.create_entity(
        "IfcSurfaceStyleRendering", SurfaceColour=colour(hexc), Transparency=transparency,
        SpecularColour=f.createIfcNormalisedRatioMeasure(spec) if spec else None,
        SpecularHighlight=f.createIfcSpecularRoughness(0.4) if spec else None, ReflectanceMethod=method)])
    m = A.material.add_material(f, name=name, category=category)
    ifcopenshell.api.style.assign_material_style(f, material=m, style=st, context=BODY)
    STYLES[name], MATS[name] = st, m
    return name

M = dict(
    beton=material("Béton armé existant", "#A8A39B", "concrete"),
    enduit_ext=material("Enduit ciment existant", "#CFC8BC", "plaster"),
    maconnerie=material("Maçonnerie existante (agglos pleins)", "#B5AEA4", "block"),
    ba13=material("Plaque de plâtre BA13", "#EEE9E0", "gypsum"),
    ba13h=material("Plaque de plâtre hydrofuge BA13 H1", "#E3E8E2", "gypsum"),
    laine=material("Laine minérale acoustique", "#E2CF8E", "insulation"),
    ossature=material("Ossature métallique / vide technique", "#C9C9C9", "steel"),
    enduit_terre=material("KDEMI - Enduit terre (argile) sable ocre", "#CDAE88", "plaster"),
    btc=material("KDEMI - Parement BTC (brique de terre compressée)", "#B07D56", "brick"),
    terre_cuite=material("KDEMI - Terre cuite", "#B4583E", "ceramic"),
    tomette=material("KDEMI - Tomettes terre cuite", "#B8664A", "ceramic"),
    terrazzo=material("KDEMI - Terrazzo coulé sable, granulats terre cuite", "#D9CDBB", "stone"),
    chape=material("Chape ciment", "#BDB5AA", "concrete"),
    iroko=material("KDEMI - Bois iroko huilé", "#9A6B43", "wood", method="PLASTIC", spec=0.15),
    iroko_fonce=material("KDEMI - Bois iroko teinté ombre", "#6E4A2F", "wood", method="PLASTIC", spec=0.15),
    indigo=material("KDEMI - Accent indigo (peinture minérale)", "#2F3E6E", "paint"),
    zellige=material("KDEMI - Zellige indigo", "#33457A", "ceramic", method="PLASTIC", spec=0.45),
    sable=material("KDEMI - Enduit chaux sable", "#E6D6BF", "plaster"),
    plafond=material("KDEMI - Plafond acoustique fibres de bois, teinte sable", "#D8C7A8", "wood"),
    acier=material("KDEMI - Acier thermolaqué encre", "#2B2420", "steel", method="METAL", spec=0.25),
    verre=material("Vitrage feuilleté clair", "#CFE3EA", "glass", transparency=0.7, method="GLASS", spec=0.6),
    tissu=material("KDEMI - Tissu terre cuite", "#A9533A", "textile"),
    tissu_indigo=material("KDEMI - Tissu indigo", "#34426F", "textile"),
    sanitaire=material("Céramique sanitaire blanche", "#F2EFEA", "ceramic", method="PLASTIC", spec=0.5),
    pvc=material("PVC gris (descentes EU/EV existantes)", "#8E8E8E", "plastic"),
    isolant_noir=material("Gaine isolante liaisons frigorifiques", "#1E1E1E", "plastic"),
    led=material("Diffuseur LED 2700 K", "#FFF3D6", "plastic", method="PLASTIC", spec=0.4),
    blanc_equip=material("Équipement technique blanc", "#F4F3EF", "plastic"),
    gris_equip=material("Équipement technique gris", "#6F6F6F", "steel"),
    livre_1=material("Livres - indigo", "#3A4675", "paper"), livre_2=material("Livres - terre cuite", "#B4583E", "paper"),
    livre_3=material("Livres - sable", "#E2D0B0", "paper"), livre_4=material("Livres - ocre", "#C49248", "paper"),
    livre_5=material("Livres - encre", "#3B302A", "paper"), livre_6=material("Livres - olive", "#6F7F52", "paper"),
    vegetal=material("Végétal (contexte)", "#5E7A48", "vegetation"),
    tronc=material("Écorce (contexte)", "#5A4636", "vegetation"),
    trottoir=material("Dallage trottoir (contexte)", "#C3BCB0", "stone"),
    chaussee=material("Enrobé chaussée (contexte)", "#6E6A66", "asphalt"),
    bordure=material("Bordure béton (contexte)", "#A8A39B", "concrete"),
)
LIVRES = [M["livre_%d" % i] for i in range(1, 7)]

# ======================================================================= géométrie (m -> mm)
P3 = lambda x, y, z: f.createIfcCartesianPoint((float(x) * MM, float(y) * MM, float(z) * MM))
P2 = lambda x, y: f.createIfcCartesianPoint((float(x) * MM, float(y) * MM))
D3 = lambda *v: f.createIfcDirection(tuple(float(a) for a in v))
D2 = lambda *v: f.createIfcDirection(tuple(float(a) for a in v))
DZ = D3(0, 0, 1)

def ax3(x=0.0, y=0.0, z=0.0, axis=None, ref=None):
    return f.createIfcAxis2Placement3D(P3(x, y, z), D3(*axis) if axis else None, D3(*ref) if ref else None)

def lp(rel=None, x=0.0, y=0.0, z=0.0, ang=0.0):
    a = math.radians(ang)
    ref = (math.cos(a), math.sin(a), 0.0) if ang else None
    return f.createIfcLocalPlacement(rel or STOREY_LP, ax3(x, y, z, (0, 0, 1) if ang else None, ref))

def polyline2d(pts):
    pts = [tuple(p) for p in pts]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return f.createIfcPolyline([P2(x, y) for x, y in pts])

def profile(outer, holes=()):
    if holes:
        return f.createIfcArbitraryProfileDefWithVoids("AREA", None, polyline2d(outer), [polyline2d(h) for h in holes])
    return f.createIfcArbitraryClosedProfileDef("AREA", None, polyline2d(outer))

def extrude(prof, pos, depth, direction=None):
    return f.createIfcExtrudedAreaSolid(prof, pos, direction or DZ, float(depth) * MM)

def box(x0, y0, x1, y1, z0, z1):
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    prof = f.createIfcRectangleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2((x0 + x1) / 2, (y0 + y1) / 2), None),
                                          (x1 - x0) * MM, (y1 - y0) * MM)
    return extrude(prof, ax3(0, 0, z0), z1 - z0)

def rbox(cx, cy, L, W, ang, z0, z1):
    a = math.radians(ang)
    prof = f.createIfcRectangleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(cx, cy), D2(math.cos(a), math.sin(a))),
                                          L * MM, W * MM)
    return extrude(prof, ax3(0, 0, z0), z1 - z0)

def prism(outer, z0, z1, holes=()):
    return extrude(profile(outer, holes), ax3(0, 0, z0), z1 - z0)

def cyl(cx, cy, r, z0, z1):
    prof = f.createIfcCircleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(cx, cy), None), r * MM)
    return extrude(prof, ax3(0, 0, z0), z1 - z0)

def tube(cx, cy, r, t, z0, z1):
    prof = f.createIfcCircleHollowProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(cx, cy), None), r * MM, t * MM)
    return extrude(prof, ax3(0, 0, z0), z1 - z0)

def xz_prism(outer, y0, y1, holes=()):
    """Profil vertical (x, z) extrudé selon y de y0 à y1."""
    return extrude(profile(outer, holes), ax3(0, y1, 0, (0, -1, 0), (1, 0, 0)), y1 - y0)

def yz_prism(outer, x0, x1, holes=()):
    """Profil vertical (y, z) extrudé selon x de x0 à x1."""
    return extrude(profile(outer, holes), ax3(x0, 0, 0, (1, 0, 0), (0, 1, 0)), x1 - x0)

def revolve(pts_rz, cx, cy):
    return f.createIfcRevolvedAreaSolid(profile(pts_rz), ax3(cx, cy, 0, (0, -1, 0), (1, 0, 0)),
                                        f.createIfcAxis1Placement(P3(0, 0, 0), D3(0, 1, 0)), 2 * math.pi)

def sweep(pts, r):
    return f.createIfcSweptDiskSolid(f.createIfcPolyline([P3(*p) for p in pts]), r * MM, None, None, None)

def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]

def arch(x0, x1, z0, zs, n=24):
    r = (x1 - x0) / 2; c = (x0 + x1) / 2
    return ([(x0, z0), (x1, z0), (x1, zs)] + [(c + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(0, math.pi, n)[1:-1]]
            + [(x0, zs)])

def styled(items, mat):
    for it in items:
        f.createIfcStyledItem(it, [STYLES[mat]], None)
    return list(items)

def rep_type(items):
    if all(i.is_a("IfcMappedItem") for i in items):
        return "MappedRepresentation"
    if all(i.is_a() in ("IfcExtrudedAreaSolid", "IfcRevolvedAreaSolid") for i in items):
        return "SweptSolid"
    if all(i.is_a("IfcSweptAreaSolid") or i.is_a("IfcSweptDiskSolid") for i in items):
        return "AdvancedSweptSolid"
    return "SolidModel"

def shape(items):
    return f.createIfcShapeRepresentation(BODY, "Body", rep_type(items), items)

# ===================================================================== produits et propriétés
EXISTANT = "Existant porteur - ne pas toucher"
def pset(el, name, props):
    ps = A.pset.add_pset(f, product=el, name=name)
    A.pset.edit_pset(f, pset=ps, properties=props)
    return ps

def product(cls, name, items=None, mat=None, container=None, placement=None, predefined=None, desc=None,
            object_type=None, tag=None, props=None):
    p = A.root.create_entity(f, ifc_class=cls, name=name, predefined_type=predefined)
    if desc:
        p.Description = desc
    if object_type:
        p.ObjectType = object_type
    if tag and hasattr(p, "Tag"):
        p.Tag = tag
    if container is not False:
        A.spatial.assign_container(f, products=[p], relating_structure=container or storey)
    p.ObjectPlacement = placement or lp(SITE_LP if container is site else None)
    if items:
        p.Representation = f.createIfcProductDefinitionShape(None, None, [shape(items)])
    if mat:
        A.material.assign_material(f, products=[p], type="IfcMaterial", material=MATS[mat])
    pset(p, "KDEMI_Esquisse", {"Indice": "V5", "Phase": "ESQ", **(props or {})})
    return p

def existing(el, common=None, extra=None):
    el.Description = EXISTANT
    pset(el, "KDEMI_Existant", {"Statut": EXISTANT, "Origine": "Immeuble existant (logements aux étages)",
                                "Intervention": "Aucune — toute réservation ou fixation lourde à valider par le BET structure",
                                **(extra or {})})
    if common:
        pset(el, common, {"LoadBearing": True, "Status": "EXISTING"})

# ---------------------------------------------------------------- murs composés (layer sets)
WALL_TYPES, WINFO = {}, {}
def wall_type(name, layers, desc, predefined="STANDARD"):
    t = A.root.create_entity(f, ifc_class="IfcWallType", name=name, predefined_type=predefined)
    t.Description = desc
    ls = A.material.add_material_set(f, name=name, set_type="IfcMaterialLayerSet")
    for mat, th, lname in layers:
        lay = A.material.add_layer(f, layer_set=ls, material=MATS[M[mat]], name=lname)
        A.material.edit_layer(f, layer=lay, attributes={"LayerThickness": th * MM})
    A.material.assign_material(f, products=[t], type="IfcMaterialLayerSet", material=ls)
    WALL_TYPES[name] = (t, sum(l[1] for l in layers), M[layers[len(layers) // 2][0]])
    return name

WT_VOILE = wall_type("EX - Voile BA existant 180", [("enduit_ext", 0.015, "Enduit"), ("beton", 0.150, "Voile béton armé"),
                                                     ("enduit_ext", 0.015, "Enduit")], "Voile porteur existant (mitoyen / refend)")
WT_MACO = wall_type("EX - Maçonnerie porteuse existante 180", [("enduit_ext", 0.015, "Enduit"), ("maconnerie", 0.150, "Agglos pleins"),
                                                               ("enduit_ext", 0.015, "Enduit")], "Mur porteur existant façade arrière / courette")
WT_C100 = wall_type("NV - Cloison 100/50 BA13×2 + LM45", [("ba13", 0.0125, "BA13"), ("ba13", 0.0125, "BA13"), ("laine", 0.050, "Ossature 48 + laine minérale 45"),
                                                          ("ba13", 0.0125, "BA13"), ("ba13", 0.0125, "BA13")],
                    "Cloison distributive toute hauteur (sous-face de dalle), Rw ≈ 45 dB", "PARTITIONING")
WT_C100H = wall_type("NV - Cloison hydro 100/50 BA13 H1×2 + LM45", [("ba13h", 0.0125, "BA13 H1"), ("ba13h", 0.0125, "BA13 H1"),
                                                                   ("laine", 0.050, "Ossature 48 + laine minérale 45"),
                                                                   ("ba13h", 0.0125, "BA13 H1"), ("ba13h", 0.0125, "BA13 H1")],
                     "Cloison de WC, parements hydrofuges", "PARTITIONING")
WT_DTECH = wall_type("NV - Doublage technique 300 (TD encastré)", [("ossature", 0.275, "Ossature + vide technique"), ("ba13", 0.0125, "BA13"),
                                                                   ("ba13", 0.0125, "BA13")],
                     "Doublage sur mur existant (non fixé structurellement), niche du tableau divisionnaire", "SOLIDWALL")
WT_DNICHE = wall_type("NV - Doublage cintré 350 (niches)", [("ossature", 0.315, "Ossature cintrée + vide"), ("ba13", 0.025, "BA13 cintrable 2×"),
                                                            ("enduit_terre", 0.010, "Enduit terre")],
                      "Doublage autoportant devant le mur du fond, 3 niches cintrées", "SOLIDWALL")
WT_PLACARD = wall_type("NV - Cloison placard technique 100", [("ba13", 0.0125, "BA13"), ("ba13", 0.0125, "BA13"), ("laine", 0.050, "Ossature 48 + LM"),
                                                              ("ba13", 0.0125, "BA13"), ("ba13", 0.0125, "BA13")],
                       "Cloison du placard technique (porte pleine)", "PARTITIONING")

def wall(name, x0, y0, x1, y1, z0, z1, wtype, extra_items=None):
    """Mur axé sur x ou y. Corps à gauche de la ligne de référence (face y0 si selon x, face x1 si selon y)."""
    t, th, core = WALL_TYPES[wtype]
    along_x = (x1 - x0) >= (y1 - y0)
    if along_x:
        L, T = x1 - x0, y1 - y0
        place = lp(None, x0, y0, z0, 0.0)
    else:
        L, T = y1 - y0, x1 - x0
        place = lp(None, x1, y0, z0, 90.0)
    items = styled([box(0, 0, L, T, 0, z1 - z0)], core)
    w = product("IfcWall", name, items, container=storey, placement=place,
                predefined="PARTITIONING" if wtype.startswith("NV - Cloison") else "STANDARD",
                props={"Epaisseur_mm": round(T * MM), "Composition": wtype})
    axis = f.createIfcShapeRepresentation(AXIS, "Axis", "Curve2D", [f.createIfcPolyline([P2(0, 0), P2(L, 0)])])
    w.Representation.Representations = list(w.Representation.Representations) + [axis]
    A.type.assign_type(f, related_objects=[w], relating_type=t)
    WINFO[w.id()] = dict(L=L, T=T, alongx=along_x, o=(x0, y0) if along_x else (x1, y0))
    return w

def wall_local(w, x, y):
    """Coordonnées monde (x, y) -> repère local du mur (u le long, v dans l'épaisseur)."""
    ox, oy = WINFO[w.id()]['o']
    return (x - ox, y - oy) if WINFO[w.id()]['alongx'] else (y - oy, ox - x)

def opening(w, name, u0, u1, z0, z1, v0=-0.05, v1=None, kind="OPENING", profile_uz=None):
    v1 = WINFO[w.id()]['T'] + 0.05 if v1 is None else v1
    if profile_uz is not None:
        item = extrude(profile(profile_uz), ax3(0, v1, 0, (0, -1, 0), (1, 0, 0)), v1 - v0)
    else:
        item = box(u0, v0, u1, v1, z0, z1)
    o = product("IfcOpeningElement", name, [item], container=False, placement=lp(w.ObjectPlacement), predefined=kind)
    A.feature.add_feature(f, feature=o, element=w)
    return o

def reservation(w, name, x, y, z, r=0.05, note=""):
    u, _ = wall_local(w, x, y)
    prof = f.createIfcCircleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(u, z - w.ObjectPlacement.RelativePlacement.Location.Coordinates[2] / MM), None), r * MM)
    item = extrude(prof, ax3(0, WINFO[w.id()]['T'] + 0.05, 0, (0, -1, 0), (1, 0, 0)), WINFO[w.id()]['T'] + 0.1)
    o = product("IfcOpeningElement", name, [item], container=False, placement=lp(w.ObjectPlacement), predefined="OPENING",
                props={"Diametre_mm": round(2 * r * MM), "Usage": "Liaisons frigorifiques splits", "Note": note})
    A.feature.add_feature(f, feature=o, element=w)
    return o

# ================================================================== 1. structure existante
Z_DALLE_BAS, Z_DALLE_HAUT = 3.30, 3.50          # dalle haute (plancher des logements)
Z_FP = 2.85                                      # faux-plafond fini
Z_DALLAGE = -0.07                                # arase du dallage existant (sous chape + terrazzo)
XE0, XE1, YE0, YE1 = -0.09, 6.69, -0.09, 7.59    # emprise extérieure 6,78 × 7,68
XI0, XI1, YI1 = 0.09, 6.51, 7.41                 # nus intérieurs des murs existants

dalle = product("IfcSlab", "Dalle haute BA existante (plancher des logements)",
                styled([box(XE0, YE0, XE1, YE1, Z_DALLE_BAS, Z_DALLE_HAUT)], M["beton"]), M["beton"], predefined="FLOOR",
                props={"Epaisseur_mm": 200})
existing(dalle, "Pset_SlabCommon")
dallage = product("IfcSlab", "Dallage BA existant sur terre-plein",
                  styled([box(XE0, YE0, XE1, YE1, Z_DALLAGE - 0.20, Z_DALLAGE)], M["beton"]), M["beton"], predefined="BASESLAB",
                  props={"Epaisseur_mm": 200})
existing(dallage, "Pset_SlabCommon")

COLS = {"P1": (-0.09, -0.09, 2.85), "P2": (3.175, -0.09, 2.85), "P3": (6.44, -0.09, 2.85),
        "P4": (-0.09, 3.625, Z_DALLE_BAS), "P5": (6.44, 3.625, Z_DALLE_BAS),
        "P6": (-0.09, 7.34, Z_DALLE_BAS), "P7": (6.44, 7.34, Z_DALLE_BAS)}
for tag, (x, y, zt) in COLS.items():
    c = product("IfcColumn", f"Poteau BA existant {tag} 25×25", styled([box(x, y, x + 0.25, y + 0.25, Z_DALLAGE, zt)], M["beton"]),
                M["beton"], predefined="COLUMN", tag=tag)
    existing(c, "Pset_ColumnCommon")
poutre = product("IfcBeam", "Poutre BA existante de devanture 25×45", styled([box(XE0, -0.09, XE1, 0.16, 2.85, Z_DALLE_BAS)], M["beton"]),
                 M["beton"], predefined="BEAM", tag="PT1", props={"Retombee_mm": 450})
existing(poutre, "Pset_BeamCommon")

W = {}
W["O1"] = wall("Voile mitoyen ouest (existant) — tronçon sud", XE0, 0.16, XI0, 3.625, Z_DALLAGE, Z_DALLE_BAS, WT_VOILE)
W["O2"] = wall("Voile mitoyen ouest (existant) — tronçon nord", XE0, 3.875, XI0, 7.34, Z_DALLAGE, Z_DALLE_BAS, WT_VOILE)
W["E1"] = wall("Voile mitoyen est (existant) — tronçon sud", XI1, 0.16, XE1, 3.625, Z_DALLAGE, Z_DALLE_BAS, WT_VOILE)
W["E2"] = wall("Voile mitoyen est (existant) — tronçon nord", XI1, 3.875, XE1, 7.34, Z_DALLAGE, Z_DALLE_BAS, WT_VOILE)
W["N1"] = wall("Mur porteur façade arrière / courette (existant)", 0.16, YI1, 6.44, YE1, Z_DALLAGE, Z_DALLE_BAS, WT_MACO)
for k in ("O1", "O2", "E1", "E2", "N1"):
    existing(W[k], "Pset_WallCommon", {"Mitoyen": k[0] in "OE"})

# ================================================================= 2. cloisons et doublages
Z0 = Z_DALLAGE
W["C1"] = wall("Cloison WC / dégagement — espace de travail", XI0, 5.25, 3.05, 5.35, Z0, Z_DALLE_BAS, WT_C100H)
W["C2"] = wall("Cloison WC / dégagement", 1.75, 5.35, 1.85, YI1, Z0, Z_DALLE_BAS, WT_C100H)
W["C3"] = wall("Cloison dégagement — salle de lecture", 2.95, 5.35, 3.05, YI1, Z0, Z_DALLE_BAS, WT_C100)
W["C4"] = wall("Cloison placard technique — façade", 2.25, 6.91, 2.95, 7.01, Z0, Z_DALLE_BAS, WT_PLACARD)
W["C5"] = wall("Cloison placard technique — côté", 2.25, 7.01, 2.35, YI1, Z0, Z_DALLE_BAS, WT_PLACARD)
W["DT"] = wall("Doublage technique du tableau divisionnaire", 6.21, 0.16, XI1, 1.40, Z0, Z_DALLE_BAS, WT_DTECH)
W["DN"] = wall("Doublage cintré des niches (mur du fond)", 3.05, 7.06, XI1, YI1, Z0, Z_DALLE_BAS, WT_DNICHE)

# portes intérieures (ouvertures réelles + remplissage)
def plan_swing(d, leaves):
    """Débattement en plan (contexte Annotation) : [(charnière, largeur, sens ouvert, sens fermé)]."""
    curves = []
    for (hx, hy), leaf, (dx, dy), (cx, cy) in leaves:
        a_open, a_c = math.atan2(dy, dx), math.atan2(cy, cx)
        da = (a_open - a_c + math.pi) % (2 * math.pi) - math.pi
        curves.append(f.createIfcPolyline([P2(hx, hy), P2(hx + leaf * dx, hy + leaf * dy)]))
        curves.append(f.createIfcPolyline([P2(hx + leaf * math.cos(a_c + da * t), hy + leaf * math.sin(a_c + da * t))
                                           for t in np.linspace(0, 1, 16)]))
    rep = f.createIfcShapeRepresentation(ANNOT, "Annotation", "GeometricCurveSet", [f.createIfcGeometricCurveSet(curves)])
    d.Representation.Representations = list(d.Representation.Representations) + [rep]

def make_door(name, w, x0, y0, x1, y1, leaf, hinge, swing_to, closed, h=2.10, mat="iroko", full=False, tag=None, desc=None):
    """hinge : charnière (x, y) au nu de la baie ; swing_to / closed : directions du vantail ouvert / fermé."""
    u0, _ = wall_local(w, x0, y0); u1, _ = wall_local(w, x1, y1)
    o = opening(w, f"Baie {name}", min(u0, u1), max(u0, u1), 0.0 - Z0, h + 0.02 - Z0)
    fr = 0.04
    if WINFO[w.id()]['alongx']:
        ya, yb = min(y0, y1), max(y0, y1); cy = (ya + yb) / 2
        items = styled([box(x0, ya, x0 + fr, yb, 0, h), box(x1 - fr, ya, x1, yb, 0, h), box(x0, ya, x1, yb, h - fr, h + 0.02)], M["iroko_fonce"])
        items += styled([box(x0 + fr, cy - 0.02, x1 - fr, cy + 0.02, 0.01, h - fr)], M[mat])
    else:
        xa, xb = min(x0, x1), max(x0, x1); cx = (xa + xb) / 2
        items = styled([box(xa, y0, xb, y0 + fr, 0, h), box(xa, y1 - fr, xb, y1, 0, h), box(xa, y0, xb, y1, h - fr, h + 0.02)], M["iroko_fonce"])
        items += styled([box(cx - 0.02, y0 + fr, cx + 0.02, y1 - fr, 0.01, h - fr)], M[mat])
    d = product("IfcDoor", name, items, M[mat], predefined="DOOR", tag=tag, desc=desc,
                props={"Passage_utile_mm": round(leaf * MM), "Porte_pleine": full})
    d.OverallHeight, d.OverallWidth = h * MM, (abs(x1 - x0) if WINFO[w.id()]['alongx'] else abs(y1 - y0)) * MM
    d.OperationType = "SINGLE_SWING_LEFT"
    A.feature.add_filling(f, opening=o, element=d)
    plan_swing(d, [(hinge, leaf, swing_to, closed)])
    pset(d, "Pset_DoorCommon", {"IsExternal": False})
    return d

D_DEG = make_door("Porte dégagement / sanitaires", W["C3"], 2.95, 5.50, 3.05, 6.43, 0.83, (2.95, 5.50), (-1, 0), (0, 1), tag="P02",
                  desc="Bloc-porte bois iroko 0,83 × 2,10, poussant côté dégagement")
D_WC = make_door("Porte WC", W["C2"], 1.75, 5.50, 1.85, 6.43, 0.83, (1.75, 5.50), (-1, 0), (0, 1), tag="P03",
                 desc="Bloc-porte bois iroko 0,83 × 2,10, condamnation libre/occupé")
D_PL = make_door("Porte pleine placard technique", W["C4"], 2.38, 6.91, 2.93, 7.01, 0.55, (2.93, 6.91), (0, -1), (-1, 0), tag="P04",
                 mat="indigo", full=True, desc="Porte pleine 0,55 × 2,10 (EI30 conseillée), serrure à clé, peinte indigo")

# niches cintrées : vraies ouvertures dans le doublage
NICHES = [(3.20, 4.10, 1.95), (4.18, 5.43, 1.80), (5.51, 6.41, 1.95)]
NICHE_OPEN = []
for k, (x0, x1, zs) in enumerate(NICHES, 1):
    u0 = x0 - 3.05; u1 = x1 - 3.05
    NICHE_OPEN.append(opening(W["DN"], f"Niche cintrée {k}", 0, 0, 0, 0, profile_uz=arch(u0, u1, 0.0 - Z0, zs - Z0), kind="RECESS"))

# claustra terre cuite : modules Adinkra (Eban « la clôture » et Nsoromma « l'étoile »)
def block_items(kind, d):
    s = 0.20
    if kind == "EBAN":
        sq = [(0, 0), (s, 0), (s, s), (0, s)]
        inner = [(0.02, 0.02), (s - 0.02, 0.02), (s - 0.02, s - 0.02), (0.02, s - 0.02)]
        dia = [(0.10, 0.02), (0.18, 0.10), (0.10, 0.18), (0.02, 0.10)]
        dia_in = [(0.10, 0.048), (0.152, 0.10), (0.10, 0.152), (0.048, 0.10)]
        core = [(0.085, 0.085), (0.115, 0.085), (0.115, 0.115), (0.085, 0.115)]
        prof = [profile(sq, [inner]), profile(dia, [dia_in]), profile(core)]
    else:
        star = []
        for i in range(16):
            r = 0.082 if i % 2 == 0 else 0.042
            a = math.pi / 2 + i * math.pi / 8
            star.append((0.10 + r * math.cos(a), 0.10 + r * math.sin(a)))
        corners = [[(cx + 0.012 * math.cos(a), cy + 0.012 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
                   for cx, cy in ((0.025, 0.025), (0.175, 0.025), (0.175, 0.175), (0.025, 0.175))]
        prof = [profile([(0, 0), (s, 0), (s, s), (0, s)], [star] + corners)]
    return styled([extrude(p, ax3(0, 0, 0), d) for p in prof], M["terre_cuite"])

BLOCK_MAPS = {}
def block_map(kind, d):
    key = (kind, d)
    if key not in BLOCK_MAPS:
        BLOCK_MAPS[key] = f.createIfcRepresentationMap(ax3(), f.createIfcShapeRepresentation(BODY, "Body", "SweptSolid", block_items(kind, d)))
    return BLOCK_MAPS[key]

def claustra_items(origin, u_dir, n_u, n_v, d, normal):
    """Grille de modules 20 × 20 : origin = coin bas, u_dir horizontal, v = verticale, extrusion selon normal."""
    items = []
    ox, oy, oz = origin
    for i in range(n_u):
        for j in range(n_v):
            kind = "EBAN" if (i + j) % 2 == 0 else "NSOROMMA"
            op = f.createIfcCartesianTransformationOperator3D(D3(*u_dir, 0), D3(0, 0, 1), P3(ox + u_dir[0] * 0.2 * i, oy + u_dir[1] * 0.2 * i, oz + 0.2 * j),
                                                              1.0, D3(*normal))
            items.append(f.createIfcMappedItem(block_map(kind, d), op))
    return items

ADINKRA = ("Modules 20 × 20 cm en terre cuite alternés : « Eban » (la clôture : sécurité, foyer) et "
           "« Nsoromma » (l'étoile : enfant du ciel, veille) ; Gye Nyame exclu")
claustra = product("IfcWall", "Claustra terre cuite Adinkra — espace de travail / salle de lecture",
                   claustra_items((3.05, 3.45, 0.05), (0, 1), 9, 14, 0.10, (-1, 0, 0)), M["terre_cuite"],
                   predefined="USERDEFINED", object_type="CLAUSTRA", desc=ADINKRA,
                   props={"Motif": "Eban / Nsoromma", "Module_mm": "200 × 200 × 100", "Nombre_modules": 126})
claustra_cadre = product("IfcMember", "Cadre iroko du claustra (socle, poteau d'about, lisse haute)",
                         styled([box(2.95, 3.45, 3.05, 5.25, 0.0, 0.05), box(2.95, 3.35, 3.05, 3.45, 0.0, Z_FP)], M["iroko"]),
                         M["iroko"], predefined="MEMBER")

# ======================================================================== 3. devanture
devanture = product("IfcCurtainWall", "Devanture vitrée sur rue (menuiserie acier thermolaqué encre)", None, None,
                    predefined="USERDEFINED", object_type="DEVANTURE",
                    desc="Devanture dans la baie existante entre poteaux P1-P2-P3 et sous poutre PT1 ; vitrages feuilletés 44.2")
Y_CW0, Y_CW1 = 0.02, 0.12
def cw_part(cls, name, items, mat, predefined):
    p = product(cls, name, items, mat, container=False, predefined=predefined)
    A.aggregate.assign_object(f, products=[p], relating_object=devanture)
    return p

MULL = [(0.16, 0.21), (1.6425, 1.6925), (3.125, 3.175), (3.425, 3.475), (4.825, 4.875), (5.635, 5.685), (6.39, 6.44)]
for k, (a, b) in enumerate(MULL, 1):
    cw_part("IfcMember", f"Montant devanture M{k}", styled([box(a, Y_CW0, b, Y_CW1, 0.0, 2.85)], M["acier"]), M["acier"], "MULLION")
for k, (a, b) in enumerate(((0.21, 3.125), (3.475, 6.39)), 1):
    cw_part("IfcMember", f"Imposte devanture T{k}", styled([box(a, Y_CW0, b, Y_CW1, 2.15, 2.20)], M["acier"]), M["acier"], "TRANSOM")
    cw_part("IfcMember", f"Traverse haute devanture H{k}", styled([box(a, Y_CW0, b, Y_CW1, 2.80, 2.85)], M["acier"]), M["acier"], "TRANSOM")
for k, (a, b) in enumerate(((0.21, 1.6425), (1.6925, 3.125), (4.875, 5.635), (5.685, 6.39)), 1):
    cw_part("IfcMember", f"Soubassement devanture S{k}", styled([box(a, Y_CW0, b, Y_CW1, 0.0, 0.10)], M["acier"]), M["acier"], "TRANSOM")
    cw_part("IfcPlate", f"Vitrage fixe devanture V{k}", styled([box(a, 0.065, b, 0.075, 0.10, 2.15)], M["verre"]), M["verre"], "CURTAIN_PANEL")
for k, (a, b) in enumerate(((0.21, 1.6425), (1.6925, 3.125), (3.475, 4.825), (4.875, 5.635), (5.685, 6.39)), 1):
    cw_part("IfcPlate", f"Vitrage imposte devanture I{k}", styled([box(a, 0.065, b, 0.075, 2.20, 2.80)], M["verre"]), M["verre"], "CURTAIN_PANEL")
# porte d'entrée double, vantaux inégaux 0,90 + 0,45, ouvrant vers l'intérieur
dx0, dx1, dxm = 3.475, 4.825, 4.375
items = styled([box(dx0, Y_CW0, dxm, Y_CW1, 2.10, 2.15), box(dxm, Y_CW0, dx1, Y_CW1, 2.10, 2.15)], M["acier"])
for a, b in ((dx0, dxm), (dxm, dx1)):
    items += styled([box(a, 0.045, a + 0.06, 0.095, 0.0, 2.10), box(b - 0.06, 0.045, b, 0.095, 0.0, 2.10),
                     box(a + 0.06, 0.045, b - 0.06, 0.095, 0.0, 0.18), box(a + 0.06, 0.045, b - 0.06, 0.095, 2.04, 2.10)], M["acier"])
    items += styled([box(a + 0.06, 0.066, b - 0.06, 0.074, 0.18, 2.04)], M["verre"])
items += styled([box(dxm - 0.10, 0.10, dxm - 0.08, 0.13, 0.75, 1.65), box(dxm + 0.08, 0.10, dxm + 0.10, 0.13, 0.75, 1.65)], M["iroko"])
porte = cw_part("IfcDoor", "Porte d'entrée vitrée double 0,90 + 0,45", items, M["acier"], "DOOR")
porte.Tag = "P01"
porte.OverallHeight, porte.OverallWidth, porte.OperationType = 2150.0, 1350.0, "DOUBLE_DOOR_SINGLE_SWING"
porte.Description = "Vantail principal 0,90 (passage PMR), semi-fixe 0,45 ; ouvrant vers l'intérieur ; seuil plat ≤ 2 cm ; poignées iroko"
pset(porte, "Pset_DoorCommon", {"IsExternal": True, "HandicapAccessible": True})
plan_swing(porte, [((dx0, Y_CW1), 0.90, (0, 1), (1, 0)), ((dx1, Y_CW1), 0.45, (0, 1), (-1, 0))])

# claustra Adinkra en imposte, côté intérieur (filtre la lumière du sud)
for k, (x0, n) in enumerate(((0.2675, 14), (4.93, 7)), 1):
    sd = product("IfcShadingDevice", f"Claustra Adinkra d'imposte {k} (intérieur devanture)",
                 claustra_items((x0, 0.13, 2.20), (1, 0), n, 3, 0.08, (0, 1, 0)), M["terre_cuite"],
                 predefined="USERDEFINED", object_type="CLAUSTRA", desc=ADINKRA + " ; posé en retrait du vitrage d'imposte")

# enseigne : bandeau indigo sur la poutre + lettres découpées DECIMO (DM Serif Display)
FP = FontProperties(fname=ROOT + "/charte/fonts/dm-serif-display-latin-400-normal.ttf")
def text_polys(txt, size, x0, z0):
    tp = TextPath((0, 0), txt, size=100, prop=FP)
    k = size / 100.0
    rings = [np.array(r) * k for r in tp.to_polygons() if len(r) > 3]
    polys = sorted([Polygon(r).buffer(0) for r in rings], key=lambda p: -p.area)
    outers = []
    for p in polys:
        host = next((o for o in outers if o[0].contains(p.representative_point())), None)
        if host is not None and not any(h.contains(p.representative_point()) for h in host[1]):
            host[1].append(p)
        else:
            outers.append([p, []])
    w = tp.get_extents().width * k
    out = []
    for o, holes in outers:
        o = orient(o)
        out.append(([(x0 - w / 2 + x, z0 + z) for x, z in list(o.exterior.coords)[:-1]],
                    [[(x0 - w / 2 + x, z0 + z) for x, z in list(h.exterior.coords)[:-1]] for h in holes]))
    return out

ens = styled([box(2.30, -0.12, 4.30, -0.09, 2.92, 3.24)], M["indigo"])
for outer, holes in text_polys("DECIMO", 0.20, 3.30, 3.00):
    ens += styled([xz_prism(outer, -0.15, -0.12, holes)], M["sable"])
for outer, holes in text_polys("BIBLIOTHÈQUE", 0.055, 3.30, 2.945):
    ens += styled([xz_prism(outer, -0.135, -0.12, holes)], M["sable"])
product("IfcBuildingElementProxy", "Enseigne DECIMO (bandeau indigo, lettres sable rétroéclairées)", ens, M["indigo"],
        predefined="USERDEFINED", object_type="ENSEIGNE", desc="Bandeau 2,00 × 0,32 fixé sur la poutre existante (fixation légère à valider)")

# ====================================================================== 4. arbre à livres
CX, CY = 4.55, 5.25
tree = styled([cyl(CX, CY, 0.46, 0.0, 0.08), cyl(CX, CY, 0.18, 0.08, 2.25)], M["iroko"])
LEVELS = [0.08 + 0.34 * k for k in range(7)]
tree += styled([cyl(CX, CY, 0.45, z, z + 0.025) for z in LEVELS[1:]], M["iroko"])
tree += styled([rbox(CX + 0.32 * math.cos(math.radians(a)), CY + 0.32 * math.sin(math.radians(a)), 0.27, 0.02, a, 0.08, LEVELS[-1] + 0.025)
                for a in range(0, 360, 45)], M["iroko"])
rng = random.Random(7)
for z in LEVELS[:-1]:
    zb = z + (0.025 if z > 0.1 else 0.0)
    for s in range(8):
        a0 = math.radians(s * 45 + 4); a1 = math.radians(s * 45 + 41)
        a = a0
        while a < a1 - 0.05:
            da = rng.uniform(0.06, 0.12)
            am = a + da / 2
            h = rng.uniform(0.20, 0.29)
            r = 0.31
            tree += styled([rbox(CX + r * math.cos(am), CY + r * math.sin(am), 0.20, max(r * da - 0.004, 0.012), math.degrees(am), zb, zb + h)],
                           rng.choice(LIVRES))
            a += da
zc = np.linspace(2.10, 3.20, 26)
rc = 0.18 + 1.14 * ((zc - 2.10) / 1.10) ** 2.2
canopy = [(r, z) for r, z in zip(rc, zc)] + [(max(r - 0.04, 0.14), z - 0.03) for r, z in zip(rc[::-1], zc[::-1])]
tree += styled([revolve(canopy, CX, CY)], M["iroko"])
for k in range(12):
    a = math.radians(k * 30 + 15)
    pts = []
    for t in np.linspace(0, 1, 9):
        z = 1.95 + t * (3.13 - 1.95)
        zz = max(z, 2.10)
        r = 0.18 + 1.14 * ((zz - 2.10) / 1.10) ** 2.2 - 0.07 if z > 2.10 else 0.19
        pts.append((CX + r * math.cos(a), CY + r * math.sin(a), z))
    tree += styled([sweep(pts, 0.018)], M["iroko_fonce"])
arbre = product("IfcFurniture", "DECIMO_L01 Arbre à livres (sculpture sur mesure)", tree, M["iroko"], predefined="SHELF", tag="L01",
                desc="Fût Ø 36 et 6 plateaux tournants Ø 90 garnis de livres ; 12 branches cintrées portant une canopée bois "
                     "évasée Ø 2,64 qui monte dans la coupole indigo du faux-plafond (sommet +3,20)",
                props={"Diametre_plateaux_mm": 900, "Diametre_canopee_mm": 2640, "Hauteur_mm": 3200,
                       "Passage_libre_autour_mm": 900})

# ========================================================================= 5. mobilier
def ftype(name, items, cls="IfcFurnitureType", predefined="NOTDEFINED", mat=None):
    t = A.root.create_entity(f, ifc_class=cls, name=name, predefined_type=predefined)
    t.RepresentationMaps = [f.createIfcRepresentationMap(ax3(), shape(items))]
    if hasattr(t, "AssemblyPlace"):
        t.AssemblyPlace = "FACTORY"
    if mat:
        A.material.assign_material(f, products=[t], type="IfcMaterial", material=MATS[mat])
    return t

def inst(t, name, x, y, ang=0.0, cls="IfcFurniture", tag=None, z=0.0, predefined=None):
    p = product(cls, name, None, None, placement=lp(None, x, y, z, ang), tag=tag, predefined=predefined)
    A.type.assign_type(f, related_objects=[p], relating_type=t)
    return p

# chaise courbe iroko (origine = centre de l'assise, dos vers -y)
ch = styled([box(-0.21, -0.21, -0.18, -0.18, 0, 0.45), box(0.18, -0.21, 0.21, -0.18, 0, 0.45),
             box(-0.21, 0.18, -0.18, 0.21, 0, 0.45), box(0.18, 0.18, 0.21, 0.21, 0, 0.45),
             box(-0.22, -0.22, 0.22, 0.22, 0.43, 0.46)], M["iroko"])
back = [(0.23 * math.cos(a), -0.05 - 0.17 * math.sin(a)) for a in np.linspace(0, math.pi, 14)]
back = back + [(0.20 * math.cos(a), -0.05 - 0.145 * math.sin(a)) for a in np.linspace(math.pi, 0, 14)]
ch += styled([prism(back, 0.62, 0.80), box(-0.205, -0.20, -0.185, -0.18, 0.45, 0.62), box(0.185, -0.20, 0.205, -0.18, 0.45, 0.62)], M["iroko"])
ch += styled([box(-0.19, -0.19, 0.19, 0.19, 0.46, 0.48)], M["tissu"])
T_CHAISE = ftype("DECIMO_C01 Chaise courbe iroko", ch, predefined="CHAIR", mat=M["iroko"])

tl = styled([box(-0.90, -0.40, 0.90, 0.40, 0.72, 0.76)], M["iroko"])
tl += styled([box(-0.75, -0.30, -0.70, 0.30, 0, 0.72), box(0.70, -0.30, 0.75, 0.30, 0, 0.72), box(-0.70, -0.03, 0.70, 0.03, 0.10, 0.16)], M["iroko_fonce"])
tl += styled([box(-0.60, -0.05, 0.60, 0.05, 0.76, 0.79)], M["terre_cuite"])
T_TABLE = ftype("DECIMO_T01 Table de lecture 180 × 80 (iroko, réglette terre cuite à prises)", tl, predefined="TABLE", mat=M["iroko"])

tj = styled([cyl(0, 0, 0.35, 0.52, 0.55)], M["terrazzo"]) + styled([cyl(0, 0, 0.05, 0, 0.52), cyl(0, 0, 0.22, 0, 0.02)], M["iroko"])
T_TABLE_J = ftype("DECIMO_T02 Table jeunesse ronde Ø 70 (plateau terrazzo)", tj, predefined="TABLE", mat=M["terrazzo"])
T_TAB = ftype("DECIMO_S01 Tabouret terre cuite Ø 30", styled([cyl(0, 0, 0.15, 0, 0.30)], M["terre_cuite"]) +
              styled([cyl(0, 0, 0.15, 0.30, 0.34)], M["tissu_indigo"]), predefined="CHAIR", mat=M["terre_cuite"])
T_POUF = ftype("DECIMO_P01 Pouf indigo Ø 45", styled([cyl(0, 0, 0.225, 0, 0.42)], M["tissu_indigo"]), predefined="CHAIR", mat=M["tissu_indigo"])

fa = styled([box(-0.30, -0.30, 0.30, 0.30, 0.0, 0.08)], M["iroko_fonce"])
fa += styled([box(-0.28, -0.28, 0.28, 0.24, 0.08, 0.42), box(-0.30, -0.30, 0.30, -0.16, 0.08, 0.80),
              box(-0.30, -0.16, -0.22, 0.30, 0.08, 0.60), box(0.22, -0.16, 0.30, 0.30, 0.08, 0.60)], M["tissu"])
T_FAUT = ftype("DECIMO_A01 Fauteuil de lecture (tissu terre cuite)", fa, predefined="CHAIR", mat=M["tissu"])
T_TBASSE = ftype("DECIMO_T03 Table d'appoint Ø 45 terrazzo", styled([cyl(0, 0, 0.225, 0.45, 0.48)], M["terrazzo"]) +
                 styled([cyl(0, 0, 0.03, 0, 0.45), cyl(0, 0, 0.16, 0, 0.02)], M["acier"]), predefined="TABLE", mat=M["terrazzo"])

def shelf_items(L, D, H, n, books=True, double=False, seed=1):
    r = random.Random(seed)
    it = styled([box(0, 0, 0.02, D, 0, H), box(L - 0.02, 0, L, D, 0, H), box(0, 0, L, D, 0, 0.08), box(0, 0, L, D, H - 0.02, H)], M["iroko"])
    if not double:
        it += styled([box(0.02, D - 0.01, L - 0.02, D, 0.08, H - 0.02)], M["iroko_fonce"])
    zs = np.linspace(0.08, H - 0.02, n + 1)
    for z in zs[1:-1]:
        it += styled([box(0.02, 0, L - 0.02, D, z, z + 0.02)], M["iroko"])
    if books:
        for z0, z1 in zip(zs[:-1], zs[1:]):
            zb = z0 + (0.02 if z0 > 0.081 else 0.0)
            x = 0.03
            while x < L - 0.06:
                w = r.uniform(0.025, 0.05)
                h = min(r.uniform(0.18, 0.30), z1 - zb - 0.03)
                dd = D - 0.04 if not double else D / 2 - 0.02
                it += styled([box(x, 0.02, x + w, 0.02 + dd, zb, zb + h)], r.choice(LIVRES))
                if double:
                    it += styled([box(x, D - 0.02 - dd, x + w, D - 0.02, zb, zb + r.uniform(0.18, h))], r.choice(LIVRES))
                x += w + (r.uniform(0.0, 0.01) if r.random() > 0.15 else 0.06)
    return it

T_R01 = ftype("DECIMO_R01 Rayonnage bas jeunesse 80 × 35 × 120", shelf_items(0.80, 0.35, 1.20, 3, seed=11), predefined="SHELF", mat=M["iroko"])
T_R02 = ftype("DECIMO_R02 Rayonnage bas double face 92 × 35 × 120", shelf_items(0.92, 0.35, 1.20, 3, double=True, seed=12),
              predefined="SHELF", mat=M["iroko"])
T_R03 = ftype("DECIMO_R03 Rayonnage haut 90 × 35 × 210", shelf_items(0.90, 0.35, 2.10, 6, seed=13), predefined="SHELF", mat=M["iroko"])

# implantations (origine des rayonnages : coin arrière gauche, dos contre le mur)
inst(T_R01, "Rayonnage bas jeunesse 1", XI0 + 0.015 + 0.35, 0.75, 90, tag="R01")
inst(T_R01, "Rayonnage bas jeunesse 2", XI0 + 0.015 + 0.35, 1.55, 90, tag="R01")
for k, x in enumerate((0.16, 1.08), 1):
    inst(T_R02, f"Rayonnage double face (limite espace de travail) {k}", x, 2.40, 0, tag="R02")
inst(T_R03, "Rayonnage haut salle de lecture", XI1 - 0.015 - 0.35, 7.05, -90, tag="R03")
inst(T_TABLE, "Table de lecture 1", 1.40, 3.95, 90, tag="T01")
for k, (x, y, a) in enumerate([(0.75, 3.35, -90), (0.75, 3.95, -90), (0.75, 4.55, -90), (2.05, 3.35, 90), (2.05, 3.95, 90), (2.05, 4.55, 90)], 1):
    inst(T_CHAISE, f"Chaise table de lecture {k}", x, y, a, tag="C01")
inst(T_TABLE_J, "Table jeunesse", 1.75, 1.45, tag="T02")
for k, a in enumerate((90, 210, 330), 1):
    inst(T_TAB, f"Tabouret jeunesse {k}", 1.75 + 0.50 * math.cos(math.radians(a)), 1.45 + 0.50 * math.sin(math.radians(a)), tag="S01")
for k, (x, y) in enumerate(((3.55, 4.25), (3.62, 6.40)), 1):
    inst(T_POUF, f"Pouf indigo {k}", x, y, tag="P01")
inst(T_FAUT, "Fauteuil de lecture 1", 6.18, 4.75, 90, tag="A01")
inst(T_FAUT, "Fauteuil de lecture 2", 6.18, 5.85, 90, tag="A01")
inst(T_TBASSE, "Table d'appoint", 6.25, 5.30, tag="T03")

# banc de vitrine (coin jeunesse) : coffres iroko + coussins indigo
banc = styled([box(0.30, 0.16, 3.00, 0.62, 0.0, 0.08)], M["iroko_fonce"])
banc += styled([box(0.30, 0.16, 3.00, 0.62, 0.38, 0.42), box(0.30, 0.58, 3.00, 0.62, 0.08, 0.38)], M["iroko"])
banc += styled([box(x, 0.16, x + 0.02, 0.58, 0.08, 0.38) for x in (0.30, 0.97, 1.65, 2.32, 2.98)], M["iroko"])
r_ = random.Random(3)
for x0 in (0.33, 1.00, 1.68, 2.35):
    x = x0
    while x < x0 + 0.60:
        w = r_.uniform(0.02, 0.04)
        banc += styled([box(x, 0.20, x + w, 0.40, 0.08, 0.08 + r_.uniform(0.18, 0.27))], r_.choice(LIVRES))
        x += w + 0.004
banc += styled([box(0.32, 0.18, 2.98, 0.60, 0.42, 0.50)], M["tissu_indigo"])
product("IfcFurniture", "DECIMO_B01 Banc de vitrine (coffres à albums, coussin indigo)", banc, M["iroko"], predefined="SOFA", tag="B01",
        desc="Banc en allège de la devanture, coffres à albums jeunesse dessous")

# banque d'accueil : caisson iroko, façade en tuiles terre cuite cintrées, plateau terrazzo
bq = styled([box(5.02, 1.45, 5.60, 2.75, 0.0, 1.02)], M["iroko"])
bq += styled([box(4.98, 1.43, 5.66, 2.79, 1.02, 1.06)], M["terrazzo"])
bq += styled([box(5.36, 1.45, 5.95, 2.75, 0.72, 0.75)], M["iroko"])
for k in range(13):
    y = 1.47 + k * 0.10
    bq += styled([box(4.985, y, 5.02, y + 0.09, 0.04, 1.00)], M["terre_cuite"])
product("IfcFurniture", "DECIMO_C02 Banque d'accueil (iroko, façade tuiles terre cuite, plateau terrazzo)", bq, M["iroko"],
        predefined="DESK", tag="C02", desc="Banque 1,30 × 0,60, h 1,06 côté public ; tablette agent 0,75 ; partie basse PMR à prévoir en APS")
inst(T_CHAISE, "Siège agent d'accueil", 6.05, 2.10, 90, tag="C01")

# niches : 2 bibliothèques cintrées + 1 banquette de lecture (fond lames, coussins indigo)
def under_arch(x0, x1, zs, z):
    r = (x1 - x0) / 2; c = (x0 + x1) / 2
    if z <= zs:
        return x0, x1
    if z >= zs + r - 0.02:
        return None
    hw = math.sqrt(r * r - (z - zs) ** 2)
    return c - hw, c + hw

rb = random.Random(5)
for k, (x0, x1, zs) in enumerate((NICHES[0], NICHES[2]), 1):
    it = styled([box(x0, 7.06, x1, YI1, 0.0, 0.10)], M["iroko"])
    it += styled([xz_prism(arch(x0, x1, 0.10, zs), YI1 - 0.02, YI1)], M["indigo"])
    for z in np.arange(0.10, zs + 0.45, 0.36):
        w = under_arch(x0, x1, zs, z + 0.025)
        if not w:
            continue
        it += styled([box(w[0], 7.08, w[1], YI1 - 0.02, z, z + 0.025)], M["iroko"])
        w2 = under_arch(x0, x1, zs, z + 0.31)
        if w2 and w2[1] - w2[0] > 0.12:
            x = w2[0] + 0.02
            while x < w2[1] - 0.05:
                bw = rb.uniform(0.022, 0.045)
                it += styled([box(x, 7.12, x + bw, YI1 - 0.03, z + 0.025, z + 0.025 + rb.uniform(0.20, 0.29))], rb.choice(LIVRES))
                x += bw + (0.002 if rb.random() > 0.12 else 0.07)
    n = product("IfcFurniture", f"DECIMO_N01 Niche bibliothèque cintrée {k}", it, M["iroko"], predefined="SHELF", tag="N01",
                desc="Tablettes iroko tous les 36 cm, fond de niche indigo")
    A.feature.add_filling(f, opening=NICHE_OPEN[0 if k == 1 else 2], element=n)
x0, x1, zs = NICHES[1]
r2 = (x1 - x0) / 2; c2 = (x0 + x1) / 2
it = styled([box(x0, 7.06, x1, YI1, 0.0, 0.10), box(x0, 6.96, x1, YI1, 0.10, 0.43)], M["iroko"])
it += styled([box(xx - 0.015, YI1 - 0.03, xx + 0.015, YI1, 0.10, zs + math.sqrt(max(r2 ** 2 - (xx - c2) ** 2, 0)) - 0.01)
              for xx in np.arange(x0 + 0.03, x1 - 0.02, 0.05)], M["iroko_fonce"])
it += styled([box(x0 + 0.02, 6.98, x1 - 0.02, YI1 - 0.04, 0.43, 0.53), box(x0 + 0.05, 7.27, x1 - 0.05, YI1 - 0.04, 0.53, 0.85)], M["tissu_indigo"])
it += styled([box(x0, 7.16, x1, YI1 - 0.03, 1.50, 1.525)], M["iroko"])
n2 = product("IfcFurniture", "DECIMO_N02 Niche banquette de lecture", it, M["iroko"], predefined="SOFA", tag="N02",
             desc="Banquette dans la niche centrale, fond en lames iroko, coussins indigo, tablette à +1,50")
A.feature.add_filling(f, opening=NICHE_OPEN[1], element=n2)

# rangement réserve (dégagement)
inst(ftype("DECIMO_R04 Étagère réserve 86 × 35 × 210", shelf_items(0.86, 0.35, 2.10, 5, books=False, seed=14), predefined="SHELF",
           mat=M["iroko"]), "Étagère de réserve", 1.85, 7.41, -90, tag="R04")

# ======================================================================== 6. sanitaires
wc = styled([box(0.85, 7.21, 1.35, YI1, 0.0, 1.12)], M["ba13h"])
wc += styled([prism([(0.92, 7.21), (1.28, 7.21), (1.28, 6.95), (1.24, 6.78), (1.10, 6.69), (0.96, 6.78), (0.92, 6.95)], 0.30, 0.42)],
             M["sanitaire"])
wc += styled([box(1.04, 7.20, 1.16, 7.21, 0.95, 1.05)], M["acier"])
product("IfcSanitaryTerminal", "WC suspendu sur bâti-support", wc, M["sanitaire"], predefined="TOILETPAN", tag="WC1")
lm = styled([prism([(0.40, 5.35), (0.80, 5.35), (0.80, 5.55), (0.60, 5.62), (0.40, 5.55)], 0.78, 0.85)], M["terre_cuite"])
lm += styled([cyl(0.60, 5.40, 0.012, 0.85, 1.05)], M["acier"])
product("IfcSanitaryTerminal", "Lave-mains terre cuite", lm, M["terre_cuite"], predefined="WASHHANDBASIN", tag="LM1")

# ===================================================================== 7. technique (ESQ Ahoua)
TECH = {"Source": "Hypothèses ESQ Ahoua (fluides / électricité)", "A_confirmer": "APS"}
# tableau divisionnaire encastré dans le doublage technique, près de l'entrée, 1,00 m dégagé devant
u0, _ = wall_local(W["DT"], 6.30, 0.40); u1, _ = wall_local(W["DT"], 6.30, 1.00)
niche_td = opening(W["DT"], "Niche du tableau divisionnaire", min(u0, u1), max(u0, u1), 1.00 - Z0, 1.80 - Z0, v0=0.05, v1=0.35, kind="RECESS")
td = product("IfcElectricDistributionBoard", "Tableau divisionnaire encastré (TD)",
             styled([box(6.22, 0.40, 6.46, 1.00, 1.00, 1.80)], M["blanc_equip"]) + styled([box(6.205, 0.41, 6.215, 0.99, 1.01, 1.79)], M["indigo"]),
             M["blanc_equip"], predefined="DISTRIBUTIONBOARD", tag="TD",
             desc="TD encastré ~0,60 × 0,25, porte peinte indigo ; 1,00 m dégagé devant ; à > 2,5 m de tout point d'eau",
             props={**TECH, "Largeur_mm": 600, "Profondeur_mm": 250, "Degagement_devant_mm": 1000})
A.feature.add_filling(f, opening=niche_td, element=td)

pl_items = styled([box(2.37, 7.06, 2.93, YI1, 1.40, 1.90)], M["gris_equip"]) + styled([box(2.37, 7.05, 2.93, 7.06, 1.42, 1.88)], M["acier"])
product("IfcCommunicationsAppliance", "Baie informatique murale 9U", pl_items, M["gris_equip"], predefined="NETWORKAPPLIANCE", tag="BI",
        desc="Baie 9U 550 × 400 dans le placard technique", props=TECH)
product("IfcElectricDistributionBoard", "Coffret d'arrivée électrique de l'immeuble (comptage)",
        styled([box(2.42, 7.25, 2.88, YI1, 0.40, 1.20)], M["blanc_equip"]), M["blanc_equip"], predefined="USERDEFINED",
        object_type="COFFRET ARRIVEE", tag="AR", desc="Arrivée électrique depuis les parties communes ; pas de TGBT ni de groupe électrogène", props=TECH)

def split(name, x0, y0, x1, y1, tag, face):
    it = styled([box(x0, y0, x1, y1, 2.40, 2.69)], M["blanc_equip"])
    if face == "-y":
        it += styled([box(x0 + 0.03, y0 - 0.005, x1 - 0.03, y0, 2.42, 2.47)], M["gris_equip"])
    else:
        it += styled([box(x0 - 0.005, y0 + 0.03, x0, y1 - 0.03, 2.42, 2.47)], M["gris_equip"])
    return product("IfcUnitaryEquipment", name, it, M["blanc_equip"], predefined="SPLITSYSTEM", tag=tag,
                   desc="Unité intérieure murale ~9 000 BTU/h (2,6 kW), en hauteur sur mur plein, hors aplomb des tables de lecture",
                   props={**TECH, "Puissance_BTU_h": 9000, "Puissance_kW": 2.6, "Condensats": "Pompe de relevage ou raccord EU à confirmer"})
split("Split mural S1 (espace de travail)", 2.05, 5.05, 2.85, 5.25, "S1", "-y")
split("Split mural S2 (salle de lecture)", 6.31, 4.75, XI1, 5.55, "S2", "-x")

ZL = 3.10
L1 = [(2.50, 5.20, 2.69), (2.50, 5.20, ZL), (2.50, 7.85, ZL)]
L2 = [(6.42, 5.15, 2.69), (6.42, 5.15, ZL), (6.42, 6.80, ZL), (2.80, 6.80, ZL), (2.80, 7.85, ZL)]
for k, pts in enumerate((L1, L2), 1):
    product("IfcPipeSegment", f"Liaisons frigorifiques S{k} (gaine isolée, plénum)", styled([sweep(pts, 0.03)], M["isolant_noir"]),
            M["isolant_noir"], predefined="RIGIDSEGMENT",
            desc="Liaisons cuivre isolées + câble + condensats, dans le plénum du faux-plafond, via le placard technique, "
                 "sortie en façade arrière / courette (jamais en toiture)", props=TECH)
NOTE_BET = "Mur porteur existant : carottage à valider par le BET structure et le syndic"
reservation(W["C1"], "Réservation Ø100 liaisons S1 (cloison C1)", 2.50, 5.30, ZL)
reservation(W["C4"], "Réservation Ø100 liaisons S1 (placard)", 2.50, 6.96, ZL)
reservation(W["C4"], "Réservation Ø100 liaisons S2 (placard)", 2.80, 6.96, ZL)
reservation(W["C3"], "Réservation Ø100 liaisons S2 (cloison C3)", 3.00, 6.80, ZL)
reservation(W["N1"], "Réservation Ø100 liaisons S1 vers courette (mur existant)", 2.50, 7.50, ZL, note=NOTE_BET)
reservation(W["N1"], "Réservation Ø100 liaisons S2 vers courette (mur existant)", 2.80, 7.50, ZL, note=NOTE_BET)

# descentes EU/EV des logements traversant le local + coffrages acoustiques
COFFRAGES = {"Est (salle de lecture)": ([(6.51, 3.55), (6.16, 3.55), (6.16, 4.35), (6.51, 4.35), (6.51, 4.30), (6.21, 4.30), (6.21, 3.60), (6.51, 3.60)], (6.36, 4.10)),
             "Nord-ouest (WC)": ([(XI0, 7.05), (0.45, 7.05), (0.45, YI1), (0.40, YI1), (0.40, 7.10), (XI0, 7.10)], (0.25, 7.25))}
for k, (nm, (poly, (px, py))) in enumerate(COFFRAGES.items(), 1):
    pipe = product("IfcPipeSegment", f"Descente EU/EV existante des logements {k} ({nm})", styled([cyl(px, py, 0.055, Z_DALLAGE, Z_DALLE_HAUT)], M["pvc"]),
                   M["pvc"], predefined="RIGIDSEGMENT", desc="Descente Ø 110 des logements, traversant le local")
    existing(pipe, extra={"Statut": "Existant - réseau des logements - ne pas toucher"})
    cov = product("IfcCovering", f"Coffrage acoustique descente EU/EV {k} ({nm})", styled([prism(poly, Z_DALLAGE, Z_DALLE_BAS)], M["ba13"]),
                  None, predefined="USERDEFINED", object_type="COFFRAGE ACOUSTIQUE",
                  desc="Coffrage BA13 ×2 + laine minérale 45 + manchon résilient autour de la descente (trappe de visite au droit des tampons)")
    ls = A.material.add_material_set(f, name="Coffrage acoustique BA13×2 + LM45", set_type="IfcMaterialLayerSet")
    for mat, th, ln in (("ba13", 0.025, "BA13 ×2"), ("laine", 0.045, "Laine minérale"), ("ossature", 0.005, "Manchon résilient")):
        lay = A.material.add_layer(f, layer_set=ls, material=MATS[M[mat]], name=ln)
        A.material.edit_layer(f, layer=lay, attributes={"LayerThickness": th * MM})
    A.material.assign_material(f, products=[cov], type="IfcMaterialLayerSet", material=ls)

# =========================================================================== 8. espaces
cols_poly = unary_union([sbox(x, y, x + 0.25, y + 0.25) for x, y, _ in COLS.values()])
obst = unary_union([cols_poly, Polygon(COFFRAGES["Est (salle de lecture)"][0]).envelope,
                    Polygon(COFFRAGES["Nord-ouest (WC)"][0]).envelope, sbox(6.21, 0.16, XI1, 1.40)])
claustra_fp = sbox(2.95, 3.35, 3.05, 5.25)
SPACES = [
    ("01", "Accueil — entrée", sbox(3.05, Y_CW1, XI1, 2.95), M["terrazzo"], None),
    ("02", "Coin jeunesse — vitrine", sbox(XI0, Y_CW1, 3.05, 2.55), M["tomette"], None),
    ("03", "Salle de lecture — arbre à livres", sbox(3.05, 2.95, XI1, 7.06), M["terrazzo"], (CX, CY, 1.40)),
    ("04", "Espace de travail — tables de lecture", sbox(XI0, 2.55, 3.05, 5.25), M["terrazzo"], None),
    ("05", "Dégagement — réserve", unary_union([sbox(1.85, 5.35, 2.95, 6.91), sbox(1.85, 6.91, 2.25, YI1)]), M["terrazzo"], None),
    ("06", "WC", sbox(XI0, 5.35, 1.75, YI1), M["terrazzo"], None),
    ("07", "Placard technique", sbox(2.35, 7.01, 2.95, YI1), M["chape"], None),
]
space_objs = {}
TABLE = []
for num, nm, poly, floor_mat, dome in SPACES:
    net = poly.difference(obst)
    if num == "04":
        net = net.difference(claustra_fp)
    net = orient(net.buffer(0))
    pts = [(round(x, 4), round(y, 4)) for x, y in list(net.exterior.coords)[:-1]]
    sp = A.root.create_entity(f, ifc_class="IfcSpace", name=num, predefined_type="INTERNAL")
    sp.LongName = nm
    A.aggregate.assign_object(f, products=[sp], relating_object=storey)
    sp.ObjectPlacement = lp(None)
    sp.Representation = f.createIfcProductDefinitionShape(None, None, [shape([prism(pts, 0.0, Z_FP)])])
    h = Z_FP
    q = A.pset.add_qto(f, product=sp, name="Qto_SpaceBaseQuantities")
    A.pset.edit_qto(f, qto=q, properties={"Height": h * MM, "FinishCeilingHeight": h * MM, "FinishFloorHeight": 0.0,
                                          "GrossFloorArea": round(poly.area, 2), "NetFloorArea": round(net.area, 2),
                                          "GrossPerimeter": round(poly.length * MM), "NetPerimeter": round(net.length * MM),
                                          "GrossVolume": round(poly.area * h, 2), "NetVolume": round(net.area * h, 2)})
    pset(sp, "Pset_SpaceCommon", {"Reference": num, "IsExternal": False, "PubliclyAccessible": num in ("01", "02", "03", "04", "06"),
                                  "HandicapAccessible": num in ("01", "02", "03", "04")})
    pset(sp, "KDEMI_Esquisse", {"Indice": "V5", "Phase": "ESQ", "Revetement_sol": floor_mat,
                                "Hauteur_sous_plafond_mm": round(Z_FP * MM) if not dome else "2850 (3300 sous coupole)"})
    space_objs[num] = (sp, net, poly)
    TABLE.append((num, nm, round(net.area, 2)))

# ===================================================================== 9. revêtements
def cover(name, items, predefined, mat_layers, space=None, element=None, desc=None, object_type=None):
    c = product("IfcCovering", name, items, None, predefined=predefined, desc=desc, object_type=object_type)
    if len(mat_layers) == 1:
        A.material.assign_material(f, products=[c], type="IfcMaterial", material=MATS[M[mat_layers[0][0]]])
    else:
        ls = A.material.add_material_set(f, name=name.split(" —")[0], set_type="IfcMaterialLayerSet")
        for mat, th, ln in mat_layers:
            lay = A.material.add_layer(f, layer_set=ls, material=MATS[M[mat]], name=ln)
            A.material.edit_layer(f, layer=lay, attributes={"LayerThickness": th * MM})
        A.material.assign_material(f, products=[c], type="IfcMaterialLayerSet", material=ls)
    if space is not None:
        f.createIfcRelCoversSpaces(ifcopenshell.guid.new(), None, None, None, space, [c])
    if element is not None:
        f.createIfcRelCoversBldgElements(ifcopenshell.guid.new(), None, None, None, element, [c])
    return c

def pts_of(g):
    g = orient(g.buffer(0))
    return [(round(x, 4), round(y, 4)) for x, y in list(g.exterior.coords)[:-1]], \
           [[(round(x, 4), round(y, 4)) for x, y in list(r.coords)[:-1]] for r in g.interiors]

seuils = {"05": [sbox(2.95, 5.50, 3.05, 6.43), sbox(2.38, 6.91, 2.93, 7.01)], "06": [sbox(1.75, 5.50, 1.85, 6.43)]}
for num, nm, poly, floor_mat, dome in SPACES:
    sp, net, gross = space_objs[num]
    fl = unary_union([gross.difference(obst)] + seuils.get(num, []))
    o, holes = pts_of(fl)
    if num == "07":
        cover(f"Sol {num} — chape lissée", styled([prism(o, Z_DALLAGE, 0.0, holes)], M["chape"]), "FLOORING", [("chape", 0.07, "Chape")], sp)
    else:
        fm = "tomette" if floor_mat == M["tomette"] else "terrazzo"
        lbl = "tomettes terre cuite 20 × 20" if fm == "tomette" else "terrazzo coulé sable, joints laiton"
        cover(f"Sol {num} — {lbl}", styled([prism(o, Z_DALLAGE, 0.0, holes)], M[fm]), "FLOORING",
              [("chape", 0.05 if fm == "terrazzo" else 0.055, "Chape"), (fm, 0.02 if fm == "terrazzo" else 0.015, lbl)], sp)
    # plafonds
    cg = gross.difference(obst)
    if num == "04":
        cg = unary_union([cg, claustra_fp]).difference(obst)
    if num == "07":
        continue
    o, holes = pts_of(cg)
    if dome:
        holes = holes + [circle_pts(dome[0], dome[1], dome[2], 64)]
    cover(f"Faux-plafond acoustique {num} — fibres de bois teinte sable", styled([prism(o, Z_FP, Z_FP + 0.035, holes)], M["plafond"]),
          "CEILING", [("plafond", 0.035, "Panneau fibres de bois acoustique 35 (αw ≈ 0,8)")], sp,
          desc="Plafond acoustique suspendu à +2,85, plénum 45 cm (liaisons frigorifiques, réseaux)")
sp03 = space_objs["03"][0]
cover("Coupole — sous-face de dalle peinte indigo", styled([cyl(CX, CY, 1.40, Z_DALLE_BAS - 0.01, Z_DALLE_BAS)], M["indigo"]), "CEILING",
      [("indigo", 0.01, "Peinture minérale indigo")], sp03, desc="Ciel indigo au-dessus de l'arbre à livres")
cover("Coupole — rive cintrée du faux-plafond", styled([tube(CX, CY, 1.42, 0.02, Z_FP, Z_DALLE_BAS - 0.01)], M["indigo"]), "CLADDING",
      [("ba13", 0.02, "BA13 cintré peint indigo")], sp03)

# murs : enduit terre, parement BTC (espace de travail), zellige indigo (WC)
def wall_cover(name, w, x0, y0, x1, y1, z1, key, th_lbl, sp=None):
    c = cover(name, styled([box(x0, y0, x1, y1, 0.0, z1)], M[key]), "CLADDING", [(key, abs(x1 - x0) if abs(x1 - x0) < abs(y1 - y0) else abs(y1 - y0), th_lbl)],
              element=w)
    return c
wall_cover("Enduit terre — mur ouest (coin jeunesse)", W["O1"], XI0, 0.16, XI0 + 0.015, 2.55, Z_FP, "enduit_terre", "Enduit terre 15")
wall_cover("Parement BTC — mur ouest (espace de travail)", W["O1"], XI0, 2.55, XI0 + 0.04, 3.625, Z_FP, "btc", "Plaquettes BTC 40")
wall_cover("Parement BTC — mur ouest (espace de travail, nord)", W["O2"], XI0, 3.875, XI0 + 0.04, 5.25, Z_FP, "btc", "Plaquettes BTC 40")
wall_cover("Enduit terre — mur est (accueil)", W["E1"], XI1 - 0.015, 1.40, XI1, 3.55, Z_FP, "enduit_terre", "Enduit terre 15")
wall_cover("Enduit terre — mur est (salle de lecture)", W["E2"], XI1 - 0.015, 4.35, XI1, 7.06, Z_FP, "enduit_terre", "Enduit terre 15")
wall_cover("Zellige indigo — WC mur du fond", W["N1"], 0.45, YI1 - 0.012, 1.75, YI1, 1.40, "zellige", "Zellige 12")
wall_cover("Zellige indigo — WC cloison sud", W["C1"], XI0, 5.35, 1.75, 5.362, 1.40, "zellige", "Zellige 12")
wall_cover("Zellige indigo — WC mur ouest", W["O2"], XI0, 5.35, XI0 + 0.012, 7.05, 1.40, "zellige", "Zellige 12")
wall_cover("Zellige indigo — WC cloison est", W["C2"], 1.738, 6.43, 1.75, YI1, 1.40, "zellige", "Zellige 12")

# ======================================================================== 10. luminaires
LT = {}
def light_type(name, items, predefined, mat, props):
    t = ftype(name, items, cls="IfcLightFixtureType", predefined=predefined, mat=mat)
    pset(t, "Pset_LightFixtureTypeCommon", {"NumberOfSources": 1})
    pset(t, "KDEMI_Eclairage", {"Temperature_couleur_K": 2700, "IRC": "90 mini", **props})
    return t
LT["DL"] = light_type("KDEMI_E01 Downlight encastré Ø 80 orientable 2700 K", styled([cyl(0, 0, 0.045, -0.01, 0.0)], M["acier"]) +
                      styled([cyl(0, 0, 0.035, -0.012, -0.01)], M["led"]), "POINTSOURCE", M["acier"], {"Puissance_W": 7, "Flux_lm": 600})
LT["SU"] = light_type("KDEMI_E02 Suspension cloche terre cuite Ø 38", styled([revolve([(0.02, 0.0), (0.19, 0.0), (0.12, 0.22), (0.02, 0.26)], 0, 0)],
                      M["terre_cuite"]) + styled([cyl(0, 0, 0.004, 0.26, 1.30)], M["acier"]) + styled([cyl(0, 0, 0.06, 1.28, 1.30)], M["acier"]),
                      "DIRECTIONSOURCE", M["terre_cuite"], {"Puissance_W": 9, "Flux_lm": 800, "Hauteur_suspension": "+1,55 sous abat-jour"})
LT["AP"] = light_type("KDEMI_E03 Applique demi-lune terre cuite", styled([prism([(0.15 * math.cos(a), 0.15 * math.sin(a) * 0.5) for a in np.linspace(0, math.pi, 16)], -0.15, 0.15)],
                      M["terre_cuite"]), "DIRECTIONSOURCE", M["terre_cuite"], {"Puissance_W": 6, "Flux_lm": 400})
LT["RL"] = light_type("KDEMI_E04 Réglette LED intégrée (niches, rayonnages)", styled([box(-0.40, -0.01, 0.40, 0.01, -0.012, 0.0)], M["led"]),
                      "DIRECTIONSOURCE", M["led"], {"Puissance_W_m": 8})
LT["SP"] = light_type("KDEMI_E05 Rail vitrine 2,4 m + 4 spots", styled([box(-1.20, -0.02, 1.20, 0.02, -0.04, 0.0)], M["acier"]) +
                      styled([cyl(x, 0, 0.03, -0.14, -0.04) for x in (-0.9, -0.3, 0.3, 0.9)], M["acier"]), "DIRECTIONSOURCE", M["acier"],
                      {"Puissance_W": 4 * 8, "Usage": "Mise en valeur de la vitrine et du banc"})
LT["LP"] = light_type("KDEMI_E06 Lampadaire liseuse iroko", styled([cyl(0, 0, 0.14, 0, 0.02), cyl(0, 0, 0.012, 0.02, 1.35)], M["iroko_fonce"]) +
                      styled([revolve([(0.02, 1.32), (0.17, 1.32), (0.13, 1.50), (0.02, 1.52)], 0, 0)], M["tissu"]), "DIRECTIONSOURCE", M["iroko"],
                      {"Puissance_W": 6})

def light(t, name, x, y, z, ang=0.0, tag=None):
    p = inst(t, name, x, y, ang, cls="IfcLightFixture", z=z, tag=tag)
    return p
k = 0
for x, y in [(3.55, 0.75), (4.75, 0.75), (3.55, 2.10), (4.75, 2.30), (0.75, 1.60), (2.35, 1.60), (3.45, 3.30), (5.75, 3.30),
             (3.45, 6.60), (5.85, 6.50), (0.90, 6.40), (2.40, 5.85), (0.55, 2.95), (2.30, 2.95)]:
    k += 1
    light(LT["DL"], f"Downlight {k:02d}", x, y, Z_FP, tag="E01")
for k, y in enumerate((3.55, 4.35), 1):
    light(LT["SU"], f"Suspension table de lecture {k}", 1.40, y, 1.55, tag="E02")
light(LT["SU"], "Suspension banque d'accueil", 5.30, 2.10, 1.55, tag="E02")
light(LT["AP"], "Applique coin jeunesse", XI0 + 0.015, 2.35, 1.90, -90, tag="E03")
light(LT["AP"], "Applique WC", 0.60, 5.362, 1.85, 0, tag="E03")
for k, (x0, x1, zs) in enumerate(NICHES, 1):
    light(LT["RL"], f"Réglette LED niche {k}", (x0 + x1) / 2, 7.25, zs + 0.15, tag="E04")
light(LT["SP"], "Rail vitrine coin jeunesse", 1.65, 0.55, Z_FP, tag="E05")
light(LT["LP"], "Lampadaire liseuse (pouf, mur du fond)", 3.25, 6.85, 0.0, tag="E06")
ring = styled([tube(CX, CY, 1.30, 0.025, 3.11, 3.14)], M["led"])
product("IfcLightFixture", "Anneau LED de la canopée (indirect vers la coupole indigo)", ring, M["led"], predefined="DIRECTIONSOURCE", tag="E07",
        props={"Temperature_couleur_K": 2700, "Puissance_W": 24, "Effet": "Lumière rasante sur la coupole indigo"})

# =========================================================================== 11. contexte
def ctx(cls, name, items, mat, predefined=None, object_type=None):
    p = product(cls, name, items, mat, container=site, predefined=predefined, object_type=object_type)
    p.Description = "Contexte indicatif — hors périmètre"
    return p
ctx("IfcCivilElement", "Trottoir (contexte)", styled([box(-3.0, -2.60, 9.6, -0.09, -0.22, -0.02)], M["trottoir"]), M["trottoir"])
ctx("IfcCivilElement", "Bordure de trottoir (contexte)", styled([box(-3.0, -2.75, 9.6, -2.60, -0.37, -0.02)], M["bordure"]), M["bordure"])
ctx("IfcCivilElement", "Chaussée (contexte)", styled([box(-3.0, -9.0, 9.6, -2.75, -0.37, -0.17)], M["chaussee"]), M["chaussee"])
for k, x in enumerate((0.85, 5.95), 1):
    crown = [(0.0, 2.3), (0.9, 2.45), (1.55, 3.1), (1.75, 3.9), (1.5, 4.7), (0.9, 5.25), (0.0, 5.4)]
    items = styled([cyl(x, -1.85, 0.13, -0.02, 2.6)], M["tronc"]) + styled([revolve(crown, x, -1.85)], M["vegetal"])
    items += styled([box(x - 0.55, -2.40, x + 0.55, -1.30, -0.05, -0.02)], M["acier"])
    ctx("IfcGeographicElement", f"Arbre d'alignement {k} (contexte)", items, M["vegetal"], predefined="USERDEFINED", object_type="ARBRE")

f.write(OUT)
print("écrit", OUT)
for row in TABLE:
    print(*row, sep=" | ")
print("Total net", round(sum(r[2] for r in TABLE), 2))
