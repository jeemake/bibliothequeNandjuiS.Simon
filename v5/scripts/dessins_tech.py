"""Planches A3 des lots techniques, tirées de v5/DECIMO_ESQ_V5_tech.ifc : v5/technique/T0x_*.png|pdf|svg.

T01 plan électricité courants forts     T02 plan courants faibles et éclairage (avec BAES)
T03 plan AEP / EU / EV                   T04 détails (plénum, WC / lave-mains, baie arrière, placard)
T05 schéma unifilaire et bilan de puissance
Même charte et même cartouche que les planches A01-A08 (lockup K&Démi v3 A).
Usage : python3 v5/scripts/dessins_tech.py [T01 T02 ...]
"""
import os, sys, logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon as MPoly, Wedge, Arc, FancyBboxPatch
from matplotlib.lines import Line2D
import shapely
from shapely.geometry import box as sbox, Point, LineString
from shapely.ops import unary_union
import ifcopenshell
import ifcopenshell.util.element as ue
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import Z_FP_SOUS, Z_FP_DESSUS, Z_DALLE_SOUS, Z_DALLE_DESSUS, COFFRAGES, POCHE, INDIGO  # noqa
import dessins as DS  # noqa
from dessins import Planche, cote, niveau, bulle, label, echelle_graphique, mm, fr, W, H  # noqa
from charte_kdemi import FP_MEDIUM, FP_TITRE, ENCRE, TAUPE, TERRE_CUITE, IROKO, SABLE, SABLE_CLAIR, OLIVE  # noqa
from scene import charger, role  # noqa
import dessin2d as D  # noqa
import technique as T  # noqa
from vegetation import est_feuillage, est_vegetal, touffe  # noqa

logging.disable(logging.WARNING)
plt.rcParams["font.family"] = list(plt.rcParams["font.family"]) + ["DejaVu Sans"]   # repli pour Δ, φ, ρ, Ω, ≈ absents de Jost
# --- code couleur des lots (identique sur T01 à T05 ; fond de plan en gris clair) ---------------------------------
CFO = "#D62828"        # courants forts : prises, TD, chemins CFO, goulottes
CFA_C = "#1F5FBF"      # courants faibles : RJ45, Wi-Fi, baie, chemin CFA
ECL_C = "#E08A00"      # éclairage : luminaires, commandes, détecteurs
BAES_C = "#1E9E4A"     # sécurité : BAES
AEP_C = "#00A3C4"      # AEP eau froide
EU_C = EV_C = "#8B5A2B"  # EU (tireté) / EV (continu)
COND_C = "#7B3FA0"     # climatisation : splits, mini-pompes, liaisons, condensats
RES_C = "#C2185B"      # réservations et fourreaux
LS_EU = (0, (4, 1.6))  # EU en tireté (lisible en noir et blanc)
CIRC_C = {k: ECL_C for k in ("E1", "E2", "E3", "E4", "E5", "E6")}
FOND_TRAIT = "#C8C8C8"   # fond de plan : traits fins
FOND_POCHE = "#BDBDBD"   # fond de plan : porteurs coupés
FOND_CLOISON = "#DCDCDC" # fond de plan : cloisons coupées
FOND_TXT = "#9E9E9E"     # fond de plan : noms de locaux, contexte
SANIT = "#8C8C8C"        # WC et lave-mains V4 (existants, repères des raccordements)
LWT = D.LW[2] * 1.6      # symboles techniques : plus épais que le fond de plan
FC_CFO, FC_CFA = "#F9D4D4", "#D6E2F5"   # remplissages clairs des chemins de câbles


def lot_col(rep):
    """Couleur d'un circuit du schéma unifilaire selon son lot."""
    return ECL_C if rep.startswith("E") else COND_C if rep.startswith("C") else CFA_C if rep == "VDI" else CFO
PHASE = "ESQ V5 — lots techniques sur existant V4"


class PlancheTech(Planche):
    def __init__(self, num, titre, ligne, px=290):
        super().__init__(num, titre, ligne, px=px, maquette=T.V5_TECH, dossier=T.TECHNIQUE)

    def cartouche(self, echelle, phase=PHASE):
        super().cartouche(echelle, phase)

    def intertitre(self, s):
        # intertitres en gris : la couleur est réservée aux lots techniques
        self.T(self.px + 8, self.y, s.upper(), 7.2, ENCRE, fontproperties=FP_MEDIUM)
        self.y += 5.5


# --- données lues dans l'IFC technique ------------------------------------------------------------------
IFC = ifcopenshell.open(T.V5_TECH)
PS = {}
for p in IFC.by_type("IfcProduct"):
    PS[p.GlobalId] = ue.get_psets(p).get("KDEMI_Esquisse", {})
CIRCUITS, MEMBRE = {}, {}
for rel in IFC.by_type("IfcRelAssignsToGroup"):
    g = rel.RelatingGroup
    if g.is_a("IfcDistributionCircuit"):
        c = ue.get_psets(g)["KDEMI_Circuit"]
        CIRCUITS[c["Repere"]] = dict(c, nom=g.Name, membres=[o.GlobalId for o in rel.RelatedObjects])
        for o in rel.RelatedObjects:
            MEMBRE.setdefault(o.GlobalId, []).append(c["Repere"])
ORDRE = [c["code"] for c in T.CIRCUITS]
TYPES_LUM = {}
for p in IFC.by_type("IfcLightFixture"):
    t = ue.get_type(p)
    TYPES_LUM[p.GlobalId] = (ue.get_psets(t).get("Pset_LightFixtureTypeCommon", {}).get("TotalWattage", 0.0) if t else 0.0,
                             ue.get_predefined_type(p))
SC = None


def scene():
    global SC
    if SC is None:
        SC = charger(T.V5_TECH)
    return SC


def code(e):
    return PS.get(e["guid"], {}).get("Code")


def bbe(e):
    return e["verts"].min(0), e["verts"].max(0)


def ctr(e):
    lo, hi = bbe(e)
    return (lo + hi) / 2


def silh(e, vue):
    return D.contour_complet(e, vue)


TECHNIQUE_ROLES = ("technique", "luminaire")
MASQUE_FOND = ("logements", "fenetre_logt", "sol_ext", "trottoir", "arbre", "voisin")


def fond_de_plan(ax, sc, z=1.0, xlim=None, ylim=None, mobilier=True, tracer_wc=True):
    """Plan coupé à +z, architecture estompée : porteurs pochés noir, cloisons grises, le reste en trait fin."""
    v = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0), coupe=((0, 0, 1), z + 0.0003))
    win = sbox(xlim[0], ylim[0], xlim[1], ylim[1]) if xlim else None

    def garder(e, r):
        if r in MASQUE_FOND or r in TECHNIQUE_ROLES or e["classe"] == "IfcSlab" or r == "plafond":
            return False
        if not mobilier and r == "mobilier" and not (tracer_wc and e["tag"] in ("4350629", "4350630", "4350631")):
            return False
        if win is not None:
            lo, hi = bbe(e)
            if hi[0] < xlim[0] or lo[0] > xlim[1] or hi[1] < ylim[0] or lo[1] > ylim[1]:
                return False
        return True
    R = D.calculer(sc, v, garder)
    zz = 10
    for r in R:
        sanit = r["e"]["tag"] in ("4350629", "4350630", "4350631")
        for it in r["items"]:
            if est_feuillage(it):
                touffe(ax, it["g"], zz, "plan", col=FOND_TRAIT, lw=D.LW[1] * 0.8)
                zz += 0.001
                continue
            fc = "#FAFAFA" if r["role"] == "sol" else "white"
            D.patch(ax, it["g"], fc=fc, ec=FOND_TRAIT if not sanit else SANIT, lw=D.LW[1] * (0.5 if not sanit else 0.9), z=zz)
            zz += 0.001
        if r["tout"] is not None and r["role"] not in ("sol",) and sanit:
            D.patch(ax, r["tout"], fc="none", ec=SANIT, lw=D.LW[1] * 1.2, z=zz)
    for r in R:
        g = r["coupe"]
        if g is None:
            continue
        if est_vegetal(r["e"]):
            for c, k in r.get("coupes", []):
                if not est_feuillage(dict(rgba=k)):
                    D.patch(ax, c, fc="#F2F2F2", ec=FOND_TRAIT, lw=D.LW[1] * 0.5, z=57)
            continue
        if r["role"] == "structure":
            D.patch(ax, g, fc=FOND_POCHE, ec=FOND_POCHE, lw=D.LW[1], z=60)
        elif r["role"] == "cloison":
            D.patch(ax, g, fc=FOND_CLOISON, ec=FOND_TRAIT, lw=D.LW[1] * 0.6, z=59)
        elif r["role"] == "vitrage":
            D.patch(ax, g, fc="#F4F7F8", ec=FOND_TRAIT, lw=D.LW[1] * 0.6, z=58)
        else:
            D.patch(ax, g, fc="#F2F2F2", ec=FOND_TRAIT, lw=D.LW[1] * 0.5, z=57)
    return v, R


def etiquettes_locaux(ax, pos, size=5.2, col=FOND_TXT):
    noms = {"01": "Salle de lecture", "02": "Coin lecture", "03": "Réunion", "04": "Rangement", "05": "Placard", "06": "Dégag.", "07": "WC"}
    for k, (x, y) in pos.items():
        label(ax, x, y, f"{k}  {noms[k]}", size=size, col=col, z=300, fontproperties=FP_MEDIUM)


# --- symboles (positions en m, tailles en mm papier) ----------------------------------------------------
def _n(face):
    ax_, c, s, _ = T.FACES[face]
    return (np.array([s, 0.0]) if ax_ == "x" else np.array([0.0, s])), c


def pied(face, a):
    n, c = _n(face)
    return (np.array([c, a]) if T.FACES[face][0] == "x" else np.array([a, c])), n


def sym_prise(ax, face, a, kind, col=CFO, z=420, txt=None):
    p, n = pied(face, a)
    t = np.array([-n[1], n[0]])
    r = mm(ax, 1.6)
    k = 2 if kind in ("PC2",) else 1
    offs = [0.0] if k == 1 else [-1.35 * r, 1.35 * r]
    for o in offs:
        c = p + n * mm(ax, 0.9) + t * o
        ang = np.degrees(np.arctan2(n[1], n[0]))
        ax.add_patch(Wedge(c, r, ang - 90, ang + 90, fc="white", ec=col, lw=LWT, zorder=z))
        ax.plot(*np.array([p + t * o, c]).T, color=col, lw=LWT, zorder=z)
        e = c + n * r
        ax.plot(*np.array([e - t * r * 0.7, e + t * r * 0.7]).T, color=col, lw=LWT, zorder=z)
    if kind == "PCU":
        label(ax, *(p + n * mm(ax, 4.9)), "USB", size=3.6, col=col, z=z)
    if txt:
        label(ax, *(p + n * mm(ax, 5.4) + t * (mm(ax, 3.2) if k == 2 else 0)), txt, size=4.4, col=col, z=z, fontproperties=FP_MEDIUM)


def sym_rj(ax, face, a, col=CFA_C, z=420, txt=None):
    p, n = pied(face, a)
    t = np.array([-n[1], n[0]])
    s = mm(ax, 1.8)
    tri = [p + t * s, p - t * s, p + n * s * 1.7]
    ax.add_patch(MPoly(tri, closed=True, fc=col, ec=col, lw=D.LW[1], zorder=z))
    if txt:
        label(ax, *(p + n * mm(ax, 5.2)), txt, size=4.0, col=col, z=z)


def sym_cmd(ax, face, a, kind, col, z=430, txt=None):
    p, n = pied(face, a)
    t = np.array([-n[1], n[0]])
    r = mm(ax, 1.25)
    c = p + n * mm(ax, 2.6)
    if kind == "PLAT":
        ax.add_patch(Rectangle(c - np.array([r, r]) * 1.3, 2.6 * r, 2.6 * r, fc="white", ec=col, lw=LWT, zorder=z))
        for dx in (-0.5, 0.5):
            for dy in (-0.5, 0.5):
                ax.add_patch(Circle(c + np.array([dx, dy]) * r * 1.2, r * 0.28, fc=col, ec="none", zorder=z + 1))
    else:
        ax.add_patch(Circle(c, r, fc="white", ec=col, lw=LWT, zorder=z))
        if kind == "BP2":
            ax.add_patch(Circle(c, r * 0.35, fc=col, ec="none", zorder=z + 1))
        else:
            d = (n + t) / np.sqrt(2)
            e = c + d * r * 2.4
            ax.plot(*np.array([c + d * r, e]).T, color=col, lw=LWT, zorder=z)
            for k in range(2 if kind == "INT2" else 1):
                q = e - d * r * 0.55 * k
                ax.plot(*np.array([q, q + (t - n) / np.sqrt(2) * r * 0.8]).T, color=col, lw=LWT, zorder=z)
    ax.plot(*np.array([p, c - n * r]).T, color=col, lw=D.LW[1], zorder=z)
    if txt:
        label(ax, *(c + n * mm(ax, 3.8)), txt, size=4.4, col=col, z=z, fontproperties=FP_MEDIUM)


