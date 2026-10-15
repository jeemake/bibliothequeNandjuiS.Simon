"""Planches A3 de l'esquisse V5, entièrement tirées de v5/DECIMO_ESQ_V5.ifc : v5/dessins/*.png|pdf|svg.

A01 plan RDC (coupe +1,00)          A02 plan de faux-plafond et réseaux (coupe +2,00, vu de dessous)
A03 coupe AA (x = 4,75, vers l'ouest) A04 élévation devanture sur rue (logements esquissés)
A05 élévations intérieures Est, Nord  A06 élévations intérieures Sud, Ouest
A07 vues 3D (rendus v5/vues_rendu)    A08 axonométries (aménagement coupé à +2,40 ; technique)
Usage : python3 v5/scripts/dessins.py [A01 A02 ...]
"""
import os, sys, hashlib, logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon as MPoly
from matplotlib.lines import Line2D
from PIL import Image
import shapely
from shapely.geometry import box, LineString, Point
from shapely.ops import unary_union
import ifcopenshell, ifcopenshell.geom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import (RACINE, V5_IFC, DESSINS, VUES, RAPPORTS, Z_FP_SOUS, Z_FP_DESSUS, Z_DALLE_SOUS, Z_DALLE_DESSUS,  # noqa
                    ARBRE, R_OCULUS, INDIGO, POCHE)
sys.path.insert(0, os.path.join(RACINE, "charte"))
from charte_kdemi import (draw_lockup, FP_NOM, FP_TITRE, FP_MEDIUM, FP_LIGHT, ENCRE, TAUPE, TERRE_CUITE, IROKO, SABLE,  # noqa
                          SABLE_CLAIR, BLANC_CHAUX, OLIVE)
from scene import charger, role, triangles  # noqa
import dessin2d as D  # noqa

logging.disable(logging.WARNING)
plt.rcParams["hatch.linewidth"] = 0.25
plt.rcParams["svg.fonttype"] = "none"
W, H = 420, 297
MM = 1 / 25.4
SHA = hashlib.sha256(open(V5_IFC, "rb").read()).hexdigest()[:10]
DATE = "Octobre 2026"
GRIS_CLOISON = "#77706A"
VERRE = "#CFE0E6"
REPERES = {int(r["repere"]): r["libelle"] for r in D.lire_csv(os.path.join(RAPPORTS, "reperes.csv"))}
ESPACES = {r["nom"]: r for r in D.lire_csv(os.path.join(RAPPORTS, "espaces.csv"))}


