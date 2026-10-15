"""Charte graphique K&Démi — palette, typographies et logo.

Logo (v3 A) : une arche dans un carré + le nom en Manrope, « & » en terre cuite (charte/logo_v3/).
Dans les cartouches : toujours le lockup (nom à côté du symbole, jamais le symbole seul), 30 mm minimum
en impression, version mono sur fond clair et inverse sur fond sombre — voir draw_lockup().
Le portique voûté (draw_logo) n'est conservé que pour régénérer les planches V4 archivées.
Couleurs : terre cuite, iroko, sable, blanc chaux, encre ; olive en appoint.
Typographies : Manrope (le nom K&Démi dans le logo), Archivo (titres SemiBold, texte Regular, légendes Medium).
Charte v2 (15/10/2026) : papier blanc, encre quasi noire, terre cuite en accent seulement, indigo rare.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path

import os
FD = os.environ.get("KDEMI_FONTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "polices")) + os.sep
F_TITRE = FD + "archivo-latin-600-normal.ttf"
F_TITRE_I = FD + "archivo-latin-500-normal.ttf"
F_LIGHT = FD + "archivo-latin-400-normal.ttf"
F_TEXTE = FD + "archivo-latin-400-normal.ttf"
F_MEDIUM = FD + "archivo-latin-500-normal.ttf"
F_NOM = FD + "manrope-latin-500-normal.ttf"
F_NOM_FORT = FD + "manrope-latin-600-normal.ttf"
for p in (F_TITRE, F_TITRE_I, F_LIGHT, F_TEXTE, F_MEDIUM, F_NOM, F_NOM_FORT):
    font_manager.fontManager.addfont(p)
plt.rcParams["font.family"] = FontProperties(fname=F_TEXTE).get_name()
plt.rcParams["pdf.fonttype"] = 42
FP_TITRE = FontProperties(fname=F_TITRE)
FP_TITRE_I = FontProperties(fname=F_TITRE_I)
FP_MEDIUM = FontProperties(fname=F_MEDIUM)
FP_LIGHT = FontProperties(fname=F_LIGHT)
FP_NOM = FontProperties(fname=F_NOM)            # Manrope : le nom « K&Démi » partout où il est écrit
FP_NOM_FORT = FontProperties(fname=F_NOM_FORT)

# --- palette -------------------------------------------------------------------
ENCRE = "#4A4A4A"        # texte et traits : gris neutre (charte v2, pas de noir)
TAUPE = "#8C8C8C"        # texte secondaire, cotes, filets
TERRE_CUITE = "#B4583E"  # accent : filets courts, numéros, & du logo
IROKO = "#9A6B43"        # repères mobilier, matière bois
SABLE = "#E8E8E8"        # aplats neutres, cartouches de légende
SABLE_CLAIR = "#F4F4F4"  # alternance de lignes de tableau
BLANC_CHAUX = "#FFFFFF"  # papier
OLIVE = "#5F7A4B"        # dégagements, végétal (usage restreint)
POCHE = "#2E2E2E"        # murs coupés (poché)

def arch_path(x0, x1, z0, z_spring, n=48):
    r = (x1 - x0) / 2; c = (x0 + x1) / 2
    pts = [(x0, z0), (x1, z0), (x1, z_spring)]
    pts += [(c + r * np.cos(a), z_spring + r * np.sin(a)) for a in np.linspace(0, np.pi, n)]
    pts += [(x0, z_spring), (x0, z0)]
    return Path(pts, closed=True)

def draw_logo(fig, x_mm, y_top_mm, h_mm=17, W=420, H=297, reverse=False, inner_color=None):
    """Logo K&Démi : arche terre cuite évidée + mot-symbole. Hauteur totale h_mm."""
    w_mm = h_mm * 3.9
    ax = fig.add_axes([x_mm / W, (H - y_top_mm - h_mm) / H, w_mm / W, h_mm / H])
    ax.set_xlim(0, 3.9); ax.set_ylim(0, 1); ax.axis("off")
    ink = BLANC_CHAUX if reverse else ENCRE
    outer = arch_path(0.0, 0.62, 0.0, 0.69)
    inner = arch_path(0.13, 0.49, 0.0, 0.62)
    ax.add_patch(PathPatch(Path.make_compound_path(outer, Path(inner.vertices[::-1], inner.codes)),
                           fc=TERRE_CUITE, ec="none"))
    ax.add_patch(Rectangle((0.0, -0.0), 0.62, 0.045, fc=TERRE_CUITE, ec="none"))
    ax.add_patch(PathPatch(arch_path(0.21, 0.41, 0.0, 0.40), fc=inner_color or (SABLE if not reverse else IROKO), ec="none"))
    t1 = ax.text(0.80, 0.42, "K", fontproperties=FP_TITRE, fontsize=h_mm * 2.25, color=ink, ha="left", va="baseline")
    ax.text(1.31, 0.42, "&", fontproperties=FP_TITRE_I, fontsize=h_mm * 2.25, color=TERRE_CUITE, ha="left", va="baseline")
    ax.text(1.90, 0.42, "Démi", fontproperties=FP_TITRE, fontsize=h_mm * 2.25, color=ink, ha="left", va="baseline")
    ax.text(0.82, 0.08, "A R C H I T E C T U R E   ·   I N T É R I E U R", fontproperties=FP_MEDIUM,
            fontsize=h_mm * 0.30, color=TAUPE, ha="left", va="baseline")
    return ax


# --- logo v3 A : arche dans un carré + nom en Manrope (remplace le portique voûté) ---------------
# Règles : lockup uniquement (nom toujours à côté du symbole), largeur imprimée >= 30 mm,
# version mono sur fond clair, inverse sur fond sombre. Fichiers sources : charte/logo_v3/.
import re
LOGO_V3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_v3")
LOCKUP_SVG = {"couleur": "KDemi_v3_A_arche_lockup.svg", "mono": "KDemi_v3_A_arche_lockup_mono.svg",
              "inverse": "KDemi_v3_A_arche_lockup_inverse.svg"}
LOCKUP_MIN_MM = 30.0
LOCKUP_ART = (30.0, 30.0, 378.0, 110.0)   # emprise du dessin (symbole -> « i ») dans le viewBox 413 x 140


def _svg_path(d, transform=None):
    """Chemin SVG absolu (M L H V Q A Z, coordonnées implicites) -> liste de sous-chemins (points, codes)."""
    toks = re.findall(r"[MLHVQAZ]|-?\d*\.?\d+(?:e-?\d+)?", d)
    subs, pts, codes, cmd, i = [], [], [], None, 0
    cur = np.zeros(2); start = np.zeros(2)

    def num():
        nonlocal i
        v = float(toks[i]); i += 1
        return v
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]; i += 1
            if cmd == "Z":
                pts.append(tuple(start)); codes.append(Path.CLOSEPOLY)
                subs.append((pts, codes)); pts, codes = [], []
                cur = start.copy()
                continue
        if cmd == "M":
            cur = np.array([num(), num()]); start = cur.copy()
            pts.append(tuple(cur)); codes.append(Path.MOVETO); cmd = "L"
        elif cmd == "L":
            cur = np.array([num(), num()]); pts.append(tuple(cur)); codes.append(Path.LINETO)
        elif cmd == "H":
            cur = np.array([num(), cur[1]]); pts.append(tuple(cur)); codes.append(Path.LINETO)
        elif cmd == "V":
            cur = np.array([cur[0], num()]); pts.append(tuple(cur)); codes.append(Path.LINETO)
        elif cmd == "Q":
            c, e = (num(), num()), (num(), num())
            pts += [c, e]; codes += [Path.CURVE3, Path.CURVE3]; cur = np.array(e)
        elif cmd == "A":
            rx, ry, _, large, sweep, x, y = (num() for _ in range(7))
            e = np.array([x, y]); m = (cur + e) / 2; h = np.linalg.norm(e - cur) / 2
            r = max(rx, h); n = np.array([-(e - cur)[1], (e - cur)[0]]) / (2 * h)
            k = np.sqrt(max(r * r - h * h, 0.0)) * (1 if large != sweep else -1)
            c = m + n * k
            a0, a1 = np.arctan2(*(cur - c)[::-1]), np.arctan2(*(e - c)[::-1])
            da = (a1 - a0) % (2 * np.pi) if sweep else -((a0 - a1) % (2 * np.pi))
            for t in np.linspace(0, 1, 33)[1:]:
                pts.append(tuple(c + r * np.array([np.cos(a0 + da * t), np.sin(a0 + da * t)]))); codes.append(Path.LINETO)
            cur = e
    if pts:
        subs.append((pts, codes))
    if transform is not None:
        subs = [([transform(p) for p in s], c) for s, c in subs]
    return subs


def _aire(pts):
    p = np.asarray(pts)
    return 0.5 * np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1])


def lockup_paths(version="mono"):
    """(chemins matplotlib, couleurs, fond) du lockup, coordonnées du viewBox (y vers le bas)."""
    svg = open(os.path.join(LOGO_V3, LOCKUP_SVG[version]), encoding="utf-8").read()
    fond = re.search(r'<rect[^>]*fill="(#[0-9A-Fa-f]{6})"', svg)
    out = []
    for m in re.finditer(r'(<g transform="translate\(([\d.]+),([\d.]+)\) scale\(([\d.]+)\)">)?<path d="([^"]+)" fill="(#[0-9A-Fa-f]{6})"( fill-rule="evenodd")?', svg):
        tf = None
        if m.group(1):
            tx, ty, s = float(m.group(2)), float(m.group(3)), float(m.group(4))
            tf = lambda p, tx=tx, ty=ty, s=s: (tx + s * p[0], ty + s * p[1])
        subs = _svg_path(m.group(5), tf)
        if m.group(7):   # pair-impair -> sens alternés pour le remplissage non nul de matplotlib
            ref = np.sign(_aire(subs[0][0]))
            for k in range(1, len(subs)):
                pts, cs = subs[k]
                if np.sign(_aire(pts)) == ref and Path.CURVE3 not in cs:
                    body = pts[:-1][::-1]
                    subs[k] = (body + [body[0]], cs)
        verts = [p for s, _ in subs for p in s]
        codes = [c for _, cs in subs for c in cs]
        out.append((Path(verts, codes), m.group(6)))
    return out, (fond.group(1) if fond else None)


def draw_lockup(fig, x_mm, y_top_mm, w_mm=46.0, fond="clair", W=420, H=297):
    """Lockup v3 A (symbole + nom) : x_mm, y_top_mm = coin haut-gauche du dessin (zone de protection en plus).

    w_mm : largeur imprimée du dessin, >= 30 mm. fond : « clair » -> mono, « sombre » -> inverse.
    """
    if w_mm < LOCKUP_MIN_MM:
        raise ValueError(f"lockup K&Démi : {w_mm} mm < {LOCKUP_MIN_MM} mm minimum en impression")
    version = "mono" if fond == "clair" else "inverse"
    paths, bg = lockup_paths(version)
    x0, y0, x1, y1 = LOCKUP_ART
    k = w_mm / (x1 - x0)                    # mm par unité du viewBox
    pad = x0 * k
    ax = fig.add_axes([(x_mm - pad) / W, 1 - (y_top_mm - pad + 140 * k) / H, 413 * k / W, 140 * k / H])
    ax.set_xlim(0, 413); ax.set_ylim(140, 0); ax.axis("off")
    if bg:
        ax.add_patch(Rectangle((0, 0), 413, 140, fc=bg, ec="none"))
    for p, c in paths:
        ax.add_patch(PathPatch(p, fc=c, ec="none", lw=0))
    ax.lockup_mm = (w_mm, (y1 - y0) * k)
    return ax