def sym_det(ax, x, y, col, z=430):
    r = mm(ax, 1.7)
    ax.add_patch(Circle((x, y), r, fc="white", ec=col, lw=LWT, zorder=z))
    label(ax, x, y, "D", size=4.4, col=col, z=z + 1, fontproperties=FP_MEDIUM)


def sym_wifi(ax, x, y, col=CFA_C, z=430):
    r = mm(ax, 1.3)
    ax.add_patch(Circle((x, y), r * 0.45, fc=col, ec="none", zorder=z))
    for k in (1.3, 2.1):
        ax.add_patch(Arc((x, y), 2 * k * r, 2 * k * r, theta1=40, theta2=140, color=col, lw=LWT, zorder=z))
        ax.add_patch(Arc((x, y), 2 * k * r, 2 * k * r, theta1=220, theta2=320, color=col, lw=LWT, zorder=z))


def sym_baes(ax, x, y, ang=0.0, z=440):
    w, h = mm(ax, 5.0), mm(ax, 2.4)
    c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    R_ = np.array([[c, -s], [s, c]])
    pts = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]) @ R_.T + [x, y]
    ax.add_patch(MPoly(pts, closed=True, fc=BAES_C, ec=BAES_C, lw=D.LW[1], zorder=z))
    tri = np.array([[w * 0.05, -h * 0.32], [w * 0.05, h * 0.32], [w * 0.38, 0]]) @ R_.T + [x, y]
    ax.add_patch(MPoly(tri, closed=True, fc="white", ec="none", zorder=z + 1))
    ax.add_patch(Circle(np.array([-w * 0.22, 0]) @ R_.T + [x, y], h * 0.22, fc="white", ec="none", zorder=z + 1))


def type_lum(n):
    return ("anneau" if "Anneau" in n else "lineaire" if ("Linéaire" in n or "Réglette" in n) else "suspension" if "Suspension" in n
            else "downlight" if "Downlight" in n else "spot")


def sym_lum(ax, e, col, z=420):
    lo, hi = bbe(e)
    c = (lo + hi) / 2
    n = e["nom"]
    if "Anneau" in n:
        r = (hi[0] - lo[0]) / 2
        ax.add_patch(Circle(c[:2], r, fc="none", ec=col, lw=LWT * 1.4, ls=(0, (3, 1.4)), zorder=z))
        return c[:2] + np.array([r * 0.71, -r * 0.71])
    if "Linéaire" in n or "Réglette" in n:
        ax.add_patch(Rectangle((lo[0], lo[1] - mm(ax, 0.5)), hi[0] - lo[0], max(hi[1] - lo[1], mm(ax, 1.0)),
                               fc=col, ec=col, lw=D.LW[1], zorder=z))
        return c[:2]
    r = mm(ax, 2.2 if "Suspension" in n else 1.6 if "Downlight" in n else 1.3)
    ax.add_patch(Circle(c[:2], r, fc="white", ec=col, lw=LWT, zorder=z))
    d = r * 0.7071
    ax.plot([c[0] - d, c[0] + d], [c[1] - d, c[1] + d], color=col, lw=LWT, zorder=z)
    ax.plot([c[0] - d, c[0] + d], [c[1] + d, c[1] - d], color=col, lw=LWT, zorder=z)
    if "Suspension" in n:
        ax.add_patch(Circle(c[:2], r * 1.35, fc="none", ec=col, lw=D.LW[1], zorder=z))
    return c[:2]


def goulotte_sym(ax, e, col=CFO, z=415, txt=None):
    lo, hi = bbe(e)
    c = (lo + hi) / 2
    s = mm(ax, 1.5)
    ax.add_patch(Rectangle((c[0] - s / 2, c[1] - s / 2), s, s, fc=col, ec=col, lw=D.LW[1] * 0.6, zorder=z))
    if txt:
        label(ax, c[0], c[1] - mm(ax, 2.0), txt, size=3.0, col=col, z=z)


def chemin(ax, e, vue, col, z=150, ls="-", fc="none", lw=None):
    g = silh(e, vue)
    D.patch(ax, g, fc=fc, ec=col, lw=lw or D.LW[2], z=z, ls=ls)
    return g


def note(a_, txt, xy, xyt, col=ENCRE, ha="left", size=4.6, z=470):
    """Étiquette reliée par un filet à son objet."""
    a_.annotate(txt, xy=xy, xytext=xyt, fontsize=size, color=col, ha=ha, va="center", zorder=z, fontproperties=FP_MEDIUM,
                arrowprops=dict(arrowstyle="-", color=col, lw=D.LW[1], shrinkA=1, shrinkB=0))
    a_.add_patch(Circle(xy, mm(a_, 0.35), fc=col, ec="none", zorder=z))


def mst(points):
    """Arbre couvrant minimal (Prim) d'une liste de points 2D -> liste d'arêtes (i, j)."""
    n = len(points)
    if n < 2:
        return []
    P = np.asarray(points)
    dans, aretes = {0}, []
    while len(dans) < n:
        best = None
        for i in dans:
            for j in range(n):
                if j in dans:
                    continue
                d = np.linalg.norm(P[i] - P[j])
                if best is None or d < best[0]:
                    best = (d, i, j)
        aretes.append(best[1:])
        dans.add(best[2])
    return aretes


def legende(p, items, titre="Légende des symboles", col_w=None, n_col=1):
    """Légende : une petite vignette dessinée par une fonction f(ax) + un libellé."""
    p.intertitre(titre)
    w = col_w or (W - 18 - p.px) / n_col
    for k, (f, txt) in enumerate(items):
        col = k % n_col
        x = p.px + 8 + col * w
        ax = p.fig.add_axes([x / W, 1 - (p.y + 3.2) / H, 8 / W, 3.2 / H])
        ax.set_xlim(0, 8); ax.set_ylim(0, 3.2); ax.set_aspect("equal"); ax.axis("off")
        ax.ech = 1000
        f(ax)
        p.T(x + 10, p.y + 0.3, txt, 5.5)
        if col == n_col - 1 or k == len(items) - 1:
            p.y += 3.75


def legende_lots(p, blocs, titre="Légende technique"):
    """Légende pour le technicien, toujours au même endroit (sous l'en-tête du panneau) :
    un bloc par lot = pastille de couleur + nom du lot, puis symbole à taille réelle, libellé et quantité relevée sur la planche."""
    p.y = 57.0
    p.T(p.px + 8, p.y, titre.upper(), 7.4, ENCRE, fontproperties=FP_MEDIUM)
    p.T(W - 12, p.y + 0.2, "QTÉ", 6.4, TAUPE, ha="right", fontproperties=FP_MEDIUM)
    p.y += 5.2
    for nom, col, items in blocs:
        p.fig.add_artist(Rectangle(((p.px + 8) / W, 1 - (p.y + 3.4) / H), 7.0 / W, 3.4 / H, transform=p.fig.transFigure, fc=col, ec="none"))
        p.T(p.px + 17.5, p.y + 0.15, nom.upper(), 7.6, col, fontproperties=FP_MEDIUM)
        p.y += 5.0
        for f, txt, q in items:
            x = p.px + 8
            ax = p.fig.add_axes([x / W, 1 - (p.y + 4.4) / H, 11 / W, 4.4 / H])
            ax.set_xlim(-1.5, 9.5); ax.set_ylim(-0.6, 3.8); ax.set_aspect("equal"); ax.axis("off")
            ax.ech = 1000
            f(ax)
            p.T(x + 14.5, p.y + 0.55, txt, 8.0, ENCRE)
            if q is not None:
                p.T(W - 12, p.y + 0.55, str(q), 8.0, col, ha="right", fontproperties=FP_MEDIUM)
            p.y += 4.9
        p.y += 1.6
    p.filet(p.y + 0.5, FOND_TRAIT, 0.4)
    p.y += 4.0


def mini_ax(ax):
    """Petit axe de légende : 1 unité = 1 mm papier (mm(ax, v) = v)."""
    return ax


def vig_prise(kind, col=CFO):
    def f(ax):
        T.FACES["_leg"] = ("y", 0.6, +1, "")
        sym_prise(ax, "_leg", 4.0, kind, col=col)
        T.FACES.pop("_leg")
    return f


def vig_rj(ax):
    T.FACES["_leg"] = ("y", 0.6, +1, "")
    sym_rj(ax, "_leg", 4.0)
    T.FACES.pop("_leg")


def vig_cmd(kind, col=ENCRE):
    def f(ax):
        T.FACES["_leg"] = ("y", 0.2, +1, "")
        sym_cmd(ax, "_leg", 4.0, kind, col)
        T.FACES.pop("_leg")
    return f


def vig_trait(col, ls="-", lw=None, double=False):
    def f(ax):
        if double:
            ax.add_patch(Rectangle((0.3, 1.0), 7.4, 1.2, fc="none", ec=col, lw=lw or D.LW[2], ls=ls))
        else:
            ax.plot([0.3, 7.7], [1.6, 1.6], color=col, lw=lw or D.LW[2], ls=ls, solid_capstyle="butt")
    return f


def vig_rect(fc, ec=ENCRE, hatch=None, ls="-", lw=None):
    def f(ax):
        ax.add_patch(Rectangle((0.5, 0.5), 7.0, 2.2, fc=fc, ec=ec, lw=lw or D.LW[1], hatch=hatch, ls=ls))
    return f


def vig(fn, *a, **kw):
    def f(ax):
        fn(ax, *a, **kw)
    return f


# =========================================================================================
XL, YL = (-0.40, 7.05), (-0.75, 7.85)
LOCAUX_POS = {"01": (4.15, 2.55), "02": (1.20, 2.25), "03": (2.15, 4.85), "04": (1.40, 6.14), "06": (2.40, 6.02), "07": (2.05, 7.20)}


def plan_base(p, sc, ech=30, x0=6, y0=7):
    ax = p.axes(x0, y0, XL, YL, ech)
    v, R = fond_de_plan(ax, sc, 1.0, XL, YL)
    ax.add_patch(Rectangle((XL[0], YL[0]), XL[1] - XL[0], -0.09 - YL[0], fc="#F6F6F6", ec="none", zorder=1))
    label(ax, 3.3, -0.62, "TERRASSE (PERGOLA V4)  ·  RUE", size=4.8, col=FOND_TXT, z=300)
    label(ax, -0.25, 3.6, "MITOYEN", size=4.6, col=FOND_TXT, rotation=90, z=300)
    label(ax, 1.9, 7.74, "COURETTE (copropriété)", size=4.6, col=FOND_TXT, z=300)
    return ax, v


def pos_appareil(code_):
    for c_, kind, face, a, z_, circ, loc, lib in T.APPAREILS:
        if c_ == code_:
            p, n = pied(face, a)
            return p + n * 0.09, kind
    for c_, kind, x, y, circ, loc, lib, ori in T.PLAFOND:
        if c_ == code_:
            return np.array([x, y]), kind
    raise KeyError(code_)


def lien(ax, a, b, col, rad=0.18, z=380, ls=(0, (2.5, 1.5)), lw=None):
    ax.annotate("", xy=tuple(b), xytext=tuple(a), zorder=z,
                arrowprops=dict(arrowstyle="-", color=col, lw=lw or D.LW[1] * 1.3, ls=ls, connectionstyle=f"arc3,rad={rad}",
                                shrinkA=0, shrinkB=0))