def fr(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


# --- mise en page ---------------------------------------------------------------------------
class Planche:
    def __init__(self, num, titre, ligne, px=290, maquette=V5_IFC, dossier=DESSINS):
        self.num, self.titre, self.px = num, titre, px
        self.maquette, self.dossier = maquette, dossier
        self.sha = SHA if maquette == V5_IFC else hashlib.sha256(open(maquette, "rb").read()).hexdigest()[:10]
        self.fig = plt.figure(figsize=(W * MM, H * MM), facecolor="white")
        # charte v2 : papier blanc, panneau séparé par un filet fin (pas d'aplat de fond)
        self.fig.add_artist(Line2D([px / W] * 2, [8 / H, 1 - 8 / H], color=TAUPE, lw=0.35))
        x = px + 8
        draw_lockup(self.fig, x, 9, 46, fond="clair")
        self.T(x, 30, "Bibliothèque Decimo", 19, ENCRE, fontproperties=FP_TITRE)
        self.T(x, 41, titre, 9.5, ENCRE, fontproperties=FP_MEDIUM)
        self.T(x, 47.5, ligne, 6.3, TAUPE)
        self.filet(52)
        self.y = 58

    def T(self, x, y, s, size, color=ENCRE, **kw):
        kw.setdefault("va", "top")
        return self.fig.text(x / W, 1 - y / H, s, fontsize=size, color=color, **kw)

    def filet(self, y, color=TAUPE, lw=0.5):
        self.fig.add_artist(Line2D([(self.px + 8) / W, (W - 10) / W], [1 - y / H] * 2, color=color, lw=lw))

    def intertitre(self, s):
        self.T(self.px + 8, self.y, s.upper(), 7.2, TERRE_CUITE, fontproperties=FP_MEDIUM)
        self.y += 5.5

    def ligne(self, s, size=6.2, color=ENCRE, dy=3.9, x=0):
        self.T(self.px + 8 + x, self.y, s, size, color)
        self.y += dy

    def pastille(self, txt, libelle, fc=ENCRE, n_col=1, col=0, w=None):
        w = w or (W - 18 - self.px) / n_col
        x = self.px + 8 + col * w
        self.fig.text((x + 2) / W, 1 - (self.y + 1.4) / H, txt, fontsize=4.6, color="white", ha="center", va="center",
                      bbox=dict(boxstyle="circle,pad=0.25" if len(txt) < 3 else "round,pad=0.25", fc=fc, ec="none"))
        self.T(x + 5.5, self.y, libelle, 5.9, ENCRE)
        if col == n_col - 1:
            self.y += 3.7

    def symbole(self, kind, libelle, **kw):
        x = self.px + 8
        ax = self.fig.add_axes([x / W, 1 - (self.y + 3.0) / H, 9 / W, 3.0 / H])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        if kind == "poche":
            ax.add_patch(Rectangle((0, 0.1), 1, 0.8, fc=POCHE, ec=POCHE, lw=D.LW[4]))
        elif kind == "cloison":
            ax.add_patch(Rectangle((0, 0.2), 1, 0.6, fc=GRIS_CLOISON, ec=ENCRE, lw=D.LW[4]))
        elif kind == "coupe":
            ax.add_patch(Rectangle((0, 0.15), 1, 0.7, fc=kw.get("fc", SABLE), ec=ENCRE, lw=D.LW[2], hatch=kw.get("hatch")))
        elif kind == "aplat":
            ax.add_patch(Rectangle((0, 0.15), 1, 0.7, fc=kw.get("fc", SABLE), ec=kw.get("ec", ENCRE), lw=D.LW[1], hatch=kw.get("hatch")))
        elif kind == "trait":
            ax.add_line(Line2D([0, 1], [0.5, 0.5], color=kw.get("color", ENCRE), lw=kw.get("lw", D.LW[1]), ls=kw.get("ls", "-")))
        elif kind == "verre":
            ax.add_patch(Rectangle((0, 0.3), 1, 0.4, fc=VERRE, ec=ENCRE, lw=D.LW[1]))
        self.T(x + 11.5, self.y + 0.1, libelle, 5.9)
        self.y += 4.1

    def cartouche(self, echelle, phase="ESQ V5 — aménagement sur existant V4"):
        x0, x1, y0 = self.px + 8, W - 10, 255
        self.filet(y0 - 2, TAUPE, 0.4)
        rows = [("Projet", "Bibliothèque Decimo — RDC sous logements, Abidjan"), ("Phase", phase),
                ("Planche", f"{self.num} — {self.titre}"), ("Échelle", echelle + "  ·  format A3"),
                ("Maquette", f"{os.path.relpath(self.maquette, RACINE)} (IFC4) · sha256 {self.sha}…"), ("Date", DATE + "  ·  indice A")]
        for k, (a, b) in enumerate(rows):
            y = y0 + k * 4.3
            self.T(x0, y, a.upper(), 5.0, TAUPE, fontproperties=FP_MEDIUM)
            self.T(x0 + 17, y, b, 5.9, ENCRE)
        self.T(x0, 284, "Esquisse : cotes et surfaces indicatives, existant V4 à relever sur site.", 5.4, TAUPE)
        self.T(x0, 288.85, "K&Démi", 6.0, ENCRE, fontproperties=FP_NOM)
        self.T(x1, 289, f"{self.num}  ·  ESQ V5  ·  {DATE}", 5.6, TERRE_CUITE, ha="right")

    def axes(self, x_mm, y_top_mm, xlim, ylim, ech):
        w = (xlim[1] - xlim[0]) * 1000 / ech
        h = (ylim[1] - ylim[0]) * 1000 / ech
        ax = self.fig.add_axes([x_mm / W, 1 - (y_top_mm + h) / H, w / W, h / H])
        ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.axis("off")
        ax.ech = ech
        return ax

    def enregistrer(self, nom):
        os.makedirs(self.dossier, exist_ok=True)
        base = os.path.join(self.dossier, f"{self.num}_{nom}")
        self.fig.savefig(base + ".pdf")
        self.fig.savefig(base + ".svg")
        self.fig.savefig(base + ".png", dpi=200)
        plt.close(self.fig)
        print(base + ".png|pdf|svg")


# --- primitives de dessin (coordonnées vue, mètres) ----------------------------------------------
def mm(ax, v):
    return v * ax.ech / 1000


def cote(ax, a, b, pos, txt, horiz=True, col=TAUPE, size=5.0, z=300, ext=None):
    t = mm(ax, 0.9)
    kw = dict(color=col, lw=D.LW[1], zorder=z, solid_capstyle="butt")
    if horiz:
        ax.plot([a, b], [pos, pos], **kw)
        for p in (a, b):
            ax.plot([p - t, p + t], [pos - t, pos + t], **kw)
            if ext is not None:
                ax.plot([p, p], [ext, pos + t * 1.5], color=col, lw=D.LW[1] * 0.6, zorder=z)
        ax.text((a + b) / 2, pos + mm(ax, 0.8), txt, fontsize=size, color=col, ha="center", va="bottom", zorder=z)
    else:
        ax.plot([pos, pos], [a, b], **kw)
        for p in (a, b):
            ax.plot([pos - t, pos + t], [p - t, p + t], **kw)
            if ext is not None:
                ax.plot([ext, pos + t * 1.5], [p, p], color=col, lw=D.LW[1] * 0.6, zorder=z)
        ax.text(pos - mm(ax, 0.8), (a + b) / 2, txt, fontsize=size, color=col, ha="right", va="center",
                rotation=90, zorder=z)


def niveau(ax, x, z, txt, gauche=False, col=ENCRE, size=5.2):
    s = mm(ax, 1.6)
    ax.add_patch(MPoly([[x, z], [x - s * 0.6, z + s], [x + s * 0.6, z + s]], closed=True, fc="white", ec=col,
                       lw=D.LW[1], zorder=310))
    ax.plot([x - s * 2.2, x + s * 2.2], [z, z], color=col, lw=D.LW[1], zorder=310)
    ax.text(x + (-s * 1.0 if gauche else s * 1.0), z + s * 1.1, txt, fontsize=size, color=col,
            ha="right" if gauche else "left", va="bottom", zorder=310)


def bulle(ax, x, y, n, fc=ENCRE, size=4.6, z=400, vers=None):
    if vers is not None:
        ax.plot([vers[0], x], [vers[1], y], color=fc, lw=D.LW[1], zorder=z - 1)
        ax.add_patch(Circle(vers, mm(ax, 0.45), fc=fc, ec="none", zorder=z - 1))
    ax.text(x, y, str(n), fontsize=size, color="white", ha="center", va="center", zorder=z,
            bbox=dict(boxstyle="circle,pad=0.25" if len(str(n)) < 3 else "round,pad=0.22", fc=fc, ec="none"))


def label(ax, x, y, s, size=5.2, col=ENCRE, z=350, **kw):
    kw.setdefault("ha", "center"); kw.setdefault("va", "center")
    return ax.text(x, y, s, fontsize=size, color=col, zorder=z, **kw)


def echelle_graphique(ax, x0, y0, n=4, pas=1.0):
    h = mm(ax, 1.2)
    for k in range(n):
        ax.add_patch(Rectangle((x0 + k * pas, y0), pas, h, fc=ENCRE if k % 2 == 0 else "white", ec=ENCRE,
                               lw=D.LW[1], zorder=300, clip_on=False))
        ax.text(x0 + k * pas, y0 - mm(ax, 0.8), str(int(k * pas)) if pas >= 1 else fr(k * pas, 1), fontsize=4.6,
                color=TAUPE, ha="center", va="top", clip_on=False)
    ax.text(x0 + n * pas, y0 - mm(ax, 0.8), f"{int(n * pas) if pas >= 1 else fr(n * pas, 1)} m", fontsize=4.6,
            color=TAUPE, ha="center", va="top", clip_on=False)


# --- styles de remplissage ----------------------------------------------------------------------
CONTEXTE = ("logements", "voisin", "fenetre_logt", "sol_ext", "trottoir", "arbre")


OMBRE = "#000000"


def oriente(g):
    """Polygones orientés (extérieur direct, trous indirects) : remplissage matplotlib non nul correct pour les trous."""
    ps = [shapely.geometry.polygon.orient(q, 1.0) for q in shapely.get_parts(g) if q.geom_type == "Polygon" and q.area > 0]
    return shapely.MultiPolygon(ps) if ps else None
from ombres import OMBRE_ALPHA, calculer_ombres  # noqa: E402
from vegetation import VEG, est_feuillage, est_vegetal, touffe, arbre_plan, arbre_elev  # noqa: E402


def remplissage(r, it, mode="plan"):
    ro = r["role"]
    if ro == "logements":
        return "white"
    if ro == "voisin":
        return "#F0F0F0"
    if ro in ("sol_ext",):
        return "#F3F3F3"
    if ro == "trottoir":
        return "#E8E8E8"
    if ro == "fenetre_logt":
        return "#E7ECEE"
    if ro == "arbre":
        return D.eclaircir((0.37, 0.48, 0.29), 0.35)
    if ro == "vitrage":
        return VERRE
    k = {"sol": 0.30, "plafond": 0.40, "revetement": 0.45, "structure": 0.25, "cloison": 0.3}.get(ro, 0.42)
    return sourdine(D.eclaircir(it["rgba"], k))


def sourdine(rgb, garde=0.4):
    """Charte v2 : matières en sourdine sur papier blanc (garde 40 % de la saturation)."""
    rgb = np.asarray(rgb[:3], float); g = rgb @ np.array([0.299, 0.587, 0.114])
    return tuple(g + (rgb - g) * garde)


def peindre(ax, R, mode="plan", trait_items=True, z0=10, ombre=None, veg="plan"):
    """Algorithme du peintre : items remplis (trait fin), silhouette produit (trait moyen).
    ombre : polygones d'ombre portée (ombres.py), peints sur chaque aplat, sous son trait."""
    z = z0
    if ombre is not None:
        shapely.prepare(ombre)
    for r in R:
        ctx = r["role"] in CONTEXTE
        ec = TAUPE if ctx else ENCRE
        for it in r["items"]:
            if est_feuillage(it) and r["role"] != "arbre":
                touffe(ax, it["g"], z, veg)          # végétation : symbole au trait, pas d'aplat vert
            elif r["role"] == "vitrage":
                D.patch(ax, it["g"], fc=VERRE, ec=ENCRE, lw=D.LW[1], z=z, alpha=0.55)
            elif ombre is not None and ombre.intersects(it["g"]):
                D.patch(ax, it["g"], fc=remplissage(r, it, mode), ec="none", z=z)
                D.patch(ax, oriente(ombre.intersection(it["g"])), fc=OMBRE, ec="none", lw=0, z=z + 0.0002, alpha=OMBRE_ALPHA)
                D.patch(ax, it["g"], fc="none", ec=ec if trait_items else "none", lw=D.LW[1] * (0.7 if ctx else 1), z=z + 0.0004)
            else:
                D.patch(ax, it["g"], fc=remplissage(r, it, mode), ec=ec if trait_items else "none", lw=D.LW[1] * (0.7 if ctx else 1), z=z)
            z += 0.001
        tout = r["tout"]
        if tout is not None and est_vegetal(r["e"]):     # contour fort sur le pot / la maçonnerie seulement
            mn = [it["g"] for it in r["items"] if not est_feuillage(it)]
            fo = [it["g"] for it in r["items"] if est_feuillage(it)]
            tout = unary_union(mn) if mn else None
            if tout is not None and fo and tout.difference(unary_union(fo)).area < 0.05 * tout.area:
                tout = None                                   # pot caché sous le feuillage (plan)
        if tout is not None and not ctx and r["role"] not in ("sol", "vitrage"):
            D.patch(ax, tout, fc="none", ec=ENCRE, lw=D.LW[2], z=z)
        z += 0.001
    return z


def pocher(ax, R, z=60):
    """Éléments coupés : poché noir (porteurs), gris (cloisons), teinte matériau (le reste) — trait fort."""
    for r in R:
        g = r["coupe"]
        if g is None:
            continue
        ro = r["role"]
        if est_vegetal(r["e"]):        # jardinière / plante : feuillage coupé au trait, seule la maçonnerie est pochée
            mineral = [(c, k) for c, k in r.get("coupes", []) if not est_feuillage(dict(rgba=k))]
            if mineral:
                col = np.mean([k for it in r["e"]["items"] for k in [it[1].mean(0)] if not est_feuillage(dict(rgba=k))], axis=0)
                D.patch(ax, unary_union([c for c, _ in mineral]), fc=D.eclaircir(col, 0.75), ec=ENCRE, lw=D.LW[2], z=z + 1)
            continue
        if ro == "structure":
            D.patch(ax, g, fc=POCHE, ec=POCHE, lw=D.LW[4], z=z + 2)
        elif ro == "cloison":
            D.patch(ax, g, fc=GRIS_CLOISON, ec=ENCRE, lw=D.LW[4], z=z + 1.5)
        elif ro == "voisin":
            D.patch(ax, g, fc="white", ec=TAUPE, lw=D.LW[2], z=z, hatch="////")
        elif ro == "logements":
            D.patch(ax, g, fc="white", ec="#B9B0A6", lw=D.LW[1], z=z, hatch="\\\\")
        elif ro in ("sol_ext", "trottoir"):
            D.patch(ax, g, fc="#D8D2CA", ec=TAUPE, lw=D.LW[2], z=z)
        elif ro == "vitrage":
            D.patch(ax, g, fc=VERRE, ec=ENCRE, lw=D.LW[1], z=z + 1)
        else:
            col = r["items"][0]["rgba"] if r["items"] else (0.7, 0.6, 0.5, 1)
            if r["e"]["items"]:
                col = np.mean([c.mean(0) for _, c in r["e"]["items"]], axis=0)
            D.patch(ax, g, fc=D.eclaircir(col, 0.75), ec=ENCRE, lw=D.LW[2] if ro != "plafond" else D.LW[2], z=z + 1)


def centre(g):
    if g is None:
        return None
    p = g.representative_point() if g.geom_type != "Polygon" else shapely.ops.polylabel(g, 0.005) if g.area > 1e-4 else g.centroid
    return p.x, p.y


def bulles_reperes(ax, R, liste, decal=None, extra=None):
    """Une pastille par repère (sur le plus grand produit visible), position éventuellement décalée."""
    decal = decal or {}
    vus = {}
    for r in R:
        n = r["e"]["repere"]
        n = None if n is None else int(n)
        if n is None or n not in liste:
            continue
        g = r["tout"] if r["tout"] is not None else r["coupe"]
        if g is None:
            continue
        if n not in vus or g.area > vus[n][1]:
            vus[n] = (g, g.area)
    for n, (g, _) in (extra or {}).items():
        vus[n] = (g, 0)
    for n, (g, _) in vus.items():
        c = centre(g)
        if n in decal:
            d = decal[n]
            if len(d) == 2:
                bulle(ax, c[0] + d[0], c[1] + d[1], n, vers=c)
            else:
                bulle(ax, d[0], d[1], n, vers=(d[2], d[3]) if len(d) == 4 else None)
        else:
            bulle(ax, *c, n)
    return sorted(vus)


def codes_mobilier(ax, R, z=410, decal=None):
    decal = decal or {}
    vus = {}
    for r in R:
        code, nom = D.code_mobilier(r["e"])
        if code is None:
            continue
        g = r["tout"] if r["tout"] is not None else r["coupe"]
        if g is None:
            continue
        x, y = centre(g)
        dx, dy = decal.get(code, (0, 0))
        ax.text(x + dx, y + dy, code, fontsize=3.6, color="white", ha="center", va="center", zorder=z,
                bbox=dict(boxstyle="round,pad=0.18", fc=IROKO, ec="none"))
        vus.setdefault(code, [nom, 0]); vus[code][1] += 1
    return vus


def espaces_ifc():
    f = ifcopenshell.open(V5_IFC)
    s = ifcopenshell.geom.settings(); s.set("use-world-coords", True)
    out = []
    for sp in f.by_type("IfcSpace"):
        g = ifcopenshell.geom.create_shape(s, sp).geometry
        v = np.array(g.verts).reshape(-1, 3) / 100.0 if max(g.verts) > 50 else np.array(g.verts).reshape(-1, 3)
        fc = np.array(g.faces).reshape(-1, 3)
        poly = D.silhouette(v[fc][:, :, :2])
        out.append((sp.Name, sp.LongName, poly))
    return out


def etiquettes_espaces(ax, pos=None, size=6.0, petits=("05",)):
    pos = pos or {}
    for num, nom, g in espaces_ifc():
        e = ESPACES.get(nom)
        x, y = pos.get(num, centre(g))
        if num in petits:
            label(ax, x, y, f"{num}  {fr(float(e['surface_m2']))} m²", size=3.6, col=TERRE_CUITE, z=420)
            continue
        court = nom.replace(" (pergola V4)", "")
        label(ax, x, y + mm(ax, 1.6), court, size=size, z=420)
        label(ax, x, y - mm(ax, 1.4), f"{fr(float(e['surface_m2']), 1)} m²", size=size - 0.6, col=TERRE_CUITE, z=420)


def legende_espaces(p):
    p.intertitre("Espaces (IfcSpace)")
    for k, (num, nom, _) in enumerate(espaces_ifc()):
        e = ESPACES[nom]
        p.T(p.px + 8, p.y, num, 5.9, TERRE_CUITE, fontproperties=FP_MEDIUM)
        p.T(p.px + 15, p.y, nom, 5.9)
        p.T(W - 34, p.y, f"{fr(float(e['surface_m2']))} m²", 5.9, ha="right")
        p.T(W - 12, p.y, "HSP " + e["hsp_m"].split(" ")[0].replace(".", ","), 5.4, TAUPE, ha="right")
        p.y += 3.7
    tot = sum(float(ESPACES[n]["surface_m2"]) for _, n, _ in espaces_ifc() if ESPACES[n]["type"] == "SPACE")
    p.T(p.px + 15, p.y, "Total intérieur (hors terrasse)", 5.9, fontproperties=FP_MEDIUM)
    p.T(W - 34, p.y, f"{fr(tot)} m²", 5.9, ha="right", fontproperties=FP_MEDIUM)
    p.y += 5


def legende_reperes(p, nums, n_col=1):
    p.intertitre("Repères de l'aménagement V5")
    w = (W - 18 - p.px) / n_col
    for k, n in enumerate(nums):
        lib = REPERES[n]
        if n_col > 1 and len(lib) > 46:
            lib = lib[:44] + "…"
        p.pastille(str(n), lib, ENCRE, n_col, k % n_col, w)
    if len(nums) % n_col:
        p.y += 3.7
    p.y += 1.5


def legende_mobilier(p, vus, n_col=2):
    p.intertitre("Mobilier (repères V4 conservés)")
    w = (W - 18 - p.px) / n_col
    items = sorted(vus.items())
    for k, (code, (nom, cnt)) in enumerate(items):
        p.pastille(code, f"{nom.title()} × {cnt}", IROKO, n_col, k % n_col, w)
    if len(items) % n_col:
        p.y += 3.7
    p.y += 1.5


def legende_graphique(p, kinds):
    p.intertitre("Légende")
    for k in kinds:
        p.symbole(*k[:2], **(k[2] if len(k) > 2 else {}))
    p.y += 1.5


# --- filtres --------------------------------------------------------------------------------------
def bb(e):
    return e["verts"].min(0), e["verts"].max(0)


def est(e, *mots):
    return any(m.lower() in e["nom"].lower() for m in mots)


# =========================================================================================
def A01(sc):
    p = Planche("A01", "Plan du rez-de-chaussée — aménagement", "Esquisse V5 sur existant V4  ·  Échelle 1/50 (A3)  ·  Plan de coupe à +1,00", px=255)
    xl, yl = (-1.25, 11.0), (-5.0, 8.3)
    ax = p.axes(6, 10, xl, yl, 50)
    v = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0), coupe=((0, 0, 1), 1.0003))
    R = D.calculer(sc, v, lambda e, r: r not in ("logements", "fenetre_logt"))
    ax.add_patch(Rectangle((xl[0], yl[0]), xl[1] - xl[0], -3.8 - yl[0] - 0.05, fc="#DCD8D2", ec="none", zorder=1))
    label(ax, 3.3, -4.45, "R U E", size=6.5, col=TAUPE, z=500)
    peindre(ax, R, ombre=calculer_ombres(R, v, ax.get_xlim(), ax.get_ylim(), "plan"))
    pocher(ax, R)
    # au-dessus du plan de coupe (tirets)
    for e in sc:
        r = role(e)
        lo, hi = bb(e)
        dessus = lo[2] > 1.0 and r not in ("logements", "fenetre_logt", "luminaire", "arbre") and e["classe"] != "IfcSlab" and r != "plafond" \
            and not est(e, "Rail", "Réservation", "Chemin", "Liaisons", "Retombée", "pompe", "Enseigne", "Panneau passe")
        if dessus:
            g = D.contour_complet(e, v)
            if est(e, "Pergola"):
                g = g.convex_hull
            D.patch(ax, g, fc="none", ec=TAUPE if r == "arbre" else ENCRE, lw=D.LW[1], ls=(0, (5, 3)), z=80)
    # arbres d'alignement : symbole d'architecte (houppier festonné, charpentières, tronc), emprise des houppiers IFC
    tr = next(e for e in sc if role(e) == "arbre" and bb(e)[1][2] - bb(e)[0][2] > 3.0)
    tlo, thi = bb(tr)
    for e in sc:
        if role(e) == "arbre" and e is not tr:
            lo, hi = bb(e)
            cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            sur_tronc = abs(cx - (tlo[0] + thi[0]) / 2) < 0.3 and abs(cy - (tlo[1] + thi[1]) / 2) < 0.3
            arbre_plan(ax, cx, cy, (hi[0] - lo[0]) / 2, 80, tronc=0 if sur_tronc else None)   # tronc IFC déjà dessiné (coupé)
    arbre = next(e for e in sc if "Arbre_a_livres" in e["nom"])
    D.patch(ax, D.contour_complet(arbre, v), fc="none", ec=ENCRE, lw=D.LW[1], ls=(0, (5, 3)), z=80)
    etiquettes_espaces(ax, {"01": (4.15, 1.30), "02": (1.05, 1.55), "03": (2.20, 3.85), "04": (1.25, 6.05), "05": (0.83, 4.93),
                            "06": (2.35, 5.45), "07": (2.00, 6.95), "08": (3.40, -1.15)})
    # coupe AA
    ax.plot([4.75, 4.75], [-3.2, -2.95], color=TERRE_CUITE, lw=D.LW[4], zorder=500)
    ax.plot([4.75, 4.75], [7.85, 8.10], color=TERRE_CUITE, lw=D.LW[4], zorder=500)
    for yy in (-3.08, 7.97):
        ax.annotate("", xy=(4.40, yy), xytext=(4.75, yy), arrowprops=dict(arrowstyle="-|>", color=TERRE_CUITE, lw=D.LW[2]), zorder=500)
        label(ax, 4.95, yy, "A", size=7, col=TERRE_CUITE)
    # cotes
    cote(ax, -0.09, 6.69, 7.95, "6,78", ext=7.59)
    cote(ax, -0.09, 7.59, 7.35, "7,68", horiz=False, ext=6.69)
    cote(ax, -2.75, -0.09, 7.35, "2,66", horiz=False, ext=6.65)
    cote(ax, 1.64, 2.64, 0.95, "1,00 libre", col=OLIVE, size=4.4)
    ax.add_patch(Rectangle((1.64, 0.12), 1.0, 0.60, fc="none", ec=OLIVE, lw=D.LW[1], ls=(0, (2, 2)), zorder=90))
    D.patch(ax, Point(*ARBRE).buffer(R_OCULUS), fc="none", ec=INDIGO, lw=D.LW[1], ls=(0, (1.5, 2)), z=81)
    vus = bulles_reperes(ax, R, [3, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 27, 33], decal={
        3: (-0.65, 0.95), 7: (4.0, 3.55, 4.0, 3.85), 8: (2.55, 2.25, 2.4, 2.0), 9: (0.0, 0.0), 10: (-0.25, 0.4), 11: (0.0, -0.75),
        12: (0.0, -0.75), 13: (0.0, -1.1), 14: (0.55, -0.55), 15: (0.0, 0.42), 16: (0.0, -0.45), 17: (0.0, 0.45),
        18: (0.45, 0.55), 27: (-0.5, 0.35), 33: (0.5, 0.25)},
        extra={14: (D.contour_complet(next(e for e in sc if est(e, "Marquise")), v), 0),
               27: (D.contour_complet(next(e for e in sc if est(e, "Split mural") and "1" in e["nom"][-2:]), v), 0)})
    bulle(ax, 5.95, 6.70, 6, vers=(5.85, 6.45))
    label(ax, 6.05, -0.75, "Pergola V4 (projection)", size=4.6, col=TAUPE, ha="right")
    label(ax, 10.0, -5.2 + 0.6, "Arbres d'alignement", size=4.6, col=TAUPE)
    label(ax, -0.75, 3.5, "BÂTIMENT MITOYEN", size=4.6, col=TAUPE, rotation=90)
    label(ax, 9.0, -3.3, "TROTTOIR", size=5, col=TAUPE)
    label(ax, 3.92, -0.32, "ENTRÉE", size=4.4, col=TERRE_CUITE)
    mob = codes_mobilier(ax, R, decal={"V01": (0.0, 0.0)})
    echelle_graphique(ax, 7.0, -1.6, 4)
    legende_espaces(p)
    legende_reperes(p, sorted(set(vus) | {6}), n_col=2)
    legende_mobilier(p, mob, n_col=3)
    legende_graphique(p, [("poche", "Existant porteur coupé (V4 inchangé, ne pas toucher)"),
                          ("cloison", "Cloison légère coupée (V4 et V5)"),
                          ("coupe", "Mobilier, menuiseries, revêtements coupés", dict(fc=D.eclaircir((0.6, 0.42, 0.26), 0.75))),
                          ("trait", "Au-dessus du plan de coupe (marquise, pergola, canopée, split)", dict(ls=(0, (5, 3)))),
                          ("trait", "Oculus Ø 2,80 sous dalle (indigo)", dict(ls=(0, (1.5, 2)), color=INDIGO)),
                          ("trait", "Dégagement 1,00 m devant le tableau divisionnaire", dict(ls=(0, (2, 2)), color=OLIVE))])
    p.cartouche("1/50")
    p.enregistrer("plan_RDC")


