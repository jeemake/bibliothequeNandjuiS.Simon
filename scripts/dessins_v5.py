"""Planches de l'esquisse V5 générées depuis l'IFC (aucune géométrie saisie à la main hors contexte urbain).

Usage : python3 scripts/dessins_v5.py v5/DECIMO_ESQ_V5.ifc v5/dessins

Planches A3 (PNG 200 dpi + PDF ; SVG pour les dessins au trait) :
  01 plan RDC 1/50 (plan de coupe +1,00)   02 coupe AA 1/50          03 élévation de la devanture 1/50
  04 élévation intérieure (coupe BB) 1/25  05 axonométries           06 perspectives
Méthode : sections exactes des maillages ifcopenshell.geom (poché par règle d'enroulement), projections
orthogonales au trait avec élimination des parties cachées par tri peintre triangle par triangle.
"""
import copy, os, sys, math, collections, random
os.environ.setdefault("MPLBACKEND", "Agg")
import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.collections import PathCollection, LineCollection, PolyCollection
from matplotlib.patches import PathPatch, Rectangle, Circle, Polygon as MPoly, FancyArrowPatch
from matplotlib.backends.backend_pdf import PdfPages
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point, box as sbox
from shapely.ops import unary_union, polygonize, polylabel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "charte"))
from charte_kdemi import *  # noqa: F401,F403  (palette, polices, draw_logo)

IFC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "v5/DECIMO_ESQ_V5.ifc")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "v5/dessins")
os.makedirs(OUT, exist_ok=True)
MMI = 1 / 25.4
PT = 72 / 25.4                                     # points par mm
LW_F, LW_M, LW_G = 0.13 * PT, 0.25 * PT, 0.50 * PT  # hiérarchie des traits 1:2:4 (mm -> pt)
plt.rcParams["hatch.linewidth"] = 0.45
NOIR = "#1A1614"
EPS = 1e-4

# ================================================================================ lecture IFC
f = ifcopenshell.open(IFC)
settings = ifcopenshell.geom.settings()
settings.set("use-world-coords", True)
it = ifcopenshell.geom.iterator(settings, f, os.cpu_count() or 1)
it.initialize()

def hex2rgb(h):
    return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])

class Mesh:
    pass

MESHES = []
while True:
    sh = it.get()
    el = f.by_id(sh.id)
    if not el.is_a("IfcOpeningElement"):
        g = sh.geometry
        m = Mesh()
        m.el, m.cls, m.name = el, el.is_a(), el.Name or ""
        m.v = np.array(g.verts, dtype=float).reshape(-1, 3)
        m.t = np.array(g.faces, dtype=int).reshape(-1, 3)
        mats = g.materials
        ids = np.array(g.material_ids, dtype=int) if len(g.material_ids) else np.zeros(len(m.t), int)
        cols = np.array([[mt.diffuse.r(), mt.diffuse.g(), mt.diffuse.b(), 1 - mt.transparency] for mt in mats] or [[.8, .8, .8, 1]])
        names = [(f.by_id(mt.instance_id()).Name if mt.instance_id() else "") or "" for mt in mats] or [""]
        ids = np.clip(ids, 0, len(cols) - 1)
        m.col = cols[ids]
        m.mat = np.array(names, dtype=object)[ids]
        # soudure des sommets (adjacence des faces)
        key = np.round(m.v, 5)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        m.tw = inv.reshape(-1)[m.t]
        m.ot = getattr(el, "ObjectType", None) or ""
        m.pdt = getattr(el, "PredefinedType", None) or ""
        m.existing = (el.Description or "").startswith("Existant porteur")
        m.bb = (m.v.min(0), m.v.max(0))
        MESHES.append(m)
    if not it.next():
        break

def category(m):
    c = m.cls
    if c == "IfcSpace":
        return "space"
    if c in ("IfcCivilElement", "IfcGeographicElement"):
        return "site"
    if c == "IfcCovering":
        return {"FLOORING": "floor", "CEILING": "ceiling", "CLADDING": "finish"}.get(m.pdt, "struct")
    if c in ("IfcWall", "IfcColumn", "IfcBeam", "IfcSlab", "IfcMember"):
        return "struct"
    if c == "IfcPlate":
        return "glass"
    if c == "IfcDoor":
        return "door"
    if c == "IfcLightFixture":
        return "light"
    if c in ("IfcPipeSegment", "IfcUnitaryEquipment"):
        return "mep"
    return "furn"

for m in MESHES:
    m.cat = category(m)
SPACES = [m for m in MESHES if m.cat == "space"]
SOLIDS = [m for m in MESHES if m.cat != "space"]

def qto(el, name):
    return ue.get_psets(el).get("Qto_SpaceBaseQuantities", {}).get(name)

# ================================================================================ géométrie
def frame(R, o):
    R = np.array(R, float)
    return R, np.array(o, float)

def to_view(v, F):
    R, o = F
    return (v - o) @ R.T

def clip_poly(poly, zmax=0.0):
    """Sutherland-Hodgman : garde la partie Z <= zmax d'un polygone 3D (liste de sommets)."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ina, inb = a[2] <= zmax, b[2] <= zmax
        if ina:
            out.append(a)
        if ina != inb:
            k = (zmax - a[2]) / (b[2] - a[2])
            out.append(a + k * (b - a))
    return out

def section(m, F, h=0.0):
    """Polygones de section du maillage au plan Z' = h (repère de vue), classés par enroulement."""
    vv = to_view(m.v, F)
    tri = vv[m.t]
    z = tri[:, :, 2] - h
    pos = z > 0
    n = pos.sum(1)
    sel = (n == 1) | (n == 2)
    if not sel.any():
        return None
    tri, z, pos = tri[sel], z[sel], pos[sel]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    P = np.full((len(tri), 3, 2), np.nan)
    C = np.zeros((len(tri), 3), bool)
    for e, (i, j) in enumerate(((0, 1), (1, 2), (2, 0))):
        c = pos[:, i] != pos[:, j]
        k = np.where(c, z[:, i] / np.where(c, z[:, i] - z[:, j], 1), 0)
        P[:, e] = tri[:, i, :2] + k[:, None] * (tri[:, j, :2] - tri[:, i, :2])
        C[:, e] = c
    order = np.argsort(~C, axis=1, kind="stable")[:, :2]
    r = np.arange(len(tri))
    p0, p1 = P[r, order[:, 0]], P[r, order[:, 1]]
    d = p1 - p0
    flip = (d[:, 1] * nrm[:, 0] - d[:, 0] * nrm[:, 1]) < 0
    p0, p1 = np.where(flip[:, None], p1, p0), np.where(flip[:, None], p0, p1)
    p0, p1 = np.round(p0, 6), np.round(p1, 6)
    keep = np.linalg.norm(p1 - p0, axis=1) > 1e-7
    p0, p1 = p0[keep], p1[keep]
    if not len(p0):
        return None
    faces = list(polygonize(unary_union(MultiLineString([[tuple(a), tuple(b)] for a, b in zip(p0, p1)]))))
    solid = []
    for fc in faces:
        if fc.area < 1e-9:
            continue
        q = fc.representative_point()
        px, py = q.x, q.y
        y0, y1 = p0[:, 1], p1[:, 1]
        up = (y0 <= py) & (y1 > py)
        dn = (y1 <= py) & (y0 > py)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = p0[:, 0] + (py - y0) / (y1 - y0) * (p1[:, 0] - p0[:, 0])
        w = np.sum(up & (xi > px)) - np.sum(dn & (xi > px))
        if w != 0:
            solid.append(fc)
    return unary_union(solid) if solid else None

def footprint(m, F, zmin=-1e9, zmax=1e9):
    vv = to_view(m.v, F)
    tri = vv[m.t]
    ok = (tri[:, :, 2].max(1) >= zmin) & (tri[:, :, 2].min(1) <= zmax)
    polys = [Polygon(p[:, :2]) for p in tri[ok]]
    polys = [p.buffer(1e-5) for p in polys if p.area > 1e-10]
    return unary_union(polys).buffer(-1e-5) if polys else None

def feature_edges(m, vv, front, angle=20):
    """Arêtes vives / silhouettes des faces avant. Retourne {indice triangle: [(a, b), ...]} (sommets 3D vue)."""
    tw = m.tw
    tri = vv[m.t]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    nrm = nrm / np.where(ln[:, None] > 0, ln[:, None], 1)
    E = np.concatenate([tw[:, [0, 1]], tw[:, [1, 2]], tw[:, [2, 0]]])
    L = np.concatenate([m.t[:, [0, 1]], m.t[:, [1, 2]], m.t[:, [2, 0]]])
    T = np.tile(np.arange(len(tw)), 3)
    Es = np.sort(E, axis=1)
    order = np.lexsort((Es[:, 1], Es[:, 0]))
    Es, L, T = Es[order], L[order], T[order]
    out = collections.defaultdict(list)
    cos = math.cos(math.radians(angle))
    i, n = 0, len(Es)
    while i < n:
        j = i + 1
        while j < n and Es[j, 0] == Es[i, 0] and Es[j, 1] == Es[i, 1]:
            j += 1
        tris = T[i:j]
        fr = [t for t in tris if front[t]]
        if fr:
            if len(tris) == 2 and len(fr) == 2 and np.dot(nrm[tris[0]], nrm[tris[1]]) > cos:
                pass
            else:
                owner = max(fr, key=lambda t: tri[t, :, 2].mean())
                out[owner].append((vv[L[i, 0]], vv[L[i, 1]]))
        i = j
    return out

def wobble_circle(cx, cy, r, n=40, seed=0, amp=0.06):
    rr = random.Random(seed)
    ph = [rr.uniform(0, 2 * math.pi) for _ in range(3)]
    return [(cx + r * (1 + amp * math.sin(5 * a + ph[0]) + amp * 0.6 * math.sin(9 * a + ph[1])) * math.cos(a),
             cy + r * (1 + amp * math.sin(5 * a + ph[0]) + amp * 0.6 * math.sin(9 * a + ph[1])) * math.sin(a))
            for a in np.linspace(0, 2 * math.pi, n)]

