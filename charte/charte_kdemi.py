"""Charte graphique K&Démi — palette, typographies et logo (tirés de la proposition V4).

Symbole : l'arche cintrée (portail et niches du projet).
Couleurs : terre cuite, iroko, sable, blanc chaux, encre ; olive en appoint.
Typographies : DM Serif Display (titres, logo), Jost (texte, légendes).
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + os.sep
F_TITRE = FD + "dm-serif-display-latin-400-normal.ttf"
F_TITRE_I = FD + "dm-serif-display-latin-400-italic.ttf"
F_LIGHT = FD + "jost-latin-300-normal.ttf"
F_TEXTE = FD + "jost-latin-400-normal.ttf"
F_MEDIUM = FD + "jost-latin-500-normal.ttf"
for p in (F_TITRE, F_TITRE_I, F_LIGHT, F_TEXTE, F_MEDIUM):
    font_manager.fontManager.addfont(p)
plt.rcParams["font.family"] = FontProperties(fname=F_TEXTE).get_name()
plt.rcParams["pdf.fonttype"] = 42
FP_TITRE = FontProperties(fname=F_TITRE)
FP_TITRE_I = FontProperties(fname=F_TITRE_I)
FP_MEDIUM = FontProperties(fname=F_MEDIUM)
FP_LIGHT = FontProperties(fname=F_LIGHT)

# --- palette -------------------------------------------------------------------
ENCRE = "#2B2420"        # texte, traits
TAUPE = "#7D7168"        # texte secondaire, cotes
TERRE_CUITE = "#B4583E"  # couleur signature : titres, filets, accents
IROKO = "#9A6B43"        # repères mobilier, matière bois
SABLE = "#E6D6BF"        # aplats, fonds de cartouche
SABLE_CLAIR = "#F4EDE2"  # fond de panneau, alternance de lignes
BLANC_CHAUX = "#FBF8F3"  # fond de page
OLIVE = "#5F7A4B"        # dégagements, végétal (usage restreint)
POCHE = "#4A403A"        # murs coupés
INDIGO = "#2F3E6E"       # accent D.A. V5 « terre, ombre et bois » (usage ponctuel)

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