def A02(sc):
    p = Planche("A02", "Plan de faux-plafond et réseaux", "Vu de dessous (plan réfléchi)  ·  Échelle 1/50 (A3)  ·  Coupe à +2,00", px=255)
    xl, yl = (-1.25, 11.0), (-3.4, 8.3)
    ax = p.axes(6, 16, xl, yl, 50)
    v = D.Vue((0, 0, 1), (1, 0, 0), (0, 1, 0), coupe=((0, 0, -1), -2.0003))
    garder = lambda e, r: r not in ("logements", "fenetre_logt", "sol_ext", "trottoir", "arbre", "sol") and e["classe"] != "IfcSlab"
    R = D.calculer(sc, v, garder)
    z = peindre(ax, R, ombre=calculer_ombres(R, v, ax.get_xlim(), ax.get_ylim(), "plan"))
    pocher(ax, R)
    # trame des dalles acoustiques 0,60 x 0,60
    plaf = unary_union([r["tout"] for r in R if r["role"] == "plafond" and "acoustique" in r["e"]["nom"]])
    plaf = plaf.difference(Point(*ARBRE).buffer(R_OCULUS + 0.06))
    lignes = [LineString([(x, -0.2), (x, 7.6)]) for x in np.arange(0.09, 6.6, 0.60)] + \
             [LineString([(-0.1, y), (6.7, y)]) for y in np.arange(0.09, 7.5, 0.60)]
    for l in lignes:
        g = l.intersection(plaf)
        for s in shapely.get_parts(g):
            if s.geom_type == "LineString":
                ax.plot(*np.asarray(s.coords).T, color=TAUPE, lw=D.LW[1] * 0.6, zorder=z + 0.5)
    # réseaux en plénum (tracé complet, tiretés de couleur)
    for e in sc:
        c = e["classe"]
        col = {"IfcPipeSegment": INDIGO, "IfcCableCarrierSegment": TERRE_CUITE}.get(c)
        if est(e, "Descente"):
            col = OLIVE
        if est(e, "Réservation"):
            col = ENCRE
        if col is None:
            continue
        for fc, _ in e["items"]:
            g = D.silhouette(v.to2d(e["verts"][fc]))
            D.patch(ax, g, fc=col if est(e, "Réservation") else "none", ec=col, lw=D.LW[2], z=150,
                    ls="-" if est(e, "Réservation", "Descente") else (0, (4, 1.5)))
    for e in sc:
        if est(e, "Réservation"):
            lo, hi = bb(e)
            cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            nom = e["nom"].split(" ")[1]
            dx, dy = {"R1": (0.25, -0.35), "R2": (-0.30, -0.35), "R3": (0.25, 0.35), "R4": (-0.25, 0.35), "R5": (0.0, -0.32)}[nom]
            label(ax, cx + dx, cy + dy, nom, size=5.0, col=ENCRE, z=420)
    ext = {}
    for n, mot in ((32, "Panneau passe"), (31, "Réservation R3"), (29, "split 1"), (30, "Chemin de câbles tableau"), (28, "pompe de relevage des condensats - split 1"),
                   (22, "Anneau LED indirect"), (6, "Oculus")):
        e = next(e for e in sc if est(e, mot) and (n != 29 or e["classe"] == "IfcPipeSegment"))
        ext[n] = (D.contour_complet(e, v), 0)
    vus = bulles_reperes(ax, R, [2, 4, 5, 19, 20, 21, 23, 24, 25, 26, 27, 33], extra=ext, decal={
        2: (0.0, 0.0), 4: (5.75, 2.55, 5.75, 2.35), 5: (1.05, 6.85, 1.05, 6.85), 6: (6.10, 3.95, 5.85, 4.5),
        19: (0.45, 0.35), 20: (0.0, 0.32), 21: (0.35, 0.3), 22: (3.55, 4.05, 3.75, 4.55), 23: (0.0, 0.0),
        24: (0.0, 0.4), 25: (-0.4, -0.35), 26: (0.45, 0.0), 27: (-0.45, 0.0), 28: (6.15, 6.25, 6.43, 5.28),
        29: (5.60, 6.60, 5.65, 7.15), 30: (4.20, 1.25, 4.40, 0.48), 31: (4.25, 8.05, 4.85, 7.55), 32: (5.45, 8.05, 5.05, 7.45),
        33: (0.55, 0.0)})
    label(ax, 4.75, 8.05, "Baie arrière existante (V4)", size=4.4, col=TAUPE)
    for (x, y, s) in ((4.2, 0.30, "+3,00 sous-face FP acoustique"), (1.5, 7.18, "+3,00 FP hydrofuge"),
                      (4.75, 4.85, "+3,30 sous-face dalle (oculus)")):
        label(ax, x, y, s, size=4.2, col=TAUPE, z=430)
    label(ax, 3.35, -1.6, "Terrasse : pergola bois V4 conservée (+2,90 à +3,32)", size=4.6, col=TAUPE)
    cote(ax, -0.09, 6.69, 7.95, "6,78", ext=7.59)
    cote(ax, -0.09, 7.59, 7.35, "7,68", horiz=False, ext=6.69)
    echelle_graphique(ax, 6.9, 7.0, 4)
    p.intertitre("Principes (hypothèses ESQ Ahoua)")
    for s in ["Faux-plafond acoustique +3,00 (dalles 0,60, ép. 40 mm) ; plénum 0,26 sous dalle haute (minimum 0,25).",
              "Aucun percement dans poteaux, voiles ni dalle haute : liaisons splits et câbles",
              "cheminent en plénum puis dans le doublage des niches, et sortent par la baie arrière",
              "EXISTANTE (imposte : panneau passe-liaisons 32, réservations R3, R4 Ø 0,10).",
              "Splits 9 000 BTU/h en partie haute de murs pleins, hors aplomb des tables ;",
              "condensats relevés par mini-pompe (pas d'évacuation gravitaire possible).",
              "Câbles : placard technique › plénum (R5 dans cloison placo) › tableau divisionnaire.",
              "Descentes EU/EV de l'immeuble : coffrages 0,30 × 0,30, position à relever sur site."]:
        p.ligne(s, 5.7, dy=3.5)
    p.y += 2
    legende_reperes(p, sorted(set(vus) | {22, 28, 29, 30, 31, 32}), n_col=1)
    legende_graphique(p, [("poche", "Existant porteur coupé à +2,00"),
                          ("aplat", "Faux-plafond acoustique, trame 0,60", dict(fc=D.eclaircir((0.93, 0.91, 0.86), 0.4))),
                          ("trait", "Liaisons frigorifiques + condensats (plénum, doublage)", dict(color=INDIGO, ls=(0, (4, 1.5)), lw=D.LW[2])),
                          ("trait", "Chemin de câbles 80 × 40 en plénum", dict(color=TERRE_CUITE, ls=(0, (4, 1.5)), lw=D.LW[2])),
                          ("trait", "Descente EU/EV Ø 100 en coffrage (hypothèse)", dict(color=OLIVE, lw=D.LW[2]))])
    p.cartouche("1/50")
    p.enregistrer("plan_faux_plafond_reseaux")