def T02():
    sc = scene()
    p = PlancheTech("T02", "Courants faibles, éclairage et sécurité", "Plan de coupe +1,00, plafond superposé  ·  Échelle 1/30 (A3)  ·  27 luminaires 2700 K de la V5")
    ax, v = plan_base(p, sc)
    vtop = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0))
    par_nom = {e["nom"]: e for e in sc}
    ancre, n = {}, Counter()
    for circ, noms in T.ECLAIRAGE.items():
        for nm in noms:
            ancre[nm] = sym_lum(ax, par_nom[nm], ECL_C)
            n[type_lum(nm)] += 1
    # liaisons de commande : arbre entre luminaires d'un même circuit (même local), puis commande -> luminaire le plus proche
    locaux = {"E5": [["Linéaire suspendu - table de réunion"], [f"{T.DL}Rangement 1"], [f"{T.DL}Dégagement 1"], [f"{T.DL}WC 1"]],
              "E6": [["Réglette LED de vitrine (baie A)"], ["Spot encastré sous marquise"]]}
    for circ, noms in T.ECLAIRAGE.items():
        for grp in locaux.get(circ, [noms]):
            P_ = [ancre[q] for q in grp]
            for i, j in mst(P_):
                lien(ax, P_[i], P_[j], ECL_C, rad=0.12)
                n["lien"] += 1
    # repère de circuit sur chaque groupe de luminaires (renvoi au schéma unifilaire T05)
    TAG = {"E1": (0.16, -0.17), "E2": (0.16, 0.17), "E3": (0.20, 0.20), "E4": (0.17, -0.17), "E5": (0.15, 0.15), "E6": (-0.18, 0.15)}
    for circ, noms in T.ECLAIRAGE.items():
        for grp in locaux.get(circ, [noms]):
            q = ancre[grp[0]] + np.array(TAG[circ])
            label(ax, *q, circ, size=4.6, col="white", z=460, fontproperties=FP_MEDIUM,
                  bbox=dict(boxstyle="round,pad=0.18", fc=ECL_C, ec="none"))
    cmd_lum = {"BP-ENT": ["E1"], "PLAT-ACC": ["E1", "E2", "E3", "E6"], "INT-02": ["E4"], "INT-03": ["Linéaire suspendu - table de réunion"],
               "INT-04": [f"{T.DL}Rangement 1"], "DET-06": [f"{T.DL}Dégagement 1"], "DET-07": [f"{T.DL}WC 1"]}
    for cmd, cibles in cmd_lum.items():
        a, kind = pos_appareil(cmd)
        for cible in cibles:
            noms = T.ECLAIRAGE[cible] if cible in T.ECLAIRAGE else [cible]
            circ = cible if cible in T.ECLAIRAGE else next(k for k, v_ in T.ECLAIRAGE.items() if cible in v_)
            b = min((ancre[n] for n in noms), key=lambda q: np.linalg.norm(q - a))
            lien(ax, a, b, ECL_C, rad=-0.25 if cmd == "PLAT-ACC" else 0.2, lw=D.LW[2])
            n["lien"] += 1
    sp = ancre["Spot encastré sous marquise"]
    label(ax, sp[0] + 0.55, sp[1] - 0.02, "alimentation à travers la façade :\nà valider (point ouvert)", size=3.8, col=ECL_C, z=450)
    for c_, kind, face, a, z_, circ, loc, lib in T.APPAREILS:
        if kind in ("INT", "INT2", "BP2", "PLAT"):
            sym_cmd(ax, face, a, kind, ECL_C, txt=circ)
            n["INT" if kind in ("INT", "INT2") else kind] += 1
        elif kind == "RJ2":
            sym_rj(ax, face, a, txt="RJ")
            n["RJ2"] += 1
        elif kind == "BAES":
            n["BAES"] += 1
            q, nv = pied(face, a)
            q = q + nv * mm(ax, 2.0)
            sym_baes(ax, *q, ang=np.degrees(np.arctan2(nv[1], nv[0])) + 90)
            label(ax, *(q + nv * mm(ax, 4.0)), f"{c_.replace('BAES-', 'B')} · {circ}", size=4.0, col=BAES_C, z=450, fontproperties=FP_MEDIUM)
    for c_, kind, x, y, circ, loc, lib, ori in T.PLAFOND:
        if kind == "DET":
            sym_det(ax, x, y, ECL_C)
            n["DET"] += 1
        elif kind == "WIFI":
            sym_wifi(ax, x, y)
            n["WIFI"] += 1
            label(ax, x, y - mm(ax, 4.2), "Wi-Fi PoE", size=4.2, col=CFA_C, z=450, fontproperties=FP_MEDIUM)
        elif kind == "BAESP":
            n["BAES"] += 1
            sym_baes(ax, x, y, ang=90 if ori == "y" else 0)
            label(ax, x + (0.30 if ori == "y" else 0), y + (0.0 if ori == "y" else 0.19), f"{c_.replace('BAES-', 'B')} · {circ}", size=4.0,
                  col=BAES_C, z=450, fontproperties=FP_MEDIUM)
    for e in sc:
        if e["classe"] == "IfcCableCarrierSegment" and "courants faibles" in e["nom"]:
            g = chemin(ax, e, vtop, CFA_C, z=150, ls=(0, (5, 1.5)), fc=FC_CFA, lw=LWT)
            n["chemin"] += 1
        elif e["classe"] == "IfcCommunicationsAppliance" and "Baie" in e["nom"]:
            D.patch(ax, silh(e, vtop), fc=FC_CFA, ec=CFA_C, lw=LWT, z=190)
            n["baie"] += 1
            c = ctr(e)
            label(ax, c[0], c[1], "Baie 9U", size=4.0, col=CFA_C, z=430, fontproperties=FP_MEDIUM)
        elif e["classe"] == "IfcCableCarrierSegment" and "placard technique" in e["nom"]:
            chemin(ax, e, vtop, CFA_C, z=149, ls=(0, (1, 2)), lw=D.LW[1])
    # câbles VDI : chemin CFA -> prises (tracé orthogonal schématique)
    for c_, kind, face, a, z_, circ, loc, lib in T.APPAREILS + [(c[0], c[1], None, None, None, c[4], None, None) for c in T.PLAFOND]:
        if circ != "VDI":
            continue
        q, _ = pos_appareil(c_)
        if q[1] > 2.4 and q[0] < 2.96:
            o = np.array([0.95, q[1]])
        else:
            o = np.array([min(max(q[0], 0.95), 5.38), 1.22])
        ax.plot([o[0], q[0]], [o[1], q[1]], color=CFA_C, lw=D.LW[1] * 1.3, ls=(0, (1, 1.2)), zorder=370)
        n["vdi"] += 1
    etiquettes_locaux(ax, LOCAUX_POS, size=4.4)
    label(ax, 3.25, 1.07, "CFA 50 × 30", size=4.2, col=CFA_C, z=430)
    label(ax, 0.70, 4.25, "VDI dans C1\n(séparateur, R5)", size=3.8, col=CFA_C, z=430)
    echelle_graphique(ax, 5.0, 7.70, 2, 1.0)
    LUM = lambda nom: vig(lambda a: sym_lum(a, dict(verts=np.array([[3, 0.6, 0], [5, 2.6, 0]]), nom=nom), ECL_C))
    legende_lots(p, [
        ("Éclairage", ECL_C, [
            (LUM("Downlight"), "Downlight encastré Ø 90", n["downlight"]),
            (LUM("Suspension"), "Suspension (salon de lecture)", n["suspension"]),
            (vig(lambda a: a.add_patch(Rectangle((0.6, 1.2), 6.8, 0.9, fc=ECL_C))), "Linéaire / réglette LED", n["lineaire"]),
            (vig(lambda a: a.add_patch(Arc((4, -4), 14, 14, theta1=65, theta2=115, color=ECL_C, lw=LWT * 1.4, ls=(0, (3, 1.4))))),
             "Anneau LED (oculus, canopée)", n["anneau"]),
            (LUM("Liseuse"), "Spot / liseuse", n["spot"]),
            (vig_cmd("INT", ECL_C), "Interrupteur simple / double, +1,10", n["INT"]),
            (vig_cmd("BP2", ECL_C), "Bouton-poussoir (télérupteur)", n["BP2"]),
            (vig_cmd("PLAT", ECL_C), "Platine accueil 4 BP", n["PLAT"]),
            (vig(lambda a: sym_det(a, 4, 1.6, ECL_C)), "Détecteur de présence plafond", n["DET"]),
            (vig(lambda a: (lien(a, (0.5, 1.0), (7.5, 1.0), ECL_C, rad=-0.3, lw=D.LW[2]),
                            a.text(8.6, 1.6, "E1", fontsize=4.6, color="white", ha="center", va="center", fontproperties=FP_MEDIUM,
                                   bbox=dict(boxstyle="round,pad=0.18", fc=ECL_C, ec="none")))),
             "Liaison de commande + n° de circuit (T05)", n["lien"])]),
        ("Sécurité", BAES_C, [(vig(lambda a: sym_baes(a, 4, 1.6)), "BAES d'évacuation (repère · circuit)", n["BAES"])]),
        ("Courants faibles", CFA_C, [
            (vig_rj, "Prise RJ45 double Cat 6A", n["RJ2"]),
            (vig(lambda a: sym_wifi(a, 4, 1.3)), "Borne Wi-Fi plafond (PoE)", n["WIFI"]),
            (vig_rect(FC_CFA, CFA_C, lw=LWT), "Baie de brassage 9U", n["baie"]),
            (vig_trait(CFA_C, ls=(0, (5, 1.5)), lw=LWT, double=True), "Chemin de câbles CFA 50 × 30", n["chemin"]),
            (vig_trait(CFA_C, ls=(0, (1, 1.2)), lw=D.LW[1] * 1.3), "Câble VDI (tracé de principe)", n["vdi"])]),
    ])
    p.intertitre("Circuits d'éclairage (repères du schéma T05)")
    for k in ("E1", "E2", "E3", "E4", "E5", "E6"):
        c = CIRCUITS[k]
        p.T(p.px + 8, p.y, k, 6.4, ECL_C, fontproperties=FP_MEDIUM)
        p.T(p.px + 16, p.y, c["Designation"][:52], 5.8)
        p.T(W - 12, p.y, f"{c['Nb_points_lumineux']} pts · {fr(c['P_installee_W'], 0)} W", 5.6, TAUPE, ha="right")
        p.y += 3.7
    p.y += 1.5
    p.intertitre("Principes")
    for s_ in ["27 luminaires LED 2700 K de la V5 sur 6 circuits 1,5 mm² / 16 A, 8 points max.",
               "(BAES compris) ; les grands volumes sur télérupteurs, l'oculus sur variateur,",
               "la vitrine et le seuil sur horloge astronomique. Dégagement et WC sur détecteurs.",
               "BAES LED 45 lm, 1 h : un à l'issue (porte d'entrée), un par changement de",
               "direction ; raccordés en amont des commandes du circuit d'éclairage du local.",
               "Courants faibles : baie 9U du placard, câble U/FTP Cat 6A, chemin CFA 50 × 30",
               "à 5 cm min. du CFO ; borne Wi-Fi 6 en PoE sous le faux-plafond de la salle."]:
        p.ligne(s_, 5.6, dy=3.45)
    p.cartouche("1/30")
    p.enregistrer("plan_courants_faibles_eclairage")


