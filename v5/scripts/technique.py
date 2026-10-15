"""Lots techniques de l'esquisse V5 (électricité, courants faibles, AEP/EU/EV) : données partagées.

Source unique pour construire_tech.py (IFC), dessins_tech.py (planches T01-T05) et verif_tech.py.
Repère et unités : ceux de commun.py (mètres, origine angle intérieur sud-ouest du gros œuvre V4).

Principes : aucun mur, poteau, ouverture ni cote V4 modifiés ; aucun percement dans les poteaux,
voiles ou la dalle haute. Appareillage en saillie (collé ou chevillé court), descentes en goulotte
ou dans les doublages existants, câbles en plénum (0,26 m). Le WC et le lave-mains V4 (local 07)
ne sont ni déplacés ni modifiés : on se raccorde sur leurs sorties, lues dans l'IFC quand c'est possible.
"""
import os
import numpy as np

from commun import V5, Z_FP_SOUS, Z_FP_DESSUS, Z_DALLE_SOUS, Z_CABLES, COFFRAGES, TABLEAU

V5_TECH = os.path.join(V5, "DECIMO_ESQ_V5_tech.ifc")
TECHNIQUE = os.path.join(V5, "technique")

GAP = 0.003                       # jeu entre un appareil en saillie et son support
Z_SOUS_FP = Z_FP_SOUS - 0.005     # arrêt des goulottes sous le faux-plafond (câble par découpe de dalle)
Z_CFA = Z_CABLES                  # chemin de câbles courants faibles, même niveau que le CFO
Z_PIQUAGE_AEP = 1.20
Z_AEP = 0.30
PENTE_EU = 0.02                   # 2 % (DTU 60.11 : 1 à 3 %)
PENTE_EV = 0.02

# --- faces d'appui (plan, coordonnée, sens de la normale) -----------------------------------------------
FACES = {
    "ouest": ("x", 0.09, +1, "mur mitoyen ouest 4350587 (porteur)"),
    "est": ("x", 6.495, -1, "mur est 4350588 (porteur), sur enduit terre"),
    "facade_coin": ("y", 0.09, +1, "façade 4350590 (porteur)"),
    "facade_salle": ("y", 0.105, +1, "façade 4350590 (porteur), sur enduit terre"),
    "refend_o": ("x", 2.91, -1, "refend 4350607 / 4350608 (porteur supposé), face ouest"),
    "reunion_o": ("x", 2.955, -1, "cloison pleine salle de réunion V4 (non porteuse), face ouest"),
    "reunion_e": ("x", 3.045, +1, "cloison pleine salle de réunion V4 (non porteuse), face est"),
    "placo21_n": ("y", 5.16, +1, "cloison placo V4 4350621 (non porteuse), face nord"),
    "rangement_o": ("x", 1.76, -1, "cloison rangement / dégagement V4 (non porteuse), face ouest"),
    "lambris": ("x", 3.11, +1, "lambris iroko V5 sur refend 4350608 (vide technique derrière)"),
    "nord_wc": ("y", 7.41, -1, "mur arrière 4350589 (porteur), WC"),
    "niche": ("y", 7.405, -1, "niche banquette V4 (doublage cintré)"),
}

TAILLES = {   # largeur le long du support, hauteur, saillie
    "PC": (0.08, 0.08, 0.045), "PC2": (0.15, 0.08, 0.045), "PCU": (0.15, 0.08, 0.045),
    "RJ2": (0.08, 0.08, 0.045), "INT": (0.08, 0.08, 0.04), "INT2": (0.08, 0.08, 0.04),
    "BP2": (0.08, 0.08, 0.04), "PLAT": (0.08, 0.24, 0.04), "BAES": (0.35, 0.13, 0.06),
}


