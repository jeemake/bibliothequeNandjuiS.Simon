# Bibliothèque Decimo — esquisse V5 (aménagement sur existant V4)

RDC sous logements, Abidjan, un seul niveau (environ 6,78 × 7,68 m hors œuvre). Il n'y a pas de toiture, d'étage ni d'escalier dans le lot.

**Règle absolue : `DECIMO_ESQ_V4.ifc` est l'existant.** La V5 en est une copie migrée en IFC4. Les GlobalId, les placements et les géométries sont conservés, et on n'a fait qu'**ajouter** de l'aménagement : faux-plafonds, revêtements, cloisons légères, menuiseries dans les baies existantes, mobilier, éclairage, équipements, réservations et espaces. Un seul élément structurel manquait : la dalle haute. Elle est ajoutée sur l'emprise exacte des murs V4 et signalée comme hypothèse. La comparaison V4/V5 est scriptée (`scripts/verif_v4_v5.py`).

## Contenu

| Chemin | Rôle |
|---|---|
| `DECIMO_ESQ_V5.ifc` | Maquette IFC4 native : V4 intacte + aménagement (231 produits, 8 `IfcSpace`) |
| `DECIMO_ESQ_V5_maille_Revit.ifc` | Variante maillée pour Revit (`IfcTriangulatedFaceSet` stylés, sans ouvertures booléennes) |
| `dessins/A01…A11_*.png/pdf/svg` | Planches A3 : aménagement (A01-A08) + lots techniques A09 (électricité), A10 (plomberie), A11 (détails) |
| `rapports/quantites_lots_techniques.md` / `.csv` | Quantitatif des lots techniques (circuits, câbles, tuyaux, appareils) |
| `vues_rendu/*_ombre.png`, `*_traits.png`, `*_camera.json` | Cinq vues perspectives 2560 × 1600 sans légende (pour les rendus fal) + variante en traits + caméra reproductible |
| `rapports/verif_v4_v5.md` | Résultat de la comparaison V4/V5 et des règles techniques |
| `rapports/validation_V5*.txt` | `ifcopenshell.validate` (schéma + règles EXPRESS) et géométrie de chaque produit |
| `rapports/corrections_conformite_ifc4.txt` | Corrections non géométriques imposées par la migration IFC2X3 vers IFC4 |
| `rapports/espaces.csv`, `rapports/reperes.csv` | Surfaces des espaces, nomenclature des repères 1 à 33 |
| `scripts/` | Chaîne complète (voir ci-dessous) |

## Régénérer

```bash
sudo apt-get install -y libegl1 libegl-mesa0 libgl1-mesa-dri libgles2   # rendu OpenGL sans écran (EGL)
pip install -r v5/requirements.txt
bash v5/regenerer.sh          # depuis la racine du dépôt
```

Ordre des scripts (tous dans `v5/scripts/`) :

1. `construire_v5.py` : migre la V4 en IFC4 et ajoute l'aménagement, puis écrit `rapports/espaces.csv` et `rapports/reperes.csv`.
2. `valider_ifc.py FICHIER [rapport]` : validation du schéma et des règles EXPRESS, puis `create_shape` sur la représentation Body de chaque produit.
3. `verif_v4_v5.py` : pour chaque produit V4, compare le GlobalId, le placement monde, l'arbre de représentation, les sommets et la bbox (tolérance 1e-6 m), ainsi que les ouvertures et remplissages. Il vérifie aussi les pénétrations booléennes (manifold3d) des ajouts dans les porteurs, avec un auto-contrôle du détecteur, et les règles techniques.
4. `quantites.py` : quantitatif des trois lots techniques (électricité, plomberie, fixations) → `rapports/quantites_lots_techniques.*`.
5. `variante_revit.py` : produit la variante maillée.
6. `vues_rendu.py [l h]` : génère les vues perspectives (moteur `rendu_gl.py`, moderngl/EGL, ombres portées et occlusion approchée).
7. `dessins.py [A01 …]` : génère les planches A01-A08 ; importe `dessins_lots.py` pour A09-A11. Le moteur `dessin2d.py` calcule les coupes (poché par plan de coupe des maillages) et les projections (silhouettes par élément, peintes de l'arrière vers l'avant). Graisses 0,18 / 0,35 / 0,70 mm (1:2:4).