def T01():
    sc = scene()
    p = PlancheTech("T01", "Électricité — courants forts", "Plan de coupe +1,00, réseaux en plénum superposés  ·  Échelle 1/30 (A3)  ·  NF C 15-100")
    ax, v = plan_base(p, sc)
    vtop = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0))
    n = Counter()
    for e in sc:
        if e["classe"] == "IfcCableCarrierSegment" and "Chemin" in e["nom"] and "courants faibles" not in e["nom"]:
            chemin(ax, e, vtop, CFO, z=150, ls=(0, (5, 1.5)), fc=FC_CFO, lw=LWT)
            n["chemin"] += 1
        elif e["classe"] == "IfcDiscreteAccessory" and "CFA" not in e["nom"]:
            for fc_, _ in e["items"]:
                g = D.silhouette(vtop.to2d(e["verts"][fc_]))
                if g is not None:
                    c = g.centroid
                    ax.add_patch(Circle((c.x, c.y), mm(ax, 0.55), fc=CFO, ec="none", zorder=160))
                    n["suspente"] += 1
        elif e["classe"] == "IfcCableCarrierSegment" and e["nom"].startswith("Goulotte"):
            goulotte_sym(ax, e, CFO)
            n["goulotte"] += 1
        elif e["classe"] == "IfcBuildingElementProxy" and "Réservation" in e["nom"]:
            g = silh(e, vtop)
            D.patch(ax, g, fc=RES_C, ec=RES_C, lw=D.LW[1], z=170, alpha=0.85)
            c = ctr(e)
            nm = e["nom"].split(" ")[1]
            label(ax, c[0] + {"R5": 0.17, "R6": 0.16}.get(nm, 0.12), c[1] + {"R5": -0.12, "R6": 0.12}.get(nm, 0.1), nm, size=4.4, col=RES_C, z=430,
                  fontproperties=FP_MEDIUM)
            n["res"] += 1
        elif e["classe"] in ("IfcUnitaryEquipment",):
            g = silh(e, vtop)
            D.patch(ax, g, fc="white", ec=COND_C, lw=LWT, z=180, hatch="////")
            n["split"] += 1
        elif e["classe"] == "IfcPump":
            c = ctr(e)
            ax.add_patch(Circle(c[:2], mm(ax, 1.1), fc="white", ec=COND_C, lw=LWT, zorder=185))
            label(ax, c[0], c[1], "P", size=3.4, col=COND_C, z=186, fontproperties=FP_MEDIUM)
            n["pompe"] += 1
        elif e["classe"] == "IfcElectricDistributionBoard":
            g = silh(e, vtop)
            D.patch(ax, g, fc="white", ec=CFO, lw=D.LW[4], z=190)
            D.patch(ax, g, fc="none", ec=CFO, lw=0, z=191, hatch="//////")
            n["TD"] += 1
        elif e["classe"] == "IfcProtectiveDevice":
            g = silh(e, vtop)
            D.patch(ax, g, fc=CFO, ec=CFO, lw=LWT, z=190)
            n["coffret"] += 1
        elif e["classe"] == "IfcJunctionBox":
            g = silh(e, vtop)
            D.patch(ax, g, fc="white", ec=CFO, lw=LWT, z=190)
            n["boite"] += 1
        elif e["classe"] == "IfcCommunicationsAppliance" and "Baie" in e["nom"]:
            g = silh(e, vtop)
            D.patch(ax, g, fc="white", ec=FOND_TRAIT, lw=D.LW[1], z=150, ls=(0, (2, 1)))
    for c_, kind, face, a, z_, circ, loc, lib in T.APPAREILS:
        if kind in ("PC", "PC2", "PCU"):
            sym_prise(ax, face, a, kind, txt=circ)
            n[kind] += 1
    # cheminements particuliers
    ax.annotate("", xy=(0.70, 5.32), xytext=(0.70, 5.72), arrowprops=dict(arrowstyle="-|>", color=CFO, lw=LWT, ls=(0, (3, 1.5))), zorder=450)
    label(ax, 1.00, 5.90, "Arrivée immeuble ?", size=4.6, col=CFO, z=450, fontproperties=FP_MEDIUM)
    label(ax, 1.00, 5.78, "cheminement à relever", size=4.0, col=CFO, z=450)
    ax.plot([3.20, 3.20, 2.895, 2.895], [5.34, 5.34, 5.34, 5.34], color=CFO, lw=LWT, zorder=440)
    bulle(ax, 3.55, 5.95, "BL", fc=CFO, vers=(3.02, 5.34), size=3.8)
    for (x, y, s, cc) in ((2.30, 0.62, "liaison 3G10\nplacard › TD", CFO), (5.95, 4.05, "C2 › split 1", COND_C), (0.50, 3.80, "C1b › split 2", COND_C)):
        label(ax, x, y, s, size=4.2, col=cc, z=430, fontproperties=FP_MEDIUM)
    etiquettes_locaux(ax, LOCAUX_POS, size=4.4)
    label(ax, 0.83, 4.88, "C1 › TD", size=4.0, col=CFO, z=430)
    label(ax, 2.55, 0.40, "TD", size=4.8, col=CFO, z=430, fontproperties=FP_MEDIUM)
    echelle_graphique(ax, 5.0, 7.70, 2, 1.0)
    legende_lots(p, [
        ("Courants forts", CFO, [
            (vig_prise("PC"), "Prise 16 A 2P+T + n° de circuit", n["PC"]),
            (vig_prise("PC2"), "Prise 16 A 2P+T double", n["PC2"]),
            (vig_prise("PCU"), "Prise 16 A + USB (mobilier)", n["PCU"]),
            (vig_rect("white", CFO, "//////", lw=D.LW[4]), "Tableau divisionnaire TD (V5)", n["TD"]),
            (vig_rect(CFO, CFO), "Coffret arrivée immeuble (placard)", n["coffret"]),
            (vig_rect("white", CFO, lw=LWT), "Boîte de dérivation / coffret clim", n["boite"]),
            (vig_trait(CFO, ls=(0, (5, 1.5)), lw=LWT, double=True), "Chemin de câbles CFO 80 × 40, plénum", n["chemin"]),
            (vig(lambda a: a.add_patch(Rectangle((3.25, 0.85), 1.5, 1.5, fc=CFO, ec=CFO, lw=0.2))), "Descente en goulotte 40 × 20", n["goulotte"]),
            (vig(lambda a: a.add_patch(Circle((4, 1.6), 0.55, fc=CFO))), "Suspente M8, cheville courte", n["suspente"])]),
        ("Climatisation", COND_C, [
            (vig_rect("white", COND_C, "////", lw=LWT), "Split 9 000 BTU/h (circuits C1, C2)", n["split"]),
            (vig(lambda a: (a.add_patch(Circle((4, 1.6), 1.1, fc="white", ec=COND_C, lw=LWT)),
                            a.text(4, 1.6, "P", fontsize=3.4, color=COND_C, ha="center", va="center"))), "Mini-pompe de relevage condensats", n["pompe"])]),
        ("Réservations", RES_C, [
            (vig(lambda a: a.add_patch(Circle((4, 1.6), 0.9, fc=RES_C))), "Fourreau / réservation (R5, R6)", n["res"])]),
    ])
    p.intertitre("Circuits prises et spécialisés (repères du schéma T05)")
    for k in ("P1", "P2", "P3", "P4", "P5", "C1", "C2"):
        c = CIRCUITS[k]
        nb = f"{c['Nb_socles']} socles" if "Nb_socles" in c else "1 split + pompe"
        p.T(p.px + 8, p.y, k, 6.4, lot_col(k), fontproperties=FP_MEDIUM)
        p.T(p.px + 16, p.y, c["Designation"][:50], 5.8)
        p.T(W - 12, p.y, f"{nb} · {c['Calibre_A']} A · {fr(c['Section_mm2'], 1)} mm²", 5.4, TAUPE, ha="right")
        p.y += 3.7
    p.y += 1.5
    p.intertitre("Principes")
    for s in ["Tableau divisionnaire V5 (rep. TD) alimenté par le coffret d'arrivée du placard",
              "technique (disjoncteur de branchement de l'immeuble), liaison 3G10 dans C1.",
              "Cheminement de l'arrivée immeuble › placard inconnu : à relever (point ouvert).",
              "Câbles U1000 R2V en plénum sur chemins 80 × 40 (C1, C1b, C2), suspentes M8",
              "à cheville courte non traversante ; descentes en goulotte 40 × 20 collée ou",
              "derrière le lambris / doublage : aucune saignée dans les porteurs.",
              "Appareillage en saillie, axe +0,30 (prises) et +1,10 (commandes).",
              "BL : traversée de la baie libre V4 sous le linteau (goulotte collée, h 2,08).",
              "R6 : fourreau Ø 50 en plénum dans la cloison placo V4 4350620 (non porteuse),",
              "à valider comme R5 ; sinon goulotte franchissant l'huisserie du WC."]:
        p.ligne(s, 5.6, dy=3.45)
    p.cartouche("1/30")
    p.enregistrer("plan_electricite_courants_forts")


SYS_C = {"AEP": AEP_C, "EU": EU_C, "EV": EV_C}


def plomberie(sc):
    """Produits du lot plomberie (V5 tech) et descentes / coffrages V5, avec leur réseau."""
    out = []
    for e in sc:
        ps = PS.get(e["guid"], {})
        if ps.get("Lot", "").startswith("Technique - plomberie"):
            res = ps.get("Reseau") or ("AEP" if e["classe"] in ("IfcValve", "IfcFlowMeter", "IfcFilter") and "admission" not in e["nom"]
                                       else "EU" if ("EU" in e["nom"] or "Siphon" in e["nom"] or "admission" in e["nom"] or "Ø 40" in e["nom"])
                                       else "AEP" if ("AEP" in e["nom"] or "Robinet" in e["nom"] or "Coffret AEP" in e["nom"]) else "EV")
            out.append((e, res))
    return out


ACCESSOIRES = [   # (mot-clé du nom IFC, n°, libellé de légende)
    ("Pipe de WC", 1, "Pipe de WC excentrée Ø 100 sur la sortie existante"),
    ("Coude 87°30 Ø 100", 2, "Coude 87°30 Ø 100 à tampon de visite"),
    ("Culotte EV", 3, "Culotte EV 100/100 sur la descente (à relever)"),
    ("Siphon", 4, "Siphon Ø 40 démontable sur la bonde existante"),
    ("admission d'air", 5, "Clapet d'admission d'air Ø 40 (AAV, EN 12380)"),
    ("dégorgement 1", 6, "Coude Ø 40 à bouchon de dégorgement"),
    ("dégorgement 2", 6, None),
    ("Culotte EU", 7, "Culotte réduite 100/40 sur la descente"),
    ("Té de visite", 8, "Té de visite Ø 100 (tampon) face à la trappe"),
    ("Vanne d'arrêt", 9, "Vanne d'arrêt 1/4 de tour"),
    ("Filtre", 10, "Filtre à tamis"),
    ("Réducteur", 11, "Réducteur de pression (si P > 3 bar)"),
    ("Compteur", 12, "Compteur divisionnaire eau froide DN 15"),
    ("Clapet anti-retour", 13, "Clapet anti-retour EA (NF EN 1717)"),
    ("Té AEP", 14, "Té AEP 20/16/16, départs WC et lave-mains"),
    ("Robinet d'arrêt WC", 15, "Robinet d'arrêt + flexible du réservoir WC"),
    ("Robinet d'arrêt lave-mains", 16, "Robinet d'arrêt + flexible du lave-mains"),
    ("Coffret AEP", 17, "Coffret AEP BA13 H1, trappe à clé 0,60 × 0,26"),
    ("Trappe de visite 0,20", 18, "Trappe de visite acoustique du coffrage"),
    ("Colonne montante AEP", 19, "Colonne AEP de l'immeuble Ø 32 (hypothèse)"),
]