# ================================================================================ rendu au trait
def tint(rgb, k):
    return 1 - (1 - np.asarray(rgb[:3])) * k

def painter_ortho(ax, F, meshes, *, clip=True, tint_k=0.25, glass_alpha=0.18, edge_lw=LW_F, edge_col=NOIR,
                  style=None, zorder=2, max_depth=None, rasterized=False):
    """Projection orthogonale (vue selon -Z'), parties cachées par tri peintre, arêtes vives au trait fin."""
    items = []
    for m in meshes:
        vv = to_view(m.v, F)
        if clip and vv[:, 2].min() > 0:
            continue
        if max_depth is not None and vv[:, 2].max() < -max_depth:
            continue
        tri = vv[m.t]
        nz = (tri[:, 1, 0] - tri[:, 0, 0]) * (tri[:, 2, 1] - tri[:, 0, 1]) - (tri[:, 1, 1] - tri[:, 0, 1]) * (tri[:, 2, 0] - tri[:, 0, 0])
        front = nz > 1e-10
        if m.cat == "glass":
            front = np.abs(nz) > 1e-10
        edges = feature_edges(m, vv, front)
        st = style(m) if style else {}
        for ti in np.nonzero(front)[0]:
            poly = list(tri[ti])
            if clip and tri[ti, :, 2].max() > 0:
                poly = clip_poly(poly)
                if len(poly) < 3:
                    continue
            poly = np.array(poly)
            col = m.col[ti]
            if st.get("fill") is not None:
                fc = st["fill"]
            elif m.cat == "glass" or col[3] < 0.9:
                fc = (*tint(col, 0.5), glass_alpha)
            else:
                fc = (*tint(col, tint_k), 1.0)
            es = []
            for a, b in edges.get(ti, []):
                if clip:
                    if a[2] > 0 and b[2] > 0:
                        continue
                    if a[2] > 0 or b[2] > 0:
                        k = (0 - a[2]) / (b[2] - a[2])
                        p = a + k * (b - a)
                        a, b = (p, b) if a[2] > 0 else (a, p)
                es.append((a[:2], b[:2]))
            items.append((poly[:, 2].mean(), poly[:, :2], fc, es, st.get("edge", edge_col), st.get("lw", edge_lw)))
    items.sort(key=lambda x: x[0])
    paths, fcs, ecs, lws = [], [], [], []
    for _, poly, fc, es, ec, lw in items:
        paths.append(Path(np.vstack([poly, poly[:1]]), closed=True))
        fcs.append(fc); ecs.append((0, 0, 0, 0)); lws.append(0.0)
        if es:
            verts = np.array([p for s in es for p in s])
            codes = np.tile([Path.MOVETO, Path.LINETO], len(es))
            paths.append(Path(verts, codes))
            fcs.append((0, 0, 0, 0)); ecs.append(ec); lws.append(lw)
    pc = PathCollection(paths, facecolors=fcs, edgecolors=ecs, linewidths=lws, zorder=zorder, capstyle="round", joinstyle="round")
    pc.set_rasterized(rasterized)
    ax.add_collection(pc)
    return pc

def draw_geom(ax, g, fc="none", ec=NOIR, lw=LW_M, zorder=5, hatch=None, alpha=1.0, ls="-"):
    if g is None or g.is_empty:
        return
    geoms = getattr(g, "geoms", [g])
    for p in geoms:
        if p.geom_type == "Polygon":
            verts = [np.array(p.exterior.coords)] + [np.array(r.coords) for r in p.interiors]
            codes = []
            for v in verts:
                codes += [Path.MOVETO] + [Path.LINETO] * (len(v) - 2) + [Path.CLOSEPOLY]
            ax.add_patch(PathPatch(Path(np.vstack(verts), codes), fc=fc, ec=ec, lw=lw, zorder=zorder, hatch=hatch, alpha=alpha, ls=ls))
        elif p.geom_type in ("LineString", "LinearRing"):
            ax.plot(*p.xy, color=ec, lw=lw, zorder=zorder, ls=ls)
        elif hasattr(p, "geoms"):
            draw_geom(ax, p, fc, ec, lw, zorder, hatch, alpha, ls)

def draw_sections(ax, F, meshes, h=EPS, existing_hatch=True, furn=True):
    """Poché noir des éléments coupés ; vitrages et revêtements au trait ; mobilier coupé en silhouette."""
    for m in meshes:
        vv = to_view(m.v, F)
        if vv[:, 2].min() > h or vv[:, 2].max() < h:
            continue
        g = section(m, F, h)
        if g is None:
            continue
        if m.cat == "struct":
            draw_geom(ax, g, fc=NOIR, ec=NOIR, lw=LW_G * 0.6, zorder=8)
            if m.existing and existing_hatch:
                draw_geom(ax, g, fc="none", ec="#9A928B", lw=0.01, zorder=8.1, hatch="////")
        elif m.cat == "site":
            draw_geom(ax, g, fc="#D9D4CB", ec=NOIR, lw=LW_M, zorder=7)
        elif m.cat == "glass":
            draw_geom(ax, g, fc="white", ec=NOIR, lw=LW_F, zorder=8)
        elif m.cat in ("finish", "floor", "ceiling"):
            draw_geom(ax, g, fc=tint(m.col[0], 0.55), ec=NOIR, lw=LW_F, zorder=7.5)
        elif m.cat == "door":
            draw_geom(ax, g, fc="white", ec=NOIR, lw=LW_F, zorder=8)
        elif furn:
            draw_geom(ax, g, fc="white", ec=NOIR, lw=LW_M, zorder=7.8)

# ================================================================================ mise en page
SHEET_W, SHEET_H = 420, 297
PANEL_X = 292
FOOT = "K&Démi  ·  Bibliothèque Decimo  ·  ESQ V5  ·  Octobre 2026"
SHEETS = []

def new_sheet(num, title, subtitle, info):
    fig = plt.figure(figsize=(SHEET_W * MMI, SHEET_H * MMI))
    fig.patch.set_facecolor("white")
    fig.add_artist(Rectangle((PANEL_X / SHEET_W, 0), 1 - PANEL_X / SHEET_W, 1, transform=fig.transFigure, fc=SABLE_CLAIR, ec="none", zorder=-5))
    draw_logo(fig, 14, 12, 12)
    T = lambda x, y, s, size, color=ENCRE, **kw: fig.text(x / SHEET_W, 1 - y / SHEET_H, s, fontsize=size, color=color, va="top", **kw)
    T(PANEL_X + 8, 12, "Bibliothèque Decimo", 21, ENCRE, fontproperties=FP_TITRE)
    T(PANEL_X + 8, 24.5, title, 10.5, TERRE_CUITE)
    T(PANEL_X + 8, 31.5, subtitle, 7.2, TAUPE)
    for k, line in enumerate(info):
        T(PANEL_X + 8, 36.5 + k * 4.2, line, 6.6, TAUPE)
    fig.add_artist(plt.Line2D([(PANEL_X + 8) / SHEET_W, 412 / SHEET_W], [1 - (38.5 + 4.2 * len(info)) / SHEET_H] * 2, color=TERRE_CUITE, lw=1.1))
    # cartouche
    y0 = 252
    fig.add_artist(Rectangle(((PANEL_X + 8) / SHEET_W, 1 - 287 / SHEET_H), (412 - PANEL_X - 8) / SHEET_W, (287 - y0) / SHEET_H,
                             transform=fig.transFigure, fc=BLANC_CHAUX, ec=TAUPE, lw=0.4, zorder=-1))
    rows = [("PROJET", "Bibliothèque Decimo — local RDC, immeuble existant, Abidjan"), ("PHASE", "Esquisse (ESQ)  ·  indice V5  ·  14/10/2026"),
            ("MAQUETTE", "v5/DECIMO_ESQ_V5.ifc (IFC4, mm)"), ("ÉQUIPE", "D.A. Affoué / Stéphanie  ·  technique : hypothèses ESQ Ahoua")]
    for k, (a, b) in enumerate(rows):
        T(PANEL_X + 11, y0 + 3.2 + k * 6.2, a, 5.6, TERRE_CUITE, fontproperties=FP_MEDIUM)
        T(PANEL_X + 30, y0 + 3.2 + k * 6.2, b, 6.2, ENCRE)
    fig.add_artist(Rectangle((392 / SHEET_W, 1 - 287 / SHEET_H), 20 / SHEET_W, (287 - y0) / SHEET_H, transform=fig.transFigure,
                             fc=TERRE_CUITE, ec="none", zorder=0))
    T(402, y0 + 5, "PLANCHE", 5.2, BLANC_CHAUX, ha="center", fontproperties=FP_MEDIUM)
    T(402, y0 + 11, f"{num:02d}", 22, BLANC_CHAUX, ha="center", fontproperties=FP_TITRE)
    T(412, 291, FOOT, 5.8, TERRE_CUITE, ha="right")
    T(PANEL_X + 8, 246.5, "Document d’esquisse — dimensions et surfaces indicatives, à vérifier sur site.", 5.6, TAUPE)
    return fig, T

def drawing_axes(fig, x_mm, y_mm, w_mm, h_mm, X0, Y0, scale):
    """Zone de dessin à l'échelle 1/scale : coin bas-gauche (x_mm, y_mm depuis le haut de la feuille) <-> (X0, Y0) en m."""
    ax = fig.add_axes([x_mm / SHEET_W, 1 - (y_mm + h_mm) / SHEET_H, w_mm / SHEET_W, h_mm / SHEET_H])
    ax.set_xlim(X0, X0 + w_mm * scale / 1000)
    ax.set_ylim(Y0, Y0 + h_mm * scale / 1000)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax

