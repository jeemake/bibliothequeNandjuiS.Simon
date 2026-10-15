"""Moteur de dessin 2D tiré de la maquette V5 : coupes (poché) et projections (silhouettes, peintre).

Une vue = un plan de coupe optionnel (on garde le demi-espace regardé), une projection orthogonale
vers 2D et une fonction de proximité (pour l'ordre de peinture). Toutes les cotes en mètres.
"""
import os, sys, re, csv
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, GeometryCollection
from shapely.ops import linemerge, unary_union
from matplotlib.path import Path
from matplotlib.patches import PathPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene import role  # noqa

MM_PT = 72 / 25.4
LW = {1: 0.18 * MM_PT, 2: 0.35 * MM_PT, 4: 0.70 * MM_PT}   # graisses 1:2:4
GRID = 1e-4


class Vue:
    """d : direction du regard ; plan de coupe n.p <= c gardé (None = pas de coupe) ; u, v : axes 2D."""

    def __init__(self, d, u, v, coupe=None):
        self.d = np.asarray(d, float)
        self.u = np.asarray(u, float)
        self.v = np.asarray(v, float)
        self.coupe = None if coupe is None else (np.asarray(coupe[0], float), float(coupe[1]))

    def to2d(self, P):
        return np.stack([P @ self.u, P @ self.v], axis=-1)

    def proche(self, P):
        return -(P @ self.d)


def couper_demi_espace(T, n, c):
    """Triangles (m,3,3) restreints à n.p <= c (Sutherland-Hodgman par triangle)."""
    if len(T) == 0:
        return T
    s = T @ n - c
    ins = s <= 1e-9
    k = ins.sum(1)
    out = [T[k == 3]]
    part = np.where((k > 0) & (k < 3))[0]
    extra = []
    for i in part:
        t, sv = T[i], s[i]
        poly = []
        for j in range(3):
            a, b, sa, sb = t[j], t[(j + 1) % 3], sv[j], sv[(j + 1) % 3]
            if sa <= 1e-9:
                poly.append(a)
            if (sa <= 1e-9) != (sb <= 1e-9):
                poly.append(a + (b - a) * (sa / (sa - sb)))
        for j in range(1, len(poly) - 1):
            extra.append((poly[0], poly[j], poly[j + 1]))
    if extra:
        out.append(np.array(extra))
    return np.concatenate(out) if out else T[:0]


def silhouette(P2):
    """Union des triangles 2D (m,3,2) non dégénérés."""
    if len(P2) == 0:
        return None
    a = 0.5 * np.abs((P2[:, 1, 0] - P2[:, 0, 0]) * (P2[:, 2, 1] - P2[:, 0, 1])
                     - (P2[:, 2, 0] - P2[:, 0, 0]) * (P2[:, 1, 1] - P2[:, 0, 1]))
    P2 = P2[a > 1e-9]
    if len(P2) == 0:
        return None
    ring = np.concatenate([P2, P2[:, :1]], axis=1)
    polys = shapely.polygons(ring)
    g = shapely.union_all(shapely.make_valid(polys), grid_size=GRID)
    g = _polys(g)
    return None if g is None or g.is_empty else g


def section(T, n, c, vue):
    """Polygones de coupe d'un maillage fermé par le plan n.p = c (pair-impair sur les boucles)."""
    s = T @ n - c
    cross = (s.min(1) < 0) & (s.max(1) > 0)
    segs = []
    for t, sv in zip(T[cross], s[cross]):
        pts = []
        for j in range(3):
            a, b, sa, sb = t[j], t[(j + 1) % 3], sv[j], sv[(j + 1) % 3]
            if (sa < 0) != (sb < 0):
                pts.append(a + (b - a) * (sa / (sa - sb)))
        if len(pts) == 2:
            segs.append(pts)
    if not segs:
        return None
    S2 = np.round(vue.to2d(np.array(segs)), 5)
    lines = unary_union([LineString(p) for p in S2 if np.linalg.norm(p[0] - p[1]) > 1e-7])
    merged = linemerge(lines) if not lines.is_empty else lines
    geoms = getattr(merged, "geoms", [merged])
    res = None
    for g in geoms:
        if g.is_closed and len(g.coords) >= 4:
            p = Polygon(g.coords).buffer(0)
            res = p if res is None else res.symmetric_difference(p)
    if res is None:
        for p in shapely.get_parts(shapely.polygonize(list(geoms))):
            res = p if res is None else res.symmetric_difference(p)
    return _polys(res)


def _polys(g):
    if g is None or g.is_empty:
        return None
    if isinstance(g, (Polygon, MultiPolygon)):
        return g
    ps = [p for p in shapely.get_parts(g) if isinstance(p, Polygon) and p.area > 0]
    return MultiPolygon(ps) if ps else None


def calculer(scene, vue, garder=lambda e, r: True):
    """Pour chaque produit retenu : items projetés (silhouette, proximité, couleur), coupe et silhouette totale."""
    res = []
    for k, e in enumerate(scene):
        r = role(e)
        if not garder(e, r):
            continue
        items, cuts, cuts_rgba = [], [], []
        for fc, rgba in e["items"]:
            T = e["verts"][fc]
            if vue.coupe is not None:
                n, c = vue.coupe
                Tk = couper_demi_espace(T, n, c)
                sc = section(T, n, c, vue)
                if sc is not None:
                    cuts.append(sc)
                    cuts_rgba.append((sc, rgba.mean(0)))
            else:
                Tk = T
            if len(Tk) == 0:
                continue
            g = silhouette(vue.to2d(Tk))
            if g is None:
                continue
            items.append(dict(g=g, proche=float(vue.proche(Tk.reshape(-1, 3)).max()), rgba=rgba.mean(0)))
        if not items and not cuts:
            continue
        tot = unary_union([i["g"] for i in items]) if items else None
        res.append(dict(e=e, role=r, items=items, coupe=unary_union(cuts) if cuts else None, coupes=cuts_rgba, tout=tot,
                        proche=max([i["proche"] for i in items], default=-1e9)))
    res.sort(key=lambda x: x["proche"])
    return res


def contour_complet(e, vue):
    """Silhouette du produit entier (sans coupe) — pour les éléments au-dessus du plan de coupe."""
    T = np.concatenate([e["verts"][fc] for fc, _ in e["items"]])
    return silhouette(vue.to2d(T))


# --- matplotlib ------------------------------------------------------------------------------
def _path(g):
    verts, codes = [], []
    for p in getattr(g, "geoms", [g]):
        if not isinstance(p, Polygon):
            continue
        for ring in [p.exterior, *p.interiors]:
            c = np.asarray(ring.coords)
            if len(c) < 3:
                continue
            verts += c.tolist(); codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    return Path(verts, codes) if verts else None


def patch(ax, g, fc="none", ec="k", lw=LW[1], z=1, ls="-", hatch=None, alpha=1.0, **kw):
    if g is None or g.is_empty:
        return
    p = _path(g)
    if p is None:
        return
    pp = PathPatch(p, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha, joinstyle="miter", **kw)
    ax.add_patch(pp)
    return pp


def eclaircir(rgb, k):
    rgb = np.asarray(rgb[:3], float)
    return tuple(1 - (1 - rgb) * k)


def code_mobilier(e):
    m = re.search(r"DECIMO_([A-Z]+\d+)_([A-Za-z_0-9]+)", e["nom"])
    if not m:
        return None, None
    return m.group(1), m.group(2).replace("_", " ")


def lire_csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter=";"))