def T03():
    sc = scene()
    p = PlancheTech("T03", "AEP, EU, EV — raccordement du WC et du lave-mains", "WC et lave-mains V4 inchangés  ·  Plan 1/20, vue d'ensemble 1/100, coffrage 1/5 (A3)  ·  DTU 60.11, EN 12056")
    xl, yl = (-0.22, 3.22), (5.00, 7.74)
    ax = p.axes(8, 12, xl, yl, 20)
    v, R = fond_de_plan(ax, sc, 1.0, xl, yl, mobilier=False)
    vtop = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0))
    PL = plomberie(sc)
    n = Counter()
    for e, res in sorted(PL, key=lambda t: ctr(t[0])[2]):
        col = SYS_C[res]
        g = silh(e, vtop)
        ls = LS_EU if res == "EU" else "-"
        if e["classe"] == "IfcPipeSegment":
            D.patch(ax, g, fc=D.eclaircir(matplotlib.colors.to_rgb(col), 0.55), ec=col, lw=LWT, z=200 + ctr(e)[2], ls=ls)
            n["tube_" + res] += 1
        elif e["classe"] == "IfcBuildingElementProxy":
            D.patch(ax, g, fc="none", ec=col, lw=LWT, z=230, ls=(0, (3, 1.5)))
        else:
            D.patch(ax, g, fc="white", ec=col, lw=LWT, z=240 + ctr(e)[2], ls=ls)
    for e in sc:
        if e["nom"].startswith("Descente EU/EV"):
            D.patch(ax, silh(e, vtop), fc=D.eclaircir(matplotlib.colors.to_rgb(EV_C), 0.6), ec=EV_C, lw=LWT, z=199)
            n["descente"] += 1
        if e["nom"].startswith("Coffrage acoustique"):
            D.patch(ax, silh(e, vtop), fc="none", ec="#6E6E6E", lw=D.LW[1], z=198, ls=(0, (4, 2)))
            n["coffrage"] += 1
    # bulles des accessoires (rangées hors du local pour l'angle encombré)
    pos = {19: (0.02, 7.68), 9: (0.20, 7.68), 10: (0.38, 7.68), 11: (0.56, 7.68), 12: (0.74, 7.68), 13: (0.92, 7.68), 14: (1.10, 7.68),
           17: (1.28, 7.68), 3: (-0.15, 7.48), 7: (-0.15, 7.33), 8: (-0.15, 7.18), 18: (-0.15, 7.03), 2: (0.14, 6.52), 1: (0.36, 6.52),
           15: (0.62, 7.20), 4: (2.33, 6.80), 5: (2.33, 6.97)}
    pos6 = [(3.15, 6.92), (3.15, 7.30)]
    vus = set()
    for e, res in PL:
        for mot, num, lib in ACCESSOIRES:
            if mot in e["nom"]:
                c = ctr(e)
                q = pos6.pop(0) if num == 6 else (3.15, 6.70) if num == 16 else pos[num]
                bulle(ax, *q, num, fc=SYS_C[res], vers=tuple(c[:2]), size=4.4)
                vus.add(num)
                break

    for e, res in PL:
        ps = PS.get(e["guid"], {})
        k = ps.get("Code")
        if e["classe"] != "IfcPipeSegment" or not k:
            continue
        if res in ("EU", "EV"):
            txt = f"{res} PVC Ø {100 if res == 'EV' else 40} · pente {fr(ps['Pente_pct'], 1)} % · fe {fr(ps['FilEau_amont_m'], 3)} › {fr(ps['FilEau_aval_m'], 3)}"
        else:
            txt = f"AEP multicouche {ps['Diametre_ext_mm']} × 2"
        xy, xyt = {"EV-WC": ((0.27, 7.12), (1.00, 6.56)), "EU-LM": ((1.95, 7.30), (1.55, 7.17)), "AEP-LM": ((2.10, 7.34), (1.55, 7.68)),
                   "AEP-WC": ((0.45, 7.15), (1.00, 6.96)), "AEP-COL": ((0.95, 7.10), (1.00, 7.06))}[k]
        extra = {"AEP-COL": " · piquage +1,20, nourrice sous trappe", "AEP-WC": " › réservoir du WC", "AEP-LM": " · +0,30 le long du mur › lave-mains"}.get(k, "")
        note(ax, txt + extra, xy, xyt, SYS_C[res])
    for (x0, y0, x1, y1) in ((2.30, 7.30, 1.70, 7.30), (2.865, 6.95, 2.865, 7.20), (0.24, 6.98, 0.24, 7.12)):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=EU_C, lw=LWT), zorder=480)
        n["fleche"] += 1
    label(ax, 0.60, 6.43, "WC V4 existant — inchangé", size=5.0, col=SANIT, z=470)
    label(ax, 2.25, 6.45, "Lave-mains V4 existant — inchangé", size=5.0, col=SANIT, z=470)
    label(ax, 0.75, 5.40, "Descente EU/EV 2 : non utilisée,\ncoffrage acoustique V5 conservé", size=4.4, col=FOND_TXT, z=470)
    label(ax, 2.40, 5.70, "06  Dégagement", size=5.0, col=FOND_TXT, z=470)
    label(ax, 1.45, 5.95, "04  Rangement", size=5.0, col=FOND_TXT, z=470)
    label(ax, 1.65, 6.78, "07  WC", size=5.6, col=FOND_TXT, z=470, fontproperties=FP_MEDIUM)
    echelle_graphique(ax, 1.70, 5.10, 4, 0.25)
    # vue d'ensemble 1/100 : condensats
    xo, yo = (-0.35, 7.00), (-0.25, 8.75)
    ax2 = p.axes(8, 170, xo, yo, 100)
    fond_de_plan(ax2, sc, 1.0, xo, yo, mobilier=False)
    for e in sc:
        if e["nom"].startswith("Liaisons frigorifiques"):
            D.patch(ax2, silh(e, vtop), fc=COND_C, ec=COND_C, lw=D.LW[1], z=200)
            n["liaisons"] += 1
        elif e["classe"] in ("IfcUnitaryEquipment",):
            D.patch(ax2, silh(e, vtop), fc="white", ec=COND_C, lw=D.LW[2], z=210, hatch="////")
        elif e["classe"] == "IfcPump":
            c = ctr(e)
            ax2.add_patch(Circle(c[:2], mm(ax2, 1.0), fc="white", ec=COND_C, lw=D.LW[2], zorder=215))
        elif e["nom"].startswith("Descente EU/EV") or e["nom"].startswith("EV PVC") or e["nom"].startswith("EU PVC"):
            D.patch(ax2, silh(e, vtop), fc=EV_C if "EV" in e["nom"][:3] or "Descente" in e["nom"] else EU_C, ec="none", lw=0, z=205)
    ax2.add_patch(Rectangle((4.30, 8.05), 0.90, 0.45, fc="white", ec=COND_C, lw=D.LW[2], ls=(0, (3, 1.5)), zorder=220))
    label(ax2, 4.75, 8.27, "regard EP ?", size=4.0, col=COND_C, z=430)
    ax2.annotate("", xy=(4.72, 8.05), xytext=(4.72, 7.75), arrowprops=dict(arrowstyle="-|>", color=COND_C, lw=D.LW[2]), zorder=430)
    label(ax2, 2.4, 8.30, "Courette : groupes extérieurs et rejet\ndes condensats à relever (copropriété)", size=4.0, col=FOND_TXT, z=430)
    p.T(8, 166, "Vue d'ensemble 1/100 — condensats des splits relevés vers le réseau EP de l'immeuble", 6.2, ENCRE, fontproperties=FP_MEDIUM)
    # coffrage acoustique 1/5 (coupe horizontale à +0,75)
    xc, yc = (0.02, 0.64), (7.03, 7.50)
    ax3 = p.axes(110, 172, xc, yc, 5)
    vc = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0), coupe=((0, 0, 1), 0.7503))
    Rc = D.calculer(sc, vc, lambda e, r: r not in MASQUE_FOND and r != "luminaire" and e["classe"] != "IfcSlab" and r != "plafond"
                    and not e["nom"].startswith("Coffrage acoustique")
                    and bbe(e)[1][0] > xc[0] and bbe(e)[0][0] < xc[1] and bbe(e)[1][1] > yc[0] and bbe(e)[0][1] < yc[1])
    for r in Rc:
        if r["coupe"] is not None:
            if r["role"] == "structure":
                D.patch(ax3, r["coupe"], fc=FOND_POCHE, ec=FOND_POCHE, lw=D.LW[1], z=60)
            else:
                ps = PS.get(r["e"]["guid"], {})
                res = "AEP" if "AEP" in r["e"]["nom"] else "EV"
                D.patch(ax3, r["coupe"], fc=D.eclaircir(matplotlib.colors.to_rgb(SYS_C.get(res, EV_C)), 0.6), ec=SYS_C.get(res, EV_C), lw=D.LW[2], z=80)
        else:
            for it in r["items"]:
                res = next((rr for ee, rr in PL if ee is r["e"]), None)
                if res:
                    D.patch(ax3, it["g"], fc=D.eclaircir(matplotlib.colors.to_rgb(SYS_C[res]), 0.45), ec=SYS_C[res], lw=D.LW[1], z=50)
    x0, y0, x1, y1 = COFFRAGES["EU/EV 1 (WC)"]
    ext = sbox(x0, y0, x1, y1)
    ba13 = ext.difference(sbox(x0 - 1, y0 + 0.025, x1 - 0.025, y1 + 1))
    D.patch(ax3, ba13, fc="#EEEEEE", ec="#6E6E6E", lw=D.LW[2], z=70)
    D.patch(ax3, ext.difference(sbox(x0 - 1, y0 + 0.0125, x1 - 0.0125, y1 + 1)).difference(ext.difference(ba13)), fc="none", ec=ENCRE, lw=D.LW[1], z=71)
    xd, yd = T.DESCENTE_WC
    laine = Point(xd, yd).buffer(T.R_DESC + 0.045).difference(Point(xd, yd).buffer(T.R_DESC))
    D.patch(ax3, laine, fc="#F4E7B5", ec="#B08D3C", lw=D.LW[1], z=75, hatch="xxxx")
    for (a, b) in (((x1 - 0.025, y0 + 0.025), (x1 - 0.045, y0 + 0.025)), ((x1 - 0.025, y0 + 0.025), (x1 - 0.025, y0 + 0.045))):
        ax3.plot(*np.array([a, b]).T, color=ENCRE, lw=D.LW[2], zorder=76)
    ax3.add_patch(Rectangle((x0 + 0.002, yd + 0.07), 0.035, 0.012, fc=ENCRE, zorder=77))
    ax3.add_patch(Rectangle((0.445, yc[0]), xc[1] - 0.445, yc[1] - yc[0], fc="white", ec="none", zorder=455))
    ax3.plot([0.445, 0.445], yc, color=TAUPE, lw=D.LW[1], ls=(0, (6, 2, 1, 2)), zorder=456)
    for txt, xy, xyt in (("Collier isophonique, cheville courte", (0.11, 7.335), (0.47, 7.47)), ("Colonne AEP Ø 32 (hypothèse)", (0.18, 7.35), (0.47, 7.405)),
                         ("Trappe acoustique face au té de visite", (0.396, 7.33), (0.47, 7.34)),
                         ("Descente Ø 100 de l'immeuble (à relever)", (0.29, 7.26), (0.47, 7.275)), ("EU Ø 40 vers culotte 100/40", (0.42, 7.30), (0.47, 7.21)),
                         ("Laine minérale 45 mm", (0.30, 7.19), (0.47, 7.145)), ("2 BA13 (25 mm) sur cornières", (0.38, 7.122), (0.47, 7.08))):
        note(ax3, txt, xy, xyt, ENCRE, size=4.6)
    p.T(110, 168, "Coffrage acoustique de la descente 1 — coupe horizontale à +0,75, 1/5", 6.2, ENCRE, fontproperties=FP_MEDIUM)
    tube = lambda col, ls="-": vig(lambda a: a.add_patch(Rectangle((0.4, 1.05), 7.2, 1.1, fc=D.eclaircir(matplotlib.colors.to_rgb(col), 0.55),
                                                                  ec=col, lw=LWT, ls=ls)))
    legende_lots(p, [
        ("AEP eau froide", AEP_C, [(tube(AEP_C), "Multicouche 16 × 2 / 20 × 2 (trait continu)", n["tube_AEP"])]),
        ("EU / EV", EV_C, [
            (tube(EV_C), "EV PVC Ø 100 : trait continu", n["tube_EV"]),
            (tube(EU_C, LS_EU), "EU PVC Ø 40 : trait tireté", n["tube_EU"]),
            (vig(lambda a: a.add_patch(Circle((4, 1.6), 1.5, fc=D.eclaircir(matplotlib.colors.to_rgb(EV_C), 0.6), ec=EV_C, lw=LWT))),
             "Descente EU/EV Ø 100 de l'immeuble", n["descente"]),
            (vig(lambda a: a.annotate("", xy=(7.5, 1.6), xytext=(0.5, 1.6), arrowprops=dict(arrowstyle="-|>", color=EU_C, lw=LWT))),
             "Sens d'écoulement (pente 2 %)", n["fleche"]),
            (vig_trait("#6E6E6E", ls=(0, (4, 2)), lw=D.LW[1], double=True), "Coffrage acoustique 0,30 × 0,30 (V5)", n["coffrage"])]),
        ("Climatisation", COND_C, [(vig_trait(COND_C, lw=D.LW[4]), "Liaisons frigo + condensats (vue 1/100)", n["liaisons"])]),
    ])
    p.intertitre("Accessoires (IFC)")
    for mot, n, lib in ACCESSOIRES:
        if lib and n in vus:
            res = next(r for e, r in PL if mot in e["nom"])
            p.pastille(str(n), lib, SYS_C[res], 2, (sorted({a[1] for a in ACCESSOIRES if a[2] and a[1] in vus}).index(n)) % 2)
    p.y += 2.5
    p.y += 1.0
    p.intertitre("Raccordements (hypothèses à relever)")
    for s in ["WC V4 (0UsrJW3…9z) et lave-mains V4 (4350630, 4350631) lus dans l'IFC et",
              "conservés à l'identique ; on se raccorde sur leurs sorties existantes.",
              "Sortie du WC non décrite dans l'IFC : sortie horizontale arrière h 0,18 supposée.",
              "EV Ø 100 PVC à 2 % vers la descente 1 de l'immeuble (culotte 87°30).",
              "EU Ø 40 PVC à 2 % (siphon, AAV, bouchons de dégorgement) vers la même descente.",
              "Ventilation primaire : descente de l'immeuble prolongée en toiture (à vérifier).",
              "AEP : piquage sur la colonne supposée du coffrage 1, nourrice sous trappe,",
              "multicouche 16 × 2 vers le réservoir et le lave-mains (eau froide seule).",
              "Condensats : mini-pompes V5, refoulement Ø 6/9 dans le faisceau des liaisons,",
              "sortie par la baie arrière existante, rejet au réseau EP de la courette.",
              "Coffrages 0,30 × 0,30 des descentes : 2 BA13 + laine 45 mm, colliers",
              "isophoniques, trappe de visite ; position des descentes à relever."]:
        p.ligne(s, 5.5, dy=3.35)
    p.cartouche("1/20, 1/100, 1/5")
    p.enregistrer("plan_AEP_EU_EV")


def tcol(e, res_plb):
    n, c = e["nom"], e["classe"]
    if e["guid"] in res_plb:
        return SYS_C[res_plb[e["guid"]]]
    if n.startswith("Descente EU/EV"):
        return EV_C
    if n.startswith("Liaisons frigorifiques") or c == "IfcPump":
        return COND_C
    if c == "IfcCableCarrierSegment":
        return CFA_C if "courants faibles" in n else CFO
    if c == "IfcDiscreteAccessory":
        return CFO
    if c == "IfcLightFixture" and "BAES" in n:
        return BAES_C
    if c in ("IfcCommunicationsAppliance",) or (c == "IfcOutlet" and PS.get(e["guid"], {}).get("Circuit") == "VDI"):
        return CFA_C
    if c == "IfcUnitaryEquipment":
        return COND_C
    if c in ("IfcSwitchingDevice", "IfcSensor"):
        return ECL_C
    if c in ("IfcOutlet", "IfcJunctionBox", "IfcElectricDistributionBoard", "IfcProtectiveDevice"):
        return CFO
    if c == "IfcPlate" and "passe-liaisons" in n:
        return COND_C
    if "Réservation" in n:
        return RES_C
    return None


