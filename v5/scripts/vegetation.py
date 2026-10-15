"""Représentation de la végétation dans les planches 2D : symboles d'architecte au trait fin.

Plan : arbre = houppier à bord festonné + branches rayonnantes + point de tronc ;
       arbuste / plante en pot = touffe festonnée + nervures depuis le centre.
Élévation / coupe : arbre = tronc + charpentières + contour de houppier (entourage) ;
       arbuste = touffe festonnée posée sur la jardinière + tiges en éventail.
Tailles et positions = celles des produits IFC (silhouette de chaque touffe, boîte de chaque houppier).
"""
import numpy as np
import shapely
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from matplotlib.patches import Ellipse, Circle

import dessin2d as D

VEG = "#7E8A78"           # trait gris-vert très sourd, cohérent avec la charte grise
VERT_FEUILLAGE = np.array([0.37, 0.55, 0.29])


def est_feuillage(it):
    return np.abs(np.asarray(it["rgba"][:3]) - VERT_FEUILLAGE).max() < 0.04


def est_vegetal(e):
    """Produits dont la coupe à +1,00 ne traverse que du feuillage (plante en pot, touffes des jardinières)."""
    return "Jardinière" in e["nom"] or "V01_Plante" in e["nom"]


def _rng(g):
    c = g.centroid
    return np.random.default_rng(int(abs(c.x * 1000) * 7 + abs(c.y * 1000) * 13) % (2 ** 31))


def nuage(g, lobe, rng):
    """Contour festonné inscrit dans g : petits lobes posés sur le bord de g rétréci d'un lobe."""
    core = g.buffer(-lobe)
    if core.is_empty:
        lobe = max(min(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1]) / 4, 1e-3)
        core = g.buffer(-lobe)
        if core.is_empty:
            core = g.centroid.buffer(lobe)
    parts = [core]
    for p in shapely.get_parts(core):
        ring = p.exterior
        n = max(int(ring.length / (1.25 * lobe)), 7)
        for k in range(n):
            q = ring.interpolate((k + rng.uniform(-0.15, 0.15)) / n, normalized=True)
            parts.append(Point(q.x, q.y).buffer(lobe * rng.uniform(0.82, 1.12), quad_segs=6))
    return unary_union(parts).buffer(0)


def touffe(ax, g, z, mode="plan", col=VEG, fc="white", lw=None, alpha=1.0):
    """Arbuste, touffe de jardinière ou plante en pot, dans l'emprise exacte g de son feuillage."""
    if g is None or g.is_empty:
        return
    lw = lw or D.LW[1]
    g = g.convex_hull               # emprise pleine de la touffe (les silhouettes projetées sont fragmentées)
    rng = _rng(g)
    x0, y0, x1, y1 = g.bounds
    w, h = x1 - x0, y1 - y0
    lobe = max(min(w, h) * 0.13, 0.012)
    if mode != "plan":            # port arrondi de l'arbuste dans l'emprise du produit (pied droit, tête en dôme)
        el = Polygon(Ellipse(((x0 + x1) / 2, y0 + 0.5 * h), w, h).get_verts()).buffer(0)
        dome = el.union(Polygon([(x0 + 0.18 * w, y0), (x1 - 0.18 * w, y0), (x1 - 0.1 * w, y0 + 0.4 * h), (x0 + 0.1 * w, y0 + 0.4 * h)]))
        g = g.intersection(dome).buffer(0)
    cl = nuage(g, lobe, rng)
    D.patch(ax, cl, fc=fc, ec=col, lw=lw, z=z, alpha=alpha)
    c = np.array([g.centroid.x, g.centroid.y])
    if mode == "plan":            # nervures rayonnantes depuis le cœur de la touffe
        n = 7 if min(w, h) > 0.15 else 5
        a0 = rng.uniform(0, 2 * np.pi)
        for k in range(n):
            a = a0 + 2 * np.pi * k / n + rng.uniform(-0.2, 0.2)
            r1 = 0.62 * min(w, h) / 2 * rng.uniform(0.85, 1.1)
            d = np.array([np.cos(a), np.sin(a)])
            p0, p1 = c + d * r1 * 0.15, c + d * r1
            ax.plot(*np.array([p0, p1]).T, color=col, lw=lw * 0.6, zorder=z + 0.0002, solid_capstyle="round")
            for s in (-1, 1):     # petite feuille en chevron au bout
                q = p1 - d * r1 * 0.28 + np.array([-d[1], d[0]]) * s * r1 * 0.16
                ax.plot(*np.array([p1 - d * r1 * 0.05, q]).T, color=col, lw=lw * 0.5, zorder=z + 0.0002)
    else:                         # tiges en éventail depuis le pied de la touffe
        base = np.array([c[0], y0 + 0.05 * h])
        n = 5 if w > 0.2 else 3
        for k in range(n):
            t = (k + 0.5) / n - 0.5
            tip = np.array([c[0] + t * w * 0.62, y0 + h * rng.uniform(0.55, 0.72)])
            ax.plot(*np.array([base, (base + tip) / 2 + np.array([t * w * 0.08, 0]), tip]).T, color=col, lw=lw * 0.55,
                    zorder=z + 0.0002, solid_capstyle="round")