def scale_bar(ax, x, y, scale, length=4.0, step=1.0, label=None):
    h = 0.06 * scale / 50
    for k in range(int(length / step)):
        ax.add_patch(Rectangle((x + k * step, y), step, h, fc=NOIR if k % 2 == 0 else "white", ec=NOIR, lw=LW_F, zorder=20))
    for k in range(int(length / step) + 1):
        ax.text(x + k * step, y - h * 1.2, f"{k * step:g}", fontsize=5.5, ha="center", va="top", color=ENCRE, zorder=20)
    ax.text(x + length + 0.15 * scale / 50, y, label or f"1/{scale}  (m)", fontsize=5.5, va="bottom", color=TAUPE, zorder=20)

def dim(ax, a, b, off, text=None, scale=50, color=TAUPE, fs=5.6, side=1):
    """Cote entre a et b (m), ligne décalée de off (m) ; side=0 : texte sur la ligne, ±1 : de part et d'autre."""
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.linalg.norm(b - a)
    n = np.array([-u[1], u[0]])
    A, B = a + n * off, b + n * off
    ax.plot([A[0], B[0]], [A[1], B[1]], color=color, lw=LW_F, zorder=15)
    t = 0.07 * scale / 50
    for P, Q in ((a, A), (b, B)):
        if abs(off) > 1e-6:
            ax.plot([P[0] + n[0] * np.sign(off) * 0.05, Q[0] + n[0] * np.sign(off) * 0.06],
                    [P[1] + n[1] * np.sign(off) * 0.05, Q[1] + n[1] * np.sign(off) * 0.06], color=color, lw=LW_F, zorder=15)
        d = (u + n) / math.sqrt(2) * t
        ax.plot([Q[0] - d[0], Q[0] + d[0]], [Q[1] - d[1], Q[1] + d[1]], color=color, lw=LW_M, zorder=15)
    ang = math.degrees(math.atan2(u[1], u[0]))
    if ang > 90.1 or ang < -89.9:
        ang += 180
    M = (A + B) / 2 + n * 0.09 * scale / 50 * side
    ax.text(M[0], M[1], text or f"{np.linalg.norm(b - a):.2f}".replace(".", ","), fontsize=fs, color=color, ha="center", va="center",
            rotation=ang, rotation_mode="anchor", zorder=15,
            bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.85) if side == 0 else None)

def north_arrow(ax, x, y, r=0.35):
    ax.add_patch(Circle((x, y), r, fc="none", ec=ENCRE, lw=LW_F, zorder=20))
    ax.add_patch(MPoly([(x, y + r * 1.25), (x - r * 0.32, y - r * 0.55), (x, y - r * 0.25)], closed=True, fc=ENCRE, ec="none", zorder=20))
    ax.add_patch(MPoly([(x, y + r * 1.25), (x + r * 0.32, y - r * 0.55), (x, y - r * 0.25)], closed=True, fc="white", ec=ENCRE, lw=LW_F, zorder=20))
    ax.text(x, y + r * 1.45, "N", fontsize=6.5, ha="center", va="bottom", color=ENCRE, fontproperties=FP_MEDIUM, zorder=20)

def save(fig, name, svg=False):
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=200)
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    if svg:
        fig.savefig(os.path.join(OUT, name + ".svg"))
    SHEETS.append(fig)
    print("  planche", name)

def panel_heading(T, y, s):
    T(PANEL_X + 8, y, s, 7.6, TERRE_CUITE, fontproperties=FP_MEDIUM)

def legend_rows(fig, T, y, rows):
    """rows : (dessinateur(ax), libellé)."""
    for k, (draw, label) in enumerate(rows):
        yy = y + k * 5.4
        ax = fig.add_axes([(PANEL_X + 8) / SHEET_W, 1 - (yy + 3.2) / SHEET_H, 11 / SHEET_W, 3.2 / SHEET_H])
        ax.set_xlim(0, 11); ax.set_ylim(0, 3.2); ax.axis("off")
        draw(ax)
        T(PANEL_X + 22, yy + 0.2, label, 6.4, ENCRE)
    return y + len(rows) * 5.4

def table(fig, T, y, header, rows, widths, total=None):
    x0 = PANEL_X + 8
    W = sum(widths)
    fig.add_artist(Rectangle((x0 / SHEET_W, 1 - (y + 5) / SHEET_H), W / SHEET_W, 5 / SHEET_H, transform=fig.transFigure, fc=TERRE_CUITE, ec="none"))
    xs = np.cumsum([0] + widths)
    for k, h in enumerate(header):
        T(x0 + xs[k] + 1.5 if k < len(header) - 1 else x0 + xs[k + 1] - 1.5, y + 1.1, h, 6.2, BLANC_CHAUX,
          ha="left" if k < len(header) - 1 else "right", fontproperties=FP_MEDIUM)
    yy = y + 5
    for i, r in enumerate(rows + ([total] if total else [])):
        last = total and i == len(rows)
        if i % 2 == 0 or last:
            fig.add_artist(Rectangle((x0 / SHEET_W, 1 - (yy + 4.6) / SHEET_H), W / SHEET_W, 4.6 / SHEET_H, transform=fig.transFigure,
                                     fc=SABLE if last else BLANC_CHAUX, ec="none"))
        for k, c in enumerate(r):
            T(x0 + xs[k] + 1.5 if k < len(r) - 1 else x0 + xs[k + 1] - 1.5, yy + 1.0, c, 6.3, ENCRE,
              ha="left" if k < len(r) - 1 else "right", fontproperties=FP_MEDIUM if last else None)
        yy += 4.6
    return yy

# ============================================================== données communes (lues dans l'IFC)
def by_name(sub, cls=None):
    return [m for m in MESHES if sub in m.name and (cls is None or m.cls == cls)]

def space_rows():
    rows = []
    for m in sorted(SPACES, key=lambda m: m.name):
        rows.append((m.name, m.el.LongName, f"{qto(m.el, 'NetFloorArea'):.2f}".replace(".", ",") + " m²"))
    tot = sum(qto(m.el, "NetFloorArea") for m in SPACES)
    return rows, ("", "Total surfaces nettes", f"{tot:.2f}".replace(".", ",") + " m²")

def poche_legend(existing=False):
    def d(ax):
        ax.add_patch(Rectangle((0.5, 0.6), 10, 2, fc=NOIR, ec=NOIR, lw=0.5))
        if existing:
            ax.add_patch(Rectangle((0.5, 0.6), 10, 2, fc="none", ec="#9A928B", lw=0.01, hatch="////"))
    return d

def line_legend(color=NOIR, lw=LW_M, ls="-"):
    return lambda ax: ax.plot([0.5, 10.5], [1.6, 1.6], color=color, lw=lw, ls=ls)

def box_legend(fc, ec=NOIR, lw=LW_M, hatch=None, ls="-"):
    return lambda ax: ax.add_patch(Rectangle((0.5, 0.6), 10, 2, fc=fc, ec=ec, lw=lw, hatch=hatch, ls=ls))

TREE = by_name("Arbre à livres")[0]
TREE_C = (TREE.bb[0][:2] + TREE.bb[1][:2]) / 2
EXT = np.array([min(m.bb[0][0] for m in MESHES if m.existing and m.cls == "IfcWall"),
                min(m.bb[0][1] for m in MESHES if m.cls == "IfcBeam"),
                max(m.bb[1][0] for m in MESHES if m.existing and m.cls == "IfcWall"),
                max(m.bb[1][1] for m in MESHES if m.existing and m.cls == "IfcWall")])
Z_FP = min(m.bb[0][2] for m in MESHES if m.cat == "ceiling")
Z_DALLE = max(m.bb[1][2] for m in MESHES if m.cls == "IfcSlab")
H_CUT = 1.00
X_AA = 4.60
Y_BB = 2.90
print("emprise", EXT.round(3), "faux-plafond", round(Z_FP, 3), "arbre", TREE_C.round(3))

def mitoyens_plan(ax, y0, y1):
    for xa, xb in ((EXT[0] - 1.6, EXT[0]), (EXT[2], EXT[2] + 1.6)):
        ax.add_patch(Rectangle((xa, y0), xb - xa, y1 - y0, fc="white", ec="none", hatch="////", lw=0, zorder=1))
        ax.patches[-1].set_edgecolor("#B9B1A8")
        ax.plot([xa, xb], [y0, y0], color=TAUPE, lw=LW_F, zorder=1.1)
    ax.text(EXT[0] - 0.8, (y0 + y1) / 2, "IMMEUBLE MITOYEN", rotation=90, fontsize=5.6, color=TAUPE, ha="center", va="center",
            zorder=2, bbox=dict(fc="white", ec="none", pad=1.2))
    ax.text(EXT[2] + 0.8, (y0 + y1) / 2, "IMMEUBLE MITOYEN", rotation=90, fontsize=5.6, color=TAUPE, ha="center", va="center",
            zorder=2, bbox=dict(fc="white", ec="none", pad=1.2))

