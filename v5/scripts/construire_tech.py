"""v5/DECIMO_ESQ_V5.ifc -> v5/DECIMO_ESQ_V5_tech.ifc : lots techniques ajoutés en IFC4.

Ajouts seulement : appareillage (prises, RJ45, commandes, détecteurs, BAES, borne Wi-Fi), goulottes,
chemin de câbles courants faibles, suspentes, fourreau R6, raccordements AEP / EU / EV du WC et du
lave-mains V4 (siphon, culottes, té de visite, robinets, compteur, clapets), colonne AEP supposée,
trappes de visite, circuits électriques (IfcDistributionCircuit) et réseaux (IfcDistributionSystem).
Aucune entité de la V5 n'est modifiée ; les entités existantes sont seulement référencées par des
relations d'affectation à un circuit ou un réseau (V5 uniquement : rien n'est rattaché aux objets V4).

Usage : python3 v5/scripts/construire_tech.py
"""
import os, sys, time, importlib, logging
import numpy as np
import ifcopenshell, ifcopenshell.guid
import ifcopenshell.util.element as ue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import V5_IFC, Z_DALLE_SOUS, Z_CABLES  # noqa
import technique as T  # noqa

logging.disable(logging.WARNING)
CM = 100.0


def api(path, *a, **kw):
    mod, fn = path.rsplit(".", 1)
    return getattr(importlib.import_module("ifcopenshell.api." + mod), fn)(*a, **kw)


f = ifcopenshell.open(V5_IFC)
N_AVANT = len(f.by_type("IfcProduct"))
OH = f.by_type("IfcOwnerHistory")[0]
rdc = next(s for s in f.by_type("IfcBuildingStorey") if "RDC" in s.Name)
body = next(c for c in f.by_type("IfcGeometricRepresentationSubContext") if c.ContextIdentifier == "Body")
STYLES = {s.Name: s for s in f.by_type("IfcSurfaceStyle")}


def new_style(name, hexc):
    rgb = [int(hexc[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    ren = f.createIfcSurfaceStyleRendering(f.createIfcColourRgb(None, *rgb), 0.0, None, None, None, None,
                                           f.createIfcColourRgb(None, 0.2, 0.2, 0.2), f.createIfcSpecularRoughness(0.3), "PLASTIC")
    STYLES[name] = f.createIfcSurfaceStyle(name, "BOTH", [ren])


for nm, hexc in (("KDEMI - AEP bleu", "#2F6DB5"), ("KDEMI - EU PVC vert", "#5F7A4B"), ("KDEMI - EV PVC brun", "#7A4A2A"),
                 ("KDEMI - BAES vert", "#3E8E5A"), ("KDEMI - Laiton", "#B08D3C")):
    new_style(nm, hexc)
K = {"equip": "KDEMI - Équipement blanc", "gris": "KDEMI - Équipement gris", "pvc": "KDEMI - PVC gris", "resa": "KDEMI - Réservation (repère)",
     "acier": "KDEMI - Acier noir mat", "aep": "KDEMI - AEP bleu", "eu": "KDEMI - EU PVC vert", "ev": "KDEMI - EV PVC brun",
     "baes": "KDEMI - BAES vert", "laiton": "KDEMI - Laiton", "platre": "KDEMI - Plâtre blanc"}
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


P3 = lambda x, y, z: f.createIfcCartesianPoint((float(x) * CM, float(y) * CM, float(z) * CM))
P2 = lambda x, y: f.createIfcCartesianPoint((float(x) * CM, float(y) * CM))
DZ = f.createIfcDirection((0.0, 0.0, 1.0))


def styled(items, key):
    for it in items:
        f.createIfcStyledItem(it, [STYLES[K[key]]], None)
    return items


def box(x0, y0, x1, y1, z0, z1):
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    prof = f.createIfcRectangleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2((x0 + x1) / 2, (y0 + y1) / 2), None),
                                          (x1 - x0) * CM, (y1 - y0) * CM)
    return f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(P3(0, 0, z0), None, None), DZ, (z1 - z0) * CM)


def cyl(cx, cy, r, z0, z1):
    prof = f.createIfcCircleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(cx, cy), None), r * CM)
    return f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(P3(0, 0, z0), None, None), DZ, (z1 - z0) * CM)