def rendu_coupe(ax, sc, vue, garder, res_plb):
    R = D.calculer(sc, vue, garder)
    z = 10
    for r in R:
        col = tcol(r["e"], res_plb)
        for it in r["items"]:
            if col:
                D.patch(ax, it["g"], fc=D.eclaircir(matplotlib.colors.to_rgb(col), 0.45), ec=col, lw=D.LW[1], z=200 + z)
            elif r["role"] == "vitrage":
                D.patch(ax, it["g"], fc="#F4F7F8", ec=FOND_TRAIT, lw=D.LW[1] * 0.5, z=z)
            else:
                fc = "#F7F7F7" if r["role"] in ("mobilier", "revetement", "plafond", "autre") else "#EDEDED" if r["role"] == "structure" else "white"
                D.patch(ax, it["g"], fc=fc, ec=FOND_TRAIT, lw=D.LW[1] * 0.5, z=z)
            z += 0.001
        if r["tout"] is not None and col:
            D.patch(ax, r["tout"], fc="none", ec=col, lw=LWT, z=200 + z)
    for r in R:
        g = r["coupe"]
        if g is None:
            continue
        col = tcol(r["e"], res_plb)
        if r["role"] == "structure":
            D.patch(ax, g, fc=FOND_POCHE, ec=FOND_POCHE, lw=D.LW[1], z=300)
        elif col:
            D.patch(ax, g, fc=D.eclaircir(matplotlib.colors.to_rgb(col), 0.75), ec=col, lw=LWT, z=320)
        elif r["role"] == "cloison":
            D.patch(ax, g, fc=FOND_CLOISON, ec=FOND_TRAIT, lw=D.LW[1], z=310)
        elif r["role"] == "vitrage":
            D.patch(ax, g, fc="#F4F7F8", ec=FOND_TRAIT, lw=D.LW[1], z=310)
        else:
            D.patch(ax, g, fc="#E6E6E6", ec=FOND_TRAIT, lw=D.LW[1], z=305)
    return R


def dans(e, lo_, hi_):
    lo, hi = bbe(e)
    return np.all(hi >= np.asarray(lo_)) and np.all(lo <= np.asarray(hi_))


def tranche(sc, n, c):
    """Copie de la scène restreinte au demi-espace n.p <= c (profondeur de vue limitée pour les coupes)."""
    n = np.asarray(n, float)
    out = []
    for e in sc:
        lo, hi = bbe(e)
        if np.all(np.array([lo, hi]) @ n <= c + 1e-9) and np.all(np.array([[lo[0], lo[1], hi[2]], [hi[0], hi[1], lo[2]]]) @ n <= c + 1e-9):
            out.append(e)
            continue
        V, items = [], []
        k = 0
        for fc, rgba in e["items"]:
            Tk = D.couper_demi_espace(e["verts"][fc], n, c)
            if len(Tk) == 0:
                continue
            V.append(Tk.reshape(-1, 3))
            items.append((np.arange(k, k + 3 * len(Tk)).reshape(-1, 3), np.tile(rgba.mean(0), (len(Tk), 1))))
            k += 3 * len(Tk)
        if items:
            out.append(dict(e, verts=np.concatenate(V), items=items))
    return out


def T04():
    sc = scene()
    RES = {e["guid"]: r for e, r in plomberie(sc)}
    p = PlancheTech("T04", "Détails techniques", "Coupes tirées de l'IFC technique  ·  Échelles 1/10, 1/20 et 1/25 (A3)  ·  Aucun percement dans les porteurs ni la dalle")
    base = lambda e, r: r not in MASQUE_FOND and r != "luminaire"

    # D1 -- coupe sur le plénum, x = 3,18 vers l'ouest (profondeur limitée à x 3,00)
    yl, zl = (0.25, 1.75), (2.70, 3.62)
    ax = p.axes(8, 16, yl, zl, 10)
    v = D.Vue((-1, 0, 0), (0, 1, 0), (0, 0, 1), coupe=((1, 0, 0), 3.1803))
    s1 = tranche(sc, (-1, 0, 0), -3.0)
    rendu_coupe(ax, s1, v, lambda e, r: base(e, r) and dans(e, (3.0, yl[0], zl[0]), (3.2, yl[1], zl[1])), RES)
    p.T(8, 11, "D1  Coupe sur le plénum (x = 3,18, vue vers l'ouest) — 1/10", 6.6, ENCRE, fontproperties=FP_MEDIUM)
    for yy, top, w in ((1.10, 3.26, 0.08), (1.22, 3.255, 0.05)):
        ax.plot([yy, yy], [top, Z_DALLE_SOUS - 0.003], color=ENCRE, lw=D.LW[2], zorder=330)
        ax.add_patch(Rectangle((yy - 0.006, Z_DALLE_SOUS), 0.012, 0.04, fc="#8E8A86", ec="white", lw=D.LW[1], zorder=335))
        ax.plot([yy - w / 2 - 0.01, yy + w / 2 + 0.01], [top - 0.043] * 2, color=ENCRE, lw=D.LW[2], zorder=330)
    yL = 1.35
    ax.plot([yL + 0.05, yL + 0.05], [3.15, Z_DALLE_SOUS - 0.003], color=ENCRE, lw=D.LW[2], zorder=330)
    ax.add_patch(Rectangle((yL + 0.044, Z_DALLE_SOUS), 0.012, 0.04, fc="#8E8A86", ec="white", lw=D.LW[1], zorder=335))
    ax.add_patch(Arc((yL, 3.15), 0.075, 0.075, theta1=-60, theta2=240, color=ENCRE, lw=D.LW[2], zorder=331))
    ax.plot([yL + 0.02, yL + 0.05], [3.15 + 0.03, 3.15 + 0.03], color=ENCRE, lw=D.LW[2], zorder=331)
    for yy in (0.55, 1.62):
        ax.plot([yy, yy], [Z_FP_DESSUS + 0.012, Z_DALLE_SOUS], color=TAUPE, lw=D.LW[1], zorder=325)
        ax.add_patch(Rectangle((yy - 0.03, Z_FP_DESSUS), 0.06, 0.012, fc="#C9C3BB", ec=TAUPE, lw=D.LW[1], zorder=326))
    for zz, t in ((Z_FP_SOUS, "+3,00"), (Z_DALLE_SOUS, "+3,30"), (Z_DALLE_DESSUS, "+3,50 (hyp.)")):
        niveau(ax, 1.70, zz, t, gauche=True, size=4.6)
    cote(ax, Z_FP_DESSUS, Z_DALLE_SOUS, 0.33, "plénum 0,26", horiz=False, size=4.4)
    cote(ax, 1.14, 1.195, 3.115, "5,5 cm", size=4.2)
    note(ax, "Dalle haute existante (hypothèse ép. 0,20) : aucune carotte, aucun percement traversant", (0.60, 3.50), (0.27, 3.575), size=4.4)
    for k, (txt, xy) in enumerate((("Cheville à expansion courte, 40 mm max., non traversante (repérage ferroscan)", (1.104, 3.33)),
                                   ("Tige filetée M8, pas de 1,20 m max., cornière de reprise", (1.10, 3.285)),
                                   ("Chemin de câbles CFO 80 × 40 (C2) : câbles U1000 R2V", (1.08, 3.24)),
                                   ("Chemin de câbles CFA 50 × 30 : câbles U/FTP Cat 6A", (1.235, 3.24)),
                                   ("Liaisons split 2 sous fourreau Ø 60 : cuivre 1/4\" + 3/8\" calorifugé, condensats Ø 6/9, bus", (1.35, 3.12)),
                                   ("Collier isophonique sur tige M8", (1.40, 3.19)),
                                   ("Faux-plafond laine de bois 40 mm, ossature et suspentes propres", (0.55, 3.02)))):
        note(ax, txt, xy, (0.27 if k % 2 == 0 else 0.95, 2.93 - 0.045 * (k // 2) - (0.02 if k % 2 else 0)), size=4.2)

    # D3 -- sortie des liaisons par la baie arrière, coupe x = 4,85 vers l'ouest
    yl3, zl3 = (6.95, 8.05), (2.00, 3.62)
    ax3 = p.axes(172, 16, yl3, zl3, 10)
    v3 = D.Vue((-1, 0, 0), (0, 1, 0), (0, 0, 1), coupe=((1, 0, 0), 4.8503))
    s3 = tranche(sc, (-1, 0, 0), -4.40)
    rendu_coupe(ax3, s3, v3, lambda e, r: base(e, r) and r != "arbre" and dans(e, (4.40, yl3[0], zl3[0]), (4.86, yl3[1], zl3[1])), RES)
    p.T(172, 11, "D3  Sortie des liaisons par la baie arrière — 1/10", 6.6, ENCRE, fontproperties=FP_MEDIUM)
    ax3.annotate("", xy=(7.98, 2.67), xytext=(7.76, 2.69), arrowprops=dict(arrowstyle="-|>", color=COND_C, lw=LWT), zorder=480)
    for zz, t in ((2.15, "+2,15"), (2.55, "+2,55"), (2.80, "+2,80"), (Z_FP_SOUS, "+3,00"), (Z_DALLE_SOUS, "+3,30")):
        niveau(ax3, 6.99, zz, t, size=4.2)
    label(ax3, 7.82, 3.58, "COURETTE", size=4.6, col=FOND_TXT, z=480)
    label(ax3, 7.00, 3.58, "SALLE", size=4.6, col=FOND_TXT, z=480, ha="left")
    for txt, xy, xyt in (("Mur arrière 4350589 et baie V4 :\nconservés, aucun percement", (7.55, 3.10), (7.64, 3.42)),
                         ("Liaisons + condensats relevés\n› groupe extérieur et regard EP", (7.80, 2.69), (7.64, 2.98)),
                         ("Fourreau R3 Ø 100, manchette\nsouple, mastic MS, pente 2 %", (7.50, 2.72), (7.64, 2.47)),
                         ("Panneau passe-liaisons acier\nen imposte (+2,55 / +2,80)", (7.435, 2.60), (7.64, 2.27)),
                         ("Imposte vitrée V4 4350595\nà adapter (point ouvert)", (7.495, 2.40), (7.64, 2.08)),
                         ("Doublage cintré V4 des niches\n(vide technique)", (7.20, 2.30), (7.07, 2.08))):
        note(ax3, txt, xy, xyt, ENCRE, size=4.2)

    # D2 -- raccordement WC / lave-mains, élévation coupée y = 6,62 vers le nord
    xl2, zl2 = (-0.12, 3.12), (-0.08, 1.50)
    ax2 = p.axes(8, 124, xl2, zl2, 20)
    v2 = D.Vue((0, 1, 0), (1, 0, 0), (0, 0, 1), coupe=((0, -1, 0), -6.6203))
    rendu_coupe(ax2, sc, v2, lambda e, r: base(e, r) and not e["nom"].startswith("Coffrage acoustique") and e["classe"] != "IfcDoor"
                and dans(e, (xl2[0], 6.62, zl2[0]), (xl2[1], 7.6, zl2[1])), RES)
    for e in sc:
        if e["nom"].startswith("Coffrage acoustique") and "WC" in e["nom"]:
            lo, hi = bbe(e)
            ax2.add_patch(Rectangle((lo[0], 0), hi[0] - lo[0], zl2[1], fc="none", ec="#6E6E6E", lw=D.LW[1], ls=(0, (4, 2)), zorder=400))
    ax2.plot(xl2, [0, 0], color=ENCRE, lw=D.LW[4], zorder=350)
    p.T(8, 119, "D2  Raccordement du WC et du lave-mains existants — élévation vers le mur arrière (y = 6,62), 1/20", 6.6, ENCRE, fontproperties=FP_MEDIUM)
    for zz, t in ((0.0, "±0,00"), (0.75, "+0,75"), (T.Z_PIQUAGE_AEP, "+1,20")):
        niveau(ax2, 3.07, zz, t, gauche=True, size=4.4)
    pos = {1: (0.55, 0.06), 2: (0.12, -0.04), 3: (-0.05, 0.10), 7: (-0.05, 0.50), 8: (-0.05, 0.75), 18: (0.50, 0.80), 19: (-0.05, 1.42),
           9: (0.40, 1.44), 10: (0.53, 1.44), 11: (0.66, 1.44), 12: (0.79, 1.44), 13: (0.92, 1.44), 14: (1.10, 0.42), 15: (0.62, 0.22),
           4: (2.40, 0.40), 5: (2.40, 0.60), 16: (2.30, 0.20), 17: (1.12, 1.44)}
    for e, res in plomberie(sc):
        for mot, n, lib in ACCESSOIRES:
            if mot in e["nom"] and n in pos:
                c = ctr(e)
                bulle(ax2, *pos[n], n, fc=SYS_C[res], vers=(c[0], c[2]), size=4.2)
                break
    for txt, xy, xyt, col in (("WC V4 inchangé", (0.60, 0.55), (1.05, 0.98), SANIT), ("Lave-mains V4 inchangé", (2.70, 0.80), (1.75, 1.12), SANIT),
                              ("EV Ø 100 à 2 %", (0.27, 0.17), (1.05, 0.08), EV_C), ("EU Ø 40 à 2 % le long du mur", (1.60, 0.53), (1.45, 0.66), EU_C),
                              ("AEP 16 × 2 à +0,30", (1.80, 0.30), (1.95, 0.12), AEP_C)):
        note(ax2, txt, xy, xyt, col, size=4.6)
    echelle_graphique(ax2, 2.0, 1.38, 4, 0.25)

    # D4 -- placard technique : plan coupé à +1,40 (1/10) et vue de face porte ouverte (1/25)
    xl4, yl4 = (0.36, 1.30), (5.04, 5.74)
    ax4 = p.axes(8, 216, xl4, yl4, 10)
    v4 = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0), coupe=((0, 0, 1), 1.4003))
    rendu_coupe(ax4, sc, v4, lambda e, r: base(e, r) and r != "plafond" and e["classe"] != "IfcSlab" and dans(e, (xl4[0], yl4[0], 0), (xl4[1], yl4[1], 1.41))
                and not e["nom"].startswith("Chemin"), RES)
    for e in sc:
        if e["nom"].startswith("Chemin de câbles placard"):
            D.patch(ax4, silh(e, D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0))), fc="none", ec=CFO, lw=LWT, z=420, ls=(0, (4, 1.5)))
    p.T(8, 211, "D4  Placard technique 0,60 × 0,40 net — plan à +1,40, 1/10", 6.6, ENCRE, fontproperties=FP_MEDIUM)
    cote(ax4, 0.53, 1.13, 5.69, "0,60 net", size=4.4)
    cote(ax4, 5.16, 5.56, 1.25, "0,40 net", horiz=False, size=4.4)
    for txt, xy, xyt in (("Coffret arrivée immeuble (disjoncteur\nde branchement) : arrivée à relever", (0.70, 5.23), (0.38, 5.07)),
                         ("Coffret liaisons clim", (0.98, 5.21), (0.99, 5.09)), ("Baie 9U (sous la coupe)", (0.80, 5.40), (0.62, 5.47)),
                         ("Porte pleine iroko 0,60, serrure à clé", (0.83, 5.59), (0.38, 5.69)), ("C1 › R5 › TD (plénum)", (0.83, 5.36), (0.99, 5.36))):
        note(ax4, txt, xy, xyt, ENCRE, size=4.4)
    xe, ze = (-1.24, -0.42), (0.0, 1.90)
    ax5 = p.axes(112, 214, xe, ze, 25)
    v5 = D.Vue((0, -1, 0), (-1, 0, 0), (0, 0, 1), coupe=((0, 1, 0), 5.5503))
    rendu_coupe(ax5, sc, v5, lambda e, r: base(e, r) and not e["nom"].startswith(("Porte pleine placard", "Placard technique - façade"))
                and dans(e, (0.40, 5.10, 0), (1.26, 5.56, 2.2)) and r != "plafond", RES)
    ax5.plot(xe, [0, 0], color=ENCRE, lw=D.LW[4], zorder=350)
    p.T(112, 210, "D4b  Face, porte ouverte — 1/25", 6.2, ENCRE, fontproperties=FP_MEDIUM)
    for zz, t in ((0.55, "baie 9U"), (1.00, "PC baie"), (1.52, "coffrets")):
        label(ax5, -0.40, zz, " " + t, size=4.4, col=ENCRE, z=480, ha="left")
    # D3b -- baie arrière vue de la courette
    xb, zb = (-5.22, -4.23), (2.05, 3.45)
    ax6 = p.axes(180, 196, xb, zb, 20)
    v6 = D.Vue((0, -1, 0), (-1, 0, 0), (0, 0, 1), coupe=((0, 1, 0), 7.8003))
    s6 = tranche(sc, (0, -1, 0), -7.40)
    rendu_coupe(ax6, s6, v6, lambda e, r: base(e, r) and dans(e, (4.2, 7.40, 2.0), (5.25, 7.81, 3.5)), RES)
    p.T(180, 191, "D3b  Baie arrière vue de la courette — 1/20", 6.2, ENCRE, fontproperties=FP_MEDIUM)
    for txt, xy, xyt in (("L1 › groupe 1", (-4.85, 2.70), (-4.50, 2.24)), ("L2 › groupe 2", (-4.60, 2.70), (-5.20, 2.24))):
        note(ax6, txt, xy, xyt, COND_C, size=4.4)
    legende_lots(p, [
        ("Fond de plan (existant V4)", FOND_POCHE, [
            (vig_rect(FOND_POCHE, FOND_POCHE), "Porteur coupé : ne pas toucher", None),
            (vig_rect("#F7F7F7", FOND_TRAIT), "Second œuvre, mobilier, vu", None)]),
        ("Courants forts", CFO, [(vig_rect(D.eclaircir(matplotlib.colors.to_rgb(CFO), 0.75), CFO, lw=LWT), "Chemin CFO, appareillage, TD", None),
                                 (vig(lambda a: (a.plot([4, 4], [0.4, 3.0], color=ENCRE, lw=D.LW[2]),
                                                 a.add_patch(Rectangle((3.7, 2.4), 0.6, 0.8, fc="#8E8A86", ec=ENCRE, lw=0.2)))),
                                  "Tige M8 + cheville courte (D1)", 3)]),
        ("Courants faibles", CFA_C, [(vig_rect(D.eclaircir(matplotlib.colors.to_rgb(CFA_C), 0.75), CFA_C, lw=LWT), "Chemin CFA, baie 9U", None)]),
        ("Climatisation", COND_C, [(vig_rect(D.eclaircir(matplotlib.colors.to_rgb(COND_C), 0.75), COND_C, lw=LWT), "Liaisons, condensats, passe-liaisons", None)]),
        ("EU / EV", EV_C, [(vig_rect(D.eclaircir(matplotlib.colors.to_rgb(EV_C), 0.75), EV_C, lw=LWT), "EV Ø 100, descente : continu", None),
                           (vig_rect(D.eclaircir(matplotlib.colors.to_rgb(EU_C), 0.75), EU_C, lw=LWT, ls=LS_EU), "EU Ø 40 : tireté", None)]),
        ("AEP", AEP_C, [(vig_rect(D.eclaircir(matplotlib.colors.to_rgb(AEP_C), 0.75), AEP_C, lw=LWT), "AEP eau froide multicouche", None)]),
    ], titre="Code couleur des lots (coupes)")
    p.intertitre("Accessoires numérotés (voir T03)")
    vus = sorted({n for mot, n, lib in ACCESSOIRES if n in pos})
    libs = {n: lib for mot, n, lib in ACCESSOIRES if lib}
    for k, n in enumerate(vus):
        res = next(r for e, r in plomberie(sc) if any(m in e["nom"] for m, nn, _ in ACCESSOIRES if nn == n))
        p.pastille(str(n), libs[n][:36], SYS_C[res], 2, k % 2)
    p.y += 2.5
    p.y += 1.0
    p.intertitre("Principes de fixation et de passage")
    for s_ in ["Aucun percement de poteau, de voile ni de la dalle haute ; pas de saignée.",
               "Plénum 0,26 : chemins CFO 80 × 40 et CFA 50 × 30 à 5,5 cm l'un de",
               "l'autre, liaisons frigorifiques sous fourreau ; tiges M8 sur chevilles",
               "courtes (40 mm max.), non traversantes, après repérage des armatures.",
               "Le faux-plafond garde ses suspentes propres (aucun appui sur les réseaux).",
               "Sortie des liaisons par l'imposte de la baie arrière EXISTANTE (panneau",
               "acier 32, réservations R3 / R4) : imposte vitrée V4 à adapter, accord",
               "de la copropriété pour la courette et les groupes extérieurs.",
               "WC et lave-mains V4 inchangés : pipe de WC emboîtée sur la sortie,",
               "siphon sur la bonde ; culottes et té de visite sur la descente de",
               "l'immeuble dans le coffrage, trappe face au té.",
               "Placard technique 0,60 × 0,40 net (V5) : arrivée immeuble, coffret clim,",
               "baie 9U ; tête ouverte sur le plénum (C1, R5). 1,00 m libre devant le TD."]:
        p.ligne(s_, 5.6, dy=3.45)
    p.cartouche("1/10, 1/20, 1/25")
    p.enregistrer("details_techniques")