# ================================================================================ 01 PLAN RDC
def plan_rdc():
    F = frame(np.eye(3), (0, 0, H_CUT))
    fig, T = new_sheet(1, "Plan du rez-de-chaussée", "Esquisse V5  ·  Échelle 1/50 (A3)  ·  Plan de coupe à +1,00",
                       ["Local RDC d’un immeuble existant (logements aux étages) — un seul niveau, sans escalier ni toiture",
                        "Dessin généré par script depuis la maquette IFC4 (sections exactes des maillages)"])
    X0, Y0, scale = -1.75, -3.35, 50
    ax = drawing_axes(fig, 12, 26, 276, 262, X0, Y0, scale)
    # contexte : rue, trottoir, arbres, mitoyens
    site = [m for m in SOLIDS if m.cat == "site"]
    for m in site:
        g = footprint(m, frame(np.eye(3), (0, 0, 0)), zmax=0.3)
        if "Chaussée" in m.name:
            draw_geom(ax, g.intersection(sbox(X0, Y0, X0 + 6, 10)) if g else None, fc="#EDEAE5", ec="none", zorder=0.5)
        elif "Trottoir" in m.name:
            draw_geom(ax, g, fc="#F6F3EE", ec=TAUPE, lw=LW_F, zorder=0.6)
        elif "Bordure" in m.name:
            draw_geom(ax, g, fc="#E2DDD5", ec=TAUPE, lw=LW_F, zorder=0.7)
    for m in site:
        if m.cls == "IfcGeographicElement":
            c = (m.bb[0][:2] + m.bb[1][:2]) / 2
            r = (m.bb[1][0] - m.bb[0][0]) / 2
            ax.add_patch(MPoly(wobble_circle(c[0], c[1], r * 0.98, seed=int(c[0] * 10)), closed=True, fc=OLIVE, ec=OLIVE, lw=LW_F, alpha=0.12, zorder=12))
            ax.add_patch(MPoly(wobble_circle(c[0], c[1], r * 0.98, seed=int(c[0] * 10)), closed=True, fc="none", ec=OLIVE, lw=LW_F, zorder=12))
            ax.add_patch(Rectangle((c[0] - 0.55, c[1] - 0.55), 1.1, 1.1, fc="none", ec=TAUPE, lw=LW_F, zorder=1))
            ax.add_patch(Circle(c, 0.13, fc="white", ec=OLIVE, lw=LW_M, zorder=12.1))
    ax.text(3.3, -2.25, "TROTTOIR", fontsize=6, color=TAUPE, ha="center", fontproperties=FP_MEDIUM, zorder=13)
    ax.text(3.3, -3.12, "RUE", fontsize=6.5, color=TAUPE, ha="center", fontproperties=FP_MEDIUM, zorder=13)
    mitoyens_plan(ax, EXT[1], 8.25)
    # sols : tomettes (coin jeunesse), terrazzo à joints laiton (ailleurs)
    rr = random.Random(1)
    for m in SOLIDS:
        if m.cat != "floor":
            continue
        g = footprint(m, frame(np.eye(3), (0, 0, 0)), zmin=-0.01)
        if g is None:
            continue
        minx, miny, maxx, maxy = g.bounds
        if "tomette" in m.name:
            lines = [LineString([(x, miny), (x, maxy)]) for x in np.arange(0.09, maxx, 0.20)] + \
                    [LineString([(minx, y), (maxx, y)]) for y in np.arange(0.12, maxy, 0.20)]
            col = "#D7B9A9"
        else:
            lines = [LineString([(x, miny), (x, maxy)]) for x in np.arange(0.09 + 1.20, maxx, 1.20)] + \
                    [LineString([(minx, y), (maxx, y)]) for y in np.arange(0.12 + 1.20, maxy, 1.20)]
            col = "#C9B48C"
            pts = [(rr.uniform(minx, maxx), rr.uniform(miny, maxy)) for _ in range(int(g.area * 55))]
            pts = [p for p in pts if g.contains(Point(p))]
            if pts:
                ax.scatter(*zip(*pts), s=0.35, c="#C6A890", lw=0, zorder=1.2)
        for ln in lines:
            draw_geom(ax, ln.intersection(g), ec=col, lw=LW_F * 0.8, zorder=1.3)
    # projections sous le plan de coupe (mobilier en silhouette, éléments bas)
    below = [m for m in SOLIDS if m.cat not in ("floor", "ceiling", "site", "light") and m.cls != "IfcSlab" and m.bb[0][2] < H_CUT]
    def st(m):
        if m.cat in ("furn", "door"):
            return {"fill": "white", "lw": LW_F}
        return {"fill": "white", "lw": LW_F}
    painter_ortho(ax, F, below, style=st, zorder=3)
    # silhouettes du mobilier (contour moyen)
    for m in SOLIDS:
        if m.cat == "furn" and m.bb[0][2] < H_CUT and not (m.bb[0][2] < H_CUT < m.bb[1][2]):
            g = footprint(m, F, zmax=0)
            draw_geom(ax, g, fc="none", ec=NOIR, lw=LW_M, zorder=4)
    draw_sections(ax, F, [m for m in SOLIDS if m.cat not in ("site",)], h=EPS)
    # débattements de portes (représentation Plan/Annotation de l'IFC)
    for d in f.by_type("IfcDoor"):
        for rep in d.Representation.Representations:
            if rep.RepresentationIdentifier == "Annotation":
                for cs in rep.Items:
                    for k, pl in enumerate(cs.Elements):
                        pts = np.array([p.Coordinates for p in pl.Points]) / 1000
                        ax.plot(pts[:, 0], pts[:, 1], color=NOIR, lw=LW_M if k % 2 == 0 else LW_F, zorder=9,
                                ls="-" if k % 2 == 0 else (0, (2, 1.2)))
    # au-dessus du plan de coupe (tirets) : poutre, coupole, canopée, splits, liaisons, claustra d'imposte
    over = dict(ls=(0, (4, 2)), lw=LW_F, ec=NOIR, zorder=10)
    beam = by_name("Poutre", "IfcBeam")[0]
    ax.plot([EXT[0] + 0.25, EXT[2] - 0.25], [beam.bb[1][1]] * 2, color=NOIR, lw=LW_F, ls=(0, (4, 2)), zorder=10)
    rive = by_name("rive cintrée")[0]
    rc = (rive.bb[0][:2] + rive.bb[1][:2]) / 2
    ax.add_patch(Circle(rc, (rive.bb[1][0] - rive.bb[0][0]) / 2, fc="none", ec=NOIR, lw=LW_F, ls=(0, (4, 2)), zorder=10))
    canopy_r = max(np.hypot(*(TREE.v[:, :2] - TREE_C).T))
    ax.add_patch(Circle(TREE_C, canopy_r, fc="none", ec=IROKO, lw=LW_F, ls=(0, (4, 2)), zorder=10))
    for m in by_name("Split", "IfcUnitaryEquipment"):
        draw_geom(ax, footprint(m, F), fc="white", ec=NOIR, lw=LW_F, ls=(0, (4, 2)), zorder=10)
        c = (m.bb[0] + m.bb[1]) / 2
        ax.text(c[0] - (0.28 if c[0] > 6 else 0), c[1] - (0.0 if c[0] > 6 else 0.20), m.el.Tag, fontsize=5.6, ha="center", va="center",
                color=INDIGO, fontproperties=FP_MEDIUM, zorder=11)
    for m in by_name("Liaisons frigorifiques"):
        pts = [np.array(p.Coordinates) / 1000 for p in m.el.Representation.Representations[0].Items[0].Directrix.Points]
        pts = np.array(pts)
        ax.plot(pts[:, 0], pts[:, 1], color=INDIGO, lw=LW_M, ls=(0, (6, 1.5, 1, 1.5)), zorder=10.5)
        ax.plot(*pts[-1, :2], marker=">", ms=2.5, color=INDIGO, zorder=10.5)
    # réservations Ø100 (ouvertures) dans les murs
    for o in f.by_type("IfcOpeningElement"):
        if (o.Name or "").startswith("Réservation"):
            s_ = ifcopenshell.geom.create_shape(settings, o)
            v = np.array(s_.geometry.verts).reshape(-1, 3)
            c = (v.min(0) + v.max(0)) / 2
            ax.add_patch(Circle(c[:2], 0.07, fc="white", ec=INDIGO, lw=LW_M, zorder=11))
            ax.plot([c[0] - 0.05, c[0] + 0.05], [c[1] - 0.05, c[1] + 0.05], color=INDIGO, lw=LW_F, zorder=11.1)
    # dégagement 1,00 m devant le TD
    td = by_name("Tableau divisionnaire", "IfcElectricDistributionBoard")[0]
    x_face = td.bb[0][0]
    ax.add_patch(Rectangle((x_face - 1.0, td.bb[0][1]), 1.0, td.bb[1][1] - td.bb[0][1], fc=OLIVE, alpha=0.10, ec="none", zorder=2.5))
    ax.add_patch(Rectangle((x_face - 1.0, td.bb[0][1]), 1.0, td.bb[1][1] - td.bb[0][1], fc="none", ec=OLIVE, lw=LW_F, ls=(0, (3, 1.5)), zorder=10))
    ax.text(x_face - 0.5, (td.bb[0][1] + td.bb[1][1]) / 2, "TD\ndégagement 1,00", fontsize=4.8, color=OLIVE, ha="center", va="center", zorder=11)
    # passage libre autour de l'arbre (0,90)
    ax.add_patch(Circle(TREE_C, 0.45 + 0.90, fc="none", ec=OLIVE, lw=LW_F, ls=(0, (1, 1.5)), zorder=10))
    # étiquettes des pièces
    furn_fp = unary_union([footprint(m, frame(np.eye(3), (0, 0, 0)), zmax=2.2) or Polygon() for m in SOLIDS
                           if m.cat in ("furn",) and m.bb[0][2] < 1.0 and "Arbre" not in m.name] +
                          [Point(TREE_C).buffer(0.55)])
    OFFS = {"05": (0.0, 0.10), "06": (0.25, -0.20), "07": None}
    for m in SPACES:
        g = footprint(m, frame(np.eye(3), (0, 0, 0)))
        free = g.difference(furn_fp.buffer(0.12))
        try:
            p = polylabel(max(getattr(free, "geoms", [free]), key=lambda q: q.area), 0.01)
        except Exception:  # noqa: BLE001
            p = g.representative_point()
        num = m.name
        area = qto(m.el, "NetFloorArea")
        ar = f"{area:.2f}".replace(".", ",") + " m²"
        if num == "07":
            px, py = 2.65, 7.06
        elif num == "03":
            px, py = TREE_C[0] + 0.0, TREE_C[1] - 1.05
        elif num == "05":
            px, py = 2.05, 6.20
        else:
            px, py = p.x, p.y
        small = num in ("05", "06", "07")
        ax.add_patch(Circle((px, py + (0.20 if not small else 0.15)), 0.13 if not small else 0.10, fc=TERRE_CUITE, ec="none", zorder=14))
        ax.text(px, py + (0.20 if not small else 0.15), num, fontsize=5.6 if not small else 4.6, color="white", ha="center", va="center",
                fontproperties=FP_MEDIUM, zorder=14.1)
        if num == "07":
            continue
        name = m.el.LongName.split(" — ")[0]
        ax.text(px, py, name, fontsize=6.8 if not small else 5.0, color=ENCRE, ha="center", va="top", zorder=14,
                fontproperties=FP_TITRE if not small else None, bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.8))
        ax.text(px, py - (0.30 if not small else 0.21), ar, fontsize=5.6 if not small else 4.6, color=TERRE_CUITE, ha="center", va="top",
                zorder=14, bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.8))
    # repères de mobilier (pastilles iroko)
    for m in SOLIDS:
        tag = getattr(m.el, "Tag", None)
        if m.cat == "furn" and m.cls == "IfcFurniture" and tag and tag not in ("L01",):
            c = (m.bb[0][:2] + m.bb[1][:2]) / 2
            if tag in ("C01",) or "Tabouret" in m.name:
                continue
            ax.add_patch(Circle(c, 0.085, fc=IROKO, ec="none", zorder=13))
            ax.text(c[0], c[1], tag, fontsize=3.4, color="white", ha="center", va="center", zorder=13.1, fontproperties=FP_MEDIUM)
    c = TREE_C
    ax.add_patch(Circle(c, 0.11, fc=IROKO, ec="white", lw=0.5, zorder=13))
    ax.text(c[0], c[1], "L01", fontsize=4, color="white", ha="center", va="center", zorder=13.1, fontproperties=FP_MEDIUM)
    # cotes
    E = EXT
    dim(ax, (E[0], E[3]), (E[2], E[3]), 0.55, scale=scale)
    dim(ax, (E[0], E[1]), (E[0], E[3]), 0.55, scale=scale)
    xi0 = min(m.bb[1][0] for m in MESHES if m.existing and m.cls == "IfcWall" and m.bb[1][0] < 1)
    xi1 = max(m.bb[0][0] for m in MESHES if m.existing and m.cls == "IfcWall" and m.bb[0][0] > 5)
    dim(ax, (xi0, E[3]), (xi1, E[3]), 0.25, text=f"{xi1 - xi0:.2f}".replace(".", ",") + " nu intérieur", scale=scale, side=0, fs=5.0)
    porte = [m for m in MESHES if m.cls == "IfcDoor" and m.el.Tag == "P01"][0]
    dim(ax, (porte.bb[0][0], -0.12), (porte.bb[1][0], -0.12), -0.0, text="1,35 (0,90 + 0,45)", scale=scale, side=-1)
    dim(ax, (TREE_C[0] - 0.45 - 0.90 - 0.0, TREE_C[1] + 0.05), (TREE_C[0] - 0.45, TREE_C[1] + 0.05), 0.0, text="min. 0,90", scale=scale, side=0)
    # repères de coupe / élévations
    def cut_mark(p, lab, d):
        ax.add_patch(Circle(p, 0.20, fc="white", ec=ENCRE, lw=LW_M, zorder=16))
        ax.text(p[0], p[1], lab, fontsize=6.2, ha="center", va="center", color=ENCRE, fontproperties=FP_MEDIUM, zorder=16.1)
        q = (p[0] + d[0] * 0.42, p[1] + d[1] * 0.42)
        ax.add_patch(MPoly([(p[0] + d[0] * 0.20 - d[1] * 0.14, p[1] + d[1] * 0.20 + d[0] * 0.14),
                            (p[0] + d[0] * 0.20 + d[1] * 0.14, p[1] + d[1] * 0.20 - d[0] * 0.14), q], closed=True, fc=ENCRE, ec="none", zorder=16))
    ax.plot([X_AA, X_AA], [-1.05, -0.35], color=ENCRE, lw=LW_G, zorder=16)
    ax.plot([X_AA, X_AA], [7.85, 8.35], color=ENCRE, lw=LW_G, zorder=16)
    ax.plot([X_AA, X_AA], [-0.35, 7.85], color=ENCRE, lw=LW_F, ls=(0, (8, 2, 1, 2)), zorder=16)
    cut_mark((X_AA, -1.25), "A", (-1, 0)); cut_mark((X_AA, 8.55), "A", (-1, 0))
    ax.plot([-0.55, -0.10], [Y_BB, Y_BB], color=ENCRE, lw=LW_G, zorder=16)
    ax.plot([6.70, 7.15], [Y_BB, Y_BB], color=ENCRE, lw=LW_G, zorder=16)
    cut_mark((-0.78, Y_BB), "B", (0, 1)); cut_mark((7.38, Y_BB), "B", (0, 1))
    ax.add_patch(MPoly([(3.30, -2.55), (3.10, -2.85), (3.50, -2.85)], closed=True, fc=ENCRE, ec="none", zorder=16))
    ax.text(3.62, -2.72, "E1  élévation de la devanture", fontsize=5.4, color=ENCRE, va="center", zorder=16)
    north_arrow(ax, 7.75, 7.55)
    scale_bar(ax, -1.45, -3.25, scale)
    # panneau : espaces, légende, technique
    panel_heading(T, 52, "ESPACES — SURFACES NETTES (Qto_SpaceBaseQuantities)")
    rows, tot = space_rows()
    y = table(fig, T, 57, ["N°", "Espace", "Surface"], [list(r) for r in rows], [10, 82, 20], total=list(tot))
    panel_heading(T, y + 5, "LÉGENDE")
    y = legend_rows(fig, T, y + 9, [
        (poche_legend(True), "Existant porteur — ne pas toucher (voiles, poteaux, poutre)"),
        (poche_legend(False), "Élément coupé neuf : cloison, doublage, coffrage, claustra"),
        (box_legend("white", lw=LW_M), "Mobilier en silhouette (repère iroko, cf. nomenclature IFC)"),
        (line_legend(NOIR, LW_F, (0, (4, 2))), "Au-dessus du plan de coupe : poutre, coupole Ø 2,80, splits"),
        (line_legend(INDIGO, LW_M, (0, (6, 1.5, 1, 1.5))), "Liaisons frigorifiques (plénum) ; réservation Ø 100 (cercle)"),
        (box_legend((0.37, 0.48, 0.29, 0.12), ec=OLIVE, lw=LW_F, ls=(0, (3, 1.5))), "Dégagements : 1,00 devant TD, 0,90 autour de l’arbre"),
        (lambda a: [a.plot([0.5 + k * 2.5, 0.5 + k * 2.5], [0.6, 2.6], color="#C9B48C", lw=LW_F) for k in range(5)], "Terrazzo à joints laiton  /  tomettes 20 × 20"),
    ])
    panel_heading(T, y + 4, "TECHNIQUE RÉSERVÉE (hypothèses ESQ Ahoua)")
    notes = ["Placard technique 0,60 × 0,40 net, porte pleine : arrivée élec., baie 9U, liaisons clim",
             "TD encastré 0,60 × 0,25 près de l’entrée, 1,00 m dégagé, loin des points d’eau",
             "2 splits muraux ~9 000 BTU (S1, S2) en hauteur sur murs pleins, hors aplomb des tables",
             "Liaisons en plénum vers la façade arrière / courette (jamais en toiture), Ø 100",
             "2 descentes EU/EV des logements en coffrages acoustiques (BA13 ×2 + LM 45)",
             "Pas de local TGBT ni de groupe électrogène"]
    for k, s in enumerate(notes):
        T(PANEL_X + 8, y + 9 + k * 4.4, "—", 6.3, TAUPE)
        T(PANEL_X + 12, y + 9 + k * 4.4, s, 6.2, ENCRE)
    save(fig, "DECIMO_ESQ_V5_01_Plan_RDC", svg=True)

