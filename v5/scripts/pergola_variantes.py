"""Pergola, trois variantes (1 simple, 2 entre-deux, 3 Gen Z) : géométrie paramétrique hors IFC, vue 3D caméra 01, plan de toiture et coupe.

Rien n'est écrit dans les fichiers IFC : la scène V5 est chargée, la pergola paramétrique V4 (lattes,
lisses 4350710/4350711, poteaux) est masquée et remplacée en mémoire par la variante.
Sorties : v5/pergola/P{1,2,3}_vue01.png, _traits.png, _plan.png, _coupe.png
Usage : python3 v5/scripts/pergola_variantes.py
"""
import os, sys, json
import numpy as np
import shapely
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dessins as DS  # noqa
import dessin2d as D  # noqa
from scene import charger, role, triangles  # noqa
from rendu_gl import render  # noqa
from vues_rendu import VIEWS, EXT  # noqa
from ombres import calculer_ombres  # noqa
import matplotlib.pyplot as plt  # noqa

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pergola")
IROKO = (0.60, 0.42, 0.26, 1.0); ACIER = (0.12, 0.12, 0.12, 1.0); LAMPE = (1.0, 0.89, 0.69, 1.0)
CACHER = ("Pergola bois", "Poteau de pergola")
CACHER_TAGS = ("4350710", "4350711")
POTEAUX_X = (0.29, 6.29); POTEAU_Y = -2.46
X0, X1 = -0.05, 6.65; Y_FAC = -0.17


class Maillage:
    def __init__(self): self.V, self.F, self.C = [], [], []; self.n = 0
    def add(self, V, F, rgba):
        V = np.asarray(V, float); F = np.asarray(F, int) + self.n
        self.V.append(V); self.F.append(F); self.C.append(np.tile(rgba, (len(F), 1))); self.n += len(V)
    def boite(self, x0, y0, z0, x1, y1, z1, rgba):
        V = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        F = [(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4), (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)]
        self.add(V, F, rgba)
    def prisme_xz(self, poly, y0, y1, rgba):
        """Polygone (x, z) extrudé en y."""
        for p in shapely.get_parts(poly):
            tri = shapely.get_parts(shapely.constrained_delaunay_triangles(p))
            for t in tri:
                c = np.array(t.exterior.coords)[:3]
                for y in (y0, y1):
                    self.add([(a, y, b) for a, b in c], [(0, 1, 2)], rgba)
            for ring in [p.exterior] + list(p.interiors):
                c = np.array(ring.coords)
                for (a0, b0), (a1, b1) in zip(c[:-1], c[1:]):
                    self.add([(a0, y0, b0), (a1, y0, b1), (a1, y1, b1), (a0, y1, b0)], [(0, 1, 2), (0, 2, 3)], rgba)
    def element(self, tag, nom, classe="IfcBuildingElementProxy"):
        V = np.concatenate(self.V); F = np.concatenate(self.F); C = np.concatenate(self.C)
        items = []
        for col in np.unique(C, axis=0):
            m = np.all(C == col, axis=1)
            items.append((F[m], C[m]))
        return dict(tag=tag, nom=nom, classe=classe, statut="Variante (hors IFC)", lot="Aménagement", verts=V, items=items)


def guirlande(m, y, x0, x1, z, fleche, pas=0.30):
    xs = np.arange(x0, x1 + 1e-6, pas)
    for x in xs:
        t = (x - x0) / (x1 - x0); zz = z - fleche * 4 * t * (1 - t)
        m.boite(x - 0.025, y - 0.025, zz - 0.05, x + 0.025, y + 0.025, zz, LAMPE)


def variante(k):
    s, l = Maillage(), Maillage()
    if k == 1:   # lattes droites sur cadre acier
        for px in POTEAUX_X: s.boite(px - 0.04, POTEAU_Y - 0.04, 0, px + 0.04, POTEAU_Y + 0.04, 2.90, ACIER)
        s.boite(X0, -2.50, 2.90, X1, -2.42, 3.06, ACIER); s.boite(X0, -0.25, 2.90, X1, Y_FAC, 3.06, ACIER)
        s.boite(X0, -2.50, 2.90, X0 + 0.08, Y_FAC, 3.06, ACIER); s.boite(X1 - 0.08, -2.50, 2.90, X1, Y_FAC, 3.06, ACIER)
        for x in np.arange(0.0, 6.62, 0.10): s.boite(x, -2.58, 3.06, x + 0.04, Y_FAC, 3.12, IROKO)
    elif k == 2:  # une seule vague, rythme alterné
        for px in POTEAUX_X: s.boite(px - 0.05, POTEAU_Y - 0.05, 0, px + 0.05, POTEAU_Y + 0.05, 2.88, IROKO)
        s.boite(X0, -2.51, 2.88, X1, -2.41, 3.06, IROKO); s.boite(X0, -0.27, 2.88, X1, Y_FAC, 3.06, IROKO)
        xs = np.arange(-0.02, 6.62, 0.085)
        for i, x in enumerate(xs):
            t = (x - xs[0]) / (xs[-1] - xs[0]); top = 3.10 + 0.20 * np.sin(np.pi * t)
            s.boite(x, -2.64 if i % 2 == 0 else -2.50, 3.06, x + 0.034, Y_FAC, top, IROKO)
        for y in (-0.95, -1.75): guirlande(l, y, 0.10, 6.50, 2.92, 0.16)
    elif k == 3:  # arcades en enfilade, arc du logo
        for px in POTEAUX_X: s.boite(px - 0.06, POTEAU_Y - 0.06, 0, px + 0.06, POTEAU_Y + 0.06, 2.32, IROKO)
        cs, r, zs, zt = (1.29, 3.29, 5.29), 0.90, 2.32, 3.32
        prof = sbox(X0, zs, X1, zt).difference(unary_union([Point(c, zs).buffer(r, quad_segs=24) for c in cs]))
        for y in np.linspace(-2.52, -0.40, 6): s.prisme_xz(prof, y - 0.025, y + 0.025, IROKO)
        for px in POTEAUX_X: s.boite(px - 0.06, -2.55, 3.14, px + 0.06, Y_FAC, 3.32, IROKO)
        s.boite(X0, -0.29, 3.14, X1, Y_FAC, 3.32, IROKO)
        for x in np.arange(-0.03, 6.63, 0.12): s.boite(x, -2.56, 3.32, x + 0.03, Y_FAC, 3.355, IROKO)
        for c in cs:   # ampoules 2700 K le long de l'intrados de l'arc avant
            for a in np.linspace(0.12, np.pi - 0.12, 9):
                x, z = c + (r - 0.06) * np.cos(a), zs + (r - 0.06) * np.sin(a)
                l.boite(x - 0.025, -2.57, z - 0.025, x + 0.025, -2.52, z + 0.025, LAMPE)
    els = [s.element(f"PV{k}", f"Pergola variante {k}")]
    if l.n: els.append(l.element(f"PV{k}L", f"Guirlande variante {k}", "IfcLightFixture"))
    return els


