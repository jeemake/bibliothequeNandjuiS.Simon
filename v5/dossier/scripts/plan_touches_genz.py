"""Extrait du plan A01 (gris clair) annoté des 5 touches « côté Gen Z ». Sortie : v5/dossier/rendus/G5_plan_touches.png"""
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
BASE = "/workspace/decimo_final/repo/v5/"
FD = "/workspace/decimo_final/polices/"
for f in ("archivo-latin-400-normal", "archivo-latin-500-normal", "archivo-latin-600-normal"):
    fm.fontManager.addfont(FD + f + ".ttf")
FP = fm.FontProperties(fname=FD + "archivo-latin-500-normal.ttf")
FB = fm.FontProperties(fname=FD + "archivo-latin-600-normal.ttf")
TERRE, ENCRE, TAUPE = "#B4583E", "#4A4A4A", "#8C8C8C"

K = 200 / 25.4                               # px par mm (A01 exporté à 200 dpi)
px = lambda X: (6 + 20 * (X + 1.25)) * K       # axes A01 : x 6 mm, xlim -1,25 ; 1/50
py = lambda Y: (10 + 20 * (8.3 - Y)) * K       # y_top 10 mm, ylim haut 8,30
X0, X1, Y0, Y1 = -0.55, 7.35, -2.55, 7.95      # emprise de l'extrait (m)
im = Image.open(BASE + "dessins/A01_plan_RDC.png").convert("L")
im = im.crop((int(px(X0)), int(py(Y1)), int(px(X1)), int(py(Y0))))
a = np.asarray(im, float) / 255
a = 1 - (1 - a) * 0.42                          # fond de plan gris clair
fig = plt.figure(figsize=((X1 - X0) * 20 / 25.4, (Y1 - Y0) * 20 / 25.4), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
ax.imshow(a, cmap="gray", vmin=0, vmax=1, extent=(X0, X1, Y0, Y1), interpolation="lanczos")
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1)

T = [  # (n, point visé, position de la pastille, libellé)
    (1, (5.32, 0.85), (4.30, 0.75), "Tampon daté\nau comptoir"),
    (2, (5.32, 1.85), (4.30, 1.55), "Livres-surprises\nen kraft"),
    (3, (6.52, 1.80), (4.30, 2.35), "Réglette iroko des coups\nde cœur, mur est"),
    (4, (1.08, 0.30), (1.25, 1.35), "Vitrine\ncoin lecture"),
    (5, (3.40, -1.45), (3.40, -2.15), "Terrasse le soir : guirlande 2700 K,\njardinières plantées"),
]
for n, (x, y), (bx, by), lib in T:
    ax.plot([x, bx], [y, by], color=TERRE, lw=0.6, zorder=5)
    ax.plot([x], [y], "o", ms=2.2, color=TERRE, zorder=6)
    ax.add_patch(plt.Circle((bx, by), 0.17, fc=TERRE, ec="white", lw=0.8, zorder=7))
    ax.text(bx, by - 0.005, str(n), color="white", ha="center", va="center", fontproperties=FB, fontsize=7.2, zorder=8)
    ha = "left"; dx = 0.24
    if n in (1, 2, 3): ha, dx = "right", -0.24
    ax.text(bx + dx, by, lib, color=ENCRE, ha=ha, va="center", fontproperties=FP, fontsize=6.0, linespacing=1.2, zorder=8,
            bbox=dict(fc="white", ec="none", pad=1.2, alpha=0.9))
for xj in (1.65, 5.75):                          # jardinières plantées (rep. 5)
    ax.plot([xj, 3.40], [-0.29, -1.45], color=TERRE, lw=0.4, ls=(0, (2, 2)), zorder=5)
fig.savefig(BASE + "dossier/rendus/G5_plan_touches.png", dpi=300)
print("ok")
