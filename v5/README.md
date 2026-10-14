# Bibliothèque Decimo — Esquisse V5 (RDC, un seul niveau)

Local en rez-de-chaussée d'un immeuble existant (logements au-dessus), emprise 6,78 × 7,68 m
hors tout (6,42 m entre voiles mitoyens), **43,77 m² utiles**. Pas d'étage, d'escalier, de toiture ni de façade cintrée :
la devanture reste dans la baie existante, sous la poutre.

## Contenu

| Fichier | Rôle |
|---|---|
| `DECIMO_ESQ_V5.ifc` | Maquette IFC4 native (mm) : Project / Site / Building / Storey RDC |
| `DECIMO_ESQ_V5_maillage_Revit.ifc` | Même maquette, géométrie triangulée (`IfcTriangulatedFaceSet`), ouvertures déjà découpées |
| `dessins/DECIMO_ESQ_V5_0x_*.png / .pdf / .svg` | Planches A3 (PNG 200 dpi, PDF et SVG vectoriels, SVG sauf pour les vues 3D) |
| `dessins/DECIMO_ESQ_V5_Dessins.pdf` | Recueil des 6 planches |

Planches : 01 plan RDC 1/50 (coupé à +1,00) · 02 coupe AA 1/50 · 03 élévation de la devanture 1/50 ·
04 élévation intérieure 1/30 (le 1/25 ne tient pas sur l'A3 à côté du cartouche) · 05 axonométries · 06 perspectives.

## Régénérer

```bash
pip install ifcopenshell shapely matplotlib numpy pillow pytest   # pytest : requis par validate --express-rules
python3 scripts/generer_ifc_v5.py   v5/DECIMO_ESQ_V5.ifc
python3 scripts/maillage_revit_v5.py v5/DECIMO_ESQ_V5.ifc v5/DECIMO_ESQ_V5_maillage_Revit.ifc
python3 scripts/verifier_ifc_v5.py  v5/DECIMO_ESQ_V5.ifc v5/DECIMO_ESQ_V5_maillage_Revit.ifc   # code retour ≠ 0 si erreur
python3 scripts/dessins_v5.py       v5/DECIMO_ESQ_V5.ifc v5/dessins          # option : 3e argument "1,3" pour certaines planches
```

Testé avec Python 3.12, IfcOpenShell 0.9.0, shapely 2.2, matplotlib 3.11. Les polices DM Serif Display et
Jost (licence OFL) sont dans `charte/fonts/`. Tous les dessins sont lus dans l'IFC : sections calculées par
plan de coupe sur les maillages `ifcopenshell.geom`, faces cachées par tri en profondeur. Le contexte urbain
(trottoir, chaussée, arbres) est dans l'IFC (`IfcCivilElement` / `IfcGeographicElement` sur le site). Les
façades de l'immeuble et des mitoyens sont seulement dessinées.

## Validation (dernier passage)

| Fichier | `ifcopenshell.validate` (+ règles EXPRESS) | `ifcopenshell.geom` |
|---|---|---|
| `DECIMO_ESQ_V5.ifc` | 0 erreur | 158/158 produits, 94 224 triangles |
| `DECIMO_ESQ_V5_maillage_Revit.ifc` | 0 erreur | 158/158 produits, 94 224 triangles |

Le placement de chaque objet maillé est contrôlé contre l'original (écart de boîte englobante < 1e-12 m).

## Espaces (`Qto_SpaceBaseQuantities`, hauteur sous faux-plafond 2,85 m)

| N° | Espace | Surface nette m² |
|---|---|---|
| 01 | Accueil — entrée | 9,41 |
| 02 | Coin jeunesse — vitrine | 7,19 |
| 03 | Salle de lecture — arbre à livres | 13,94 |
| 04 | Espace de travail — tables de lecture | 7,78 |
| 05 | Dégagement — réserve | 1,92 |
| 06 | WC | 3,29 |
| 07 | Placard technique (0,60 × 0,40 net) | 0,24 |
| | **Total** | **43,77** |

## Limites et caveats

- **Revit** : un import IFC produit des formes non natives (familles « modèle générique » ou DirectShape).
  Les murs ne sont pas des murs système éditables, les portes n'ont ni paramètres ni flip. Les couches
  `IfcMaterialLayerSet` restent lisibles en propriétés mais ne pilotent pas la géométrie. Utiliser le
  fichier IFC comme lien de référence, ou redessiner en natif sur cette base. Si les booléens (ouvertures,
  coupole du faux-plafond, claustra évidé) posent problème, utiliser la variante maillée : elle n'a plus
  d'`IfcOpeningElement`, car les trous sont déjà dans le maillage, mais elle garde Psets, quantités,
  matériaux et styles.
- Les motifs du claustra (Eban, Nsoromma) sont des interprétations géométriques d'esquisse, à valider
  avec la D.A. et le fabricant. Gye Nyame est volontairement exclu.
- Le rendu des vues 3D est schématique (couleurs des styles IFC, ombrage simple) : à reprendre en APS.
- Les cotes de l'existant (poteaux, voiles, poutre, descentes EU/EV) reprennent la V4 et doivent être
  confirmées par un relevé.

## Points ouverts

1. Relevé de l'existant : positions et sections des poteaux P1 à P3, de la poutre PT1, des descentes EU/EV et de la sous-face de dalle (+3,30 supposé).
2. Splits 2 × 9 000 BTU : bilan thermique à confirmer (vitrine plein sud, occupation). Évacuation des condensats non modélisée (vers le WC ou la courette ?).
3. Réservations Ø 100 dans le mur arrière (courette) : accord du syndic et du BET structure.
4. WC : vérifier l'accessibilité PMR (cercle de rotation Ø 1,50, barres d'appui) pour un ERP de 5e catégorie.
5. Fixations de la devanture, du claustra et de l'enseigne sur la structure existante : à valider par le BET.
6. Arbre à livres et coupole : charge sur dallage, ancrage et réaction au feu (M1/B-s1,d0) du bois et du plafond acoustique.