# ================================================================================ 02 COUPE AA
def context_building_section(ax, y0, y1, z0):
    """Immeuble existant au-dessus (contexte dessiné, hors maquette)."""
    for k in range(2):
        zb = z0 + k * 3.30
        ax.add_patch(Rectangle((y0, zb), y1 - y0, 3.30, fc="none", ec="#B9B1A8", lw=LW_F, zorder=1, ls=(0, (3, 2))))
        ax.add_patch(Rectangle((y0, zb + 3.10), y1 - y0, 0.20, fc="#E4DED6", ec="#B9B1A8", lw=LW_F, zorder=1))
    ax.text((y0 + y1) / 2, z0 + 1.6, "LOGEMENTS EXISTANTS — HORS PÉRIMÈTRE", fontsize=5.8, color=TAUPE, ha="center", va="center",
            fontproperties=FP_MEDIUM, zorder=2)

def coupe_aa():
    F = frame([[0, 1, 0], [0, 0, 1], [1, 0, 0]], (X_AA, 0, 0))
    fig, T = new_sheet(2, "Coupe AA — longitudinale", "Esquisse V5  ·  Échelle 1/50 (A3)  ·  Regard vers l’ouest, plan de coupe x = 4,60",
                       ["Coupe à travers la porte d’entrée, l’arbre à livres, la coupole et la niche banquette",
                        "Dessin généré par script depuis la maquette IFC4"])
    X0, Y0, scale = -3.4, -1.6, 50
    ax = drawing_axes(fig, 12, 32, 276, 230, X0, Y0, scale)
    context_building_section(ax, EXT[1], EXT[3], Z_DALLE)
    ax.text(EXT[3] + 0.75, 1.7, "COURETTE / FAÇADE ARRIÈRE", rotation=90, fontsize=5.6, color=TAUPE, ha="center", va="center")
    ax.plot([X0 + 0.2, EXT[3] + 1.5], [-0.37, -0.37], color=TAUPE, lw=LW_F, zorder=1)
    # sol naturel
    ax.add_patch(Rectangle((X0 + 0.2, -1.2), EXT[3] + 1.3 - X0, -0.27 + 1.2 - 0.2, fc="white", ec="none", hatch="..", zorder=0.4))
    ax.patches[-1].set_edgecolor("#CFC8BE")
    vis = SOLIDS
    def st(m):
        if m.cat == "site" and m.cls == "IfcGeographicElement":
            return {"fill": (0.37, 0.48, 0.29, 0.10), "edge": OLIVE}
        return {}
    painter_ortho(ax, F, [m for m in vis if not (m.cat == "site" and m.cls == "IfcGeographicElement")], style=st, tint_k=0.30, zorder=3)
    painter_ortho(ax, F, [m for m in vis if m.cat == "site" and m.cls == "IfcGeographicElement"], style=st, zorder=6, clip=False)
    draw_sections(ax, F, SOLIDS, h=EPS)
    # niveaux
    def level(z, lab, x=EXT[3] + 1.6):
        ax.plot([x - 0.15, x + 0.15], [z, z], color=ENCRE, lw=LW_M, zorder=20)
        ax.add_patch(MPoly([(x, z), (x - 0.09, z + 0.13), (x + 0.09, z + 0.13)], closed=True, fc=ENCRE, ec="none", zorder=20))
        ax.text(x + 0.22, z, lab, fontsize=5.6, va="center", color=ENCRE, zorder=20)
    level(0.0, "±0,00 sol fini")
    level(Z_FP, f"+{Z_FP:.2f} faux-plafond".replace(".", ","))
    level(3.30, "+3,30 sous-face dalle (coupole)")
    level(Z_DALLE, f"+{Z_DALLE:.2f} dalle existante".replace(".", ","))
    level(-0.02, "", x=-1.2)
    ax.text(-1.2, 0.12, "trottoir −0,02", fontsize=5.4, color=TAUPE, ha="center")
    # annotations
    def note(xy, txt, xyt, ha="left"):
        ax.annotate(txt, xy=xy, xytext=xyt, fontsize=5.6, color=ENCRE, ha=ha, va="center", zorder=22,
                    arrowprops=dict(arrowstyle="-", lw=LW_F, color=TERRE_CUITE, shrinkA=1, shrinkB=1),
                    bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))
    note((TREE_C[1] - 1.0, 3.05), "Canopée bois de l’arbre à livres\ndans la coupole indigo (anneau LED)", (1.6, 4.25))
    note((TREE_C[1], 1.2), "Arbre à livres L01 : fût + 6 plateaux Ø 0,90", (2.0, 0.55))
    note((6.95, 3.10), "Plénum 45 cm : liaisons S2 › placard › courette", (7.0, 4.30), ha="center")
    note((0.07, 2.50), "Devanture vitrée sous poutre\nexistante, imposte à claustra", (-2.9, 2.25))
    note((7.25, 0.9), "Niche banquette\n(coussins indigo)", (7.45, 1.6), ha="left")
    dim(ax, (EXT[1], -0.75), (EXT[3], -0.75), 0.0, scale=scale, side=-1)
    dim(ax, (-0.6, 0.0), (-0.6, Z_FP), 0.0, text=f"{Z_FP:.2f}".replace(".", ","), scale=scale, side=0)
    scale_bar(ax, -3.1, -1.45, scale)
    panel_heading(T, 52, "PRINCIPES")
    lines = ["Un seul niveau : sol fini ±0,00, dalle haute existante conservée (logements au-dessus).",
             "Faux-plafond acoustique en fibres de bois à +2,85 ; plénum de 45 cm pour les réseaux.",
             "Au-dessus de l’arbre, le plafond s’ouvre en coupole Ø 2,80 jusqu’à la dalle (+3,30),",
             "peinte indigo : la canopée bois s’y épanouit, éclairée par un anneau LED 2700 K.",
             "Devanture : menuiserie acier encre sous la poutre existante, imposte en claustra",
             "terre cuite Adinkra ; porte 0,90 + 0,45 ouvrant vers l’intérieur, seuil plat.",
             "Descentes EU/EV des logements gardées en place, en coffrages acoustiques."]
    for k, s in enumerate(lines):
        T(PANEL_X + 8, 57 + k * 4.6, s, 6.4, ENCRE)
    panel_heading(T, 96, "LÉGENDE")
    legend_rows(fig, T, 100, [(poche_legend(True), "Existant porteur coupé (dalle, poutre, voiles)"),
                              (poche_legend(False), "Élément neuf coupé"),
                              (box_legend("white"), "Mobilier coupé en silhouette"),
                              (line_legend(NOIR, LW_F), "Vu au-delà du plan de coupe (traits fins)")])
    save(fig, "DECIMO_ESQ_V5_02_Coupe_AA", svg=True)