def boite_murale(face, a, z, w, h, d, gap=GAP):
    """Boîte en saillie centrée sur (a, z) du support : (x0, y0, x1, y1, z0, z1)."""
    ax, c, s, _ = FACES[face]
    n0, n1 = (c + gap, c + gap + d) if s > 0 else (c - gap - d, c - gap)
    if ax == "x":
        return (n0, a - w / 2, n1, a + w / 2, z - h / 2, z + h / 2)
    return (a - w / 2, n0, a + w / 2, n1, z - h / 2, z + h / 2)


# --- appareillage -------------------------------------------------------------------------------------
# (code, type, support, abscisse le long du support, z axe, circuit, local, libellé)
APPAREILS = [
    # coin lecture / vitrine (02)
    ("INT-02", "INT2", "refend_o", 1.95, 1.10, "E4", "02", "Interrupteur double coin lecture (downlights | suspension)"),
    ("PC-02a", "PC", "refend_o", 2.18, 0.30, "P2", "02", "PC 16 A poste de lecture banquette"),
    ("PC-02b", "PC", "refend_o", 2.30, 0.30, "P4", "02", "PC 16 A ménage coin lecture"),
    # salle de lecture (01) : entrée, accueil, poste d'écoute, niche, fond
    ("BP-ENT", "BP2", "facade_salle", 5.00, 1.10, "E1", "01", "Boutons-poussoirs entrée (E1, E2 sur télérupteurs)"),
    ("PC-ENT", "PC", "facade_salle", 5.00, 0.30, "P4", "01", "PC 16 A ménage entrée"),
    ("PLAT-ACC", "PLAT", "est", 0.60, 1.10, "E1", "01", "Platine accueil 4 BP : E1, E2, E3 (variation oculus), E6 (forçage vitrine)"),
    ("PC-ACC1", "PC2", "est", 0.95, 0.30, "P1", "01", "PC 16 A double accueil (poste agent)"),
    ("RJ-ACC1", "RJ2", "est", 1.12, 0.30, "VDI", "01", "RJ45 double accueil (poste agent)"),
    ("PC-ACC2", "PC2", "est", 1.55, 0.30, "P1", "01", "PC 16 A double accueil (imprimante, caisse)"),
    ("RJ-ACC2", "RJ2", "est", 1.72, 0.30, "VDI", "01", "RJ45 double accueil (imprimante, caisse)"),
    ("PC-CONS", "PC2", "reunion_e", 3.15, 1.10, "P2", "01", "PC 16 A double poste d'écoute (console vinyles M01)"),
    ("RJ-CONS", "RJ2", "reunion_e", 3.32, 1.10, "VDI", "01", "RJ45 double poste de consultation (console M01)"),
    ("PC-NICHE", "PCU", "niche", 5.26, 0.62, "P2", "01", "PC 16 A + USB intégrée à la niche banquette (doublage)"),
    ("PC-FOND", "PC", "lambris", 6.60, 0.30, "P4", "01", "PC 16 A ménage fond de salle (alimentée derrière le lambris)"),
    # salle de réunion (03)
    ("INT-03", "INT", "reunion_o", 3.92, 1.10, "E5", "03", "Interrupteur salle de réunion (linéaire)"),
    ("PC-03a", "PC2", "reunion_o", 3.30, 0.30, "P3", "03", "PC 16 A double réunion (côté porte)"),
    ("RJ-03a", "RJ2", "reunion_o", 3.47, 0.30, "VDI", "03", "RJ45 double réunion (côté porte)"),
    ("PC-03b", "PC2", "ouest", 4.40, 0.30, "P3", "03", "PC 16 A double réunion (mur ouest)"),
    ("RJ-03b", "RJ2", "ouest", 4.57, 0.30, "VDI", "03", "RJ45 double réunion (mur ouest)"),
    ("PC-03c", "PC2", "ouest", 3.20, 0.30, "P3", "03", "PC 16 A double réunion (sous le tableau mural)"),
    ("PC-ECR", "PC", "ouest", 2.75, 1.10, "P3", "03", "PC 16 A écran / vidéoprojecteur"),
    ("RJ-ECR", "RJ2", "ouest", 2.62, 1.10, "VDI", "03", "RJ45 double écran / visioconférence"),
    # rangement, placard technique (04, 05), dégagement (06)
    ("INT-04", "INT", "rangement_o", 5.24, 1.10, "E5", "04", "Interrupteur rangement"),
    ("PC-BAIE", "PC2", "placo21_n", 0.95, 1.00, "P5", "05", "PC 16 A double baie informatique (onduleur)"),
    ("PC-06", "PC", "placo21_n", 2.60, 0.30, "P4", "06", "PC 16 A ménage dégagement"),
    # BAES (éclairage de sécurité, en amont des commandes du circuit d'éclairage du local)
    ("BAES-1", "BAES", "facade_salle", 4.10, 2.905, "E3", "01", "BAES d'évacuation au-dessus de l'issue principale (porte d'entrée)"),
    ("BAES-3", "BAES", "reunion_o", 4.55, 2.37, "E5", "03", "BAES d'évacuation, sortie de la salle de réunion"),
    ("BAES-4", "BAES", "refend_o", 5.72, 2.37, "E5", "06", "BAES d'évacuation au-dessus de la baie libre (dégagement)"),
]

