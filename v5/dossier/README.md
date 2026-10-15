# Dossier de présentation, Bibliothèque Decimo, ESQ V5 (indice G, 15 octobre 2026)

A3 paysage, 25 pages, charte K&Démi v2 : papier blanc, texte gris (#4A4A4A, secondaire #8C8C8C), une seule famille Archivo (titres SemiBold, texte Regular, capitales Medium), terre cuite en accent, indigo rare, logo v3 A. Grille invisible : marges 14 mm, gouttières 5 mm, panneau de droite commun avec les planches A01 à A08 et T01 à T05.

Indice G : page 19 « Pergola, trois variantes » (G4), avant les planches T01 à T05, qui passent en pages 20 à 24. Même emprise, mêmes appuis et même profondeur que la pergola V4 : 1 simple (lattes iroko droites sur cadre acier noir, coût faible), 2 entre-deux (une vague, rives alternées, deux guirlandes 2700 K, coût moyen), 3 Gen Z (six arcs iroko en enfilade, arche du logo, ampoules 2700 K, coût moyen à élevé). Pour chaque option : vue 01 (même caméra que R1 et G1), plan de toiture et coupe au 1/100. Géométrie par script hors maquette (`v5/scripts/pergola_variantes.py`, sorties dans `v5/pergola/`), aucun fichier IFC modifié, pas de rendu fal. Le reste du dossier est inchangé (contrôle pixel avant/après, seuls l'indice et le sommaire bougent).

Indice F : section « Decimo, côté Gen Z » (pages 16 à 18, avant les planches T01 à T05, qui passent en pages 19 à 23). Quatre rendus chaleureux tirés des vues IFC (`rendus/G1` à `G4`, script `scripts/gen_genz.py`, nouvelle caméra 06 sur l'accueil dans `v5/scripts/vues_rendu_genz.py`) et un extrait du plan A01 annoté des 5 touches (`rendus/G5_plan_touches.png`, `scripts/plan_touches_genz.py`) : tampon daté, livres-surprises en kraft, réglette iroko des coups de cœur, vitrine du coin lecture, terrasse le soir. Écarts des rendus listés sur les pages 16 et 17. Maquette IFC inchangée, le reste du dossier aussi.

Indice E : végétation redessinée au trait comme sur un dessin d'archi classique, sans aplat vert ni disque (`v5/scripts/vegetation.py`). En plan : arbres d'alignement en houppier festonné avec charpentières rayonnantes et point de tronc (A01), touffes des jardinières et plante V01 en contour festonné avec nervures (A01, fond de plan T01 à T03). En coupe et élévation : arbres en entourage (tronc effilé, charpentières, houppier festonné, A04), arbustes des jardinières et plante V01 en touffe arrondie avec tiges en éventail (A03 à A06). Trait gris-vert très sourd #7E8A78, gris de fond sur les planches T. Tailles et positions = emprises IFC, ombres inchangées. Seuls ces éléments changent (contrôle pixel avant/après).

Indice D : ombres portées légères sur les planches A01 à A06 (pages 5 à 10), calculées sur la géométrie IFC par carte d'ombres (`v5/scripts/ombres.py`) : soleil conventionnel à 45° venant du haut à gauche, aplat noir à 15 % sans dégradé, peint sous les traits et au-dessus du sol. En plan, ombres courtes (0,25 m par mètre de hauteur sous le plan de coupe). En coupe et élévation, profondeur d'ombre égale à la profondeur réelle du débord, limitée aux objets proches de la paroi (1,0 m le long du rayon à l'intérieur, 1,6 m en façade). T01 à T05 inchangées.

Indice C : planches T01 à T05 relues pour le technicien : fond de plan en gris clair (porteurs #BDBDBD, traits #C8C8C8), une couleur saturée par lot, identique sur les 5 planches (courants forts rouge #D62828, courants faibles bleu #1F5FBF, éclairage ocre #E08A00, BAES vert #1E9E4A, AEP cyan #00A3C4, EU/EV brun #8B5A2B avec EU en tireté et EV en continu, clim et condensats violet #7B3FA0, réservations magenta #C2185B), symboles plus épais que le fond, légende par lot au même endroit sur chaque planche (pastille, symbole à taille réelle, libellé 8 pt, quantité comptée sur la planche), repères de circuits identiques au schéma unifilaire T05.

Indice B : fond beige retiré, DM Serif Display et Jost remplacés par Archivo, matières des planches mises en sourdine, planches T01 à T05 d'Ahoua intégrées (PR #5).

| Fichier | Contenu |
|---|---|
| `Decimo_ESQ_V5_Dossier_A3_v6.pdf` | Dossier final : couverture, projet, identité, D.A, A01 à A08, rendus R1 à R3, T01 à T05, cohérence |
| `Decimo_ESQ_V5_Dossier_A3_v6.pptx` | Même dossier en version modifiable (aussi importé en Google Slides) |
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