# ================================================================================ 03 ÉLÉVATION DEVANTURE
def elevation_devanture():
    F = frame([[1, 0, 0], [0, 0, 1], [0, -1, 0]], (0, -3.2, 0))
    fig, T = new_sheet(3, "Élévation de la devanture sur rue", "Esquisse V5  ·  Échelle 1/50 (A3)  ·  Façade sud, vue depuis la rue",
                       ["Devanture dans la baie existante (poteaux P1-P2-P3, poutre PT1) ; immeuble au-dessus en contexte",
                        "Dessin généré par script depuis la maquette IFC4 (arbres d’alignement en transparence)"])
    X0, Y0, scale = -2.9, -1.0, 50
    ax = drawing_axes(fig, 12, 30, 276, 236, X0, Y0, scale)
    # immeuble existant et mitoyens (contexte dessiné)
    for k in range(2):
        zb = Z_DALLE + k * 3.30
        ax.add_patch(Rectangle((EXT[0], zb), EXT[2] - EXT[0], 3.30, fc="#F7F4EF", ec="#B9B1A8", lw=LW_F, zorder=0.5))
        for xa in (0.55, 2.55, 4.55):
            ax.add_patch(Rectangle((xa, zb + 0.95), 1.4, 1.55, fc="white", ec="#B9B1A8", lw=LW_F, zorder=0.6))
            ax.add_patch(Rectangle((xa - 0.05, zb + 0.90), 1.5, 0.06, fc="#E4DED6", ec="#B9B1A8", lw=LW_F, zorder=0.6))
        ax.add_patch(Rectangle((EXT[0] - 0.02, zb + 3.10), EXT[2] - EXT[0] + 0.04, 0.20, fc="#E4DED6", ec="#B9B1A8", lw=LW_F, zorder=0.6))
    ax.text((EXT[0] + EXT[2]) / 2, Z_DALLE + 3.30 * 2 + 0.25, "IMMEUBLE EXISTANT — LOGEMENTS (contexte, hors périmètre)", fontsize=5.6,
            color=TAUPE, ha="center", fontproperties=FP_MEDIUM)
    for xa, xb in ((X0, EXT[0]), (EXT[2], X0 + 13.8)):
        ax.add_patch(Rectangle((xa, -0.02), xb - xa, 8.4, fc="white", ec="none", hatch="////", zorder=0.3))
        ax.patches[-1].set_edgecolor("#D3CCC4")
    ax.text(EXT[0] - 1.25, 4.5, "MITOYEN", rotation=90, fontsize=5.6, color=TAUPE, ha="center", va="center",
            bbox=dict(fc="white", ec="none", pad=1))
    ax.text(EXT[2] + 1.25, 4.5, "MITOYEN", rotation=90, fontsize=5.6, color=TAUPE, ha="center", va="center",
            bbox=dict(fc="white", ec="none", pad=1))
    def st(m):
        if m.cat == "site" and m.cls == "IfcGeographicElement":
            return {"fill": (0.37, 0.48, 0.29, 0.08), "edge": OLIVE}
        if m.cat == "site":
            return {"fill": "white"}
        return {}
    painter_ortho(ax, F, [m for m in SOLIDS if not (m.cat == "site" and m.cls == "IfcGeographicElement") and m.cat != "ceiling"],
                  style=st, tint_k=0.55, zorder=3, clip=True)
    painter_ortho(ax, F, [m for m in SOLIDS if m.cat == "site" and m.cls == "IfcGeographicElement"], style=st, zorder=6, clip=False)
    # silhouette appuyée de la baie et sol
    ax.plot([X0 + 0.2, X0 + 13.6], [-0.02, -0.02], color=NOIR, lw=LW_G, zorder=7)
    for m in SOLIDS:
        if m.cls in ("IfcColumn", "IfcBeam") and m.bb[0][1] < 0:
            draw_geom(ax, footprint(m, F), fc="none", ec=NOIR, lw=LW_M, zorder=7)
    def note(xy, txt, xyt, ha="left"):
        ax.annotate(txt, xy=xy, xytext=xyt, fontsize=5.6, color=ENCRE, ha=ha, va="center", zorder=22,
                    arrowprops=dict(arrowstyle="-", lw=LW_F, color=TERRE_CUITE, shrinkA=1, shrinkB=1),
                    bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))
    note((3.3, 3.08), "Enseigne : bandeau indigo, lettres\nDECIMO sable rétroéclairées", (7.4, 3.6))
    note((1.2, 2.5), "Claustra terre cuite Adinkra\n(Eban / Nsoromma) en imposte", (-2.6, 3.3))
    note((4.0, 1.2), "Porte vitrée 0,90 + 0,45\nseuil plat", (7.4, 1.7))
    note((1.0, 0.55), "Banc de vitrine\n(coin jeunesse)", (-2.6, 1.0))
    note((0.0, 1.8), "Poteau existant", (-2.6, 2.0))
    note((5.95, 4.2), "Arbre d’alignement\n(contexte)", (7.6, 5.0))
    dim(ax, (EXT[0], -0.55), (EXT[2], -0.55), 0.0, scale=scale, side=-1)
    dim(ax, (6.95, 0.0), (6.95, 2.85), 0.0, text="2,85", scale=scale, side=0)
    dim(ax, (6.95, 2.85), (6.95, 3.30), 0.0, text="0,45", scale=scale, side=0)
    scale_bar(ax, -2.6, -0.85, scale)
    panel_heading(T, 52, "DEVANTURE — PRINCIPES")
    lines = ["Pas de façade cintrée : la devanture reste dans la baie existante, sous la poutre.",
             "Menuiserie acier thermolaqué encre, vitrages feuilletés, soubassement de 10 cm.",
             "Imposte : claustra en modules terre cuite 20 × 20 à motifs Adinkra",
             "« Eban » (la clôture) et « Nsoromma » (l’étoile) ; Gye Nyame exclu.",
             "À l’ouest, banc de vitrine en iroko (coin jeunesse) ; à l’est, accueil.",
             "Enseigne sur la poutre : seule touche indigo de la façade.",
             "Fixations sur la structure existante légères, à valider (syndic, BET)."]
    for k, s in enumerate(lines):
        T(PANEL_X + 8, 57 + k * 4.6, s, 6.4, ENCRE)
    # module claustra
    T(PANEL_X + 8, 96, "MODULES DE CLAUSTRA (20 × 20 cm)", 7.6, TERRE_CUITE, fontproperties=FP_MEDIUM)
    blocks = [m for m in SOLIDS if m.cls == "IfcShadingDevice"][0]
    axb = fig.add_axes([(PANEL_X + 8) / SHEET_W, 1 - 150 / SHEET_H, 50 / SHEET_W, 50 / SHEET_H])
    axb.axis("off"); axb.set_aspect("equal")
    Fb = frame([[1, 0, 0], [0, 0, 1], [0, -1, 0]], (0, -1, 0))
    painter_ortho(axb, Fb, [blocks], clip=False, tint_k=1.0, zorder=3)
    axb.set_xlim(0.2675, 0.2675 + 0.80); axb.set_ylim(2.20, 2.20 + 0.60)
    T(PANEL_X + 62, 104, "Alternance en damier des deux modules :", 6.4, ENCRE)
    T(PANEL_X + 62, 109, "— Eban : carré, losange et cœur plein", 6.4, ENCRE)
    T(PANEL_X + 62, 114, "— Nsoromma : étoile à 8 branches évidée", 6.4, ENCRE)
    T(PANEL_X + 62, 119, "Terre cuite, ép. 8 à 10 cm, pose collée", 6.4, TAUPE)
    T(PANEL_X + 62, 124, "Même module pour le claustra intérieur", 6.4, TAUPE)
    save(fig, "DECIMO_ESQ_V5_03_Elevation_devanture", svg=True)