def tube(points, r):
    return f.createIfcSweptDiskSolid(f.createIfcPolyline([P3(*p) for p in points]), r * CM, None, None, None)


def run_boxes(points, w, h):
    out = []
    for (x0, y0, z0), (x1, y1, z1) in zip(points[:-1], points[1:]):
        if abs(x1 - x0) > 1e-6:
            out.append(box(min(x0, x1) - w / 2, y0 - w / 2, max(x0, x1) + w / 2, y0 + w / 2, z0 - h / 2, z0 + h / 2))
        else:
            out.append(box(x0 - w / 2, min(y0, y1) - w / 2, x0 + w / 2, max(y0, y1) + w / 2, z0 - h / 2, z0 + h / 2))
    return out


TECH = {"CFO": "Technique - courants forts", "CFA": "Technique - courants faibles", "ECL": "Technique - éclairage",
        "PLB": "Technique - plomberie AEP/EU/EV"}
HYP = {"KDEMI_Hypothese": {"Statut": "À relever sur site", "Source": "Hypothèse ESQ technique V5"}}
AJOUTS = []


def new(ifc_class, name, items, mat=None, predefined_type=None, description=None, lot="CFO", props=None, psets=None, **attrs):
    p = api("root.create_entity", f, ifc_class=ifc_class, name=name, predefined_type=predefined_type)
    p.OwnerHistory = OH
    p.Description = description
    for k, v in attrs.items():
        setattr(p, k, v)
    api("spatial.assign_container", f, products=[p], relating_structure=rdc)
    api("geometry.edit_object_placement", f, product=p, matrix=np.eye(4), is_si=True)
    if items:
        rt = "AdvancedSweptSolid" if any(i.is_a("IfcSweptDiskSolid") for i in items) else "SweptSolid"
        api("geometry.assign_representation", f, product=p, representation=f.createIfcShapeRepresentation(body, "Body", rt, items))
    vals = {"Indice": "V5 tech", "Lot": TECH[lot], "Origine": "Lots techniques V5 sur existant V4"}
    vals.update({k: v for k, v in (props or {}).items() if v is not None})
    api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=p, name="KDEMI_Esquisse"), properties=vals)
    for nm, pr in (psets or {}).items():
        api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=p, name=nm), properties=pr)
    if mat:
        rel = material_rel(mat)
        rel.RelatedObjects = list(rel.RelatedObjects) + [p]
    AJOUTS.append(p)
    return p


def by_name(name):
    r = [e for e in f.by_type("IfcProduct") if e.Name == name]
    assert len(r) == 1, (name, len(r))
    return r[0]


MEMBRES = {}   # circuit / réseau -> produits


def membre(groupe, p):
    MEMBRES.setdefault(groupe, []).append(p)


# ============================ 1. appareillage mural et plafond ==================================
CLASSE = {"PC": ("IfcOutlet", "POWEROUTLET"), "PC2": ("IfcOutlet", "POWEROUTLET"), "PCU": ("IfcOutlet", "POWEROUTLET"),
          "RJ2": ("IfcOutlet", "DATAOUTLET"), "INT": ("IfcSwitchingDevice", "TOGGLESWITCH"), "INT2": ("IfcSwitchingDevice", "TOGGLESWITCH"),
          "BP2": ("IfcSwitchingDevice", "MOMENTARYSWITCH"), "PLAT": ("IfcSwitchingDevice", "MOMENTARYSWITCH"),
          "BAES": ("IfcLightFixture", "SECURITYLIGHTING"), "BAESP": ("IfcLightFixture", "SECURITYLIGHTING"),
          "DET": ("IfcSensor", "MOVEMENTSENSOR"), "WIFI": ("IfcCommunicationsAppliance", "USERDEFINED")}
SOCLES = {"PC": 1, "PC2": 2, "PCU": 1, "RJ2": 2}
baes_type = api("root.create_entity", f, ifc_class="IfcLightFixtureType", name="BAES d'évacuation LED (SATI, 45 lm, 1 h)", predefined_type="SECURITYLIGHTING")
baes_type.OwnerHistory = OH
api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=baes_type, name="Pset_LightFixtureTypeCommon"),
    properties={"TotalWattage": T.P_BAES_W, "NumberOfSources": 1})