# appareils en plafond : (code, type, x, y, circuit, local, libellé, orientation du drapeau)
PLAFOND = [
    ("BAES-2", "BAESP", 2.55, 1.35, "E4", "02", "BAES d'évacuation en drapeau, passage coin lecture > salle", "y"),
    ("BAES-5", "BAESP", 3.60, 4.50, "E2", "01", "BAES d'évacuation en drapeau, fond de salle > entrée", "x"),
    ("DET-06", "DET", 2.40, 5.45, "E5", "06", "Détecteur de présence plafond dégagement", None),
    ("DET-07", "DET", 1.90, 6.80, "E5", "07", "Détecteur de présence plafond WC (temporisé)", None),
    ("WIFI-01", "WIFI", 4.20, 2.75, "VDI", "01", "Borne Wi-Fi plafond (PoE, Wi-Fi 6)", None),
]


def boite_plafond(kind, x, y, ori=None):
    if kind == "BAESP":
        if ori == "x":
            return (x - 0.175, y - 0.03, x + 0.175, y + 0.03, 2.80, 2.93)
        return (x - 0.03, y - 0.175, x + 0.03, y + 0.175, 2.80, 2.93)
    r, h = {"DET": (0.05, 0.05), "WIFI": (0.10, 0.04)}[kind]
    return (x - r, y - r, x + r, y + r, Z_FP_SOUS - 0.002 - h, Z_FP_SOUS - 0.002)


# --- goulottes (descentes et plinthes) ---------------------------------------------------------------
# verticales : (code, support, abscisse, z0, z1) ; horizontales : (code, support, a0, a1, z0, z1)
GOULOTTES_V = [
    ("G-02", "refend_o", 2.40, 0.26, Z_SOUS_FP),
    ("G-ENT", "facade_salle", 5.08, 0.26, Z_SOUS_FP),
    ("G-ACC", "est", 1.30, 0.26, Z_SOUS_FP),
    ("G-ACC2", "est", 0.60, 1.225, Z_SOUS_FP),
    ("G-CONS", "reunion_e", 3.00, 1.06, Z_SOUS_FP),
    ("G-03a", "reunion_o", 3.65, 0.26, Z_SOUS_FP),
    ("G-03b", "ouest", 4.85, 0.10, Z_SOUS_FP),
    ("G-ECR", "ouest", 2.86, 1.06, Z_SOUS_FP),
    ("G-04", "rangement_o", 5.22, 1.145, Z_SOUS_FP),
    ("G-BAIE", "placo21_n", 1.105, 0.96, Z_SOUS_FP),
    ("G-06", "placo21_n", 2.75, 0.26, Z_SOUS_FP),
]
GOULOTTES_H = [
    ("G-03p", "ouest", 3.10, 4.89, 0.10, 0.18),   # plinthe sous le tableau mural V4
]
# traversée de la baie libre V4 (dégagement) sans percement : sous-face du linteau puis face dégagement
GOULOTTES_BOITES = [
    ("G-BL1", (2.885, 5.32, 3.13, 5.36, 2.078, 2.098), "Goulotte collée en sous-face du linteau de la baie libre V4 (h libre 2,08)"),
    ("G-BL2", (2.885, 5.32, 2.905, 5.36, 2.098, Z_SOUS_FP), "Goulotte côté dégagement, collée sur le refend 4350608"),
]