def A03(sc):
    p = Planche("A03", "Coupe AA sur l'arbre à livres", "Coupe x = 4,75 vers l'ouest  ·  Échelle 1/50 (A3)  ·  Logements existants esquissés", px=290)
    xl, zl = (-4.3, 8.6), (-0.75, 11.95)
    ax = p.axes(10, 12, xl, zl, 50)
    v = D.Vue((-1, 0, 0), (0, 1, 0), (0, 0, 1), coupe=((1, 0, 0), 4.7503))
    R = D.calculer(sc, v, lambda e, r: r not in ("sol_ext", "arbre", "voisin"))
    ax.add_patch(Rectangle((xl[0], zl[0]), xl[1] - xl[0], -0.2 - zl[0], fc="#E2DDD6", ec="none", zorder=1))
    ax.plot(xl, [-0.2, -0.2], color=ENCRE, lw=D.LW[2], zorder=2)
    peindre(ax, R, ombre=calculer_ombres(R, v, ax.get_xlim(), ax.get_ylim(), "int"), veg="elev")
    pocher(ax, R)
    for zz in (6.60, 9.90):
        ax.plot([-0.09, 7.59], [zz, zz], color=TAUPE, lw=D.LW[1], ls=(0, (6, 3)), zorder=95)
    label(ax, 3.75, 7.9, "LOGEMENTS EXISTANTS (hors lot, volumétrie V4 esquissée)", size=5.4, col=TAUPE, z=420)
    for zz, t in ((0.0, "±0,00 sol fini RDC"), (Z_FP_SOUS, "+3,00 sous-face faux-plafond"), (Z_DALLE_SOUS, "+3,30 sous-face dalle (à relever)"),
                  (Z_DALLE_DESSUS, "+3,50 plancher logements (hyp.)"), (6.60, "+6,60 N02"), (11.40, "+11,40 acrotère (V4)")):
        niveau(ax, 7.95, zz, t)
    cote(ax, 0.0, Z_FP_SOUS, 1.1, "HSP 3,00")
    cote(ax, Z_FP_DESSUS, Z_DALLE_SOUS, 2.2, "plénum 0,26", size=4.4)
    cote(ax, Z_DALLE_SOUS, Z_DALLE_DESSUS, 0.55, "0,20 hyp.", size=4.2)
    cote(ax, -0.09, 7.59, -0.55, "7,68", ext=-0.2)
    cote(ax, -2.75, -0.09, -0.55, "2,66", ext=-0.2)
    vus = bulles_reperes(ax, R, [1, 4, 6, 9, 10, 13, 14, 22, 23, 29, 31, 32], decal={
        1: (-1.6, 0.25), 4: (0.0, -0.32), 6: (-0.85, 0.42), 9: (0.0, 0.0), 13: (0.0, 0.0), 14: (0.0, 0.45), 22: (-0.4, 0.38),
        23: (0.75, -0.25), 29: (6.55, 3.85, 6.9, 3.17), 31: (7.85, 2.40, 7.5, 2.70), 32: (8.05, 2.95, 7.45, 2.72), 10: (0.0, 0.0)},
        extra={29: (Point(6.9, 3.17).buffer(0.01), 0), 31: (Point(7.5, 2.70).buffer(0.01), 0), 32: (Point(7.44, 2.68).buffer(0.01), 0)})
    label(ax, -1.45, 1.05, "TERRASSE", size=5.2, col=TAUPE, z=420)
    label(ax, -3.3, 0.25, "TROTTOIR", size=5.0, col=TAUPE, z=420)
    label(ax, 3.9, 1.5, "SALLE DE LECTURE", size=5.2, col=ENCRE, z=420)
    label(ax, 6.95, 1.35, "Niches", size=4.6, col=TAUPE, z=420)
    echelle_graphique(ax, -4.0, 10.6, 4)
    p.intertitre("Lecture de la coupe")
    for s in ["Gros œuvre V4 repris tel quel (GlobalId, placements, géométrie : écarts nuls).",
              "Dalle haute absente de la V4 : ajoutée sans modifier l'emprise (rep. 1),",
              "épaisseur 0,20 en hypothèse ; elle double la base du volume « logements » V4.",
              "Faux-plafond acoustique abaissé à +3,00 : plénum 0,26 (minimum exigé 0,25).",
              "Oculus Ø 2,80 autour de l'arbre à livres : sous-face de dalle laquée indigo,",
              "bandeau iroko et anneau LED indirect 2700 K (rep. 6, 22).",
              "Liaisons split en plénum › doublage cintré des niches › imposte de la baie",
              "arrière existante (panneau 32, réservations R3/R4 Ø 0,10) : aucune traversée",
              "de poteau, voile ou dalle."]:
        p.ligne(s, 5.9, dy=3.6)
    p.y += 2
    legende_reperes(p, sorted(vus), n_col=1)
    legende_graphique(p, [("poche", "Existant porteur coupé et dalle haute (hypothèse)"),
                          ("coupe", "Logements existants (volumétrie V4, hors lot)", dict(fc="white", hatch="\\\\\\\\")),
                          ("trait", "Planchers des logements (esquisse)", dict(color=TAUPE, ls=(0, (6, 3))))])
    p.cartouche("1/50")
    p.enregistrer("coupe_AA")