def appareil(code, kind, b, circuit, local, libelle, support):
    cls, pdt = CLASSE[kind]
    lot = "CFA" if circuit == "VDI" else ("ECL" if kind.startswith("BAES") else "CFO")
    if kind == "DET":
        items = styled([cyl((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, (b[2] - b[0]) / 2, b[4], b[5])], "equip")
    elif kind == "WIFI":
        items = styled([cyl((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, (b[2] - b[0]) / 2, b[4], b[5])], "equip")
    elif kind == "BAESP":
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        items = styled([box(*b)], "baes") + styled([cyl(cx, cy, 0.006, b[5], T.Z_FP_SOUS - 0.002)], "acier")
    else:
        items = styled([box(*b)], "baes" if kind == "BAES" else "equip")
    props = {"Code": code, "Circuit": circuit, "Local": local, "Symbole": kind, "Hauteur_axe_m": round((b[4] + b[5]) / 2, 3),
             "Support": support, "Pose": "En saillie, collée ou chevillée court (aucune saignée)" if support else "Sous faux-plafond",
             "Nb_socles": SOCLES.get(kind)}
    attrs = {"ObjectType": "Borne Wi-Fi PoE"} if pdt == "USERDEFINED" else {}
    p = new(cls, f"{code} - {libelle}", items, mat="baes" if kind.startswith("BAES") else "equip", predefined_type=pdt,
            description=libelle, lot=lot, props=props, **attrs)
    if kind.startswith("BAES"):
        api("type.assign_type", f, related_objects=[p], relating_type=baes_type)
    membre(circuit, p)
    return p


APP = {}
for code, kind, face, a, z, circ, loc, lib in T.APPAREILS:
    w, h, d = T.TAILLES[kind]
    APP[code] = appareil(code, kind, T.boite_murale(face, a, z, w, h, d), circ, loc, lib, T.FACES[face][3])
for code, kind, x, y, circ, loc, lib, ori in T.PLAFOND:
    APP[code] = appareil(code, kind, T.boite_plafond(kind, x, y, ori), circ, loc, lib, None)

# ============================ 2. goulottes, chemin CFA, suspentes, R6 =================================
for code, b, desc in T.goulottes():
    p = new("IfcCableCarrierSegment", f"Goulotte {code}", styled([box(*b)], "equip"), mat="equip", predefined_type="CABLETRUNKINGSEGMENT",
            description=desc + " ; arrêt sous le faux-plafond, passage du câble par découpe de dalle", props={"Code": code})
    membre("CFO", p)
cfa = new("IfcCableCarrierSegment", "Chemin de câbles courants faibles 50 x 30 en plénum", styled(run_boxes(T.CFA, 0.05, 0.03), "gris"),
          mat="gris", predefined_type="CABLETRAYSEGMENT", lot="CFA", psets=HYP,
          description="Dalle 50 x 30 à 0,12 m du chemin CFO (séparation ≥ 5 cm, EN 50174-2) ; entre le placard et la réunion, les câbles VDI "
                      "partagent la dalle C1 (cloison séparatrice) au passage de la réservation R5",
          props={"Code": "CFA", "Z_axe_m": Z_CABLES})
membre("VDI", cfa)


def suspentes(segment_pts, top):
    pts = []
    for (x0, y0, _), (x1, y1, _) in zip(segment_pts[:-1], segment_pts[1:]):
        L = abs(x1 - x0) + abs(y1 - y0)
        if L < 0.25:
            continue
        n = max(1, int(np.ceil((L - 0.30) / 1.20)) + 1)
        for t in np.linspace(0.15, L - 0.15, n) / L:
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return [cyl(x, y, 0.004, top, Z_DALLE_SOUS - 0.003) for x, y in pts], len(pts)


C1 = [(0.83, 3.60), (0.83, 0.44), (2.78, 0.44)]
C1h = [(0.83, 5.40), (0.83, 5.30)]
C2 = [(2.78, 0.44), (2.78, 1.10), (5.50, 1.10), (5.50, 4.30), (6.40, 4.30), (6.40, 4.95)]
C1b = [(0.83, 3.60), (0.18, 3.60)]
for nom, pts, top in (("C1", [(0.83, 4.90)] + C1, Z_CABLES + 0.02), ("C1b", C1b, Z_CABLES + 0.02), ("C2", C2, Z_CABLES + 0.02),
                      ("CFA", [p[:2] for p in T.CFA], Z_CABLES + 0.015)):
    its, n = suspentes([(x, y, 0) for x, y in pts], top)
    p = new("IfcDiscreteAccessory", f"Suspentes du chemin de câbles {nom} ({n} tiges M8)", styled(its, "acier"), mat="acier",
            predefined_type="USERDEFINED", ObjectType="Suspente tige filetée M8", lot="CFA" if nom == "CFA" else "CFO",
            description="Tige filetée M8 au pas ≤ 1,20 m, cheville à expansion courte (≤ 40 mm, non traversante, repérage ferroscan) "
                        "en sous-face de dalle ; la tige s'arrête à 3 mm sous la dalle dans la maquette (la cheville n'est pas modélisée)",
            props={"Nb_tiges": n, "Fixation": "Non traversante, ancrage ≤ 40 mm"}, psets=HYP)
    membre("CFA" if nom == "CFA" else "CFO", p)

code, nm, (x, y, z), depth, r = T.R6
solid = f.createIfcExtrudedAreaSolid(f.createIfcCircleProfileDef("AREA", None, f.createIfcAxis2Placement2D(P2(0, 0), None), r * CM),
                                     f.createIfcAxis2Placement3D(P3(x, y, z), f.createIfcDirection((0.0, 1.0, 0.0)), f.createIfcDirection((1.0, 0.0, 0.0))),
                                     DZ, depth * CM)
new("IfcBuildingElementProxy", f"Réservation {code} Ø 0,05 - {nm}", styled([solid], "resa"), mat="resa", predefined_type="PROVISIONFORVOID",
    description="Support : cloison placo V4 4350620 (non porteuse), en plénum à +3,17 ; même statut que R5 : percement léger d'une cloison V4, "
                "à valider par la MOA. Variante sans percement : goulotte en applique franchissant l'huisserie de la porte du WC",
    psets={"Pset_ProvisionForVoid": {"Shape": "Round", "Diameter": round(2 * r * CM, 1), "Depth": round(depth * CM, 1), "System": "Éclairage WC"},
           "KDEMI_Reservation": {"Code": code, "Support": "Cloison placo V4 non porteuse 4350620", "Traverse_structure": False}, **HYP})

# ============================ 3. AEP / EU / EV ======================================================
SAN, NOTES = T.lire_sanitaires(f)
RES = T.reseaux_sanitaires(SAN)
PLB = {}
STY = {"AEP": "aep", "EU": "eu", "EV": "ev"}
for k, r in RES.items():
    pc, Lh = T.pente(r["pts"])
    flex = k in ("AEP-WC", "AEP-LM")
    props = {"Code": k, "Reseau": r["sys"], "Diametre_ext_mm": round(r["d_ext"] * 1000), "Longueur_horizontale_m": round(Lh, 2)}
    if r["sys"] in ("EU", "EV"):
        props.update({"Pente_pct": round(pc, 2), "FilEau_amont_m": round(r["pts"][0][2] - r["d_ext"] / 2, 3),
                      "FilEau_aval_m": round(r["pts"][-1][2] - r["d_ext"] / 2, 3), "Materiau": "PVC NF ME (EN 1329)"})
    else:
        props.update({"Materiau": "Multicouche PER-Alu-PER (NF DTU 60.1, ATec)"})
    if k.endswith("-WC"):
        props["Raccorde_a"] = SAN["WC"]["guid"]
    elif k.endswith("-LM"):
        props["Raccorde_a"] = ", ".join(SAN["LM"]["guid"])
    PLB[k] = new("IfcPipeSegment", r["nom"], styled([tube(r["pts"], r["d_ext"] / 2)], STY[r["sys"]]), mat=STY[r["sys"]],
                 predefined_type="RIGIDSEGMENT", lot="PLB", description=r["desc"], props=props)
    membre(r["sys"], PLB[k])

xd, yd = T.DESCENTE_WC


def accessoire(cls, name, items, key, pdt, desc, sysname, obj=None, props=None, psets=None):
    attrs = {"ObjectType": obj} if pdt == "USERDEFINED" else {}
    p = new(cls, name, styled(items, key), mat=key, predefined_type=pdt, lot="PLB", description=desc, props=props, psets=psets, **attrs)
    membre(sysname, p)
    return p


accessoire("IfcPipeSegment", "Colonne montante AEP de l'immeuble Ø 32 (hypothèse)", [cyl(*T.COLONNE_AEP, 0.016, 0.004, Z_DALLE_SOUS)], "aep",
           "RIGIDSEGMENT", "Colonne AEP supposée dans le coffrage EU/EV 1 : existence, matériau, diamètre et pression à relever", "AEP",
           psets=HYP)
if "EV-WC" in RES:
    p0, p1, p2 = RES["EV-WC"]["pts"]
    accessoire("IfcPipeFitting", "Pipe de WC excentrée Ø 100 (sortie horizontale)", [tube([(p0[0] - 0.040, p0[1], p0[2]), (p0[0] - 0.003, p0[1], p0[2])], 0.062)],
               "ev", "CONNECTOR", "Emboîtement sur la sortie existante du WC (joint à lèvre), sans dépose ni déplacement de la cuvette", "EV",
               props={"Raccorde_a": SAN["WC"]["guid"]})
    accessoire("IfcPipeFitting", "Coude 87°30 Ø 100 avec tampon de visite", [cyl(p1[0], p1[1], 0.060, p1[2] - 0.06, p1[2] + 0.06)], "ev", "BEND",
               "Coude à porte de visite (tampon) derrière la cuvette", "EV")
    accessoire("IfcPipeFitting", "Culotte EV Ø 100 / 100 à 87°30 sur la descente 1", [cyl(xd, yd, 0.0625, p2[2] - 0.08, p2[2] + 0.10)], "ev", "JUNCTION",
               "Culotte sur la descente de l'immeuble (remplacement d'un tronçon, coupe et manchons de dilatation)", "EV", psets=HYP)
if "EU-LM" in RES:
    pts = RES["EU-LM"]["pts"]
    bx, by = SAN["LM"]["bonde"]
    zp = SAN["LM"]["z_plan"]
    accessoire("IfcWasteTerminal", "Siphon Ø 40 du lave-mains (sur bonde existante)",
               [cyl(bx, by, 0.030, pts[0][2] - 0.03, zp - 0.07), cyl(bx, by, 0.016, zp - 0.07, zp - 0.005)], "eu", "USERDEFINED",
               "Siphon bouteille démontable sur la bonde existante (garde d'eau 50 mm), sans dépose du lave-mains", "EU", obj="Siphon",
               props={"Raccorde_a": ", ".join(SAN["LM"]["guid"])})
    accessoire("IfcValve", "Clapet d'admission d'air Ø 40 (AAV, EN 12380)",
               [tube([(bx + 0.08, by, pts[0][2]), (bx + 0.08, by, pts[0][2] + 0.08)], 0.020), cyl(bx + 0.08, by, 0.030, pts[0][2] + 0.08, pts[0][2] + 0.14)],
               "eu", "ANTIVACUUM", "Ventilation du branchement (longueur > 2 m) ; accessible sous le plan du lave-mains", "EU")
    for k, q in enumerate(pts[1:3], 1):
        accessoire("IfcPipeFitting", f"Coude 87°30 Ø 40 avec bouchon de dégorgement {k}", [cyl(q[0], q[1], 0.025, q[2] - 0.04, q[2] + 0.04)], "eu", "BEND",
                   "Bouchon de dégorgement à chaque changement de direction", "EU")
    accessoire("IfcPipeFitting", "Culotte EU Ø 100 / 40 sur la descente 1", [cyl(xd, yd, 0.0625, pts[-1][2] - 0.06, pts[-1][2] + 0.06)], "eu", "JUNCTION",
               "Culotte réduite 100/40 au-dessus de la culotte EV", "EU", psets=HYP)
accessoire("IfcPipeFitting", "Té de visite Ø 100 (tampon hermétique) sur la descente 1",
           [cyl(xd, yd, 0.0625, 0.65, 0.85), tube([(xd + 0.05, yd, 0.75), (0.335, yd, 0.75)], 0.045)], "ev", "USERDEFINED",
           "Tampon de visite face à la trappe du coffrage (curage de la descente et des branchements)", "EV", obj="Té de visite", psets=HYP)
yc = T.COLONNE_AEP[1]
for nom, x0, pdt, cls, desc in (("Vanne d'arrêt 1/4 de tour", 0.47, "ISOLATING", "IfcValve", "Isolement du local (accessible derrière la trappe)"),
                                ("Filtre à tamis", 0.56, "STRAINER", "IfcFilter", "Protection du compteur et du réducteur"),
                                ("Réducteur de pression (réglé 3 bar)", 0.65, "PRESSUREREDUCING", "IfcValve", "À poser si la pression de la colonne dépasse 3 bar"),
                                ("Clapet anti-retour EA contrôlable", 0.88, "CHECK", "IfcValve", "Protection anti-pollution du réseau de l'immeuble (NF EN 1717)")):
    accessoire(cls, nom, [tube([(x0 - 0.03, yc, T.Z_PIQUAGE_AEP), (x0 + 0.03, yc, T.Z_PIQUAGE_AEP)], 0.022)], "laiton", pdt, desc, "AEP")
accessoire("IfcFlowMeter", "Compteur divisionnaire eau froide DN 15", [box(0.715, yc - 0.03, 0.825, yc + 0.03, T.Z_PIQUAGE_AEP - 0.04, T.Z_PIQUAGE_AEP + 0.04)],
           "laiton", "WATERMETER", "Sous-comptage du local (à faire agréer par le syndic / la SODECI)", "AEP", psets=HYP)
accessoire("IfcPipeFitting", "Té AEP 20 / 16 / 16", [cyl(0.95, yc, 0.016, T.Z_AEP - 0.02, T.Z_AEP + 0.02)], "aep", "JUNCTION", "Départs WC et lave-mains", "AEP")
if "AEP-WC" in RES:
    accessoire("IfcValve", "Robinet d'arrêt WC", [tube([(0.45, 7.245, T.Z_AEP), (0.45, 7.195, T.Z_AEP)], 0.018)], "laiton", "ISOLATING",
               "Robinet d'arrêt avant le flexible du réservoir", "AEP")
if "AEP-LM" in RES:
    accessoire("IfcValve", "Robinet d'arrêt lave-mains", [cyl(2.89, 6.75, 0.018, 0.575, 0.625)], "laiton", "ISOLATING",
               "Robinet d'arrêt sous le plan ; robinet temporisé eau froide existant conservé", "AEP")
trappe = [box(0.40, 7.295, 1.00, 7.303, 1.08, 1.34), box(0.40, 7.303, 0.408, 7.407, 1.08, 1.34), box(0.992, 7.303, 1.00, 7.407, 1.08, 1.34),
          box(0.408, 7.303, 0.992, 7.407, 1.332, 1.34), box(0.408, 7.303, 0.992, 7.407, 1.08, 1.088)]
accessoire("IfcBuildingElementProxy", "Coffret AEP avec trappe de visite 0,60 x 0,26", trappe, "platre", "USERDEFINED",
           "Habillage BA13 H1 sur le mur arrière, trappe à clé : vanne, filtre, réducteur, compteur, clapet EA", "AEP", obj="Trappe de visite")
accessoire("IfcBuildingElementProxy", "Trappe de visite 0,20 x 0,34 du coffrage EU/EV 1", [box(0.392, 7.16, 0.400, 7.36, 0.58, 0.92)], "platre",
           "USERDEFINED", "Trappe acoustique dans la face est du coffrage, face au té de visite", "EV", obj="Trappe de visite")

# ============================ 4. circuits et réseaux ==================================================
LUM = {e.Name: e for e in f.by_type("IfcLightFixture")}
watt = {}
for nm, e in LUM.items():
    t = ue.get_type(e)
    watt[nm] = (ue.get_psets(t).get("Pset_LightFixtureTypeCommon", {}).get("TotalWattage") if t else None) or 0.0
for circ, noms in T.ECLAIRAGE.items():
    for nm in noms:
        membre(circ, LUM[nm])
for c in T.CIRCUITS:
    for nm in c.get("membres", []):
        membre(c["code"], by_name(nm))
for nm in ("Tableau divisionnaire (encastré dans l'habillage)", "Coffret arrivée électrique immeuble (disjoncteur de branchement)",
           "Coffret liaisons clim (alimentation et bus des 2 splits)", "Chemin de câbles placard technique -> tableau divisionnaire",
           "Chemin de câbles dérivation split 2", "Chemin de câbles tableau -> salle de lecture / split 1"):
    membre("CFO", by_name(nm))
membre("VDI", by_name("Baie informatique murale 9U"))
for nm in ("Liaisons frigorifiques et condensats - split 1", "Liaisons frigorifiques et condensats - split 2",
           "Mini-pompe de relevage des condensats - split 1", "Mini-pompe de relevage des condensats - split 2"):
    membre("COND", by_name(nm))
for nm in ("Descente EU/EV 1 (WC) Ø 100 (hypothèse)", "Descente EU/EV 2 (rangement) Ø 100 (hypothèse)"):
    membre("EV", by_name(nm))


def groupe(cls, name, pdt, desc, membres, pset=None):
    g = api("root.create_entity", f, ifc_class=cls, name=name, predefined_type=pdt)
    g.OwnerHistory = OH
    g.Description = desc
    if pset:
        api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=g, name="KDEMI_Circuit"), properties=pset)
    uniq = list({p.id(): p for p in membres}.values())
    if uniq:
        f.createIfcRelAssignsToGroup(ifcopenshell.guid.new(), OH, None, None, uniq, None, g)
    return g


