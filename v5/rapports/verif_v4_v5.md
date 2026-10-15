# Comparaison V4 (existant) / V5

- V4 : `DECIMO_ESQ_V4.ifc` (IFC2X3, 141 produits) ; V5 : `v5/DECIMO_ESQ_V5.ifc` (IFC4, 431 produits)
- Tolérance : 1e-06 m ; géométrie calculée par ifcopenshell.geom 0.9.0 (coordonnées monde, ouvertures déduites)

| Catégorie | Éléments V4 | Retrouvés (GlobalId) | Identiques | Écart max placement (m) | Écart max sommets (m) | Écart max bbox (m) | Représentation identique | Ouvertures/remplissages identiques |
|---|---|---|---|---|---|---|---|---|
| Mur | 11 | 11 | 11 | 0 | 0 | 0 | 11/11 | 11/11 |
| Poteau | 1 | 1 | 1 | 0 | 0 | 0 | 1/1 | 1/1 |
| Dalle | 0 | - | - | - | - | - | - | - |
| Ouverture | 9 | 9 | 9 | 0 | 0 | 0 | 9/9 | 9/9 |
| Autre | 120 | 120 | 120 | 0 | 0 | 0 | 120/120 | 120/120 |

**Bilan : 141/141 produits V4 strictement identiques ; 0 écart(s).**


## Détail murs, poteau, ouvertures (V5)