# ================================================================================ 04 ÉLÉVATION INTÉRIEURE
def elevation_interieure():
    F = frame([[1, 0, 0], [0, 0, 1], [0, -1, 0]], (0, Y_BB, 0))
    fig, T = new_sheet(4, "Élévation intérieure — mur du fond (coupe BB)", "Esquisse V5  ·  Échelle 1/30 (A3)  ·  Regard vers le nord, plan de coupe y = 2,90",
                       ["Arbre à livres, niches cintrées, claustra Adinkra, bloc sanitaire et splits",
                        "Dessin généré par script depuis la maquette IFC4"])
    X0, Y0, scale = -0.95, -0.75, 30
    ax = drawing_axes(fig, 12, 52, 272, 160, X0, Y0, scale)
    painter_ortho(ax, F, [m for m in SOLIDS if m.cat != "site"], tint_k=0.55, zorder=3, max_depth=6)
    draw_sections(ax, F, [m for m in SOLIDS if m.cat != "site"], h=EPS)
    def note(xy, txt, xyt, ha="left"):
        ax.annotate(txt, xy=xy, xytext=xyt, fontsize=5.8, color=ENCRE, ha=ha, va="center", zorder=22,
                    arrowprops=dict(arrowstyle="-", lw=LW_F, color=TERRE_CUITE, shrinkA=1, shrinkB=1),
                    bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.92))
    note((TREE_C[0] + 0.9, 3.05), "Canopée bois Ø 2,64 et anneau LED\ndans la coupole indigo", (TREE_C[0], 3.75), ha="center")
    note((TREE_C[0], 1.5), "Arbre à livres L01", (TREE_C[0] - 1.0, 0.25), ha="center")
    note((3.65, 1.0), "Niche bibliothèque N01", (3.15, -0.30), ha="center")
    note((4.8, 0.6), "Niche banquette N02", (4.95, -0.30), ha="center")
    note((2.45, 2.55), "Split S1 ~9 000 BTU\nsur cloison pleine", (1.2, 3.30), ha="center")
    note((6.41, 2.55), "Split S2 (mur est)", (6.35, 3.75), ha="center")
    note((3.0, 1.6), "Claustra Adinkra\n(vu de chant)", (2.15, 1.95), ha="center")
    note((1.4, 0.76), "Table de lecture T01", (1.3, -0.30), ha="center")
    note((6.33, 1.2), "Coffrage acoustique EU/EV", (6.55, -0.30), ha="center")
    for z, lab in ((0.0, "±0,00"), (Z_FP, "+2,85 FP"), (3.30, "+3,30 dalle")):
        ax.plot([-0.45, -0.25], [z, z], color=ENCRE, lw=LW_M, zorder=20)
        ax.text(-0.47, z, lab, fontsize=5.4, ha="right", va="center", color=ENCRE, zorder=20)
    scale_bar(ax, -0.6, -0.68, scale, length=2.0, step=0.5)
    panel_heading(T, 52, "D.A. — TERRE, OMBRE ET BOIS")
    lines = ["Palette encre › terre cuite, iroko, sable ; accent indigo ponctuel.",
             "Murs : enduit terre (argile) sable ocre ; parement BTC derrière les tables.",
             "Sol terrazzo coulé sable à granulats terre cuite ; tomettes au coin jeunesse.",
             "Bois iroko huilé pour l’arbre, les niches, les rayonnages et la banque.",
             "Indigo : coupole, fonds de niches, coussins, porte du placard, zellige du WC.",
             "Lumière 2700 K, IRC 90 mini : downlights, suspensions terre cuite, anneau LED."]
    for k, s in enumerate(lines):
        T(PANEL_X + 8, 57 + k * 4.6, s, 6.4, ENCRE)
    panel_heading(T, 90, "PALETTE (styles de surface IFC)")
    pal = [("Enduit terre", "#CDAE88"), ("BTC", "#B07D56"), ("Terre cuite", "#B4583E"), ("Iroko", "#9A6B43"),
           ("Terrazzo", "#D9CDBB"), ("Sable", "#E6D6BF"), ("Indigo", "#2F3E6E"), ("Encre", "#2B2420")]
    for k, (n, h) in enumerate(pal):
        x = PANEL_X + 8 + (k % 4) * 28; yy = 95 + (k // 4) * 19
        fig.add_artist(Rectangle((x / SHEET_W, 1 - (yy + 10) / SHEET_H), 25 / SHEET_W, 10 / SHEET_H, transform=fig.transFigure, fc=h, ec="none"))
        T(x, yy + 11.5, n, 6.0, ENCRE)
        T(x, yy + 14.6, h, 5.2, TAUPE)
    save(fig, "DECIMO_ESQ_V5_04_Elevation_interieure", svg=True)

# ================================================================================ vues 3D
def subdivide(tri, maxlen):
    out = []
    stack = list(tri)
    while stack:
        t = stack.pop()
        e = [np.linalg.norm(t[1] - t[0]), np.linalg.norm(t[2] - t[1]), np.linalg.norm(t[0] - t[2])]
        if max(e) <= maxlen or len(out) > 4e5:
            out.append(t)
            continue
        a, b, c = t
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        stack += [np.array([a, ab, ca]), np.array([ab, b, bc]), np.array([ca, bc, c]), np.array([ab, bc, ca])]
    return out

def render3d(ax, meshes, cam, target, *, ortho=False, fov=60, up=(0, 0, 1), clip_z=None, keep_unclipped=(), light=(-0.4, -0.6, 0.75),
             edges=True, maxlen=0.35, extra=()):
    cam, target = np.array(cam, float), np.array(target, float)
    fwd = target - cam; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, up); right /= np.linalg.norm(right)
    upv = np.cross(right, fwd)
    R = np.array([right, upv, -fwd])
    Ldir = np.array(light, float); Ldir /= np.linalg.norm(Ldir)
    near = 0.15
    paths, fcs, ecs, lws, depth = [], [], [], [], []
    focal = 1 / math.tan(math.radians(fov) / 2)
    def proj(p):
        if ortho:
            return p[:, :2]
        return np.column_stack([p[:, 0] / -p[:, 2] * focal, p[:, 1] / -p[:, 2] * focal])
    for m in list(meshes) + list(extra):
        v = m.v
        t = m.t
        tri_w = v[t]
        if clip_z is not None and m not in keep_unclipped:
            keep = tri_w[:, :, 2].min(1) < clip_z
            tri_w = tri_w[keep]; cols = m.col[keep]; tidx = np.nonzero(keep)[0]
        else:
            cols = m.col; tidx = np.arange(len(t))
        if not len(tri_w):
            continue
        nrm = np.cross(tri_w[:, 1] - tri_w[:, 0], tri_w[:, 2] - tri_w[:, 0])
        ln = np.linalg.norm(nrm, axis=1); ok = ln > 1e-12
        nrm[ok] /= ln[ok, None]
        vv = (tri_w - cam) @ R.T
        cen = vv.mean(1)
        if ortho:
            front = nrm @ (-fwd) > 1e-6
        else:
            front = np.einsum("ij,ij->i", nrm, cam - tri_w.mean(1)) > 0
        glass = cols[:, 3] < 0.9
        front |= glass
        shade = 0.58 + 0.42 * np.clip(nrm @ Ldir, 0, 1) + 0.08 * np.clip(nrm[:, 2], 0, 1)
        ed = feature_edges(m, (m.v - cam) @ R.T, np.isin(np.arange(len(m.t)), tidx[front]), angle=25) if edges else {}
        for k in np.nonzero(front)[0]:
            if not ok[k]:
                continue
            tri = vv[k]
            if clip_z is not None and m not in keep_unclipped and tri_w[k][:, 2].max() > clip_z:
                pass
            polys = [tri]
            if not ortho:
                if tri[:, 2].min() > -near:
                    continue
                if tri[:, 2].max() > -near:
                    pc = clip_poly(list(tri), -near)
                    if len(pc) < 3:
                        continue
                    polys = [np.array([pc[0], pc[i], pc[i + 1]]) for i in range(1, len(pc) - 1)]
            c = np.clip(cols[k, :3] * shade[k], 0, 1)
            alpha = 0.35 if glass[k] else float(cols[k, 3])
            for tp in polys:
                subs = subdivide([tp], maxlen) if not ortho else [tp]
                for s in subs:
                    paths.append(Path(np.vstack([proj(s), proj(s[:1])]), closed=True))
                    fcs.append((*c, alpha)); ecs.append((*c, alpha)); lws.append(0.15)
                    depth.append(s[:, 2].mean() if not ortho else s[:, 2].mean())
            if edges:
                es = ed.get(tidx[k], [])
                segs = []
                for a, b in es:
                    if not ortho:
                        if a[2] > -near and b[2] > -near:
                            continue
                        if a[2] > -near or b[2] > -near:
                            kk = (-near - a[2]) / (b[2] - a[2])
                            p = a + kk * (b - a)
                            a, b = (p, b) if a[2] > -near else (a, p)
                    segs.append(np.array([a, b]))
                if segs:
                    verts = np.vstack([proj(s_) for s_ in segs])
                    paths.append(Path(verts, np.tile([Path.MOVETO, Path.LINETO], len(segs))))
                    fcs.append((0, 0, 0, 0)); ecs.append((0.12, 0.1, 0.09, 0.55)); lws.append(0.25)
                    depth.append(tri[:, 2].max() + 1e-4)
    order = np.argsort(depth, kind="stable")
    pc = PathCollection([paths[i] for i in order], facecolors=[fcs[i] for i in order], edgecolors=[ecs[i] for i in order],
                        linewidths=[lws[i] for i in order], zorder=3)
    pc.set_rasterized(True)
    ax.add_collection(pc)
    ax.set_aspect("equal"); ax.axis("off")
    ax.autoscale_view()
    return pc

