# Dossier de présentation, Bibliothèque Decimo, ESQ V5 (indice C, 15 octobre 2026)

A3 paysage, 21 pages, charte K&Démi v2 : papier blanc, texte gris (#4A4A4A, secondaire #8C8C8C), une seule famille Archivo (titres SemiBold, texte Regular, capitales Medium), terre cuite en accent, indigo rare, logo v3 A. Grille invisible : marges 14 mm, gouttières 5 mm, panneau de droite commun avec les planches A01 à A08 et T01 à T05.

Indice C : planches T01 à T05 relues pour le technicien : fond de plan en gris clair (porteurs #BDBDBD, traits #C8C8C8), une couleur saturée par lot, identique sur les 5 planches (courants forts rouge #D62828, courants faibles bleu #1F5FBF, éclairage ocre #E08A00, BAES vert #1E9E4A, AEP cyan #00A3C4, EU/EV brun #8B5A2B avec EU en tireté et EV en continu, clim et condensats violet #7B3FA0, réservations magenta #C2185B), symboles plus épais que le fond, légende par lot au même endroit sur chaque planche (pastille, symbole à taille réelle, libellé 8 pt, quantité comptée sur la planche), repères de circuits identiques au schéma unifilaire T05.

Indice B : fond beige retiré, DM Serif Display et Jost remplacés par Archivo, matières des planches mises en sourdine, planches T01 à T05 d'Ahoua intégrées (PR #5).

| Fichier | Contenu |
|---|---|
| `Decimo_ESQ_V5_Dossier_A3_v3.pdf` | Dossier final : couverture, projet, identité, D.A, A01 à A08, rendus R1 à R3, T01 à T05, cohérence |
| `Decimo_ESQ_V5_Dossier_A3_v3.pptx` | Même dossier en version modifiable (aussi importé en Google Slides) |
| `rendus/` | Rendus finaux tirés des vues `v5/vues_rendu` (fal nano-banana-pro/edit), `01_devanture_fal_brut.jpg` = sortie brute avant retouche |
| `scripts/layout.py`, `scripts/render.py` | Mise en page unique vers PDF (reportlab) et PPTX (python-pptx) |
| `scripts/gen_rendus.py` | Génération des rendus depuis les vues IFC |
| `scripts/fix_r1.py` | Retouche locale de R1 : retire les balcons inventés sur l'immeuble voisin (la maquette montre un mur plein) |
| `scripts/controle_v4_v5_independant.py` | Contre-vérification V4 / V5 indépendante du script de Téïsson |

## Contrôles

- Sur `main` : 141/141 produits V4 retrouvés en V5, placements et géométries identiques (écart 0), emprise des murs 6,78 × 7,68 m, WC 4350629 et lave-mains 4350630/4350631 conservés, 0 toiture, 0 escalier.
- Rendus comparés à leur vue IFC source. R2 à R5 conformes. R1 : balcons inventés retirés. Écart restant : les jardinières de la terrasse sont rendues en banquettes (la maquette fait foi).

## Reste à faire

- R1 : jardinières de la terrasse rendues en banquettes, à reprendre (budget fal épuisé).
- Points ouverts des lots techniques : voir `v5/technique/NOTE_TECHNIQUE.md`.