def goulottes():
    """[(code, boîte, description)] de toutes les goulottes, en mètres."""
    out = []
    for code, face, a, z0, z1 in GOULOTTES_V:
        b = boite_murale(face, a, (z0 + z1) / 2, 0.04, z1 - z0, 0.02)
        out.append((code, b, f"Goulotte 40 x 20 en saillie, {FACES[face][3]}"))
    for code, face, a0, a1, z0, z1 in GOULOTTES_H:
        b = boite_murale(face, (a0 + a1) / 2, (z0 + z1) / 2, a1 - a0, z1 - z0, 0.02)
        out.append((code, b, f"Goulotte plinthe 80 x 20, {FACES[face][3]}"))
    out += [(c, b, d) for c, b, d in GOULOTTES_BOITES]
    return out


# --- chemins de câbles -------------------------------------------------------------------------------
CFA = [(0.95, 4.95, Z_CFA), (0.95, 1.22, Z_CFA), (5.38, 1.22, Z_CFA)]
R6 = ("R6", "Fourreau éclairage WC (cloison placo 4350620)", (1.30, 6.24, 3.17), 0.12, 0.025)

# --- éclairage : 27 luminaires V5 répartis par circuit (noms IFC) --------------------------------------
DL = "Downlight encastré "
ECLAIRAGE = {
    "E1": [f"{DL}Salle de lecture {k}" for k in range(1, 9)],
    "E2": [f"{DL}Salle de lecture {k}" for k in range(9, 14)] + ["Suspension terre cuite - salon de lecture", "Liseuse niche banquette"],
    "E3": ["Anneau LED indirect de l'oculus", "Anneau LED sous la canopée de l'arbre à livres"],
    "E4": [f"{DL}Coin lecture / vitrine {k}" for k in (1, 2, 3)] + ["Suspension terre cuite - table coin lecture"],
    "E5": ["Linéaire suspendu - table de réunion", f"{DL}Rangement 1", f"{DL}Dégagement 1", f"{DL}WC 1"],
    "E6": ["Réglette LED de vitrine (baie A)", "Spot encastré sous marquise"],
}
COMMANDES = {   # circuit -> appareils de commande
    "E1": ["BP-ENT", "PLAT-ACC"], "E2": ["PLAT-ACC"], "E3": ["PLAT-ACC"], "E4": ["INT-02"],
    "E5": ["INT-03", "INT-04", "DET-06", "DET-07"], "E6": ["PLAT-ACC"],
}