def context_boxes(side=6.0, floors=2):
    """Volumes de contexte (immeuble au-dessus, mitoyens) pour les vues 3D — hors maquette IFC."""
    out = []
    def mk(x0, y0, z0, x1, y1, z1, hexc):
        m = Mesh()
        v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
        t = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
        m.v, m.t = v, t
        m.tw = t
        m.col = np.tile([*hex2rgb(hexc), 1.0], (len(t), 1))
        m.cat = "ctx"
        out.append(m)
    mk(EXT[0], EXT[1], Z_DALLE, EXT[2], EXT[3], Z_DALLE + 3.3 * floors, "#EFEBE5")
    mk(EXT[0] - side, EXT[1], -0.02, EXT[0], EXT[3] + 2, Z_DALLE + 3.3 * floors - 0.3, "#E6E1DA")
    mk(EXT[2], EXT[1], -0.02, EXT[2] + side, EXT[3] + 2, Z_DALLE + 3.3 * floors - 1.6, "#E6E1DA")
    for k in range(floors):
        for xa in (0.55, 2.55, 4.55):
            mk(xa, EXT[1] - 0.02, Z_DALLE + k * 3.3 + 0.95, xa + 1.4, EXT[1] - 0.01, Z_DALLE + k * 3.3 + 2.5, "#9FA9AE")
    return out

def vues_axo():
    fig, T = new_sheet(5, "Axonométries", "Esquisse V5  ·  Vues 3D générées depuis la maquette IFC4",
                       ["Axonométrie coupée (dalle, plafonds et murs arasés à +2,40, arbre conservé entier)",
                        "et axonométrie de la devanture depuis la rue (immeuble au-dessus en contexte)"])
    interior = [m for m in SOLIDS if m.cat not in ("site",) and m.cls != "IfcSlab" or (m.cls == "IfcSlab" and "Dallage" in m.name)]
    interior = [m for m in interior if m.cat != "ceiling" and m.cat != "light" or "Anneau" in m.name or "Suspension" in m.name]
    keep = [TREE] + by_name("Anneau LED") + by_name("Suspension")
    ax1 = fig.add_axes([0.01, 0.10, 0.36, 0.78])
    render3d(ax1, interior, cam=(16, -12, 15), target=(3.3, 3.8, 0.6), ortho=True, clip_z=2.40, keep_unclipped=keep, maxlen=10)
    ax1.set_title("Axonométrie coupée depuis le sud-est (arasé à +2,40)", fontsize=7.5, color=TERRE_CUITE, loc="left", pad=2)
    ax2 = fig.add_axes([0.355, 0.10, 0.34, 0.78])
    allm = [m for m in SOLIDS if m.cat != "space"]
    render3d(ax2, allm, cam=(-9, -16, 9.5), target=(3.3, 0.0, 2.6), ortho=True, maxlen=10, extra=context_boxes(side=1.6, floors=1))
    ax2.set_title("Axonométrie de la devanture depuis la rue (sud-ouest)", fontsize=7.5, color=TERRE_CUITE, loc="left", pad=2)
    panel_heading(T, 52, "LECTURE")
    lines = ["Le local tient dans l’enveloppe existante : voiles, poteaux, poutre",
             "et dalle haute conservés (propriété « Existant porteur - ne pas toucher »).",
             "Au centre, l’arbre à livres s’ouvre en canopée dans la coupole indigo.",
             "À l’ouest : coin jeunesse en vitrine, espace de travail derrière le",
             "claustra Adinkra ; au fond : WC, dégagement-réserve, placard technique.",
             "À l’est : accueil près de l’entrée (TD encastré), salon de lecture et",
             "coffrage acoustique des descentes EU/EV.",
             "Volumes gris clair des vues : contexte non modélisé dans l’IFC."]
    for k, s in enumerate(lines):
        T(PANEL_X + 8, 57 + k * 4.6, s, 6.4, ENCRE)
    save(fig, "DECIMO_ESQ_V5_05_Axonometries")

def translucent(m, alpha):
    c = copy.copy(m)
    c.col = m.col.copy()
    c.col[:, 3] = alpha
    return c

def vues_perspective():
    fig, T = new_sheet(6, "Perspectives", "Esquisse V5  ·  Vues 3D générées depuis la maquette IFC4",
                       ["Perspective intérieure depuis l’entrée vers l’arbre à livres et le mur des niches",
                        "Perspective depuis le trottoir d’en face (arbres d’alignement, immeuble en contexte)"])
    inside = [m for m in SOLIDS if m.cat != "site"]
    ax1 = fig.add_axes([0.02, 0.50, 0.66, 0.40])
    render3d(ax1, inside, cam=(3.55, 0.45, 1.50), target=(4.85, 6.6, 1.55), fov=74, maxlen=0.30)
    ax1.set_xlim(-1.35, 1.35); ax1.set_ylim(-0.66, 0.74)
    ax1.set_title("Depuis l’entrée : accueil, arbre à livres, niches cintrées", fontsize=7.5, color=TERRE_CUITE, loc="left", pad=2)
    ax2 = fig.add_axes([0.02, 0.05, 0.66, 0.40])
    allm = [m for m in SOLIDS if m.cat != "space"]
    allm = [translucent(m, 0.30) if m.cat == "site" and m.cls == "IfcGeographicElement" else m for m in allm]
    render3d(ax2, allm, cam=(3.35, -8.4, 1.55), target=(3.35, 0.0, 1.85), fov=58, maxlen=0.45, extra=context_boxes())
    ax2.set_xlim(-1.35, 1.35); ax2.set_ylim(-0.60, 0.80)
    ax2.set_title("Depuis le trottoir d’en face", fontsize=7.5, color=TERRE_CUITE, loc="left", pad=2)
    panel_heading(T, 52, "AMBIANCE")
    lines = ["Terre, ombre et bois : enduit terre, BTC, terrazzo, tomettes et iroko,",
             "lumière chaude 2700 K, accent indigo pour la coupole et les assises.",
             "Rendu schématique (couleurs des styles IFC, ombrage simple),",
             "sans textures ni éclairage calculé : à reprendre en APS (Twinmotion,",
             "Enscape ou Blender) à partir de la maquette IFC."]
    for k, s in enumerate(lines):
        T(PANEL_X + 8, 57 + k * 4.6, s, 6.4, ENCRE)
    save(fig, "DECIMO_ESQ_V5_06_Perspectives")

if __name__ == "__main__":
    which = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else {"1", "2", "3", "4", "5", "6"}
    jobs = [("1", plan_rdc), ("2", coupe_aa), ("3", elevation_devanture), ("4", elevation_interieure), ("5", vues_axo), ("6", vues_perspective)]
    for k, fn in jobs:
        if k in which:
            fn()
    if which == {"1", "2", "3", "4", "5", "6"}:
        with PdfPages(os.path.join(OUT, "DECIMO_ESQ_V5_Dessins.pdf")) as pdf:
            for fig in SHEETS:
                pdf.savefig(fig)
        print("  recueil DECIMO_ESQ_V5_Dessins.pdf")