TD_POS = np.array([2.78, 0.44, 1.75])
COFFRET_POS = np.array([0.70, 5.23, 1.52])


def longueur(a, b, z_plenum=3.24, marge=1.15):
    """Longueur de câble estimée : montée en plénum, parcours orthogonal, descente, + 15 %."""
    return marge * ((z_plenum - a[2]) + abs(a[0] - b[0]) + abs(a[1] - b[1]) + max(z_plenum - b[2], 0.0))


def bilan():
    sc = scene()
    pos = {e["guid"]: ctr(e) for e in sc}
    rows = []
    for k in ORDRE:
        c = CIRCUITS[k]
        L = max((longueur(TD_POS, pos[g]) for g in c["membres"] if g in pos), default=0.0)
        P = c["P_installee_W"]
        Ib = P / (230 * T.COS_PHI)
        dU = 100 * 2 * T.RHO * L * Ib * T.COS_PHI / c["Section_mm2"] / 230
        rows.append(dict(c, L=L, Ib=Ib, dU=dU, Pu=P * c["ku"]))
    Pi = sum(r["P_installee_W"] for r in rows)
    Pu = sum(r["Pu"] for r in rows)
    Pf = Pu * T.KS
    S = Pf / T.COS_PHI
    I = S / 230
    Lt = longueur(COFFRET_POS, TD_POS)
    dUt = 100 * 2 * T.RHO * Lt * I * T.COS_PHI / 10 / 230
    return rows, dict(Pi=Pi, Pu=Pu, Pf=Pf, S=S, I=I, Lt=Lt, dUt=dUt)