def scene_variante(sc, k):
    base = [e for e in sc if not (any(c in e["nom"] for c in CACHER) or e["tag"] in CACHER_TAGS)]
    return base + variante(k)


def vue3d(sc2, k):
    cam, light, hide, _ = VIEWS["01_devanture_rue_pieton"]
    T, C, I = triangles(sc2, lambda e: role(e) not in hide)
    sh, tr = render(T, C, I, cam, size=(2560, 1600), **light)
    sh.save(f"{OUT}/P{k}_vue01.png", optimize=True); tr.save(f"{OUT}/P{k}_traits.png", optimize=True)


def fig_mm(w, h):
    f = plt.figure(figsize=(w / 25.4, h / 25.4)); ax = f.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.ech = 100; return f, ax


def plan(sc2, k):
    xl, yl = (-0.30, 6.90), (-3.05, 0.35)            # 1/100 : 72 x 34 mm
    f, ax = fig_mm((xl[1] - xl[0]) * 10, (yl[1] - yl[0]) * 10)
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal")
    v = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0), coupe=((0, 0, 1), 3.4203))
    R = D.calculer(sc2, v, lambda e, r: r not in ("logements", "fenetre_logt", "plafond") and e["classe"] != "IfcSlab"
                   and e["verts"][:, 1].min() < 0.4)
    ax.add_patch(plt.Rectangle((xl[0], yl[0]), xl[1] - xl[0], 0.0 - yl[0], fc="#EFEDEA", ec="none", zorder=1))
    var = [r for r in R if r["e"]["tag"].startswith("PV")]
    z = DS.peindre(ax, [r for r in R if r not in var], ombre=calculer_ombres(R, v, xl, yl, "plan"))
    DS.pocher(ax, [r for r in R if r not in var])
    for r in var:          # pergola : trait fin pour rester lisible au 1/100
        for it in r["items"]:
            lampe = it["rgba"][0] > 0.98 and it["rgba"][1] > 0.86
            D.patch(ax, it["g"], fc="#FFE3A8" if lampe else DS.sourdine(D.eclaircir(it["rgba"], 0.35)),
                    ec=DS.TERRE_CUITE if lampe else DS.ENCRE, lw=0.08 * D.MM_PT, z=z)
            z += 0.001
    ax.plot([X0, X1], [Y_FAC, Y_FAC], color=DS.ENCRE, lw=D.LW[1], zorder=90)
    f.savefig(f"{OUT}/P{k}_plan.png", dpi=300); plt.close(f)


def coupe(sc2, k):
    xl, zl = (-3.35, 0.95), (-0.25, 4.05)            # 1/100 : 43 x 43 mm, coupe x = 4,40 vers l'ouest
    f, ax = fig_mm((xl[1] - xl[0]) * 10, (zl[1] - zl[0]) * 10)
    ax.set_xlim(*xl); ax.set_ylim(*zl); ax.set_aspect("equal")
    v = D.Vue((-1, 0, 0), (0, 1, 0), (0, 0, 1), coupe=((1, 0, 0), 4.4003))
    R = D.calculer(sc2, v, lambda e, r: r not in ("sol_ext", "arbre", "voisin", "logements", "fenetre_logt"))
    ax.add_patch(plt.Rectangle((xl[0], zl[0]), xl[1] - xl[0], -0.0 - zl[0], fc="#E2DDD6", ec="none", zorder=1))
    DS.peindre(ax, R, ombre=calculer_ombres(R, v, xl, zl, "elev"), veg="elev")
    DS.pocher(ax, R)
    ax.plot(xl, [0, 0], color=DS.ENCRE, lw=D.LW[2], zorder=95)
    pv = [r["e"] for r in R if r["e"]["tag"] == f"PV{k}"][0]
    top, bas = pv["verts"][:, 2].max(), {1: 2.90, 2: 2.88, 3: 2.32}[k]
    for zz in (top,):          # sous-face donnée dans le tableau de la planche
        DS.niveau(ax, -3.05, zz, f"+{zz:.2f}".replace(".", ","))
    f.savefig(f"{OUT}/P{k}_coupe.png", dpi=300); plt.close(f)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sc = charger()
    ks = [int(a) for a in sys.argv[1:]] or [1, 2, 3]
    for k in ks:
        sc2 = scene_variante(sc, k)
        vue3d(sc2, k); plan(sc2, k); coupe(sc2, k)
        print("variante", k)