# --- circuits (NF C 15-100) ----------------------------------------------------------------------------
# P_W : puissance installée hors éclairage (l'éclairage est lu dans l'IFC) ; ku : facteur d'utilisation
CIRCUITS = [
    dict(code="E1", nom="Éclairage salle de lecture, zone entrée / accueil", type="LIGHTING", id="ID1", In=16, S=1.5, ku=1.0,
         cmd="Télérupteur TL1 (BP entrée + platine accueil)"),
    dict(code="E2", nom="Éclairage salle de lecture, zone fond + BAES 5", type="LIGHTING", id="ID2", In=16, S=1.5, ku=1.0,
         cmd="Télérupteur TL2 (platine accueil) ; liseuse à interrupteur intégré"),
    dict(code="E3", nom="Éclairage oculus et canopée (graduable) + BAES 1", type="LIGHTING", id="ID2", In=16, S=1.5, ku=1.0,
         cmd="Variateur à BP en tableau (platine accueil)"),
    dict(code="E4", nom="Éclairage coin lecture + BAES 2", type="LIGHTING", id="ID1", In=16, S=1.5, ku=1.0,
         cmd="Interrupteur double local"),
    dict(code="E5", nom="Éclairage réunion, rangement, dégagement, WC + BAES 3, 4", type="LIGHTING", id="ID2", In=16, S=1.5, ku=1.0,
         cmd="Interrupteurs locaux, détecteurs dégagement et WC"),
    dict(code="E6", nom="Éclairage vitrine et seuil (spot sous marquise)", type="LIGHTING", id="ID1", In=10, S=1.5, ku=1.0,
         cmd="Horloge astronomique + contacteur, forçage platine accueil"),
    dict(code="P1", nom="PC accueil (poste agent, imprimante, caisse)", type="ELECTRICAL", id="ID2", In=20, S=2.5, P_W=800, ku=0.6),
    dict(code="P2", nom="PC postes de lecture et d'écoute", type="ELECTRICAL", id="ID1", In=20, S=2.5, P_W=350, ku=0.7),
    dict(code="P3", nom="PC salle de réunion (écran, portables)", type="ELECTRICAL", id="ID2", In=20, S=2.5, P_W=450, ku=0.7),
    dict(code="P4", nom="PC ménage (entrée, coin lecture, fond, dégagement)", type="ELECTRICAL", id="ID1", In=20, S=2.5, P_W=1200, ku=0.25),
    dict(code="P5", nom="PC baie informatique (onduleur, box, switch PoE)", type="ELECTRICAL", id="ID3", In=16, S=2.5, P_W=150, ku=1.0),
    dict(code="C1", nom="Split 1 salle de lecture + mini-pompe 1", type="AIRCONDITIONING", id="ID3", In=16, S=2.5, P_W=835, ku=1.0,
         membres=["Split mural 9 000 BTU/h - unité intérieure 1", "Mini-pompe de relevage des condensats - split 1"]),
    dict(code="C2", nom="Split 2 salle de réunion + mini-pompe 2", type="AIRCONDITIONING", id="ID3", In=16, S=2.5, P_W=835, ku=1.0,
         membres=["Split mural 9 000 BTU/h - unité intérieure 2", "Mini-pompe de relevage des condensats - split 2"]),
]
RESERVES = ["R1", "R2"]
DIFFERENTIELS = {"ID1": "Interrupteur différentiel 40 A 30 mA type A", "ID2": "Interrupteur différentiel 40 A 30 mA type A",
                 "ID3": "Interrupteur différentiel 40 A 30 mA type F (splits inverter, onduleur)"}
P_BAES_W = 2.0
KS = 0.9                       # coefficient de simultanéité global
COS_PHI = 0.9
RHO = 0.0225                   # Ω·mm²/m, cuivre (NF C 15-100, chute de tension)

# --- AEP / EU / EV ---------------------------------------------------------------------------------------
DESCENTE_WC = ((COFFRAGES["EU/EV 1 (WC)"][0] + COFFRAGES["EU/EV 1 (WC)"][2]) / 2, (COFFRAGES["EU/EV 1 (WC)"][1] + COFFRAGES["EU/EV 1 (WC)"][3]) / 2)
R_DESC = 0.055
COLONNE_AEP = (0.165, 7.34)      # hypothèse : colonne montante AEP de l'immeuble dans le coffrage 1, à relever