| GlobalId | Classe | Nom | bbox min (m) | bbox max (m) | écart |
|---|---|---|---|---|---|
| `0TozFI3mL15O4poHyEQ8iA` | IfcBuildingElementProxy | 4351026 | [5.61, 3.3, 0.0] | [6.51, 4.2, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJToAZ` | IfcWallStandardCase | Mur de base:Agglos creux 15 + Enduit 2 Faces 1.5_K&D:4350587 | [-0.09, -0.09, 0.0] | [0.09, 7.59, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJToAa` | IfcWallStandardCase | Mur de base:Agglos creux 15 + Enduit 2 Faces 1.5_K&D:4350588 | [6.51, -0.09, 0.0] | [6.69, 7.59, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJToAb` | IfcWallStandardCase | Mur de base:Agglos creux 15 + Enduit 2 Faces 1.5_K&D:4350589 | [0.09, 7.41, 0.0] | [6.51, 7.59, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJToAc` | IfcWallStandardCase | Mur de base:Agglos creux 15 + Enduit 2 Faces 1.5_K&D:4350590 | [0.09, -0.09, 0.0] | [6.51, 0.09, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJTo9M` | IfcWallStandardCase | Mur de base:Agglos creux 15 + Enduit 2 Faces 1.5_K&D:4350606 | [2.91, 0.09, 0.0] | [3.09, 0.9, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJTo9N` | IfcWallStandardCase | Mur de base:Agglos creux 15 + Enduit 2 Faces 1.5_K&D:4350607 | [2.91, 1.8, 0.0] | [3.09, 2.8, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJTo98` | IfcWallStandardCase | Mur de base:Agglos creux 15 + Enduit 2 Faces 1.5_K&D:4350608 | [2.91, 5.04, 0.0] | [3.09, 7.41, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJTo94` | IfcWallStandardCase | Mur de base:Placo double  BA13_K&D:4350620 | [0.09, 6.24, 0.0] | [2.91, 6.36, 3.3] | 0 |
| `0UsrJW3tn86Pjy_3YJTo95` | IfcWallStandardCase | Mur de base:Placo double  BA13_K&D:4350621 | [0.09, 5.04, 0.0] | [2.91, 5.16, 3.3] | 0 |
| `1Xbo9Rxj54lBdGQdAKCQT2` | IfcWallStandardCase | Cloison rangement / dégagement | [1.76, 5.16, 0.0] | [1.88, 6.24, 3.3] | 0 |
| `23COPw6uz2Jumi0TgCM4LE` | IfcWallStandardCase | Cloison pleine salle de réunion | [2.955, 2.82, 0.0] | [3.045, 5.04, 3.3] | 0 |
| `2Bt4XlQeb8OAhxGeId5xHf` | IfcOpeningElement | Mur de base:Agglos creux 15 + Enduit 2 Faces 1.5_K&D:4350589 | [4.4, 7.41, 2.15] | [5.05, 7.59, 2.8] | 0 |
| `05QJ2s8uzA8PACe5Udts0Y` | IfcOpeningElement | Baie porte WC | [1.9, 6.22, 0.0] | [2.83, 6.38, 2.1] | 0 |
| `3Aybq3nGPAHgq8rnJ1Iuyh` | IfcOpeningElement | Baie porte salle de réunion | [2.94, 4.07, 0.0] | [3.06, 5.0, 2.1] | 0 |
| `2wVhltp1PCr9qcLFvWNPom` | IfcOpeningElement | Baie libre dégagement WC | [2.89, 5.3, 0.0] | [3.11, 6.14, 2.1] | 0 |
| `2tRnzcvWzB$8LrrmKmB_jp` | IfcOpeningElement | Baie porte coulissante rangement | [1.74, 5.32, 0.0] | [1.9, 6.08, 2.1] | 0 |
| `2txirjxH91tRmbhe4sIsKy` | IfcOpeningElement | Baie cintrée A | [0.55, -0.15, 0.45] | [1.75, 0.15, 2.549] | 0 |
| `3Ue7xYFnHCAuypiLGgV0Ps` | IfcOpeningElement | Baie cintrée B | [2.0, -0.15, 0.901] | [2.7, 0.15, 2.399] | 0 |
| `11kjkXgwrDjBpawVHlY$fa` | IfcOpeningElement | Baie cintrée C | [5.15, -0.15, 0.602] | [6.25, 0.15, 2.498] | 0 |
| `3y4g3CN_r7DOmYFlZr$cZQ` | IfcOpeningElement | Baie entrée principale | [3.35, -0.15, 0.0] | [4.85, 0.15, 2.798] | 0 |

## Ajouts V5

- 290 produits ajoutés ; nouvelles ouvertures dans un élément V4 : **0**
- Éléments structurels contrôlés (pset KDEMI_Existant « Existant porteur - ne pas toucher ») : 9
- Pénétrations > 2 mm d'un ajout dans la structure : **0**
- Auto-contrôle du détecteur : dalle haute ajoutée / volume de contexte « logements » V4 (4350698) -> recouvrement mesuré 0.2 m (attendu 0,20 : le volume V4 démarre à +3,30, signalé en point ouvert)

## Règles techniques

| Règle | Mesure | OK |
|---|---|---|
| Plénum sous dalle haute ≥ 0,25 m | 0.260 m (faux-plafond +3.00 / +3.04, dalle +3.30) | oui |
| Placard technique 0,60 x 0,40 net, porte pleine | 0.60 x 0.40 m ; porte : IfcDoor | oui |
| Tableau divisionnaire : 1,00 m dégagé devant | zone x 1.64-2.64, y 0.12-0.72, h 2,00 : 0 obstacle(s) [] | oui |
| Tableau loin de l'eau | 5.92 m du WC (lave-mains et WC dans le local 07) | oui |
| Split mural 9 000 BTU/h - unité intérieure 1 : sur mur plein, en hauteur, hors tables | +2.42 / +2.71 ; fixé sur ['4350588'] ; au-dessus de : aucune table | oui |
| Split mural 9 000 BTU/h - unité intérieure 2 : sur mur plein, en hauteur, hors tables | +2.30 / +2.59 ; fixé sur ['4350587'] ; au-dessus de : aucune table | oui |
| Réservations hors structure (8 : Ø 0,10 et Ø 0,04) | 0 intersection(s) avec poteaux / voiles / dalle | oui |
| Liaisons splits : faux-plafond puis baie arrière existante | 2 faisceaux, 0 intersection(s) avec la structure | oui |
| Coffrages EU/EV 0,30 x 0,30 « À relever sur site » | 2 coffrages [(0.3, 0.3), (0.3, 0.3)] ; statut ['À relever sur site'] | oui |
| Luminaires 2700 K de la V5 conservés et raccordés | 27 luminaires ; sans circuit : [] | oui |
| Appareillage électrique rattaché à un circuit du TD | 64 appareils / câbles, 16 circuits ; sans circuit : aucun | oui |
| BAES au-dessus de la porte d'entrée et en circulation | 4 BAES : ["au-dessus de la porte d'entrée", 'dégagement, vers la salle de lecture', 'coin lecture, passage à galandage', 'circulation salle de lecture (drapeau)'] | oui |
| Prise du WC hors volumes (≥ 0,60 m du lave-mains) | 1.03 m | oui |
| WC et lave-mains V4 conservés, non dupliqués, raccordés en V5 | doublons : 0 ; raccords : 4350629 <- ["Flexible d'alimentation du réservoir WC V4", 'Pipe WC Ø 100 (raccord cuvette V4)'] ; 4350630 <- ['Robinet temporisé eau froide (lave-mains V4)'] ; 4350631 <- ['Siphon du lave-mains V4'] | oui |
| Évacuations EU / EV : pente 1 à 3 % (DTU 60.11), mesurée sur l'axe | 3 tronçons, pentes [1.95, 2.0] % | oui |
| Fixations non traversantes (ancrage ≤ 60 mm et ≤ 1/3 du support) | 27 fixations ; non conformes : aucune | oui |
| Raccordements aux réseaux de l'immeuble marqués « à relever » | 6 réseaux ; à relever / vérifier : ['CFO', 'AEP', 'EU', 'EV', 'Condensats des 2 splits (mini-pompes -> EU)', 'VP'] | oui |
| Pas de toiture, d'escalier, de TGBT ni de groupe électrogène | 0 trouvé(s) | oui |

**Résultat global : CONFORME**
