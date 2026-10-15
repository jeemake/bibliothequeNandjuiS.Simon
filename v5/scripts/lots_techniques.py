"""Lots techniques de la V5 (hypothèses ESQ Ahoua) : électricité CFO/CFA, AEP / EU / EV, condensats, fixations.

Appelé par construire_v5.py (après l'aménagement, avant l'écriture du fichier) avec l'espace de noms du
constructeur. Rien n'est ajouté dans un élément V4 : appareillage en saillie sur goulottes, câbles en plénum
(routage sur grille hors murs, poteau, coffrages, doublage et oculus), passages par les baies existantes et
par des réservations légères dans des cloisons V4 non porteuses (signalées). Le WC (4350629) et le lave-mains
(4350630 / 4350631) V4 ne sont pas dupliqués : on leur raccorde les réseaux (IfcRelConnectsElements).
"""
import heapq
import numpy as np
import shapely
from shapely.geometry import Point, LineString, box as sbox
from shapely.ops import unary_union
from scipy import ndimage

from commun import (Z_FP_SOUS, Z_FP_DESSUS, Z_DALLE_SOUS, Z_DALLE_DESSUS, Z_CABLES, Z_LIAISONS, ARBRE, R_OCULUS,
                    TABLEAU, COFFRAGES, SPLIT1, SPLIT2, PLACARD_NET)

LOT_E = "Technique - électricité (hyp. ESQ Ahoua)"
LOT_P = "Technique - plomberie (hyp. ESQ Ahoua)"
LOT_F = "Technique - fixations (hyp. ESQ Ahoua)"
Z_COND = 3.08                       # refoulement des condensats en plénum
GRILLE = 0.05

# --- circuits (hypothèse ESQ : NF C 15-100 adaptée CI, tableau divisionnaire unique) --------------------------
CIRCUITS = [
    # code, désignation, type, protection, différentiel, section, système
    ("E1", "Éclairage salle de lecture - accueil et entrée", "LIGHTING", "DJ 10 A courbe C", "ID1 40 A 30 mA type AC", "3G1,5"),
    ("E2", "Éclairage salle de lecture - fond, salon, niche", "LIGHTING", "DJ 10 A courbe C", "ID1 40 A 30 mA type AC", "3G1,5"),
    ("E3", "Éclairage scénographique arbre à livres (gradable)", "LIGHTING", "DJ 10 A courbe C", "ID1 40 A 30 mA type AC", "3G1,5"),
    ("E4", "Éclairage coin lecture et salle de réunion", "LIGHTING", "DJ 10 A courbe C", "ID1 40 A 30 mA type AC", "3G1,5"),
    ("E5", "Éclairage locaux de service (rangement, dégagement, WC)", "LIGHTING", "DJ 10 A courbe C", "ID1 40 A 30 mA type AC", "3G1,5"),
    ("E6", "Vitrine et marquise (horloge + interrupteur crépusculaire)", "LIGHTING", "DJ 10 A courbe C", "ID1 40 A 30 mA type AC", "3G1,5"),
    ("E7", "BAES (alimentation non commandée, télécommande de repos)", "LIGHTING", "DJ 2 A", "ID1 40 A 30 mA type AC", "3G1,5"),
    ("P1", "Prises banque d'accueil", "ELECTRICAL", "DJ 20 A", "ID2 40 A 30 mA type A", "3G2,5"),
    ("P2", "Prises postes de lecture - salle", "ELECTRICAL", "DJ 20 A", "ID2 40 A 30 mA type A", "3G2,5"),
    ("P3", "Prises coin lecture et vitrine", "ELECTRICAL", "DJ 20 A", "ID2 40 A 30 mA type A", "3G2,5"),
    ("P4", "Prises salle de réunion", "ELECTRICAL", "DJ 20 A", "ID2 40 A 30 mA type A", "3G2,5"),
    ("P5", "Prises ménage et locaux de service (WC hors volumes)", "ELECTRICAL", "DJ 20 A", "ID3 40 A 30 mA type A", "3G2,5"),
    ("P6", "Baie informatique (onduleur) - circuit spécialisé", "ELECTRICAL", "DJ 16 A", "ID2 40 A 30 mA type A", "3G2,5"),
    ("CL1", "Split 1 salle de lecture (unité int. + mini-pompe) - spécialisé", "ELECTRICAL", "DJ 16 A courbe D", "ID3 40 A 30 mA type A", "3G2,5"),
    ("CL2", "Split 2 salle de réunion (unité int. + mini-pompe) - spécialisé", "ELECTRICAL", "DJ 16 A courbe D", "ID3 40 A 30 mA type A", "3G2,5"),
    ("VDI", "Courants faibles : RJ45 cat. 6A depuis la baie 9U (1 câble par prise)", "DATA", "-", "-", "U/FTP cat. 6A"),
]