for c in T.CIRCUITS:
    m = MEMBRES.get(c["code"], [])
    n_lum = sum(1 for p in m if p.is_a("IfcLightFixture") and ue.get_predefined_type(p) != "SECURITYLIGHTING")
    n_baes = sum(1 for p in m if p.is_a("IfcLightFixture") and ue.get_predefined_type(p) == "SECURITYLIGHTING")
    socles = sum(ue.get_psets(p)["KDEMI_Esquisse"].get("Nb_socles") or 0 for p in m if p.is_a("IfcOutlet"))
    P = c.get("P_W") or round(sum(watt.get(p.Name, 0.0) for p in m if p.is_a("IfcLightFixture") and ue.get_predefined_type(p) != "SECURITYLIGHTING")
                              + n_baes * T.P_BAES_W, 1)
    pset = {"Repere": c["code"], "Designation": c["nom"], "Protection": f"Disjoncteur 1P+N {c['In']} A courbe C",
            "Calibre_A": c["In"], "Section_mm2": c["S"], "Cable": f"U1000 R2V 3G{str(c['S']).replace('.', ',')}",
            "Differentiel": c["id"], "Nb_points_lumineux": n_lum + n_baes if c["type"] == "LIGHTING" else None,
            "Nb_socles": socles if c["code"].startswith("P") else None, "P_installee_W": float(P), "ku": c["ku"],
            "Commande": c.get("cmd")}
    groupe("IfcDistributionCircuit", f"Circuit {c['code']} - {c['nom']}", c["type"], c.get("cmd"), m,
           {k: v for k, v in pset.items() if v is not None})