### Lots techniques (hyp. ESQ Ahoua)

- `lots_techniques.py` (section 13 de `construire_v5.py`) : ajoute à l'IFC les circuits CFO/CFA (`IfcDistributionCircuit` E1-E7, P1-P6, CL1-CL2, VDI ; pset `KDEMI_Circuit`), les systèmes (`KDEMI_Reseau`), prises/commandes/BAES, câbles et goulottes, AEP/EU/EV/condensats/VP, fixations non traversantes (`KDEMI_Fixation`) et le seuil de vitrine baie A. Trois lots IFC : `Technique - électricité`, `Technique - plomberie`, `Technique - fixations`.
- **WC (tag 4350629) et lave-mains V4 (4350630 plan, 4350631 vasque) ne sont pas dupliqués** : les raccordements V5 sont des `IfcRelConnectsElements` nommés « Raccordement V5 sur appareil V4 conservé » (flexible + évacuation WC, robinet temporisé, siphon).
- **Pas de chauffe-eau** : un seul lave-mains, eau froide réseau (26-30 °C à Abidjan), pas de circuit 20 A dédié ni de stockage d'eau chaude (risque de légionelles).
- Planches **A09** (plan électricité 1/50 + tableau des circuits), **A10** (plomberie 1/50, zoom et élévation WC 1/25), **A11** (six détails 1/10 et 1/20) dans `dessins_lots.py`.

`scene.py` met en cache dans `v5/cache/` (non versionné) le maillage de chaque produit et ses couleurs.

Repère : celui de la V4. L'origine est l'angle intérieur sud-ouest du gros œuvre, x va vers l'est, y de la rue vers le fond, et z part du sol fini du RDC. L'IFC est en centimètres (unité héritée de la V4) ; les scripts travaillent en mètres.

## Vérification V4 / V5 (extrait de `rapports/verif_v4_v5.md`)

- 141 produits V4 sur 141 sont strictement identiques : murs 11, poteau 1, ouvertures 9, autres 120. Les écarts de placement, de sommets et de bbox sont tous nuls.
- Aucune nouvelle ouverture dans un élément V4, et aucune pénétration de plus de 2 mm d'un ajout dans un poteau, un voile ou la dalle.
- Toutes les règles techniques sont respectées : plénum 0,26 m (minimum 0,25), placard 0,60 × 0,40 net, 1,00 m libre devant le tableau, splits sur murs pleins hors aplomb des tables, réservations hors structure, coffrages EU/EV « À relever sur site ».
- Validation : V5 en IFC4 avec 0 erreur et 225/225 géométries ; variante Revit avec 0 erreur et 215/215 géométries. L'écart de bbox entre la V5 et la variante maillée est de 0,5 µm au maximum sur 207 produits.

## Import Revit

- Utiliser `DECIMO_ESQ_V5_maille_Revit.ifc` (Insérer > Lier IFC, ou Ouvrir IFC). Tous les objets arrivent comme **formes non natives (DirectShape)** dans la catégorie correspondant à leur classe IFC. Ce ne sont pas des murs, portes ou familles Revit éditables, et les murs ne sont pas paramétriques.
- Les ouvertures sont déjà creusées dans le maillage des murs. Les portes et fenêtres sont des objets indépendants, sans hébergement.
- Couleurs : un style de surface par matériau. Les textures (`../textures/*.png`) ne sont référencées que dans la V5 native.
- Les propriétés (`KDEMI_Esquisse.Repere`, `KDEMI_Existant.Statut`, psets standards) et les `IfcSpace` sont conservés.
- La V5 native reste la référence pour les autres logiciels (BlenderBIM/Bonsai, ArchiCAD, Solibri).