def T05():
    p = PlancheTech("T05", "Schéma unifilaire et bilan de puissance", "Tableau divisionnaire V5  ·  Monophasé 230 V  ·  NF C 15-100  ·  sans échelle")
    rows, tot = bilan()
    ax = p.fig.add_axes([6 / W, 1 - 290 / H, 280 / W, 282 / H])
    ax.set_xlim(0, 280); ax.set_ylim(282, 0); ax.axis("off")
    lw = D.LW[2]

    def T_(x, y, s, size=5.4, col=ENCRE, **kw):
        kw.setdefault("va", "center")
        ax.text(x, y, s, fontsize=size, color=col, **kw)

    def disj(x, y, h=8, diff=False, sect=False, col=ENCRE):
        ax.plot([x, x], [y, y + h * 0.3], color=col, lw=lw)
        ax.plot([x, x - h * 0.28], [y + h * 0.7, y + h * 0.33], color=col, lw=lw)
        ax.plot([x, x], [y + h * 0.7, y + h], color=col, lw=lw)
        if sect:
            ax.plot([x - 1.2, x + 1.2], [y + h * 0.3, y + h * 0.3], color=col, lw=lw)
        else:
            ax.plot([x - 0.9, x + 0.9], [y + h * 0.3 - 0.9, y + h * 0.3 + 0.9], color=col, lw=lw)
            ax.plot([x - 0.9, x + 0.9], [y + h * 0.3 + 0.9, y + h * 0.3 - 0.9], color=col, lw=lw)
        if diff:
            ax.add_patch(matplotlib.patches.Ellipse((x, y + h * 0.88), 4.2, 1.6, fc="none", ec=col, lw=lw))

    # arrivée
    x0 = 14
    T_(x0 - 4, 7, "Réseau BT de l'immeuble — origine et cheminement à relever (point ouvert)", 5.8, fontproperties=FP_MEDIUM)
    ax.plot([x0, x0], [10, 14], color=ENCRE, lw=lw, ls=(0, (2, 1.5)))
    disj(x0, 14, 9, diff=True)
    T_(x0 + 5, 18.5, "Placard technique : disjoncteur de branchement 2P, 500 mA sélectif (calibre selon abonnement, distributeur)", 5.2)
    ax.plot([x0, x0], [23, 31], color=ENCRE, lw=D.LW[4])
    T_(x0 + 5, 27, f"Liaison U1000 R2V 3G10 dans C1 et R5 · L ≈ {fr(tot['Lt'], 1)} m · ΔU {fr(tot['dUt'], 2)} %", 5.2, CFO)
    ax.add_patch(Rectangle((x0 - 6, 31), 268, 112, fc="none", ec=TAUPE, lw=D.LW[1], ls=(0, (6, 2))))
    T_(x0 - 4, 34.5, "TABLEAU DIVISIONNAIRE (habillage iroko, 1,00 m dégagé devant)", 5.2, TAUPE, fontproperties=FP_MEDIUM)
    disj(x0, 37, 9, sect=True)
    T_(x0 + 5, 41.5, "Interrupteur-sectionneur général 2P 40 A", 5.2)
    ax.plot([x0, x0], [46, 54], color=ENCRE, lw=lw)
    ax.plot([x0, x0 + 6], [50, 50], color=ENCRE, lw=lw)
    ax.add_patch(Rectangle((x0 + 6, 47.5), 5, 5, fc="white", ec=ENCRE, lw=lw))
    ax.plot([x0 + 8.5, x0 + 8.5, x0 + 7, x0 + 10], [52.5, 55, 55, 55], color=ENCRE, lw=lw)
    T_(x0 + 13, 50, "Parafoudre type 2 (In 5 kA, Up 1,5 kV) + disjoncteur associé — Abidjan, forte densité de foudroiement", 5.2)
    ax.plot([x0, x0], [54, 60], color=ENCRE, lw=lw)
    ids = [("ID1", [r for r in rows if r["Differentiel"] == "ID1"] + [None]), ("ID2", [r for r in rows if r["Differentiel"] == "ID2"] + [None]),
           ("ID3", [r for r in rows if r["Differentiel"] == "ID3"])]
    n_tot = sum(len(v) for _, v in ids)
    pas = 252 / n_tot
    xb = x0
    ax.plot([x0, x0 + 6 + pas * (n_tot - 1) + 4], [60, 60], color=ENCRE, lw=D.LW[4])
    res_k = 0
    xc = x0 + 6
    for idn, rs in ids:
        xs = [xc + pas * k for k in range(len(rs))]
        xi = (xs[0] + xs[-1]) / 2
        ax.plot([xi, xi], [60, 64], color=ENCRE, lw=lw)
        disj(xi, 64, 9, diff=True, sect=True)
        T_(xi + 3.2, 68.5, f"{idn} : {T.DIFFERENTIELS[idn].replace('Interrupteur différentiel ', 'ID ')}", 4.8, fontproperties=FP_MEDIUM)
        ax.plot([xi, xi], [73, 76], color=ENCRE, lw=lw)
        ax.plot([xs[0], xs[-1]], [76, 76], color=ENCRE, lw=lw)
        for x, r in zip(xs, rs):
            ax.plot([x, x], [76, 80], color=ENCRE, lw=lw)
            col = lot_col(r["Repere"]) if r else TAUPE
            disj(x, 80, 8, col=col if r else TAUPE)
            ax.plot([x, x], [88, 96 if r and r.get("Commande") and r["Repere"] in ("E1", "E2", "E3", "E6") else 104], color=col, lw=lw)
            if r and r["Repere"] in ("E1", "E2", "E3", "E6"):
                tag = {"E1": "TL", "E2": "TL", "E3": "VAR", "E6": "KM+H"}[r["Repere"]]
                ax.add_patch(Rectangle((x - 3.2, 96), 6.4, 4, fc="white", ec=col, lw=lw))
                T_(x, 98, tag, 3.8, col, ha="center", fontproperties=FP_MEDIUM)
                ax.plot([x, x], [100, 104], color=col, lw=lw)
            ax.plot([x - 1.5, x + 1.5, x, x - 1.5], [104, 104, 106.5, 104], color=col, lw=lw)
            if r:
                T_(x, 110, r["Repere"], 6.4, col, ha="center", fontproperties=FP_MEDIUM)
                T_(x, 115, f"{r['Calibre_A']} A", 4.8, ha="center")
                T_(x, 119, f"{fr(r['Section_mm2'], 1)} mm²", 4.8, ha="center")
                n = r.get("Nb_points_lumineux") or r.get("Nb_socles")
                T_(x, 123, f"{n} {'pts' if 'Nb_points_lumineux' in r else 'socles'}" if n else "spécialisé", 4.4, TAUPE, ha="center")
                T_(x, 127, f"{fr(r['P_installee_W'], 0)} W", 4.4, TAUPE, ha="center")
                words = r["Designation"].replace(" + ", " +").split(" ")
                lines, cur = [], ""
                for w_ in words:
                    if len(cur) + len(w_) > 13 and cur:
                        lines.append(cur); cur = w_
                    else:
                        cur = (cur + " " + w_).strip()
                lines.append(cur)
                for j, l_ in enumerate(lines[:4]):
                    T_(x, 132 + j * 3.1, l_, 3.7, ENCRE, ha="center")
            else:
                res_k += 1
                T_(x, 110, f"R{res_k}", 6.4, TAUPE, ha="center", fontproperties=FP_MEDIUM)
                T_(x, 115, "réserve", 4.8, TAUPE, ha="center")
        xc = xs[-1] + pas
    T_(x0 - 4, 146.5, "Terre : barrette de coupure au tableau, conducteur principal de protection 16 mm² vers la prise de terre de l'immeuble (existence et R < 100 Ω à vérifier) ; "
       "réserve de 20 % de modules.", 4.8, TAUPE)
    # bilan
    yb = 156
    T_(x0 - 4, yb, "BILAN DE PUISSANCE (puissances lues dans l'IFC : luminaires, BAES ; hypothèses d'usage pour les prises et les splits)", 6.0, ENCRE, fontproperties=FP_MEDIUM)
    cols = [("Circuit", 8, "left"), ("Désignation", 22, "left"), ("Protection", 104, "left"), ("Câble", 128, "left"), ("Pts / socles", 160, "right"),
            ("P inst. (W)", 180, "right"), ("ku", 192, "right"), ("P util. (W)", 212, "right"), ("L (m)", 228, "right"), ("Ib (A)", 244, "right"), ("ΔU (%)", 262, "right")]
    y = yb + 7
    ax.add_patch(Rectangle((x0 - 6, y - 2.8), 268, 5.6, fc=SABLE, ec="none"))
    for t_, x, ha in cols:
        T_(x0 - 6 + x, y, t_, 5.0, ha=ha)
    for k, r in enumerate(rows):
        y += 5.4
        if k % 2:
            ax.add_patch(Rectangle((x0 - 6, y - 2.7), 268, 5.4, fc=SABLE_CLAIR, ec="none"))
        lim = 3.0 if r["Repere"].startswith("E") else 5.0
        n = r.get("Nb_points_lumineux") or r.get("Nb_socles") or "-"
        vals = [r["Repere"], r["Designation"][:48], f"1P+N {r['Calibre_A']} A C", r["Cable"], str(n), fr(r["P_installee_W"], 0), fr(r["ku"], 2),
                fr(r["Pu"], 0), fr(r["L"], 1), fr(r["Ib"], 2), fr(r["dU"] + tot["dUt"], 2)]
        for (t_, x, ha), val in zip(cols, vals):
            T_(x0 - 6 + x, y, val, 4.9, lot_col(r["Repere"]) if t_ == "Circuit" else ("#B03A2E" if t_ == "ΔU (%)" and r["dU"] + tot["dUt"] > lim else ENCRE),
               ha=ha, fontproperties=FP_MEDIUM if t_ == "Circuit" else None)
    y += 6.5
    ax.plot([x0 - 6, x0 + 262], [y - 3.2, y - 3.2], color=TAUPE, lw=D.LW[1])
    T_(x0 - 6 + 22, y, "Total installé / utilisé", 5.2, fontproperties=FP_MEDIUM)
    T_(x0 - 6 + 180, y, fr(tot["Pi"], 0), 5.2, ha="right", fontproperties=FP_MEDIUM)
    T_(x0 - 6 + 212, y, fr(tot["Pu"], 0), 5.2, ha="right", fontproperties=FP_MEDIUM)
    y += 5.6
    T_(x0 - 6 + 22, y, f"Puissance foisonnée (ks {fr(T.KS, 1)}) : {fr(tot['Pf'] / 1000, 2)} kW · cos φ {fr(T.COS_PHI, 1)} : {fr(tot['S'] / 1000, 2)} kVA · "
       f"I = {fr(tot['I'], 1)} A sous 230 V  ›  abonnement monophasé 6 kVA (30 A) proposé, à confirmer (CIE, syndic)", 5.2, ENCRE, fontproperties=FP_MEDIUM)
    y += 5.0
    T_(x0 - 6 + 22, y, "ΔU cumulée = liaison placard › TD + circuit ; limites 3 % (éclairage) et 5 % (autres usages) depuis l'origine de l'installation du local.", 4.6, TAUPE)
    nE = sum(r["Repere"].startswith("E") for r in rows)
    nC = sum(r["Repere"].startswith("C") for r in rows)
    nP = len(rows) - nE - nC
    nres = sum(1 for _, v_ in ids for r in v_ if r is None)
    ntl = sum(r["Repere"] in ("E1", "E2", "E3", "E6") for r in rows)
    legende_lots(p, [
        ("Éclairage  ·  circuits E", ECL_C, [(vig(lambda a: a.plot([0.3, 7.7], [1.6, 1.6], color=ECL_C, lw=LWT * 1.4)), "Départs éclairage (plan T02)", nE)]),
        ("Courants forts  ·  circuits P", CFO, [(vig(lambda a: a.plot([0.3, 7.7], [1.6, 1.6], color=CFO, lw=LWT * 1.4)), "Départs prises (plan T01)", nP)]),
        ("Climatisation  ·  circuits C", COND_C, [(vig(lambda a: a.plot([0.3, 7.7], [1.6, 1.6], color=COND_C, lw=LWT * 1.4)), "Départs splits (plan T01)", nC)]),
        ("Appareillage du tableau", ENCRE, [
            (vig(lambda a: (a.plot([4, 4], [0.2, 3.0], color=ENCRE, lw=D.LW[2]), a.plot([3.4, 4.6], [1.0, 1.6], color=ENCRE, lw=D.LW[2]),
                            a.plot([3.4, 4.6], [1.6, 1.0], color=ENCRE, lw=D.LW[2]))), "Disjoncteur 1P+N courbe C", len(rows)),
            (vig(lambda a: (a.plot([4, 4], [0.2, 3.0], color=ENCRE, lw=D.LW[2]),
                            a.add_patch(matplotlib.patches.Ellipse((4, 1.6), 3.0, 1.2, fc="none", ec=ENCRE, lw=D.LW[2])))), "Interrupteur différentiel 30 mA", len(ids)),
            (vig(lambda a: (a.plot([4, 4], [0.2, 3.0], color=ENCRE, lw=D.LW[2]), a.plot([3.2, 4.8], [1.6, 1.6], color=ENCRE, lw=D.LW[2]))),
             "Sectionnement", None),
            (vig_rect("white", ENCRE), "TL télérupteur, VAR, KM+H horloge", ntl),
            (vig(lambda a: a.plot([2.5, 5.5, 4, 2.5], [2.6, 2.6, 0.6, 2.6], color=TAUPE, lw=D.LW[2])), "Réserve équipée (R)", nres)]),
    ], titre="Légende et code couleur")
    p.intertitre("Hypothèses")
    for s_ in [f"Monophasé 230 V, cos φ {fr(T.COS_PHI, 1)}, cuivre ρ = {fr(T.RHO, 4)} Ω·mm²/m, longueurs = trajet",
               "plénum orthogonal depuis le TD + 15 % ; Ib = P installée / (230 cos φ).",
               "Éclairage : 27 luminaires LED de la V5 (puissance des types IFC) +",
               f"5 BAES à {fr(T.P_BAES_W, 0)} W. Splits 9 000 BTU/h : 2,6 kW froid, ~0,82 kW",
               "électriques (EER 3,2) + mini-pompe 15 W ; ku 1 (climat tropical humide).",
               "Prises : usages déclarés (poste d'accueil, écoute, réunion, ménage hors",
               f"ouverture, baie informatique) ; ks global {fr(T.KS, 1)}.",
               "Pas de TGBT ni de groupe électrogène ; pas d'eau chaude (lave-mains en",
               "eau froide seule) ; extraction du WC à arbitrer (voir note technique)."]:
        p.ligne(s_, 5.6, dy=3.45)
    p.y += 1.5
    p.intertitre("Règles appliquées (NF C 15-100)")
    for s_ in ["Éclairage 1,5 mm² / 16 A, 8 points max. (BAES compris) ; prises 2,5 mm²",
               "/ 20 A, 8 socles max. ; circuits spécialisés par split (16 A, 2,5 mm²).",
               "ID 30 mA : 8 circuits max. chacun ; éclairage réparti sur 2 différentiels ;",
               "type F pour les splits inverter et l'onduleur (déclenchements intempestifs).",
               "BAES en amont des commandes du circuit d'éclairage du local (ERP type S).",
               "Sectionneur de proximité IP65 au pied de chaque groupe extérieur (courette).",
               "Câbles U1000 R2V en plénum, CFA séparés (5 cm min., EN 50174-2)."]:
        p.ligne(s_, 5.6, dy=3.45)
    p.y += 1.5
    p.cartouche("sans échelle")
    p.enregistrer("schema_unifilaire_bilan")


PLANCHES = {"T01": T01, "T02": T02, "T03": T03, "T04": T04, "T05": T05}

if __name__ == "__main__":
    for k in (sys.argv[1:] or PLANCHES):
        PLANCHES[k]()