for code, nom, pdt in (("AEP", "Réseau AEP eau froide (local 07)", "DOMESTICCOLDWATER"), ("EU", "Réseau EU (lave-mains)", "WASTEWATER"),
                       ("EV", "Réseau EV (WC, descentes de l'immeuble)", "SEWAGE"), ("COND", "Condensats des splits (relevage)", "DRAINAGE"),
                       ("VDI", "Courants faibles (VDI, Wi-Fi)", "DATA"), ("CFO", "Courants forts (tableau, chemins, goulottes)", "ELECTRICAL")):
    groupe("IfcDistributionSystem", nom, pdt, None, MEMBRES.get(code, []))

# ============================ 5. écriture ==========================================================
f.header.file_name.name = os.path.basename(T.V5_TECH)
f.header.file_name.time_stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
f.header.file_name.originating_system = "IfcOpenShell " + ifcopenshell.version + " - v5/scripts/construire_tech.py"
f.header.file_description.description = ("ViewDefinition [DesignTransferView]", "Bibliotheque Decimo - V5 lots techniques sur existant V4")
f.write(T.V5_TECH)
os.makedirs(T.TECHNIQUE, exist_ok=True)
with open(os.path.join(T.TECHNIQUE, "lecture_sanitaires.txt"), "w", encoding="utf-8") as fh:
    fh.write("Lecture des sanitaires V4 du local 07 dans v5/DECIMO_ESQ_V5.ifc (aucune modification)\n")
    fh.write("".join(f"- {n}\n" for n in NOTES))
print(f"ok {T.V5_TECH} : {len(AJOUTS)} produits ajoutés ({N_AVANT} -> {len(f.by_type('IfcProduct'))}), "
      f"{len(T.CIRCUITS)} circuits ; sanitaires lus : {sorted(SAN)}")
for n in NOTES:
    print("  -", n)