def lire_sanitaires(f):
    """Repère le WC et le lave-mains V4 du local 07 dans l'IFC (sans les modifier).

    Retourne (sanitaires, notes) ; sanitaires[nom] = dict(guid, bbox, ...) ; une entrée absente
    signifie que l'appareil n'a pas pu être lu (consigné dans notes, le raccordement est sauté).
    """
    import ifcopenshell.geom
    import ifcopenshell.util.element as ue
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    zone = (0.09, 6.36, 2.91, 7.41)
    out, notes = {}, []

    def bbox(p):
        try:
            rep = next(r for r in p.Representation.Representations if r.RepresentationIdentifier == "Body")
            g = ifcopenshell.geom.create_shape(s, p, rep).geometry
            v = np.array(g.verts).reshape(-1, 3)
            return v.min(0), v.max(0), v, np.array(g.faces).reshape(-1, 3)
        except Exception as e:  # noqa
            notes.append(f"{p.GlobalId} {p.Name} : géométrie illisible ({str(e)[:60]})")
            return None

    def dans_zone(b):
        c = (b[0] + b[1]) / 2
        return zone[0] <= c[0] <= zone[2] and zone[1] <= c[1] <= zone[3]

    wc = [p for p in f.by_type("IfcFlowTerminal") if p.is_a() in ("IfcFlowTerminal", "IfcSanitaryTerminal") and "wc" in (p.Name or "").lower()]
    wc = [(p, b) for p in wc for b in [bbox(p)] if b is not None and dans_zone(b)]
    if len(wc) == 1:
        p, (lo, hi, v, fc) = wc[0]
        low = v[v[:, 2] < 0.25]
        # sortie non portée par l'IFC : on la prend au dos du pied de cuvette, côté mur, h 0,18 (sortie horizontale)
        murs = {"ouest": lo[0] - 0.09, "est": 2.91 - hi[0], "nord": 7.41 - hi[1]}
        dos = min(murs, key=murs.get)
        cy = float((low[:, 1].min() + low[:, 1].max()) / 2) if len(low) else float((lo[1] + hi[1]) / 2)
        if dos == "ouest" and len(low):
            sortie = (float(low[:, 0].min()), cy, 0.18)
        else:
            sortie = None
            notes.append(f"WC {p.GlobalId} : dos côté {dos}, sortie non déduite ; raccordement EV à définir sur site")
        out["WC"] = dict(guid=p.GlobalId, nom=p.Name, lo=lo, hi=hi, dos=dos, sortie=sortie,
                         reservoir=(float(lo[0]), float(lo[1]), float(lo[0] + 0.18), float(hi[1])))
        notes.append(f"WC {p.GlobalId} lu (bbox {np.round(lo, 3).tolist()} - {np.round(hi, 3).tolist()}) ; "
                     "sortie EV non décrite dans l'IFC (représentation mappée sans port) : hypothèse sortie horizontale arrière h 0,18, à relever")
    else:
        notes.append(f"WC : {len(wc)} IfcFlowTerminal « WC » trouvé(s) dans le local 07, raccordement EV non dessiné")

    def est_lave_mains(p):
        txt = " ".join(str(v) for ps in ue.get_psets(p).values() for v in ps.values())
        return "lave-mains" in (txt + " " + (p.Name or "") + " " + (p.ObjectType or "")).lower()

    cand = list(f.by_type("IfcBuildingElementProxy")) + [p for p in f.by_type("IfcFlowTerminal") if p.is_a() in ("IfcFlowTerminal", "IfcSanitaryTerminal")]
    lm = [(p, b) for p in cand if est_lave_mains(p)
          for b in [bbox(p)] if b is not None and dans_zone(b)]
    if lm:
        plan = max(lm, key=lambda t: (t[1][1][0] - t[1][0][0]) * (t[1][1][1] - t[1][0][1]))
        vasque = min(lm, key=lambda t: (t[1][1][0] - t[1][0][0]) * (t[1][1][1] - t[1][0][1]))
        lo, hi = vasque[1][0], vasque[1][1]
        out["LM"] = dict(guid=[t[0].GlobalId for t in lm], plan=(plan[1][0], plan[1][1]), vasque=(lo, hi),
                         bonde=(float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2)), z_plan=float(plan[1][0][2]))
        notes.append(f"Lave-mains lu : {len(lm)} élément(s) V4 ({', '.join(t[0].Name for t in lm)}), plan à +{plan[1][0][2]:.2f} ; "
                     "bonde au centre de la vasque, siphon et robinetterie non modélisés en V4 (hypothèse)")
    else:
        notes.append("Lave-mains : aucun élément identifié dans le local 07, raccordements EU et AEP du lave-mains non dessinés")
    return out, notes