def arbre_plan(ax, cx, cy, R, z, col=VEG, tronc=None, lw=None):
    """Arbre en plan : houppier festonné (fond transparent), charpentières rayonnantes, point de tronc."""
    lw = lw or D.LW[1]
    g = Point(cx, cy).buffer(R, quad_segs=24)
    rng = _rng(g)
    cl = nuage(g, R * 0.15, rng)
    D.patch(ax, cl, fc="none", ec=col, lw=lw * 1.15, z=z)
    a0 = rng.uniform(0, 2 * np.pi)
    n = 7
    for k in range(n):
        a = a0 + 2 * np.pi * k / n + rng.uniform(-0.18, 0.18)
        d = np.array([np.cos(a), np.sin(a)]); t = np.array([-d[1], d[0]])
        r1 = R * rng.uniform(0.62, 0.78)
        p0 = np.array([cx, cy]) + d * R * 0.08
        p1 = np.array([cx, cy]) + d * r1
        ax.plot(*np.array([p0, p1]).T, color=col, lw=lw * 0.6, zorder=z, solid_capstyle="round")
        pm = np.array([cx, cy]) + d * r1 * 0.6                         # fourche
        ax.plot(*np.array([pm, pm + (d * 0.75 + t * rng.choice([-1, 1]) * 0.55) * R * 0.22]).T, color=col, lw=lw * 0.5, zorder=z)
    rt = R * 0.03 if tronc is None else tronc
    if rt > 0:
        ax.add_patch(Circle((cx, cy), rt, fc=col, ec="none", zorder=z + 0.001))


def arbre_elev(ax, tronc, houppiers, z, col=VEG, lw=None, alpha=0.88):
    """Arbre en élévation (entourage) : tronc légèrement effilé, charpentières, contours de houppier festonnés.
    tronc = (x0, x1, z0, z1) ; houppiers = liste d'ellipses (cx, cz, w, h) dans l'ordre de dessin."""
    lw = lw or D.LW[1]
    tx0, tx1, tz0, tz1 = tronc
    tc, tw = (tx0 + tx1) / 2, tx1 - tx0
    tr = Polygon([(tx0, tz0), (tx1, tz0), (tc + tw * 0.30, tz1), (tc - tw * 0.30, tz1)])
    D.patch(ax, tr, fc="white", ec=col, lw=lw, z=z)
    for k, (cx, cz, w, h) in enumerate(houppiers):
        e = Ellipse((cx, cz), w, h)
        pts = e.get_verts()
        g = Polygon(pts).buffer(0)
        rng = _rng(g)
        cl = nuage(g, min(w, h) * 0.085, rng)
        D.patch(ax, cl, fc="white", ec=col, lw=lw, z=z + 1 + k * 0.01, alpha=alpha)
    # charpentières : depuis le haut du tronc vers chaque houppier, puis rameaux
    zb = tz1
    for k, (cx, cz, w, h) in enumerate(houppiers):
        rng = np.random.default_rng(1000 + k)
        p0 = np.array([tc, min(zb, cz - h * 0.3)])
        tgt = np.array([cx, cz - h * 0.05])
        mid = p0 + (tgt - p0) * 0.55
        ax.plot(*np.array([p0, mid, tgt]).T, color=col, lw=lw * 0.8, zorder=z + 2, solid_capstyle="round")
        for s in (-1, 1):
            for f in (0.45, 0.8):
                q0 = p0 + (tgt - p0) * f
                q1 = q0 + np.array([s * w * rng.uniform(0.16, 0.26), h * rng.uniform(0.12, 0.22)])
                ax.plot(*np.array([q0, q1]).T, color=col, lw=lw * 0.5, zorder=z + 2, solid_capstyle="round")