def ajouter(B):
    f, new, styled, box, cyl, tube, api, OH = B["f"], B["new"], B["styled"], B["box"], B["cyl"], B["tube"], B["api"], B["OH"]
    by_tag, by_name, ZONES, MURS_V4 = B["by_tag"], B["by_name"], B["ZONES"], B["MURS_V4"]
    K, new_style = B["K"], B["new_style"]
    guid = B["ifcopenshell"].guid.new
    HYP = B["HYP"]

    for nm, hexc, key, kw in [("KDEMI - Réseau eau froide (multicouche)", "#3F6FA8", "aep", {}),
                              ("KDEMI - Câble électrique", "#2F2F2F", "cable", {}),
                              ("KDEMI - Goulotte iroko", "#A57650", "goulotte", {}),
                              ("KDEMI - Pictogramme BAES", "#3C8D4F", "baes", {"method": "FLAT"}),
                              ("KDEMI - Condensats (PVC cristal)", "#7FA7B8", "condensat", {})]:
        new_style(nm, hexc, **kw)
        K[key] = nm

    # ======================================================================================== géométrie
    def bar(p0, p1, hx, hy, hz):
        """Boîte entre p0 et p1 (axe dominant), demi-sections hx, hy, hz sur les axes non parcourus."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        h = np.array([hx, hy, hz])
        ax = int(np.argmax(np.abs(p1 - p0)))
        lo, hi = np.minimum(p0, p1) - h, np.maximum(p0, p1) + h
        lo[ax], hi[ax] = min(p0[ax], p1[ax]), max(p0[ax], p1[ax])
        return box(lo[0], lo[1], hi[0], hi[1], lo[2], hi[2])

    def fbox(face, u0, u1, z0, z1, d0, d1):
        """Boîte sur une face de mur : face = (axe, coordonnée, sens vers le local)."""
        a, c, s = face
        w0, w1 = sorted((c + s * d0, c + s * d1))
        return box(w0, u0, w1, u1, z0, z1) if a == "x" else box(u0, w0, u1, w1, z0, z1)

    def fpt(face, u, z, d):
        a, c, s = face
        return (c + s * d, u, z) if a == "x" else (u, c + s * d, z)

    def clean(pts):
        out = []
        for p in pts:
            p = tuple(round(float(v), 4) for v in p)
            if not out or np.linalg.norm(np.subtract(p, out[-1])) > 1e-4:
                out.append(p)
        keep = [out[0]]
        for i in range(1, len(out) - 1):
            a, b, c = np.array(keep[-1]), np.array(out[i]), np.array(out[i + 1])
            if np.linalg.norm(np.cross(b - a, c - b)) > 1e-9:
                keep.append(out[i])
        keep.append(out[-1])
        return keep

    # ======================================================================================== systèmes
    def systeme(cls, name, ptype, desc, props=None):
        s = api("system.add_system", f, ifc_class=cls)
        s.Name, s.Description, s.PredefinedType, s.OwnerHistory = name, desc, ptype, OH
        if props:
            api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=s, name="KDEMI_Circuit" if cls == "IfcDistributionCircuit" else "KDEMI_Reseau"),
                properties=props)
        return s

    def assign(s, *els):
        api("system.assign_system", f, products=list(els), system=s)

    SYS = {}
    for code, des, typ, prot, idf, sec in CIRCUITS:
        SYS[code] = systeme("IfcDistributionCircuit", f"{code} - {des}", typ, f"Circuit {code} du tableau divisionnaire (hyp. ESQ)",
                            {"Code": code, "Designation": des, "Protection": prot, "Differentiel": idf, "Cable": sec,
                             "Tableau": "TD (coin lecture, habillage iroko)", "Norme": "NF C 15-100 adaptée CI (CIE) - hypothèse ESQ"})
    SYS["CFO"] = systeme("IfcDistributionSystem", "CFO - Courants forts (tableau divisionnaire)", "ELECTRICAL",
                         "Arrivée immeuble (disjoncteur de branchement, placard technique) -> TD -> circuits E/P/CL",
                         {"Origine": "Colonne électrique de l'immeuble (pas de TGBT, pas de groupe électrogène)", "Statut": "À relever sur site"})
    SYS["AEP"] = systeme("IfcDistributionSystem", "AEP - Eau froide (réseau immeuble / SODECI)", "DOMESTICCOLDWATER",
                         "Piquage sur la colonne de l'immeuble (gaine EU/EV 1, à relever), comptage divisionnaire, WC et lave-mains V4",
                         {"Origine": "Colonne montante de l'immeuble (hypothèse)", "Eau_chaude": "Non (voir justification)", "Statut": "À relever sur site"})
    SYS["EU"] = systeme("IfcDistributionSystem", "EU - Eaux usées", "WASTEWATER", "Lave-mains V4 -> descente EU/EV 1 (DTU 60.11)",
                        {"Exutoire": "Descente EU/EV 1 de l'immeuble (à relever)", "Statut": "À relever sur site"})
    SYS["EV"] = systeme("IfcDistributionSystem", "EV - Eaux vannes", "SEWAGE", "WC V4 -> descente EU/EV 1 (DTU 60.11)",
                        {"Exutoire": "Descente EU/EV 1 de l'immeuble (à relever)", "Statut": "À relever sur site"})
    SYS["COND"] = systeme("IfcDistributionSystem", "Condensats des 2 splits (mini-pompes -> EU)", "DRAINAGE",
                          "Refoulement par mini-pompes en plénum, siphon puis piquage sur la descente EU/EV 2",
                          {"Exutoire": "Descente EU/EV 2 de l'immeuble (à relever)", "Statut": "À relever sur site"})
    SYS["VP"] = systeme("IfcDistributionSystem", "VP - Ventilation primaire des chutes (immeuble)", "VENT",
                        "Ventilation primaire assurée par le prolongement des chutes de l'immeuble hors toiture ; clapet aérateur sur l'antenne du lave-mains",
                        {"Statut": "À vérifier avec le syndic (chutes et ventilation de l'immeuble)"})

    def epset(el, circuit, typ, h=None, extra=None):
        props = {"Circuit": circuit, "Type": typ, "Tableau": "TD"}
        if h is not None:
            props["Hauteur_axe_m"] = round(float(h), 2)
        props.update(extra or {})
        api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=el, name="KDEMI_Electricite"), properties=props)
        assign(SYS[circuit], el)

    # ======================================================================================== routeur du plénum
    td = by_name("Tableau divisionnaire (encastré dans l'habillage)")
    INT = sbox(0.09, 0.09, 6.51, 7.41)
    COFF = unary_union([sbox(*v) for v in COFFRAGES.values()])
    DOUBLAGE = sbox(3.09, 7.06, 6.51, 7.41)
    OCU = Point(*ARBRE).buffer(R_OCULUS + 0.07, 64)
    R5_PORTAL = sbox(0.80, 5.00, 0.83, 5.20)
    R7_X = 2.415
    R7_PORTAL = sbox(R7_X - 0.015, 6.20, R7_X + 0.015, 6.40)
    obst = unary_union([MURS_V4, COFF, DOUBLAGE]).buffer(0.03, join_style=2).union(OCU)
    libre = INT.difference(obst).union(R5_PORTAL).union(R7_PORTAL)
    nx, ny = int((6.51 - 0.09) / GRILLE), int((7.41 - 0.09) / GRILLE)
    XC = 0.09 + GRILLE / 2 + GRILLE * np.arange(nx)
    YC = 0.09 + GRILLE / 2 + GRILLE * np.arange(ny)
    GX, GY = np.meshgrid(XC, YC, indexing="ij")
    FREE = shapely.contains_xy(libre, GX, GY)
    TRAYS = [LineString([(0.83, 5.40), (0.83, 0.44), (2.78, 0.44)]), LineString([(0.83, 3.60), (0.18, 3.60)]),
             LineString([(2.78, 0.44), (2.78, 1.10), (5.50, 1.10), (5.50, 4.30), (6.40, 4.30), (6.40, 4.95)]),
             LineString([(3.20, 1.10), (3.20, 6.95)])]
    near_tray = shapely.distance(unary_union(TRAYS), shapely.points(GX, GY)) < 0.06
    COST = np.where(near_tray, 0.45, 1.0)
    LAB, _ = ndimage.label(FREE)

    def cell(p):
        i, j = int(round((p[0] - XC[0]) / GRILLE)), int(round((p[1] - YC[0]) / GRILLE))
        best, bd = None, 9
        for di in range(-4, 5):
            for dj in range(-4, 5):
                a, b = i + di, j + dj
                if 0 <= a < nx and 0 <= b < ny and FREE[a, b]:
                    d = (XC[a] - p[0]) ** 2 + (YC[b] - p[1]) ** 2
                    if d < bd:
                        best, bd = (a, b), d
        assert best is not None, ("point hors plénum libre", p)
        return best

    def comp(p):
        return LAB[cell(p)]

    DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    def astar(a, b):
        s, t = cell(a), cell(b)
        assert LAB[s] == LAB[t], ("compartiments de plénum différents", a, b)
        dist = {}
        pq = [(0.0, s[0], s[1], -1)]
        prev = {}
        while pq:
            d, i, j, k = heapq.heappop(pq)
            if (i, j, k) in dist:
                continue
            dist[(i, j, k)] = d
            if (i, j) == t:
                end = (i, j, k)
                break
            for kk, (di, dj) in enumerate(DIRS):
                a2, b2 = i + di, j + dj
                if 0 <= a2 < nx and 0 <= b2 < ny and FREE[a2, b2] and (a2, b2, kk) not in dist:
                    nd = d + COST[a2, b2] + (4.0 if k not in (-1, kk) else 0.0)
                    key = (a2, b2, kk)
                    if nd < prev.get(key, (1e18,))[0]:
                        prev[key] = (nd, (i, j, k))
                        heapq.heappush(pq, (nd, a2, b2, kk))
        path = [end]
        while path[-1][:2] != s:
            path.append(prev[path[-1]][1])
        cells = [(XC[i], YC[j]) for i, j, _ in reversed(path)]
        c0, c1 = cells[0], cells[-1]
        pts = [(a[0], a[1]), (c0[0], a[1]) if abs(a[1] - c0[1]) < abs(a[0] - c0[0]) else (a[0], c0[1])] + cells \
            + [(c1[0], b[1]) if abs(b[1] - c1[1]) < abs(b[0] - c1[0]) else (b[0], c1[1]), (b[0], b[1])]
        return [(x, y, Z_CABLES) for x, y in pts]

    # passage du dégagement par la baie libre V4 (sans percement) : goulotte sur lambris, moulure sous linteau
    Y_SOF, Z_SOF = 5.36, 2.088
    SOF_MAIN, SOF_DEG = (3.165, Y_SOF), (2.865, Y_SOF)
    SOFFIT = [(3.165, Y_SOF, Z_CABLES), (3.12, Y_SOF, Z_CABLES), (3.12, Y_SOF, Z_SOF), (2.90, Y_SOF, Z_SOF), (2.90, Y_SOF, Z_CABLES),
              (2.865, Y_SOF, Z_CABLES)]
    MAIN = comp((2.78, 0.44))
    DEG = comp((2.40, 5.70))

    def route(a, b):
        ca, cb = comp(a), comp(b)
        if ca == cb:
            return astar(a, b)
        if ca == MAIN and cb == DEG:
            return astar(a, SOF_MAIN) + SOFFIT + astar(SOF_DEG, b)
        if ca == DEG and cb == MAIN:
            return astar(a, SOF_DEG) + SOFFIT[::-1] + astar(SOF_MAIN, b)
        raise AssertionError(("route impossible", a, b))

    # ======================================================================================== appareils électriques
    F = {"EST": ("x", 6.495, -1), "OUEST": ("x", 0.09, 1), "R07E": ("x", 3.09, 1), "R07O": ("x", 2.91, -1),
         "R08O": ("x", 2.91, -1), "LAMB": ("x", 3.11, 1), "FAC": ("y", 0.09, 1), "FACE": ("y", 0.105, 1),
         "PIL": ("x", 5.61, -1), "CLP": ("x", 2.96, -1), "C176": ("x", 1.76, -1), "P620": ("y", 6.36, 1), "JOUE": ("x", 1.13, -1)}
    GAP = 0.002                     # jeu laissé contre les porteurs (fixation en applique, aucune saignée)

    def goulotte(nom, face, u, z0, z1, w=0.06, d=0.02, circuit_txt="", label="Goulotte en applique (descente depuis le plénum)"):
        a = face[0]
        hu, hd = w / 2, d / 2
        p0, p1 = fpt(face, u, z0, GAP + hd), fpt(face, u, z1, GAP + hd)
        it = bar(p0, p1, hd if a == "x" else hu, hu if a == "x" else hd, 0)
        g = new("IfcCableCarrierSegment", f"Goulotte {nom}", styled([it], "goulotte"), predefined_type="CABLETRUNKINGSEGMENT",
                lot=LOT_E, mat="goulotte", rep_label=label,
                description=f"Goulotte iroko {int(w * 1000)} x {int(d * 1000)} en applique, chevillage court (aucune saignée ni boîte d'encastrement dans l'existant) ; {circuit_txt}",
                props={"Traverse_structure": False}, psets=HYP)
        return g, fpt(face, u, z1, GAP + hd)

    def appareil(cls, ptype, nom, items, circuit, typ, h, mat="equip", extra=None, otype=None, label=None, desc=None):
        kw = {"ObjectType": otype} if otype else {}
        el = new(cls, nom, styled(items, mat), predefined_type=ptype, lot=LOT_E, mat=mat, rep_label=label, description=desc, psets=HYP, **kw)
        epset(el, circuit, typ, h, extra)
        return el

    def normale(face):
        return ("+" if face[2] > 0 else "-") + face[0]

    def prise(nom, face, u, z, circuit, d0, kind="PC", label=None, desc=None):
        it = fbox(face, u - 0.036, u + 0.036, z - 0.036, z + 0.036, d0, d0 + 0.035)
        if kind == "PC":
            el = appareil("IfcOutlet", "POWEROUTLET", nom, [it], circuit, "PC 16 A 2P+T à éclips", z, extra={"Socles": 1, "Normale": normale(face)}, label=label, desc=desc)
        else:
            el = appareil("IfcOutlet", "DATAOUTLET", nom, [it], "VDI", "RJ45 cat. 6A blindée (données)", z, mat="equip_gris",
                          extra={"Socles": 1, "Brassage": "Baie 9U placard technique", "Normale": normale(face)}, label=label, desc=desc)
        return el

    def commande(cls, ptype, nom, face, u, z, circuit, typ, d0, commande_de, otype=None):
        it = fbox(face, u - 0.045, u + 0.045, z - 0.045, z + 0.045, d0, d0 + 0.035)
        el = appareil(cls, ptype, nom, [it], circuit, typ, z, extra={"Commande": commande_de, "Normale": normale(face)}, otype=otype,
                      label="Commande d'éclairage (axe +1,10)")
        return el

    # -- groupe accueil (mur est, banque d'accueil) ---------------------------------------------------------
    gA, topA = goulotte("accueil - mur est", F["EST"], 1.80, 0.37, Z_FP_DESSUS, circuit_txt="circuits P1, E1/E2/E3 (commande), VDI")
    nr = new("IfcJunctionBox", "Nourrice de goulotte - banque d'accueil", styled([fbox(F["EST"], 1.55, 2.05, 0.25, 0.37, GAP, 0.05)], "goulotte"),
             predefined_type="POWER", ObjectType="Nourrice de goulotte", lot=LOT_E, mat="goulotte",
             rep_label="Nourrice de goulotte / boîte de sol", description="Nourrice 6 modules (4 PC 16 A + 2 RJ45) en pied de mur, alimentée par la goulotte",
             psets=HYP)
    epset(nr, "P1", "Nourrice de goulotte 6 modules", 0.31)
    acc = [prise(f"PC 16 A accueil {k + 1}", F["EST"], 1.59 + 0.075 * k, 0.31, "P1", 0.05) for k in range(4)]
    acc += [prise(f"RJ45 accueil {k + 1}", F["EST"], 1.89 + 0.075 * k, 0.31, "P1", 0.05, kind="RJ") for k in range(2)]
    s1 = commande("IfcSwitchingDevice", "KEYPAD", "S1 - Clavier de commande éclairage (accueil)", F["EST"], 1.80, 1.10, "E1", "Clavier 4 boutons-poussoirs + variateur", GAP + 0.02,
                  "E1, E2 (télérupteurs, va-et-vient avec S2), E3 (variateur), E6 (forçage)")
    PP = {}
    PP["accueil"] = (topA[0], topA[1])

    # -- pilier (salon de lecture, boîte de sol, ménage salle) ---------------------------------------------
    gP, topP = goulotte("pilier - face ouest", F["PIL"], 3.47, 0.05, Z_FP_DESSUS, circuit_txt="circuits P2 (boîte de sol salon), P5 (ménage salle), VDI")
    pm1 = prise("PC 16 A ménage salle de lecture (pilier)", F["PIL"], 3.47, 0.30, "P5", GAP + 0.02)
    fb1 = new("IfcJunctionBox", "Boîte de sol - salon de lecture", styled([box(5.11, 3.36, 5.33, 3.58, -0.075, 0.004)], "acier"), predefined_type="POWER",
              ObjectType="Boîte de sol", lot=LOT_E, mat="acier", rep_label="Nourrice de goulotte / boîte de sol",
              description="Boîte de sol 3 modules, couvercle laiton affleurant le terrazzo ; table centrale sans mur proche (pilier à 0,56 m)",
              props={"Profondeur_dans_sol_existant_m": 0.075}, psets=HYP)
    epset(fb1, "P2", "Boîte de sol 3 modules", 0.0)
    sal = [new("IfcOutlet", f"{'PC 16 A' if k < 2 else 'RJ45'} boîte de sol salon {k + 1 if k < 2 else 1}",
               styled([box(5.14 + 0.055 * k, 3.43, 5.19 + 0.055 * k, 3.51, -0.03, -0.002)], "equip" if k < 2 else "equip_gris"),
               predefined_type="POWEROUTLET" if k < 2 else "DATAOUTLET", lot=LOT_E, mat="equip", psets=HYP) for k in range(3)]
    for k, e in enumerate(sal):
        epset(e, "P2" if k < 2 else "VDI", "PC 16 A 2P+T (boîte de sol)" if k < 2 else "RJ45 cat. 6A (boîte de sol)", 0.0, {"Socles": 1})
    cs = new("IfcCableCarrierSegment", "Conduit sous sol - pilier -> boîte de sol salon",
             styled([tube([(5.595, 3.47, 0.06), (5.595, 3.47, -0.035), (5.33, 3.47, -0.035)], 0.012)], "pvc"),
             predefined_type="CONDUITSEGMENT", lot=LOT_E, mat="pvc", description="Conduit ICTA Ø 25 en saignée de chape (dallage existant : épaisseur à relever)",
             props={"Traverse_structure": False}, psets=HYP)
    PP["pilier"] = (topP[0], topP[1])

    # -- console vinyles / poste catalogue (refend 4350607, face est) -----------------------------------------
    gC, topC = goulotte("poste catalogue - refend 4350607", F["R07E"], 2.40, 1.12, Z_FP_DESSUS, circuit_txt="circuit P2, VDI")
    nc = new("IfcJunctionBox", "Nourrice de goulotte - poste catalogue et écoute (console)", styled([fbox(F["R07E"], 2.25, 2.55, 1.00, 1.12, GAP, 0.05)], "goulotte"),
             predefined_type="POWER", ObjectType="Nourrice de goulotte", lot=LOT_E, mat="goulotte", rep_label="Nourrice de goulotte / boîte de sol",
             description="Nourrice 3 modules au-dessus de la console V4 (+0,95)", psets=HYP)
    epset(nc, "P2", "Nourrice de goulotte 3 modules", 1.06)
    con = [prise(f"PC 16 A poste catalogue {k + 1}", F["R07E"], 2.29 + 0.075 * k, 1.06, "P2", 0.05) for k in range(2)]
    con += [prise("RJ45 poste catalogue", F["R07E"], 2.44, 1.06, "P2", 0.05, kind="RJ")]
    PP["console"] = (topC[0], topC[1])

    # -- niche banquette (conduit dans le doublage V4 par R6) -------------------------------------------------
    cn = new("IfcCableCarrierSegment", "Conduit dans le doublage V4 - niche banquette",
             styled([tube([(4.14, 6.98, Z_CABLES), (4.14, 7.24, Z_CABLES), (4.14, 7.24, 0.60), (4.175, 7.24, 0.60)], 0.010)], "pvc"),
             predefined_type="CONDUITSEGMENT", lot=LOT_E, mat="pvc", rep_label="Réservation Ø 0,04 (passage léger, hors structure)",
             description="Conduit ICTA Ø 20 dans le vide du doublage cintré V4 entre les niches (entrée par R6)", props={"Traverse_structure": False}, psets=HYP)
    pn = prise("PC 16 A + USB niche banquette", ("x", 4.18, 1), 7.24, 0.60, "P2", 0.0, desc="Joue de la niche N02, sous la liseuse")
    PP["niche"] = (4.14, 6.98)

    # -- coin lecture / vitrine : trumeau entre baies A et B, boîte de sol de la table ------------------------
    gV, topV = goulotte("trumeau baies A / B", F["FAC"], 1.875, 0.0, Z_FP_DESSUS, d=0.025, circuit_txt="circuits P3, VDI (descente vers le sol, hors dégagement du TD)")
    pv = prise("PC 16 A podium de vitrine", ("x", 1.58, 1), 0.30, 0.30, "P3", 0.0, desc="Joue est du podium V5 (écran ou éclairage d'appoint de la vitrine), hors dégagement du TD")
    fb2 = new("IfcJunctionBox", "Boîte de sol - table du coin lecture", styled([box(1.01, 0.95, 1.23, 1.17, -0.075, 0.004)], "acier"), predefined_type="POWER",
              ObjectType="Boîte de sol", lot=LOT_E, mat="acier", rep_label="Nourrice de goulotte / boîte de sol",
              description="Boîte de sol 3 modules sous parquet (couvercle iroko) ; table ronde centrale, rayonnages à 0,53 m",
              props={"Profondeur_dans_sol_existant_m": 0.075}, psets=HYP)
    epset(fb2, "P3", "Boîte de sol 3 modules", 0.0)
    coin = [new("IfcOutlet", f"{'PC 16 A' if k < 2 else 'RJ45'} boîte de sol coin lecture {k + 1 if k < 2 else 1}",
                styled([box(1.04 + 0.055 * k, 1.02, 1.09 + 0.055 * k, 1.10, -0.03, -0.002)], "equip" if k < 2 else "equip_gris"),
                predefined_type="POWEROUTLET" if k < 2 else "DATAOUTLET", lot=LOT_E, mat="equip", psets=HYP) for k in range(3)]
    for k, e in enumerate(coin):
        epset(e, "P3" if k < 2 else "VDI", "PC 16 A 2P+T (boîte de sol)" if k < 2 else "RJ45 cat. 6A (boîte de sol)", 0.0, {"Socles": 1})
    cv = new("IfcCableCarrierSegment", "Conduit sous sol - trumeau -> boîte de sol coin lecture et podium",
             styled([tube([(1.875, 0.1045, 0.06), (1.875, 0.1045, -0.035)], 0.010), tube([(1.875, 0.1045, -0.035), (1.875, 0.30, -0.035)], 0.010),
                     tube([(1.875, 0.30, -0.035), (1.875, 1.06, -0.035), (1.23, 1.06, -0.035)], 0.010),
                     tube([(1.875, 0.30, -0.035), (1.595, 0.30, -0.035)], 0.010), tube([(1.595, 0.30, -0.035), (1.595, 0.30, 0.26)], 0.010)], "pvc"),
             predefined_type="CONDUITSEGMENT", lot=LOT_E, mat="pvc", description="Conduits ICTA Ø 20 en saignée de chape (dallage existant : épaisseur à relever), remontée dans la goulotte du trumeau",
             props={"Traverse_structure": False}, psets=HYP)
    PP["vitrine"] = (topV[0], topV[1])
    gS3, topS3 = goulotte("commande coin lecture", F["R07O"], 1.92, 1.16, Z_FP_DESSUS, circuit_txt="circuit E4")
    s3 = commande("IfcSwitchingDevice", "TOGGLESWITCH", "S3 - Interrupteur double coin lecture", F["R07O"], 1.92, 1.10, "E4", "Double allumage (downlights / suspension)", GAP + 0.02,
                  "E4 (coin lecture)")
    PP["s3"] = (topS3[0], topS3[1])

    # -- salle de réunion : goulotte basse sur mur mitoyen ouest ------------------------------------------------
    gR, topR = goulotte("réunion - descente mur ouest", F["OUEST"], 2.70, 0.28, Z_FP_DESSUS, circuit_txt="circuit P4, VDI")
    gRb = new("IfcCableCarrierSegment", "Goulotte basse réunion - mur ouest",
              styled([bar(fpt(F["OUEST"], 2.67, 0.22, GAP + 0.02), fpt(F["OUEST"], 4.70, 0.22, GAP + 0.02), 0.02, 0, 0.06)], "goulotte"),
              predefined_type="CABLETRUNKINGSEGMENT", lot=LOT_E, mat="goulotte", rep_label="Goulotte en applique (descente depuis le plénum)",
              description="Goulotte 120 x 40 à +0,16 / +0,28 sous le tableau mural V4, appareillage en façade", props={"Traverse_structure": False}, psets=HYP)
    reu = []
    for g, y0 in (("A", 3.00), ("B", 4.35)):
        reu += [prise(f"PC 16 A réunion {g}{k + 1}", F["OUEST"], y0 + 0.075 * k, 0.22, "P4", GAP + 0.04) for k in range(2)]
        reu += [prise(f"RJ45 réunion {g}", F["OUEST"], y0 + 0.15, 0.22, "P4", GAP + 0.04, kind="RJ")]
    PP["reunion"] = (topR[0], topR[1])
    gS4, topS4 = goulotte("commande réunion", F["CLP"], 3.95, 1.16, Z_FP_DESSUS, circuit_txt="circuit E4")
    s4 = commande("IfcSwitchingDevice", "DIMMERSWITCH", "S4 - Interrupteur variateur salle de réunion", F["CLP"], 3.95, 1.10, "E4", "Interrupteur + variateur (linéaire)", GAP + 0.02,
                  "E4 (réunion)")
    PP["s4"] = (topS4[0], topS4[1])

    # -- salle de lecture, fond : bouton-poussoir de va-et-vient dans le lambris ---------------------------------
    cl = new("IfcCableCarrierSegment", "Conduit dans le lambris - commande S2",
             styled([tube([(3.10, 5.18, Z_CABLES), (3.10, 5.18, 1.10), (3.11, 5.18, 1.10)], 0.006)], "pvc"), predefined_type="CONDUITSEGMENT",
             lot=LOT_E, mat="pvc", description="Conduit ICTA Ø 12 entre tasseaux du lambris iroko V5", props={"Traverse_structure": False}, psets=HYP)
    s2 = commande("IfcSwitchingDevice", "MOMENTARYSWITCH", "S2 - Bouton-poussoir double (fond de salle, va-et-vient)", F["LAMB"], 5.18, 1.10, "E1",
                  "Boutons-poussoirs sur télérupteurs E1 / E2", 0.0, "E1, E2 (2e point de commande, va-et-vient avec S1)")
    PP["s2"] = (3.165, 5.18)

    # -- passage du dégagement par la baie libre V4 (moulure sous linteau) -------------------------------------
    gsof = new("IfcCableCarrierSegment", "Goulotte et moulure du passage de la baie libre (dégagement)",
               styled([bar((3.12, Y_SOF, Z_SOF + 0.02), (3.12, Y_SOF, Z_FP_DESSUS), 0.01, 0.02, 0),
                       bar((3.13, Y_SOF, Z_SOF), (2.89, Y_SOF, Z_SOF), 0, 0.02, 0.009),
                       bar((2.90, Y_SOF, Z_SOF + 0.02), (2.90, Y_SOF, Z_FP_DESSUS), 0.008, 0.02, 0)], "goulotte"),
               predefined_type="CABLETRUNKINGSEGMENT", lot=LOT_E, mat="goulotte", rep_label="Goulotte en applique (descente depuis le plénum)",
               description="Goulotte 40 x 20 sur le lambris, moulure iroko 40 x 18 sous le linteau de la baie libre V4 (aucun percement du refend 4350608), goulotte côté dégagement",
               props={"Traverse_structure": False}, psets=HYP)
    gD, topD = goulotte("dégagement - refend 4350608", F["R08O"], 5.22, 0.36, Z_FP_DESSUS, circuit_txt="circuits E5, P5")
    s5 = commande("IfcSwitchingDevice", "TOGGLESWITCH", "S5 - Interrupteur dégagement", F["R08O"], 5.22, 1.10, "E5", "Interrupteur simple", GAP + 0.02, "E5 (dégagement)")
    pm2 = prise("PC 16 A ménage dégagement", F["R08O"], 5.22, 0.30, "P5", GAP + 0.02)
    PP["deg"] = (topD[0], topD[1])

    # -- WC : réservation R7 dans la cloison placo 4350620, prise hors volumes, détecteur -------------------------
    gW, topW = goulotte("WC - cloison 4350620", F["P620"], 1.50, 1.16, Z_FP_DESSUS, circuit_txt="circuit P5")
    pw = prise("PC 16 A WC (hors volumes)", F["P620"], 1.50, 1.10, "P5", 0.02, desc="À plus de 0,60 m du lave-mains, +1,10")
    det = new("IfcSensor", "D1 - Détecteur de présence WC", styled([cyl(2.00, 6.80, 0.05, Z_FP_SOUS - 0.035, Z_FP_SOUS), cyl(2.00, 6.80, 0.03, Z_FP_SOUS, Z_FP_SOUS + 0.04)], "equip"),
              predefined_type="MOVEMENTSENSOR", ObjectType="Détecteur de présence", lot=LOT_E, mat="equip", rep_label="Détecteur de présence plafond (WC)",
              description="Détecteur de présence 360° encastré, temporisation 5 min, commande le downlight du WC (E5)", psets=HYP)
    epset(det, "E5", "Détecteur de présence encastré", Z_FP_SOUS, {"Commande": "E5 (WC)"})
    PP["wc_pc"] = (topW[0], topW[1])
    PP["det"] = (2.00, 6.80)

    # -- rangement et placard technique ---------------------------------------------------------------------
    gG, topG = goulotte("rangement - cloison V4", F["C176"], 5.24, 0.36, Z_FP_DESSUS, circuit_txt="circuits E5, P5")
    s6 = commande("IfcSwitchingDevice", "TOGGLESWITCH", "S6 - Interrupteur rangement", F["C176"], 5.24, 1.10, "E5", "Interrupteur simple", GAP + 0.02, "E5 (rangement)")
    pm3 = prise("PC 16 A rangement", F["C176"], 5.24, 0.30, "P5", GAP + 0.02)
    PP["rangement"] = (topG[0], topG[1])
    pb = [prise(f"PC 16 A baie informatique {k + 1}", F["JOUE"], 5.30 + 0.09 * k, 1.00, "P6", 0.0, desc="Onduleur et alimentation de la baie 9U") for k in range(2)]
    PP["baie"] = (1.05, 5.40)

    # -- point d'accès Wi-Fi plafond ------------------------------------------------------------------------
    ap = new("IfcCommunicationsAppliance", "Point d'accès Wi-Fi plafond (PoE)", styled([cyl(3.75, 3.00, 0.10, Z_FP_SOUS - 0.035, Z_FP_SOUS)], "equip"),
             predefined_type="USERDEFINED", ObjectType="Point d'accès Wi-Fi", lot=LOT_E, mat="equip", rep_label="Point d'accès Wi-Fi plafond (PoE)",
             description="Borne Wi-Fi 6 PoE fixée sur une platine de faux-plafond, centre de la salle de lecture", psets=HYP)
    epset(ap, "VDI", "Point d'accès Wi-Fi 6 PoE", Z_FP_SOUS)
    rap = new("IfcOutlet", "RJ45 point d'accès Wi-Fi (plénum)", styled([box(3.71, 2.96, 3.79, 3.04, Z_FP_DESSUS, Z_FP_DESSUS + 0.04)], "equip_gris"),
              predefined_type="DATAOUTLET", lot=LOT_E, mat="equip_gris", description="Prise RJ45 cat. 6A en plénum au-dessus de la borne", psets=HYP)
    epset(rap, "VDI", "RJ45 cat. 6A (plénum)", Z_FP_DESSUS, {"Socles": 1})
    PP["ap"] = (3.75, 3.00)

    # -- BAES ---------------------------------------------------------------------------------------------------
    def baes(nom, items, h, desc, pp, nrm="plafond"):
        el = new("IfcLightFixture", nom, items, predefined_type="SECURITYLIGHTING", lot=LOT_E, rep_label="BAES évacuation / balisage (SATI, 1 h)",
                 description=desc, psets={"KDEMI_BAES": {"Type": "BAES évacuation SATI", "Autonomie_h": 1.0, "Flux_lm": 45, "Alimentation": "E7 non commandée"}, **HYP})
        epset(el, "E7", "BAES évacuation SATI 45 lm 1 h", h, {"Normale": nrm})
        PP[nom] = pp
        return el

    def baes_mur(face, u, z0):
        return styled([fbox(face, u - 0.165, u + 0.165, z0, z0 + 0.12, GAP, GAP + 0.06)], "equip") + \
            styled([fbox(face, u - 0.06, u + 0.06, z0 + 0.03, z0 + 0.09, GAP + 0.06, GAP + 0.062)], "baes")
    B1 = baes("BAES 1 - au-dessus de la porte d'entrée", baes_mur(F["FACE"], 4.10, 2.84), 2.90,
              "BAES d'évacuation « SORTIE » au-dessus de la porte d'entrée (face intérieure, sur l'enduit terre)", (4.10, 0.16), "+y")
    B2 = baes("BAES 2 - dégagement, vers la salle de lecture", baes_mur(F["R08O"], 5.72, 2.20), 2.26,
              "Balisage au-dessus de la baie libre V4, côté dégagement (sortie vers la salle)", (2.865, 5.72), "-x")
    B3 = baes("BAES 3 - coin lecture, passage à galandage", baes_mur(("x", 2.91, -1), 1.35, 2.20), 2.26,
              "Balisage sur la retombée BA13 du passage à galandage, côté coin lecture", (2.865, 1.35), "-x")
    B4 = baes("BAES 4 - circulation salle de lecture (drapeau)",
              styled([box(3.52, 4.385, 3.58, 4.715, 2.78, 2.90), cyl(3.55, 4.55, 0.006, 2.90, Z_FP_SOUS)], "equip")
              + styled([box(3.582, 4.49, 3.584, 4.61, 2.81, 2.87), box(3.516, 4.49, 3.518, 4.61, 2.81, 2.87)], "baes"), 2.84,
              "BAES drapeau double face sous faux-plafond, circulation entre la réunion et l'arbre à livres", (3.55, 4.55))

    # ======================================================================================== luminaires V5 existants
    LUM = {lf.Name: lf for lf in f.by_type("IfcLightFixture") if lf.PredefinedType != "SECURITYLIGHTING"}
    assert len(LUM) == 27, len(LUM)

    def lum_pp(lf):
        v = B["bbox_monde"](lf)
        return ((v[0][0] + v[1][0]) / 2, (v[0][1] + v[1][1]) / 2)

    ECL = {"E1": [f"Downlight encastré Salle de lecture {k}" for k in range(1, 9)],
           "E2": [f"Downlight encastré Salle de lecture {k}" for k in range(9, 14)] + ["Suspension terre cuite - salon de lecture", "Liseuse niche banquette"],
           "E3": ["Anneau LED indirect de l'oculus", "Anneau LED sous la canopée de l'arbre à livres"],
           "E4": [f"Downlight encastré Coin lecture / vitrine {k}" for k in range(1, 4)] + ["Suspension terre cuite - table coin lecture", "Linéaire suspendu - table de réunion"],
           "E5": ["Downlight encastré Rangement 1", "Downlight encastré Dégagement 1", "Downlight encastré WC 1"],
           "E6": ["Réglette LED de vitrine (baie A)", "Spot encastré sous marquise"]}
    COMMANDE = {"E1": "S1 + S2 (télérupteur, va-et-vient)", "E2": "S1 + S2 (télérupteur, va-et-vient)", "E3": "S1 (variateur)",
                "E4": "S3 (coin lecture), S4 (réunion)", "E5": "S6 (rangement), S5 (dégagement), D1 détecteur (WC)", "E6": "Horloge + interrupteur crépusculaire au TD, forçage S1"}
    assert sorted(sum(ECL.values(), [])) == sorted(LUM), set(LUM) ^ set(sum(ECL.values(), []))
    for c, noms in ECL.items():
        for n in noms:
            epset(LUM[n], c, "Luminaire LED 2700 K (V5)", None, {"Commande": COMMANDE[c]})
    # le détecteur pilote le downlight du WC
    f.createIfcRelFlowControlElements(guid(), OH, "D1 -> downlight WC", None, [det], LUM["Downlight encastré WC 1"])

    # point plénum spécifique (luminaires hors faux-plafond)
    PPL = {n: lum_pp(lf) for n, lf in LUM.items()}
    PPL["Anneau LED indirect de l'oculus"] = (3.24, 5.61)
    PPL["Anneau LED sous la canopée de l'arbre à livres"] = (3.24, 5.71)
    PPL["Liseuse niche banquette"] = PP["niche"]
    PPL["Réglette LED de vitrine (baie A)"] = (1.15, 0.16)
    PPL["Spot encastré sous marquise"] = (4.25, 0.16)
    DROP_L = {
        "Anneau LED indirect de l'oculus": [(3.24, 5.61, Z_CABLES), (3.30, 5.61, Z_CABLES), (3.30, 5.61, 3.13)],
        "Anneau LED sous la canopée de l'arbre à livres": [(3.24, 5.71, Z_CABLES), (3.45, 5.71, Z_CABLES), (3.45, 5.71, 3.26), (4.28, 5.71, 3.26), (4.28, 5.71, 2.37)],
        "Liseuse niche banquette": [(4.14, 6.98, Z_CABLES), (4.14, 7.24, Z_CABLES), (4.14, 7.24, 0.60), (4.20, 7.30, 0.60), (5.26, 7.30, 0.60), (5.26, 7.30, 1.30)],
        "Réglette LED de vitrine (baie A)": [(1.15, 0.16, Z_CABLES), (1.15, 0.115, Z_CABLES), (1.15, 0.115, 2.40), (1.15, 0.07, 2.40), (1.15, 0.07, 2.33)],
        "Spot encastré sous marquise": [(4.25, 0.16, Z_CABLES), (4.25, 0.125, Z_CABLES), (4.25, 0.125, 2.95)],
    }

    # ======================================================================================== câbles par circuit
    def drop_to(pp, z_dev, extra=()):
        return [(pp[0], pp[1], Z_CABLES), (pp[0], pp[1], z_dev)] + list(extra)

    STOPS = {  # circuit -> [(point plénum, descente 3D)]
        "E1": [(PPL[n], drop_to(PPL[n], 3.08)) for n in ECL["E1"]] + [(PP["s2"], [(3.165, 5.18, Z_CABLES), (3.10, 5.18, Z_CABLES), (3.10, 5.18, 1.10)]),
                                                                    (PP["accueil"], drop_to(PP["accueil"], 1.10))],
        "E2": [(PPL[n], DROP_L.get(n) or drop_to(PPL[n], 3.08)) for n in ECL["E2"]],
        "E3": [(PPL[n], DROP_L[n]) for n in ECL["E3"]],
        "E4": [(PPL[n], drop_to(PPL[n], 3.08)) for n in ECL["E4"]] + [(PP["s3"], drop_to(PP["s3"], 1.10)), (PP["s4"], drop_to(PP["s4"], 1.10))],
        "E5": [(PPL[n], drop_to(PPL[n], 3.08)) for n in ECL["E5"]] + [(PP["rangement"], drop_to(PP["rangement"], 1.10)), (PP["deg"], drop_to(PP["deg"], 1.10)),
                                                                    (PP["det"], drop_to(PP["det"], 3.04))],
        "E6": [(PPL[n], DROP_L[n]) for n in ECL["E6"]],
        "E7": [(pp, drop_to(pp, z)) for pp, z in ((PP[B1.Name], 2.96), (PP[B2.Name], 2.32), (PP[B3.Name], 2.32), (PP[B4.Name], 3.00))],
        "P1": [(PP["accueil"], drop_to(PP["accueil"], 0.31))],
        "P2": [(PP["pilier"], drop_to(PP["pilier"], 0.06)), (PP["console"], drop_to(PP["console"], 1.06)), (PP["niche"], DROP_L["Liseuse niche banquette"][:4])],
        "P3": [(PP["vitrine"], drop_to(PP["vitrine"], 0.06))],
        "P4": [(PP["reunion"], drop_to(PP["reunion"], 0.22))],
        "P5": [(PP["pilier"], drop_to(PP["pilier"], 0.30)), (PP["rangement"], drop_to(PP["rangement"], 0.30)), (PP["deg"], drop_to(PP["deg"], 0.30)),
               (PP["wc_pc"], drop_to(PP["wc_pc"], 1.10))],
        "P6": [(PP["baie"], drop_to(PP["baie"], 1.00))],
        "CL1": [((0.98, 5.30), drop_to((0.98, 5.30), 1.55)), ((6.39, 4.95), [(6.39, 4.95, Z_CABLES), (6.39, 4.95, SPLIT1[5])])],
        "CL2": [((0.98, 5.30), drop_to((0.98, 5.30), 1.55)), ((0.18, 3.66), [(0.18, 3.66, Z_CABLES), (0.18, 3.66, SPLIT2[5])])],
        "VDI": [(PP["baie"], drop_to(PP["baie"], 0.80)), (PP["reunion"], drop_to(PP["reunion"], 0.22)), (PP["vitrine"], drop_to(PP["vitrine"], 0.06)),
                (PP["accueil"], drop_to(PP["accueil"], 0.31)), (PP["pilier"], drop_to(PP["pilier"], 0.06)), (PP["ap"], drop_to(PP["ap"], 3.08)),
                (PP["console"], drop_to(PP["console"], 1.06))],
    }
    ORIG = (2.78, 0.44)
    CABLES = {}

    def ordre(start, stops):
        rest, out, cur = list(stops), [], start
        while rest:
            k = min(range(len(rest)), key=lambda i: (rest[i][0][0] - cur[0]) ** 2 + (rest[i][0][1] - cur[1]) ** 2
                    + (25.0 if comp(rest[i][0]) != comp(cur) else 0))
            out.append(rest.pop(k)); cur = out[-1][0]
        return out

    for code, stops in STOPS.items():
        start = PP["baie"] if code == "VDI" else ORIG
        seq = ordre(start, stops)
        main, cur = [], start
        for pp, _ in seq:
            main += route(cur, pp)
            cur = pp
        items = [tube(clean(main), 0.004)] + [tube(clean(d), 0.004) for _, d in seq if len(clean(d)) > 1]
        cdes = dict((c[0], c) for c in CIRCUITS)[code]
        el = new("IfcCableSegment", f"Câble circuit {code} - {cdes[1]}", styled(items, "cable"), predefined_type="CABLESEGMENT", lot=LOT_E, mat="cable",
                 description=f"{cdes[5]} depuis le TD, posé sur chemin de câbles ou attaches en plénum, descentes en goulotte ; "
                             "passages : galandage (au-dessus de la retombée), R5, R7, baie libre (moulure)",
                 props={"Traverse_structure": False}, psets=HYP)
        epset(el, code, f"Câble {cdes[5]}", None, {"Longueur_plenum_m": round(float(LineString([p[:2] for p in clean(main)]).length), 1)})
        CABLES[code] = (el, clean(main), seq)
    # spot sous marquise : traversée de façade par le fourreau existant de l'enseigne V4 (aucun nouveau percement)
    ext = new("IfcCableSegment", "Câble circuit E6 - partie extérieure (enseigne V4 -> spot sous marquise)",
              styled([tube([(4.10, -0.23, 2.87), (4.10, -0.23, 2.86), (4.10, -0.50, 2.86), (4.10, -0.50, 2.83)], 0.004)], "cable"),
              predefined_type="CABLESEGMENT", lot=LOT_E, mat="cable",
              description="Reprend le fourreau existant d'alimentation de l'enseigne V4 pour traverser la façade ; à relever sur site",
              props={"Traverse_structure": False}, psets=HYP)
    epset(ext, "E6", "Câble 3G1,5 extérieur IP65", None)
    # arrivée immeuble -> TD et nappe de départs dans l'habillage
    arr = new("IfcCableSegment", "Liaison disjoncteur de branchement -> tableau divisionnaire",
              styled([tube([(0.705, 5.23, 1.75), (0.705, 5.23, Z_CABLES)], 0.007), tube(clean(route((0.705, 5.23), ORIG)), 0.007),
                      tube([(2.78, 0.44, Z_CABLES), (2.78, 0.44, TABLEAU[5])], 0.007)], "cable"),
              predefined_type="CABLESEGMENT", lot=LOT_E, mat="cable", description="U1000 R2V 3G10 mm² sur le chemin de câbles C1 (hypothèse ESQ, à valider CIE)",
              props={"Traverse_structure": False}, psets=HYP)
    assign(SYS["CFO"], arr, td, by_name("Coffret arrivée électrique immeuble (disjoncteur de branchement)"))
    nap = new("IfcCableSegment", "Nappe des départs du tableau (gaine de l'habillage)", styled([tube([(2.78, 0.44, TABLEAU[5]), (2.78, 0.44, Z_CABLES)], 0.02)], "cable"),
              predefined_type="CABLESEGMENT", lot=LOT_E, mat="cable", description="Départs E1-E7, P1-P6, CL1-CL2 remontant dans la colonne iroko jusqu'au plénum",
              props={"Traverse_structure": False}, psets=HYP)
    assign(SYS["CFO"], nap)
    for c in SYS:
        if c in dict((x[0], x) for x in CIRCUITS) and c != "VDI":
            assign(SYS[c], td)
    assign(SYS["VDI"], by_name("Baie informatique murale 9U"))
    for k, sp in ((1, "CL1"), (2, "CL2")):
        u = by_name(f"Split mural 9 000 BTU/h - unité intérieure {k}")
        epset(u, sp, "Unité intérieure split 9 000 BTU/h", None)
        assign(SYS[sp], by_name(f"Mini-pompe de relevage des condensats - split {k}"))
    assign(SYS["CL1"], by_name("Coffret liaisons clim (alimentation et bus des 2 splits)"))

    # chemin de câbles complémentaire (fond ouest de la salle) + suspentes non traversantes
    c3 = [(3.20, 1.10, Z_CABLES), (3.20, 6.95, Z_CABLES)]
    new("IfcCableCarrierSegment", "Chemin de câbles fond ouest salle de lecture (vers baie libre et niches)", styled(B["run_boxes"](c3, 0.08, 0.04), "equip_gris"),
        predefined_type="CABLETRAYSEGMENT", lot=LOT_E, mat="equip_gris", rep_label="Chemin de câbles 80 x 40 en plénum",
        description="Dalle marine 80 x 40 sous dalle, entre le lambris et l'oculus ; suspentes à chevillage court", psets=HYP)

    # ======================================================================================== réservations légères
    def resa(code, nom, p0, p1, host, r=0.02):
        it = tube([p0, p1], r)
        return new("IfcBuildingElementProxy", f"Réservation {code} Ø 0,04 - {nom}", styled([it], "resa"), predefined_type="PROVISIONFORVOID",
                   lot=LOT_E if code != "R8" else LOT_P, mat="resa", rep_label="Réservation Ø 0,04 (passage léger, hors structure)",
                   description=f"Support : {host}. Carottage Ø 40 au-dessus du faux-plafond ; ne traverse ni poteau, ni voile, ni dalle.",
                   psets={"Pset_ProvisionForVoid": {"Shape": "Round", "Diameter": 4.0, "Depth": round(float(np.linalg.norm(np.subtract(p1, p0))) * 100, 1),
                                                    "System": "Courants forts" if code != "R8" else "Condensats"},
                          "KDEMI_Reservation": {"Code": code, "Support": host, "Traverse_structure": False}, **HYP})
    resa("R6", "Entrée conduit dans le doublage V4 (niche banquette)", (4.14, 7.06, Z_CABLES), (4.14, 7.14, Z_CABLES), "Doublage cintré V4 (non structurel)")
    resa("R7", "Passage câbles dégagement -> WC (cloison placo 4350620)", (R7_X, 6.24, Z_CABLES), (R7_X, 6.36, Z_CABLES), "Cloison placo V4 4350620 non porteuse")
    resa("R8", "Passage condensats réunion -> rangement (cloison placo 4350621)", (0.26, 5.04, Z_COND), (0.26, 5.16, Z_COND), "Cloison placo V4 4350621 non porteuse")

    # ======================================================================================== plomberie
    def pente(pts):
        out = []
        for a, b in zip(pts[:-1], pts[1:]):
            h = np.hypot(b[0] - a[0], b[1] - a[1])
            if h > 0.05:
                out.append(round(100 * (a[2] - b[2]) / h, 2))
        return out

    def tuyau(nom, pts, r, reseau, mat_ifc, materiau, dn, dext, desc, ptype="RIGIDSEGMENT", pente_txt=None, label=None, raccord=None):
        pts = clean(pts)
        p = pente(pts)
        el = new("IfcPipeSegment", nom, styled([tube(pts, r)], mat_ifc), predefined_type=ptype, lot=LOT_P, mat=mat_ifc, description=desc, rep_label=label,
                 props={"Traverse_structure": False},
                 psets={"KDEMI_Plomberie": {"Reseau": reseau, "Materiau": materiau, "DN_mm": dn, "Diametre_ext_mm": dext,
                                            "Pente_pct": pente_txt or (f"{min(p):.1f} % mini" if p else "vertical"),
                                            "Pente_min_pct": float(min(p)) if p else 0.0, "Raccordement": raccord or "-"}, **HYP})
        return el

    def organe(cls, ptype, nom, items, reseau, typ, mat="acier", desc=None, label=None, extra=None):
        props = {"Reseau": reseau, "Type": typ}
        props.update(extra or {})
        return new(cls, nom, styled(items, mat), predefined_type=ptype, lot=LOT_P, mat=mat, description=desc, rep_label=label,
                   psets={"KDEMI_Plomberie": props, **HYP})

    def relier(*els):
        for a, b in zip(els[:-1], els[1:]):
            pa, pb = api("system.add_port", f, element=a), api("system.add_port", f, element=b)
            pa.FlowDirection, pb.FlowDirection = "SOURCE", "SINK"
            api("system.connect_port", f, port1=pa, port2=pb)

    def raccord_v4(el, v4, txt):
        f.createIfcRelConnectsElements(guid(), OH, "Raccordement V5 sur appareil V4 conservé", txt, None, el, v4)

    WC = by_tag("4350629")            # WC à réservoir V4 (IfcFlowTerminal)
    LM_PLAN, LM_VASQUE = by_tag("4350630"), by_tag("4350631")
    DESC1 = by_name("Descente EU/EV 1 (WC) Ø 100 (hypothèse)")
    DESC2 = by_name("Descente EU/EV 2 (rangement) Ø 100 (hypothèse)")
    for d in (DESC1, DESC2):
        api("pset.edit_pset", f, pset=api("pset.add_pset", f, product=d, name="KDEMI_Plomberie"),
            properties={"Reseau": "EU/EV (chute immeuble)", "Materiau": "PVC (supposé)", "DN_mm": 100, "Diametre_ext_mm": 110,
                        "Ventilation_primaire": "Prolongement de la chute hors toiture par l'immeuble - à vérifier", "Pente_pct": "vertical"})
    assign(SYS["VP"], DESC1, DESC2)

    # AEP
    CX, CY = 0.165, 7.185
    col = tuyau("Colonne montante AEP immeuble (hypothèse, gaine EU/EV 1)", [(CX, CY, 0.0), (CX, CY, Z_DALLE_SOUS)], 0.016, "AEP", "aep",
                "Acier galvanisé / PEHD (supposé)", 25, 32, "Colonne d'eau froide de l'immeuble supposée dans la gaine EU/EV 1 ; position, diamètre et pression à relever",
                pente_txt="vertical", label="Raccordement immeuble « à relever »", raccord="Réseau immeuble / SODECI")
    te0 = organe("IfcPipeFitting", "JUNCTION", "Té de piquage sur colonne AEP immeuble", [cyl(CX, CY, 0.024, 1.07, 1.13)], "AEP", "Té Ø 32 / 20 (piquage)",
                 desc="Piquage sur la colonne de l'immeuble, accord du syndic et de la SODECI", label="Raccordement immeuble « à relever »")
    v0 = organe("IfcValve", "ISOLATING", "Robinet d'arrêt de piquage (dans la gaine, trappe de visite)", [tube([(0.24, CY, 1.10), (0.30, CY, 1.10)], 0.02)], "AEP",
                "Robinet d'arrêt 1/4 de tour DN 15", desc="Accessible par une trappe 0,20 x 0,20 dans le coffrage EU/EV 1", label="Organes AEP (vanne, compteur, clapet)")
    br = tuyau("AEP branchement Ø 20 - piquage -> coffret de comptage", [(0.181, CY, 1.10), (0.45, CY, 1.10), (0.45, 7.34, 1.10), (0.98, 7.34, 1.10)], 0.010, "AEP", "aep",
               "Multicouche 20 x 2", 15, 20, "Branchement eau froide sous fourreau, en applique sur le mur arrière", pente_txt="horizontal")
    cof = new("IfcBuildingElementProxy", "Coffret de comptage AEP (porte de visite)", styled([box(0.98, 7.27, 1.43, 7.408, 0.95, 1.30)], "iroko"),
              predefined_type="USERDEFINED", ObjectType="Coffret technique", lot=LOT_P, mat="iroko", rep_label="Organes AEP (vanne, compteur, clapet)",
              description="Coffret iroko en applique sur le mur arrière (vis courtes), compteur lisible à +1,10", psets=HYP)
    va = organe("IfcValve", "ISOLATING", "Vanne d'arrêt générale AEP (avant compteur)", [cyl(1.05, 7.34, 0.018, 1.08, 1.12)], "AEP", "Robinet d'arrêt 1/4 de tour DN 15")
    cpt = organe("IfcFlowMeter", "WATERMETER", "Compteur divisionnaire eau froide", [box(1.11, 7.30, 1.25, 7.38, 1.05, 1.15)], "AEP", "Compteur volumétrique DN 15 classe C, tête émettrice",
                 mat="equip", desc="Compteur divisionnaire de la bibliothèque sur le réseau de l'immeuble (relève syndic)", label="Organes AEP (vanne, compteur, clapet)")
    ca = organe("IfcValve", "CHECK", "Clapet antiretour EA", [cyl(1.30, 7.34, 0.016, 1.08, 1.12)], "AEP", "Clapet antipollution contrôlable EA DN 15")
    rp = organe("IfcValve", "PRESSUREREDUCING", "Réducteur de pression (si P > 3 bar)", [cyl(1.38, 7.34, 0.02, 1.07, 1.13)], "AEP", "Réducteur de pression DN 15 réglé à 3 bar",
                desc="À poser seulement si la pression mesurée dépasse 3 bar")
    te1 = organe("IfcPipeFitting", "JUNCTION", "Té de distribution AEP (WC / lave-mains)", [cyl(1.50, 7.34, 0.016, 1.07, 1.13)], "AEP", "Té égal 16")
    dwc = tuyau("AEP distribution Ø 16 - alimentation WC", [(1.50, 7.34, 1.10), (1.50, 7.37, 1.10), (1.50, 7.37, 0.32), (0.50, 7.37, 0.32), (0.50, 7.22, 0.32)], 0.008,
                "AEP", "aep", "Multicouche 16 x 2", 12, 16, "En applique sous cache, sous la canalisation EU du lave-mains", pente_txt="horizontal")
    vwc = organe("IfcValve", "ISOLATING", "Robinet d'arrêt WC", [cyl(0.50, 7.20, 0.016, 0.30, 0.34)], "AEP", "Robinet d'arrêt équerre 12 x 17", label="Organes AEP (vanne, compteur, clapet)")
    fwc = tuyau("Flexible d'alimentation du réservoir WC V4", [(0.50, 7.18, 0.32), (0.50, 7.18, 0.60), (0.40, 7.10, 0.60)], 0.006, "AEP", "aep", "Flexible inox 12 x 17", 10, 12,
                "Raccord sur le robinet flotteur du réservoir V4 conservé (alimentation latérale, à vérifier)", ptype="FLEXIBLESEGMENT", pente_txt="sans objet",
                raccord="WC V4 4350629 (conservé)")
    raccord_v4(fwc, WC, "Alimentation eau froide du réservoir")
    dlm = tuyau("AEP distribution Ø 16 - alimentation lave-mains", [(1.50, 7.34, 1.10), (2.84, 7.34, 1.10), (2.84, 7.10, 1.10), (2.84, 7.10, 0.74)], 0.008, "AEP", "aep",
                "Multicouche 16 x 2", 12, 16, "En applique sous cache iroko, descente le long du refend 4350608", pente_txt="horizontal")
    vlm = organe("IfcValve", "ISOLATING", "Robinet d'arrêt lave-mains", [cyl(2.84, 7.10, 0.016, 0.88, 0.92)], "AEP", "Robinet d'arrêt équerre 12 x 17")
    rob = organe("IfcValve", "FAUCET", "Robinet temporisé eau froide (lave-mains V4)", [cyl(2.82, 7.07, 0.018, 0.85, 0.99), box(2.81, 6.95, 2.83, 7.07, 0.97, 0.99)], "AEP",
                 "Robinet temporisé sur plan, eau froide seule", mat="equip_gris", desc="Posé sur le plan V4 conservé (perçage Ø 35 du plan, à relever)",
                 label="Organes AEP (vanne, compteur, clapet)")
    raccord_v4(rob, LM_PLAN, "Robinet temporisé posé sur le plan du lave-mains")
    relier(col, te0, v0, br, va, cpt, ca, rp, te1)
    relier(te1, dwc, vwc, fwc)
    relier(te1, dlm, vlm, rob)
    assign(SYS["AEP"], col, te0, v0, br, va, cpt, ca, rp, te1, dwc, vwc, fwc, dlm, vlm, rob)

    # EU (lave-mains) et EV (WC)
    sip = organe("IfcWasteTerminal", "WASTETRAP", "Siphon du lave-mains V4", [cyl(2.72, 6.87, 0.03, 0.52, 0.74)], "EU", "Siphon bouteille Ø 32 à culot démontable",
                 mat="pvc", desc="Sous la vasque V4 conservée (bonde existante)", label="Siphon / raccord sur appareil V4")
    raccord_v4(sip, LM_VASQUE, "Raccordement de la bonde de la vasque")
    eu = tuyau("EU lave-mains PVC Ø 40 -> descente EU/EV 1", [(2.72, 6.90, 0.52), (2.72, 7.31, 0.512), (0.40, 7.31, 0.4656)], 0.020, "EU", "pvc", "PVC M1 NF Me", 32, 40,
               "Antenne du lave-mains en applique le long du mur arrière, pente 2 % (DTU 60.11 : 1 à 3 %)", label="Évacuation EU / EV (PVC, pente)",
               raccord="Descente EU/EV 1 (à relever)")
    aav = organe("IfcValve", "ANTIVACUUM", "Clapet aérateur Ø 40 (antenne lave-mains)", [cyl(2.72, 7.31, 0.012, 0.53, 0.80), cyl(2.72, 7.31, 0.03, 0.80, 0.88)], "VP",
                 "Clapet d'admission d'air Ø 40 sous cache ventilé", mat="pvc", desc="Évite le désiphonnage de l'antenne (longueur 2,8 m) ; au-dessus du siphon, accessible")
    pq1 = organe("IfcPipeFitting", "JUNCTION", "Piquage Ø 40 sur descente EU/EV 1", [tube([(0.40, 7.31, 0.4656), (0.29, 7.28, 0.4656)], 0.022)], "EU", "Culotte / piquage à joint Ø 100 x 40",
                 mat="pvc", desc="Piquage sur la chute de l'immeuble : position, matériau et diamètre à relever", label="Raccordement immeuble « à relever »")
    relier(sip, eu, pq1, DESC1)
    relier(eu, aav)
    pwc = organe("IfcPipeFitting", "BEND", "Pipe WC Ø 100 (raccord cuvette V4)", [tube([(0.24, 6.92, 0.19), (0.24, 7.00, 0.1884)], 0.055)], "EV", "Pipe coudée Ø 100 à joint",
                 mat="pvc", desc="Sortie horizontale de la cuvette V4 conservée, à orienter vers la gaine", label="Siphon / raccord sur appareil V4")
    raccord_v4(pwc, WC, "Raccordement de la sortie de cuvette")
    ev = tuyau("EV WC PVC Ø 100 -> descente EU/EV 1", [(0.24, 7.00, 0.1884), (0.24, 7.19, 0.1846)], 0.050, "EV", "pvc", "PVC M1 NF Me", 100, 110,
               "Raccordement direct cuvette -> chute, pente 2 % (DTU 60.11 : 1 à 3 %)", label="Évacuation EU / EV (PVC, pente)", raccord="Descente EU/EV 1 (à relever)")
    pq2 = organe("IfcPipeFitting", "JUNCTION", "Culotte Ø 100 sur descente EU/EV 1 (WC)", [cyl(0.24, 7.26, 0.068, 0.12, 0.25)], "EV", "Culotte 45° Ø 100 à joint (reprise de chute)",
                 mat="pvc", desc="Raccordement sur la chute de l'immeuble : à relever, accord du syndic", label="Raccordement immeuble « à relever »")
    relier(pwc, ev, pq2, DESC1)
    assign(SYS["EU"], sip, eu, pq1, DESC1)
    assign(SYS["EV"], pwc, ev, pq2, DESC1)
    assign(SYS["VP"], aav)

    # condensats : refoulement par les mini-pompes vers la descente EU/EV 2 (siphon sec)
    k1 = tuyau("Condensats split 1 - refoulement mini-pompe -> collecteur", [(6.42, 5.25, 2.735), (6.42, 5.20, 2.735), (6.42, 5.20, Z_COND), (6.42, 4.36, Z_COND),
                                                                           (5.58, 4.36, Z_COND), (5.58, 1.22, Z_COND), (0.26, 1.22, Z_COND), (0.26, 4.18, Z_COND)],
               0.008, "Condensats", "condensat", "PVC cristal 10 x 14 sous fourreau Ø 16", 10, 16,
               "Refoulement en plénum (point haut +3,08), passage du galandage au-dessus de la retombée", pente_txt="refoulement (sans objet)",
               label="Condensats : refoulement mini-pompe -> EU")
    k2 = tuyau("Condensats split 2 - refoulement mini-pompe -> collecteur", [(0.15, 4.18, 2.615), (0.26, 4.18, 2.615), (0.26, 4.18, Z_COND)], 0.008, "Condensats", "condensat",
               "PVC cristal 10 x 14 sous fourreau Ø 16", 10, 16, "Refoulement court vers le collecteur", pente_txt="refoulement (sans objet)",
               label="Condensats : refoulement mini-pompe -> EU")
    tc = organe("IfcPipeFitting", "JUNCTION", "Té de jonction des condensats", [cyl(0.26, 4.18, 0.014, Z_COND - 0.02, Z_COND + 0.02)], "Condensats", "Té 16", mat="condensat")
    k3 = tuyau("Condensats collecteur -> siphon (descente EU/EV 2)", [(0.26, 4.18, Z_COND), (0.26, 6.015, Z_COND), (0.26, 6.015, 2.50)], 0.008, "Condensats", "condensat",
               "PVC cristal 10 x 14 sous fourreau Ø 16", 10, 16, "Traverse la cloison placo 4350621 par R8, entre dans le coffrage EU/EV 2", pente_txt="refoulement puis vertical",
               label="Condensats : refoulement mini-pompe -> EU")
    sk = organe("IfcWasteTerminal", "WASTETRAP", "Siphon sec à membrane des condensats", [cyl(0.26, 6.015, 0.018, 2.38, 2.50)], "Condensats", "Siphon sec Ø 32 (anti-odeur sans garde d'eau)",
                mat="pvc", desc="Dans le coffrage EU/EV 2, accessible par trappe 0,20 x 0,20 à +2,40", label="Siphon / raccord sur appareil V4")
    pq3 = organe("IfcPipeFitting", "JUNCTION", "Piquage Ø 32 condensats sur descente EU/EV 2", [tube([(0.26, 6.015, 2.385), (0.245, 6.04, 2.375)], 0.012)], "Condensats",
                 "Piquage à joint Ø 100 x 32", mat="pvc", desc="Sur la chute de l'immeuble : à relever, accord du syndic", label="Raccordement immeuble « à relever »")
    pu1, pu2 = by_name("Mini-pompe de relevage des condensats - split 1"), by_name("Mini-pompe de relevage des condensats - split 2")
    relier(pu1, k1, tc)
    relier(pu2, k2, tc)
    relier(tc, k3, sk, pq3, DESC2)
    assign(SYS["COND"], pu1, pu2, k1, k2, tc, k3, sk, pq3, DESC2)

    # ======================================================================================== fixations non traversantes
    def fixation(nom, items, ancrage_mm, support, desc):
        return new("IfcMechanicalFastener", nom, styled(items, "acier"), predefined_type="ANCHORBOLT", lot=LOT_F, mat="acier",
                   rep_label="Fixation non traversante (cheville ≤ 50 mm)", description=desc,
                   psets={"KDEMI_Fixation": {"Support": support, "Ancrage_mm": ancrage_mm, "Epaisseur_support_mm": 200 if "dalle" in support.lower() else 100,
                                             "Traversant": False, "Remarque": "Cheville non modélisée en volume dans le support ; profondeur portée ici"}, **HYP})
    ax, ay = ARBRE
    for k, a in enumerate(np.radians([0, 90, 180, 270])):
        x, y = ax + 1.20 * np.cos(a), ay + 1.20 * np.sin(a)
        fixation(f"Platine de stabilisation de la canopée sous dalle {k + 1}", [box(x - 0.05, y - 0.05, x + 0.05, y + 0.05, 3.282, Z_DALLE_SOUS - 0.0005)], 50, "Dalle haute (ép. 0,20 hyp.)",
                 "Platine acier 100 x 100 x 18 entre la canopée V4 (+3,28) et la dalle, 2 chevilles M8 ancrage 50 mm (non traversantes)")
    for k, a in enumerate(np.radians(np.arange(0, 360, 45))):
        x, y = ax + 1.41 * np.cos(a), ay + 1.41 * np.sin(a)
        if not (3.09 < x < 6.51 and 0.09 < y < 7.06):
            continue
        fixation(f"Suspente du bandeau de l'oculus {k + 1}", [cyl(x, y, 0.004, Z_FP_SOUS + 0.12, Z_DALLE_SOUS - 0.004), cyl(x, y, 0.025, Z_DALLE_SOUS - 0.004, Z_DALLE_SOUS - 0.0005)],
                 40, "Dalle haute (ép. 0,20 hyp.)", "Tige M6 + platine Ø 50, cheville M6 ancrage 40 mm (non traversante), réglage de niveau du bandeau iroko")
    for k, a in enumerate(np.radians([30, 150, 270])):
        x, y = ax + 0.40 * np.cos(a), ay + 0.40 * np.sin(a)
        fixation(f"Platine de pied de l'arbre à livres {k + 1}", [box(x - 0.04, y - 0.04, x + 0.04, y + 0.04, 0.004, 0.012)], 30, "Dallage existant (ép. 0,10 hyp., à relever)",
                 "Équerre acier sous le pied, 2 chevilles à frapper Ø 6 ancrage 30 mm dans le dallage (non traversantes)")
    hang = [(0.83, y) for y in (1.2, 2.4, 4.4)] + [(x, 0.44) for x in (1.8,)] + [(x, 1.10) for x in (3.9, 4.8)] + [(5.50, y) for y in (2.2, 3.4)] \
        + [(3.20, y) for y in (2.3, 3.5, 4.7, 5.9)]
    for k, (x, y) in enumerate(hang):
        fixation(f"Suspente de chemin de câbles {k + 1}", [cyl(x, y, 0.004, Z_CABLES + 0.02, Z_DALLE_SOUS - 0.004), box(x - 0.025, y - 0.025, x + 0.025, y + 0.025, Z_DALLE_SOUS - 0.004, Z_DALLE_SOUS - 0.0005)],
                 40, "Dalle haute (ép. 0,20 hyp.)", "Tige filetée M6 + platine, cheville M6 ancrage 40 mm (non traversante)")

    # ======================================================================================== seuil de vitrine (baie A)
    new("IfcPlate", "Seuil de vitrine - tôle pliée acier noir (baie A)",
        styled([box(0.62, 0.052, 1.68, 0.090, 0.4505, 0.4535), box(0.62, 0.0905, 1.68, 0.0935, 0.40, 0.4535)], "acier"), predefined_type="SHEET", lot="Devanture",
        mat="acier", rep_label="Seuil de vitrine acier noir (baie A)",
        description="Tôle pliée 30/10 posée sur l'appui existant derrière le dormant, retour collé sur la face intérieure (aucune fixation dans l'allège V4)", psets=HYP)
    return {"SYS": SYS, "CABLES": CABLES}