## Charte des cartouches

Les planches A01 à A11 utilisent le logo K&Démi v3 A (`charte/logo_v3/`), tracé en vectoriel à partir du SVG par `draw_lockup()` (`charte/charte_kdemi.py`). Les règles sont les suivantes :
- on utilise toujours le lockup, avec le nom à côté du symbole ;
- sa largeur imprimée est de 46 mm, et la fonction refuse toute largeur sous 30 mm ;
- on prend la version mono sur le panneau sable clair, et la version inverse sur fond sombre.

Le nom « K&Démi » est composé en Manrope. Jost reste la police du texte et DM Serif Display celle des titres. Les polices (licence OFL) sont dans `charte/polices/`.

## Limites

- Esquisse : cotes et surfaces indicatives. L'existant V4 est lui-même une maquette d'esquisse, à relever sur site.
- Les dessins sont des projections orthogonales calculées sur maillage. L'élimination des parties cachées se fait objet par objet (algorithme du peintre), pas par arête exacte, ce qui peut donner de légers défauts sur les objets imbriqués.
- Les vues 3D sont des pré-rendus OpenGL (sans lancer de rayons) : elles servent de base de cadrage et de matériaux pour la génération fal.
- Les espaces sont calculés comme zones moins l'emprise des murs V4. La terrasse fait 15,74 m² nets (la V4 annonçait 18,1 m² bruts).

## Points ouverts

1. **Dalle haute ajoutée** (absente de la V4) : épaisseur 0,20 en hypothèse, sous-face à +3,30. Elle recouvre la base du volume « logements » V4 (4350698, qui démarre à +3,30), que l'on n'a pas modifié. Épaisseur et sous-face sont à relever.
2. Les claustras V4 de la baie A sont conservés devant la vitrine en arche, ce qui la rend peu lisible depuis la rue. Il faut décider avec la MOA si on les retire (ce serait une modification de l'existant, non faite).
3. Les motifs Adinkra (Adinkrahene, Eban ; pas de Gye Nyame) sont ajoutés en inserts dans les anneaux V4 conservés. Leur fabrication est à valider avec l'artisan terre cuite.
4. Les rails lumineux et suspensions V4 (z +3,02 à +3,14) se retrouvent dans le plénum ou traversent le faux-plafond à +3,00. Ils sont à redescendre ou à supprimer en APS.
5. Imposte vitrée V4 (4350595) de la baie arrière : à adapter pour recevoir le panneau passe-liaisons (rep. 32), avec l'accord de la copropriété pour la sortie sur la courette.
6. Les condensats sont refoulés par mini-pompes vers la descente EU/EV 2 (siphon sec), car aucune évacuation gravitaire n'est possible sans percement.
7. Le cheminement de l'arrivée électrique de l'immeuble jusqu'au placard technique est inconnu et doit être relevé.
8. Tableau divisionnaire : la hauteur de 0,75 est une hypothèse, et son habillage iroko masque 6 cm du tableau de la baie B.
9. La réservation R5 traverse la cloison placo V4 4350621 (non porteuse) : c'est un percement léger dans un élément V4, à confirmer.
10. Le statut porteur des refends en agglos (4350606, 4350607, 4350608) est à confirmer par le BET ; par prudence, ils sont traités comme porteurs.
11. Les fixations du chemin de câbles et des liaisons sous la dalle ne doivent pas être des percements traversants (chevilles de faible profondeur) : à valider avec le BET.
12. Les niveaux SS1, N01 et N02, la pergola V4 et les tables de lecture V4 sont conservés tels quels.
13. **Réservations légères R6, R7, R8** (Ø 0,04) dans des cloisons / doublages V4 non porteurs ; **boîtes de sol** dans la chape du sol fini ; **fourreau d'enseigne V4** réutilisé ; **branchements immeuble** (AEP, EU, EV, CFO) « à relever sur site » ; **réducteur de pression** seulement si P > 3 bar.