def reseaux_sanitaires(san):
    """Tracés AEP / EU / EV de raccordement (polylignes 3D) déduits des sanitaires lus."""
    xd, yd = DESCENTE_WC
    R = {}
    if "WC" in san and san["WC"]["sortie"]:
        sx, sy, sz = san["WC"]["sortie"]
        p0 = (sx + 0.002, sy, sz)
        p1 = (xd, sy, sz - PENTE_EV * (sx + 0.002 - xd))
        p2 = (xd, yd - R_DESC, p1[2] - PENTE_EV * (yd - R_DESC - sy))
        R["EV-WC"] = dict(pts=[p0, p1, p2], d_ext=0.110, sys="EV", nom="EV PVC Ø 100 - WC vers descente 1",
                          desc="Pipe de WC excentrée sur la sortie existante, coude 87°30, collecteur Ø 100 à 2 %, culotte sur la descente")
        tx, ty = san["WC"]["reservoir"][0] + 0.11, san["WC"]["hi"][1] + 0.010
        R["AEP-WC"] = dict(pts=[(0.95, COLONNE_AEP[1], Z_AEP), (0.45, COLONNE_AEP[1], Z_AEP), (0.45, ty, Z_AEP), (tx, ty, 0.45)],
                           d_ext=0.016, sys="AEP", nom="AEP multicouche 16 x 2 - réservoir du WC",
                           desc="Antenne vers le robinet d'arrêt du WC puis flexible inox sur l'alimentation existante du réservoir")
    if "LM" in san:
        bx, by = san["LM"]["bonde"]
        zp = san["LM"]["z_plan"]
        x_mur, y_mur = 2.865, 7.30
        z0 = zp - 0.17
        pts = [(bx, by, z0)]
        for q in [(x_mur, by), (x_mur, y_mur), (xd + np.sqrt(R_DESC ** 2 - (y_mur - yd) ** 2) + 0.006, y_mur)]:
            a = pts[-1]
            L = abs(q[0] - a[0]) + abs(q[1] - a[1])
            pts.append((q[0], q[1], a[2] - PENTE_EU * L))
        R["EU-LM"] = dict(pts=pts, d_ext=0.040, sys="EU", nom="EU PVC Ø 40 - lave-mains vers descente 1",
                          desc="Siphon sur la bonde existante, branchement Ø 40 à 2 % le long du refend puis du mur arrière, culotte sur la descente")
        R["AEP-LM"] = dict(pts=[(0.95, COLONNE_AEP[1], Z_AEP), (2.89, COLONNE_AEP[1], Z_AEP), (2.89, 6.75, Z_AEP), (2.89, 6.75, 0.62),
                                (bx + 0.03, 6.75, zp - 0.015)],
                           d_ext=0.016, sys="AEP", nom="AEP multicouche 16 x 2 - lave-mains",
                           desc="Antenne le long du mur arrière puis du refend, robinet d'arrêt sous le plan, flexible sur le robinet existant")
    R["AEP-COL"] = dict(pts=[(COLONNE_AEP[0] + 0.016, COLONNE_AEP[1], Z_PIQUAGE_AEP), (0.95, COLONNE_AEP[1], Z_PIQUAGE_AEP),
                             (0.95, COLONNE_AEP[1], Z_AEP)],
                        d_ext=0.020, sys="AEP", nom="AEP multicouche 20 x 2 - piquage sur la colonne de l'immeuble",
                        desc="Piquage sur la colonne montante (hypothèse), traversée du coffrage BA13 sous fourreau, nourrice compteur")
    return R


def pente(pts):
    """Pente moyenne (%) d'une polyligne : dénivelé total / longueur horizontale."""
    p = np.asarray(pts, float)
    Lh = np.sum(np.linalg.norm(np.diff(p[:, :2], axis=0), axis=1))
    return 100 * (p[0, 2] - p[-1, 2]) / Lh if Lh > 0 else 0.0, Lh
