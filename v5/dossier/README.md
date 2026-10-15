# Dossier de présentation, Bibliothèque Decimo, ESQ V5 (indice A, 15 octobre 2026)

A3 paysage, 21 pages, charte K&Démi (logo v3 A, DM Serif Display + Jost, encre, terre cuite, iroko, sable, accent indigo). Grille invisible : marges 14 mm, gouttières 5 mm, panneau de droite commun avec les planches A01 à A08.

| Fichier | Contenu |
|---|---|
| `Decimo_ESQ_V5_Dossier_A3.pdf` | Dossier final : couverture, projet, identité, D.A, A01 à A08, rendus R1 à R3, T01 à T05, cohérence |
| `Decimo_ESQ_V5_Dossier_A3.pptx` | Même dossier en version modifiable (aussi importé en Google Slides) |
| `rendus/` | Rendus finaux tirés des vues `v5/vues_rendu` (fal nano-banana-pro/edit), `01_devanture_fal_brut.jpg` = sortie brute avant retouche |
| `scripts/layout.py`, `scripts/render.py` | Mise en page unique vers PDF (reportlab) et PPTX (python-pptx) |
| `scripts/gen_rendus.py` | Génération des rendus depuis les vues IFC |
| `scripts/fix_r1.py` | Retouche locale de R1 : retire les balcons inventés sur l'immeuble voisin (la maquette montre un mur plein) |
| `scripts/controle_v4_v5_independant.py` | Contre-vérification V4 / V5 indépendante du script de Téïsson |

## Contrôles

- Sur `main` : 141/141 produits V4 retrouvés en V5, placements et géométries identiques (écart 0), emprise des murs 6,78 × 7,68 m, WC 4350629 et lave-mains 4350630/4350631 conservés, 0 toiture, 0 escalier.
- Rendus comparés à leur vue IFC source. R2 à R5 conformes. R1 : balcons inventés retirés. Écart restant : les jardinières de la terrasse sont rendues en banquettes (la maquette fait foi).

## Reste à faire

- Pages 16 à 20 : réserves propres en attendant les planches T01 à T05 d'Ahoua (branche `cursor/v5-lots-techniques-c041`). Déposer les PDF dans `technique/` sous le nom `T0x_*.pdf` et relancer `render.py` : la page réelle remplace la réserve.
