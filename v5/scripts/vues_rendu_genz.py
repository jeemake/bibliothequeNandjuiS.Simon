"""Vues IFC supplémentaires pour les rendus « Decimo, côté Gen Z » (structure / contrôle des rendus fal).

Ne modifie pas les vues 01 à 05. Écrit v5/vues_rendu/06_accueil_vignette_*.png (+ caméra json).
Usage : python3 v5/scripts/vues_rendu_genz.py
"""
import os, sys, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import VUES, V5_IFC  # noqa
from scene import charger, triangles, role  # noqa
from rendu_gl import render, camera_info  # noqa
from vues_rendu import INT, SIZE  # noqa

VIEWS = {
    "06_accueil_vignette": (dict(position=(3.75, 2.05, 1.45), target=(5.55, 1.05, 0.95), fov_v=50.0), INT, ("sol_ext",),
                            "Accueil : comptoir iroko C02, siège C05, mur est (tampon, livres-surprises, réglette des coups de cœur)"),
}

if __name__ == "__main__":
    sc = charger()
    h = hashlib.sha256(open(V5_IFC, "rb").read()).hexdigest()
    for name, (cam, light, hide, desc) in VIEWS.items():
        T, C, I = triangles(sc, lambda e: role(e) not in hide)
        shaded, trait = render(T, C, I, cam, size=SIZE, **light)
        shaded.save(os.path.join(VUES, f"{name}_ombre.png"), optimize=True)
        trait.save(os.path.join(VUES, f"{name}_traits.png"), optimize=True)
        json.dump({"vue": name, "description": desc, "source_ifc": "v5/DECIMO_ESQ_V5.ifc", "source_sha256": h,
                   "camera": camera_info(cam, SIZE), "eclairage": dict(light), "masques": list(hide),
                   "script": "python3 v5/scripts/vues_rendu_genz.py"},
                  open(os.path.join(VUES, f"{name}_camera.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(name)