def A04(sc):
    p = Planche("A04", "Élévation de la devanture sur rue", "Vue depuis la rue  ·  Échelle 1/50 (A3)  ·  Logements existants esquissés au-dessus", px=290)
    xl, zl = (-1.6, 11.6), (-0.95, 11.9)
    ax = p.axes(8, 14, xl, zl, 50)
    v = D.Vue((0, 1, 0), (1, 0, 0), (0, 0, 1), coupe=((0, -1, 0), 2.95))
    R = D.calculer(sc, v, lambda e, r: r not in ("sol_ext", "trottoir", "arbre"))
    ax.add_patch(Rectangle((xl[0], zl[0]), xl[1] - xl[0], -0.12 - zl[0], fc="#DCD8D2", ec="none", zorder=1))
    ax.add_patch(Rectangle((xl[0], -0.12), xl[1] - xl[0], 0.12, fc="#EDEAE5", ec=TAUPE, lw=D.LW[1], zorder=2))
    ax.plot(xl, [-0.12, -0.12], color=ENCRE, lw=D.LW[4], zorder=3)
    peindre(ax, R, ombre=calculer_ombres(R, v, ax.get_xlim(), ax.get_ylim(), "elev"), veg="elev")
    pocher(ax, R)
    # arbres d'alignement (devant le plan de coupe : silhouettes en traits fins)
    va = D.Vue((0, 1, 0), (1, 0, 0), (0, 0, 1))
    tronc, houppiers = None, []
    for e in sc:
        if role(e) == "arbre":
            lo, hi = bb(e)
            if hi[2] - lo[2] > 3.0:
                tronc = (lo[0], hi[0], 0.0, hi[2])
            else:
                houppiers.append(((lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2, hi[0] - lo[0], hi[2] - lo[2] + 0.6))
    arbre_elev(ax, tronc, houppiers, 200)
    for zz in (6.60, 9.90):
        ax.plot([-0.09, 6.69], [zz, zz], color=TAUPE, lw=D.LW[1], ls=(0, (6, 3)), zorder=95)
    label(ax, 3.3, 10.6, "LOGEMENTS EXISTANTS (hors lot, esquisse)", size=5.4, col=TAUPE, z=420)
    label(ax, -0.95, 6.0, "MITOYEN", size=5.0, col=TAUPE, rotation=90, z=420)
    label(ax, 10.1, -0.55, "TROTTOIR / RUE", size=5.0, col=TAUPE, z=420)
    for zz, t in ((0.0, "±0,00"), (Z_DALLE_SOUS, "+3,30"), (6.60, "+6,60"), (9.90, "+9,90"), (11.40, "+11,40")):
        niveau(ax, 7.2, zz, t)
    cote(ax, -0.09, 6.69, -0.70, "6,78", ext=-0.12)
    cote(ax, 0.0, 3.30, -0.45, "3,30", horiz=False)
    vus = bulles_reperes(ax, R, [11, 12, 13, 14, 24, 26], decal={11: (0.0, 0.85), 12: (0.0, 0.0), 13: (0.0, -0.35), 14: (0.0, 0.45),
                                                                 24: (-0.25, 0.25), 26: (0.4, 0.0)},
                         extra={11: (D.contour_complet(next(e for e in sc if est(e, "Vitrine en arche")), va), 0),
                                12: (D.contour_complet(next(e for e in sc if est(e, "baie C") and e["classe"] == "IfcMember"), va), 0),
                                13: (D.contour_complet(next(e for e in sc if est(e, "Inserts Adinkra") and est(e, "baie C")), va), 0),
                                24: (D.contour_complet(next(e for e in sc if est(e, "Réglette")), va), 0),
                                26: (D.contour_complet(next(e for e in sc if est(e, "sous marquise")), va), 0)})
    label(ax, 3.92, 3.45, "Portail terre cuite et enseigne V4", size=4.4, col=TAUPE, z=420)
    echelle_graphique(ax, -1.4, 11.2, 4)
    p.intertitre("Devanture (dans les baies V4 existantes)")
    for s in ["Baies cintrées A, B, C et portail d'entrée : ouvertures V4 inchangées.",
              "A — vitrine en arche : châssis acier noir posé derrière le vitrage V4 (rep. 11),",
              "     podium iroko à hauteur d'allège ; claustra V4 maintenu en avant (point ouvert).",
              "B, C — châssis fixes acier noir fins (rep. 12).",
              "Claustras terre cuite V4 conservés ; motifs géométriques d'inspiration Adinkra",
              "ajoutés en inserts : Adinkrahene (cercles concentriques) dans les anneaux,",
              "Eban (carrés emboîtés) dans les interstices (rep. 13).",
              "Marquise acier noir fine au-dessus de la porte cintrée, débord 0,60 (rep. 14).",
              "Pergola bois V4, jardinières et mobilier de terrasse conservés (vus en coupe à",
              "y = −2,95, au droit du trottoir)."]:
        p.ligne(s, 5.9, dy=3.6)
    p.y += 2
    legende_reperes(p, sorted(vus), n_col=1)
    legende_graphique(p, [("poche", "Coupé (poteaux de pergola, plan y = −2,95)"),
                          ("aplat", "Terre cuite (portail, claustras)", dict(fc=D.eclaircir((0.70, 0.35, 0.24), 0.42))),
                          ("aplat", "Iroko (pergola, menuiseries)", dict(fc=D.eclaircir((0.60, 0.42, 0.26), 0.42))),
                          ("verre", "Vitrage V4"),
                          ("trait", "Arbres d'alignement (contexte V4), végétation au trait", dict(color=VEG))])
    p.cartouche("1/50")
    p.enregistrer("elevation_devanture")


def _elev(p, sc, ax, v, garder, decal_rep, nums, titre, x_titre, y_titre):
    R = D.calculer(sc, v, garder)
    peindre(ax, R, ombre=calculer_ombres(R, v, ax.get_xlim(), ax.get_ylim(), "int"), veg="elev")
    pocher(ax, R)
    vus = bulles_reperes(ax, R, nums, decal=decal_rep)
    p.T(x_titre, y_titre, titre, 7.5, ENCRE, fontproperties=FP_MEDIUM)
    return R, vus


def A05(sc):
    p = Planche("A05", "Élévations intérieures Est et Nord", "Salle de lecture  ·  Échelle 1/30 (A3)", px=290)
    # Est : on regarde vers +x, coupe x = 3,30, gauche = fond (y = 7,6), droite = façade
    ax = p.axes(14, 18, (-7.75, 0.35), (-0.25, 3.62), 30)
    v = D.Vue((1, 0, 0), (0, -1, 0), (0, 0, 1), coupe=((-1, 0, 0), -3.3003))
    keep = lambda e, r: r not in CONTEXTE and bb(e)[0][1] >= -0.15 and (bb(e)[0][0] >= 5.5 or r in ("structure", "cloison", "plafond", "sol", "revetement"))
    R1, v1 = _elev(p, sc, ax, v, keep, {27: (0.0, 0.32), 9: (-6.6, 1.7, -6.8, 1.4), 4: (-1.2, 3.25, -1.2, 3.02), 6: (-5.1, 3.45, -5.2, 3.2),
                                        21: (0.0, -0.18), 28: (0.3, 0.1), 30: (0.0, 0.0), 1: (-3.6, 3.48, -3.6, 3.40)},
                   [1, 4, 6, 9, 21, 27, 28, 30], "Élévation intérieure Est — mur mitoyen enduit terre", 14, 13)
    ax.plot([-7.75, 0.35], [0, 0], color=ENCRE, lw=D.LW[4], zorder=90)
    for zz, t in ((0.0, "±0,00"), (Z_FP_SOUS, "+3,00"), (Z_DALLE_SOUS, "+3,30")):
        niveau(ax, 0.30, zz, t)
    cote(ax, -5.35, -4.55, 2.95, "split 0,80", size=4.2)
    cote(ax, 0.0, 2.42, -5.0, "2,42", horiz=False, size=4.2)
    label(ax, -7.45, 0.25, "Niches", size=4.6, col=TAUPE, z=420)
    label(ax, -0.2, 0.25, "Façade", size=4.6, col=TAUPE, z=420)
    label(ax, -3.75, 1.3, "Poteau existant\n(ne pas toucher)", size=4.4, col=ENCRE, z=420)
    echelle_graphique(ax, -7.6, -0.18, 2, 1.0)
    # Nord : on regarde vers +y, coupe y = 6,93
    ax2 = p.axes(14, 156, (-0.35, 7.0), (-0.25, 3.62), 30)
    v2 = D.Vue((0, 1, 0), (1, 0, 0), (0, 0, 1), coupe=((0, -1, 0), -6.9303))
    R2, v2r = _elev(p, sc, ax2, v2, lambda e, r: r not in CONTEXTE, {10: (0.0, 0.0), 29: (5.9, 3.45, 6.0, 3.15), 31: (4.25, 2.95, 4.6, 2.70),
                                                                     32: (5.45, 2.95, 4.95, 2.68), 33: (0.0, 0.6), 25: (0.0, -0.2), 4: (5.6, 3.45, 5.6, 3.02),
                                                                     5: (1.5, 3.45, 1.5, 3.02), 1: (2.6, 3.48, 2.6, 3.40)},
                     [1, 4, 5, 25, 29, 31, 32, 33], "Élévation intérieure Nord — niches cintrées et baie arrière existante", 14, 151)
    ax2.plot([-0.35, 7.0], [0, 0], color=ENCRE, lw=D.LW[4], zorder=90)
    for zz, t in ((0.0, "±0,00"), (Z_FP_SOUS, "+3,00"), (Z_DALLE_SOUS, "+3,30")):
        niveau(ax2, 6.95, zz, t)
    label(ax2, 1.5, 1.6, "WC", size=5.2, col=ENCRE, z=420)
    label(ax2, 4.8, 0.25, "Banquette", size=4.4, col=TAUPE, z=420)
    cote(ax2, Z_FP_DESSUS, Z_DALLE_SOUS, 3.85, "0,26", horiz=False, size=4.2)
    echelle_graphique(ax2, -0.2, -0.18, 2, 1.0)
    p.intertitre("Finitions")
    for s in ["Mur mitoyen est : enduit terre (argile locale) 15 mm, teinte sable (rep. 9).",
              "Refend 4350608 côté lecture : lambris iroko à claire-voie (rep. 10).",
              "Sols : terrazzo sable (salle de lecture), parquet iroko (coin lecture, réunion).",
              "Faux-plafond acoustique blanc cassé +3,00 ; WC : plaque hydrofuge.",
              "Split 1 en partie haute du mur est, au-dessus des rayonnages B01 et hors",
              "aplomb des tables ; mini-pompe de relevage (rep. 28).",
              "Fond : niches V4 et doublage cintré conservés ; liaisons dans le doublage,",
              "sortie par l'imposte de la baie arrière existante (rep. 31, 32)."]:
        p.ligne(s, 5.9, dy=3.6)
    p.y += 2
    legende_reperes(p, sorted(set(v1) | set(v2r)), n_col=1)
    legende_graphique(p, [("poche", "Existant porteur et dalle haute coupés"), ("cloison", "Cloison légère coupée"),
                          ("coupe", "Faux-plafond, revêtements coupés", dict(fc=D.eclaircir((0.93, 0.91, 0.86), 0.75)))])
    p.cartouche("1/30")
    p.enregistrer("elevations_interieures_est_nord")


def A06(sc):
    p = Planche("A06", "Élévations intérieures Sud et Ouest", "Façade intérieure, coin lecture, réunion, locaux de service  ·  Échelle 1/30 (A3)", px=290)
    ax = p.axes(14, 18, (-6.95, 0.35), (-0.25, 3.62), 30)
    v = D.Vue((0, -1, 0), (-1, 0, 0), (0, 0, 1), coupe=((0, 1, 0), 0.8003))
    keep = lambda e, r: r not in CONTEXTE and bb(e)[1][1] >= -0.5 and not est(e, "Pergola", "Poteau de pergola", "Jardinière", "Chaise", "Table_Ronde") \
        and e["tag"] not in ("4350710", "4350711")
    R1, v1 = _elev(p, sc, ax, v, keep, {11: (-1.15, 2.85, -1.15, 2.5), 12: (-2.35, 2.75, -2.35, 2.4), 13: (0.0, 0.0), 15: (0.0, 0.0),
                                        18: (0.0, 0.0), 24: (0.0, 0.2), 9: (-4.6, 2.75, -4.6, 2.5), 4: (-0.5, 3.25, -0.5, 3.02)},
                   [4, 9, 11, 12, 13, 15, 18, 24], "Élévation intérieure Sud — façade vue de l'intérieur (coupe y = 0,80)", 14, 13)
    ax.plot([-6.95, 0.35], [0, 0], color=ENCRE, lw=D.LW[4], zorder=90)
    for zz, t in ((0.0, "±0,00"), (Z_FP_SOUS, "+3,00"), (Z_DALLE_SOUS, "+3,30")):
        niveau(ax, 0.30, zz, t)
    cote(ax, 1.00, 1.75, -2.95, "TD 1,00–1,75", horiz=False, size=4.0)
    label(ax, -4.1, 0.3, "Entrée", size=4.6, col=TAUPE, z=420)
    echelle_graphique(ax, -6.8, -0.18, 2, 1.0)
    ax2 = p.axes(14, 156, (-0.35, 7.75), (-0.25, 3.62), 30)
    v2 = D.Vue((-1, 0, 0), (0, 1, 0), (0, 0, 1), coupe=((1, 0, 0), 2.8503))
    R2, v2r = _elev(p, sc, ax2, v2, lambda e, r: r not in CONTEXTE and bb(e)[1][1] >= -0.2,
                    {27: (0.0, 0.32), 28: (0.3, -0.15), 3: (0.0, 0.0), 17: (0.0, 0.0), 33: (0.0, 0.5), 2: (0.0, 0.0), 31: (5.25, 3.45, 5.10, 3.24),
                     5: (6.6, 3.45, 6.6, 3.02), 4: (3.6, 3.45, 3.6, 3.02), 30: (4.4, 3.45, 4.4, 3.25)},
                    [2, 3, 4, 5, 17, 27, 28, 30, 31, 33], "Élévation intérieure Ouest — coin lecture, réunion, rangement, WC (coupe x = 2,85)", 14, 151)
    ax2.plot([-0.35, 7.75], [0, 0], color=ENCRE, lw=D.LW[4], zorder=90)
    for zz, t in ((0.0, "±0,00"), (Z_FP_SOUS, "+3,00"), (Z_DALLE_SOUS, "+3,30")):
        niveau(ax2, 7.70, zz, t)
    for x, s in ((1.25, "Coin lecture"), (3.75, "Réunion"), (5.6, "Rangement"), (6.85, "WC")):
        label(ax2, x, 0.22, s, size=4.6, col=TAUPE, z=420)
    cote(ax2, 0.0, 2.30, 3.25, "2,30", horiz=False, size=4.2)
    echelle_graphique(ax2, -0.2, -0.18, 2, 1.0)
    p.intertitre("Technique (hypothèses ESQ Ahoua)")
    for s in ["Tableau divisionnaire ~0,60 × 0,25 encastré dans un habillage iroko près de",
              "l'entrée (coin lecture), 1,00 m libre devant, loin de tout point d'eau (rep. 18).",
              "Placard technique 0,60 × 0,40 net, porte pleine : arrivée électrique de",
              "l'immeuble, baie informatique, coffret des liaisons clim (rep. 3).",
              "Split 2 en partie haute du mur mitoyen de la réunion, hors aplomb de la table.",
              "Coffrages acoustiques 0,30 × 0,30 des descentes EU/EV (rep. 33) :",
              "« À relever sur site ». Pas de TGBT ni de groupe électrogène."]:
        p.ligne(s, 5.9, dy=3.6)
    p.y += 2
    legende_reperes(p, sorted(set(v1) | set(v2r)), n_col=1)
    legende_graphique(p, [("poche", "Existant porteur coupé"), ("cloison", "Cloison légère coupée"), ("verre", "Vitrage")])
    p.cartouche("1/30")
    p.enregistrer("elevations_interieures_sud_ouest")


def A07(sc):
    p = Planche("A07", "Vues 3D de la maquette", "Rendus OpenGL tirés de l'IFC V5 (v5/vues_rendu)  ·  sans échelle", px=290)
    vues = [("01_devanture_rue_pieton_ombre", "Devanture sur rue, vue piéton"), ("02_interieur_depuis_entree_ombre", "Intérieur depuis l'entrée"),
            ("03_interieur_vers_devanture_ombre", "Intérieur vers la devanture"), ("04_arbre_a_livres_ombre", "Arbre à livres et oculus indigo"),
            ("05_coin_lecture_ombre", "Coin lecture et vitrine en arche"), ("05_coin_lecture_traits", "Coin lecture — traits")]
    w, gx, gy = 136, 6, 8
    h = w / 1.6
    for k, (f, t) in enumerate(vues):
        x = 8 + (k % 2) * (w + gx)
        y = 10 + (k // 2) * (h + gy)
        a = p.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
        a.imshow(Image.open(os.path.join(VUES, f + ".png")).convert("RGB").resize((1360, 850), Image.LANCZOS)); a.axis("off")
        p.T(x, y + h + 1.2, f"{k + 1:02d}  ·  {t}", 6.2, ENCRE)
    p.intertitre("Vues pour les rendus finaux")
    for s in ["Cinq cadrages fixes, exportés en 2560 × 1600 px dans v5/vues_rendu :",
              "<nom>_ombre.png (couleurs matériaux IFC, ombre portée, sans légende),",
              "<nom>_traits.png (silhouettes et arêtes) et <nom>_camera.json",
              "(position, cible, FOV, focale équivalente 24 × 36) pour un cadrage",
              "reproductible lors de la génération des rendus (fal).",
              "",
              "Les vues sont recalculées à partir de l'IFC par :",
              "python3 v5/scripts/vues_rendu.py"]:
        p.ligne(s, 6.0, dy=3.7)
    p.cartouche("sans échelle")
    p.enregistrer("vues_3D")


def A08(sc):
    from rendu_gl import render
    p = Planche("A08", "Axonométries", "Aménagement coupé à +2,40  ·  Réseaux techniques en plénum  ·  sans échelle", px=290)
    cam = dict(position=(3.3 + 14.0, 3.3 - 15.0, 1.0 + 17.0), target=(3.3, 3.3, 1.0), ortho_h=9.6)
    cache = os.path.join(DESSINS, "_axo")
    os.makedirs(cache, exist_ok=True)
    masque = ("logements", "fenetre_logt", "voisin", "arbre", "sol_ext", "trottoir")
    # 1. aménagement coupé à +2,40
    T, C, I = triangles(sc, lambda e: role(e) not in masque and e["classe"] != "IfcSlab" and role(e) != "plafond"
                        and not est(e, "Pergola", "Rail", "Downlight") and e["tag"] not in ("4350710", "4350711"))
    keep_full = np.array([("Arbre_a_livres" in sc[i]["nom"]) or role(sc[i]) in ("luminaire",) for i in I])
    Tc, Cc, Ic = [T[keep_full]], [C[keep_full]], [I[keep_full]]
    for i in np.unique(I[~keep_full]):
        m = (I == i) & ~keep_full
        t = D.couper_demi_espace(T[m], np.array([0, 0, 1.0]), 2.40)
        if len(t):
            Tc.append(t); Cc.append(np.tile(C[m].mean(0), (len(t), 1))); Ic.append(np.full(len(t), i))
    T1, C1, I1 = np.concatenate(Tc), np.concatenate(Cc), np.concatenate(Ic)
    gr = np.array([[-0.8, -3.6, -0.02], [7.4, -3.6, -0.02], [7.4, 8.3, -0.02], [-0.8, 8.3, -0.02]])
    T1 = np.concatenate([T1, gr[[0, 1, 2]][None], gr[[0, 2, 3]][None]])
    C1 = np.concatenate([C1, np.tile((0.90, 0.88, 0.85, 1.0), (2, 1))]); I1 = np.concatenate([I1, [len(sc), len(sc)]])
    sh1, tr1 = render(T1, C1, I1, cam, size=(2400, 1500), ss=2, sun_dir=(-0.45, -0.35, 0.82), sky=(0.92, 0.90, 0.88),
                      ground=(0.6, 0.55, 0.5), background=(1, 1, 1), exposure=1.0, ao=0.45)
    # 2. technique : tout en fantôme sauf les réseaux et équipements
    TT, CT, IT = triangles(sc, lambda e: role(e) not in masque and e["classe"] != "IfcSlab" and not est(e, "Pergola")
                           and e["tag"] not in ("4350710", "4350711"))
    tech = np.array([role(sc[i]) == "technique" for i in IT])
    CT = CT.copy()
    pal = {"IfcPipeSegment": (0.18, 0.24, 0.43), "IfcCableCarrierSegment": (0.71, 0.35, 0.24), "IfcUnitaryEquipment": (0.96, 0.96, 0.95),
           "IfcPump": (0.25, 0.25, 0.25), "IfcElectricDistributionBoard": (0.85, 0.75, 0.2), "IfcBuildingElementProxy": (0.1, 0.1, 0.1),
           "IfcPlate": (0.15, 0.15, 0.15)}
    for i in np.unique(IT[tech]):
        e = sc[i]
        c = pal.get(e["classe"])
        if est(e, "Descente"):
            c = (0.37, 0.48, 0.29)
        if c:
            CT[IT == i] = (*c, 1.0)
    gh = ~tech
    CT[gh, :3] = 0.80 + 0.17 * CT[gh, :3]
    CT[gh, 3] = 1.0
    cam2 = dict(cam, ortho_h=10.2)
    sh2, tr2 = render(TT, CT, IT, cam2, size=(2400, 1500), ss=2, shadows=True, sun_dir=(-0.45, -0.35, 0.82), sky=(0.95, 0.94, 0.92),
                      ground=(0.75, 0.72, 0.68), background=(1, 1, 1), exposure=1.0, ao=0.35)
    mult = lambda a, b, k: Image.fromarray((np.asarray(a, float) * (1 - k + k * np.asarray(b, float)[..., None] / 255)).astype(np.uint8))
    sh1, sh2 = mult(sh1, tr1, 0.35), mult(sh2, tr2, 0.55)
    for k, (img, tit) in enumerate(((sh1, "Axonométrie de l'aménagement, coupe horizontale à +2,40 (dalle, faux-plafonds et pergola masqués)"),
                                    (sh2, "Axonométrie technique, dalle masquée : réseaux en plénum au-dessus du faux-plafond — liaisons splits (indigo), chemins de câbles (terre cuite), descentes EU/EV (olive)"))):
        img.save(os.path.join(cache, f"axo_{k + 1}.png"))
        y = 10 + k * 140
        a = p.fig.add_axes([6 / W, 1 - (y + 130) / H, 278 / W, 130 / H])
        a.imshow(img); a.axis("off")
        p.T(10, y + 130, tit, 6.2, ENCRE)
    p.intertitre("Lecture")
    for s in ["Haut : volumes de l'aménagement dans l'existant V4 — arbre à livres,",
              "niches, rayonnages, comptoir, coin lecture, réunion, placard technique.",
              "Bas : le cheminement des réseaux reste dans le plénum (+3,04 à +3,30)",
              "puis dans le doublage des niches, et sort par l'imposte de la baie",
              "arrière existante ; aucun poteau, voile ou dalle n'est traversé",
              "(vérification booléenne : v5/rapports/verif_v4_v5.md).",
              "Vue orthographique depuis le sud-est, sans échelle."]:
        p.ligne(s, 6.0, dy=3.7)
    p.cartouche("sans échelle")
    p.enregistrer("axonometries")


PLANCHES = {"A01": A01, "A02": A02, "A03": A03, "A04": A04, "A05": A05, "A06": A06, "A07": A07, "A08": A08}

if __name__ == "__main__":
    sc = charger()
    for k in (sys.argv[1:] or PLANCHES):
        PLANCHES[k](sc)
