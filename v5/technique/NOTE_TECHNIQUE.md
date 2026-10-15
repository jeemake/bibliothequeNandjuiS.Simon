# Bibliothèque Decimo — note technique ESQ V5 (lots électricité, courants faibles, AEP/EU/EV)

Local commercial de 43,55 m² intérieurs au RDC d'un immeuble d'habitation à Abidjan (climat tropical humide). C'est un ERP de type S (bibliothèque), de 5e catégorie supposée. Niveau esquisse : les cotes, les positions et les puissances sont indicatives.

## 1. Base et règles

- Maquette de départ : `v5/DECIMO_ESQ_V5.ifc` (IFC4), dont la V4 est l'existant. La maquette technique `v5/DECIMO_ESQ_V5_tech.ifc` est une copie à laquelle on a seulement **ajouté** 78 produits. Elle contient aussi les circuits (`IfcDistributionCircuit`) et les réseaux (`IfcDistributionSystem`).
- Aucun mur, poteau, ouverture ni cote V4 n'est modifié. Aucun percement n'est fait dans les poteaux, les voiles ou la dalle haute, et aucune saignée dans les porteurs.
- Le WC (`0UsrJW3tn86Pjy_3YJTo9z`) et le lave-mains (plan 4350630, vasque 4350631) du local 07 restent exactement tels qu'ils sont. Ils sont lus dans l'IFC (`technique.lire_sanitaires`) et on se contente de s'y raccorder. Aucune relation ni aucun pset n'est ajouté sur un objet V4.
- Vérifications :
  - `technique/verif_v4_v5_tech.md` : 141/141 produits V4 identiques, 0 nouvelle ouverture, 0 pénétration de plus de 2 mm dans la structure ;
  - `technique/verif_technique.md` : 231/231 produits V5 identiques, et règles techniques ci-dessous toutes respectées ;
  - `technique/validation_V5_tech.txt` : 0 erreur de schéma, 303/303 géométries.

## 2. Normes et référentiels

| Lot | Référentiel |
|---|---|
| Électricité | NF C 15-100 (installations BT), règlement ERP (PE 24 éclairage de sécurité, EC), NF EN 60598-2-22 (BAES), guide UTE C 15-443 (parafoudres) |
| Courants faibles | NF EN 50173 / EN 50174-2 (câblage et séparation CFO/CFA), Cat 6A |
| Plomberie | NF DTU 60.11 (calcul), NF EN 12056 (évacuation gravitaire), NF DTU 60.1, NF EN 1717 (anti-pollution), EN 12380 (clapets d'admission d'air) |
| Acoustique | Coffrages de descentes : 2 BA13 + laine minérale 45 mm, colliers isophoniques |

## 3. Électricité (T01, T05)

- **Origine** : le coffret d'arrivée existant du placard technique (disjoncteur de branchement 2P 500 mA S) alimente le tableau divisionnaire V5 par une liaison U1000 R2V 3G10 posée dans le chemin C1 et passant par la réservation R5. La longueur est d'environ 11,6 m et la chute de tension de 0,31 %. **Le cheminement entre l'immeuble et le placard est inconnu.**
- **Tête du tableau** : interrupteur-sectionneur 2P 40 A et parafoudre type 2 (Abidjan a une forte densité de foudroiement). Trois interrupteurs différentiels 40 A 30 mA protègent les départs :
  - ID1 (type A) : E1, E4, E6, P2, P4 ;
  - ID2 (type A) : E2, E3, E5, P1, P3 ;
  - ID3 (type F) : C1, C2, P5.

  Il y a 2 réserves et 20 % de modules libres.
- **Éclairage** : les 27 luminaires LED 2700 K de la V5 sont répartis sur 6 circuits en 1,5 mm² / 16 A, avec 8 points au plus par circuit (BAES compris) :
  - E1 (salle, entrée et accueil) et E2 (fond de salle) sont sur télérupteurs ;
  - E3 (oculus et canopée) est sur variateur ;
  - E4 (coin lecture) est commandé par un interrupteur double ;
  - E5 (réunion, rangement, dégagement, WC) est commandé par interrupteurs et détecteurs ;
  - E6 (vitrine et seuil) est sur horloge astronomique.

  L'appareillage est en saillie, à +1,10 pour les commandes.
- **BAES** : 5 BAES LED 45 lm / 1 h. B1 est au-dessus de l'issue principale, B2 à B5 aux changements de direction (passage du coin lecture, sortie de la réunion, baie libre du dégagement, fond de salle). Ils sont alimentés en amont des commandes du circuit d'éclairage du local.
- **Prises 16 A** : 21 socles en saillie à +0,30 (ou +1,10 au-dessus du mobilier), répartis ainsi :
  - P1 accueil : 4 socles ;
  - P2 postes de lecture et d'écoute : 4 socles, dont une prise USB intégrée à la niche ;
  - P3 réunion : 7 socles ;
  - P4 ménage : 4 socles ;
  - P5 baie informatique : 2 socles.
- **Splits 2 × 9 000 BTU/h** : chaque split a son circuit spécialisé en 16 A / 2,5 mm² (C1, C2), avec sa mini-pompe de condensats. Il faut prévoir un sectionneur de proximité IP65 à chaque groupe extérieur.
- **Cheminements** :
  - en plénum (0,26 m) sur les chemins existants C1, C1b et C2 (80 × 40) ;
  - suspentes M8 au pas de 1,20 m au plus, sur chevilles courtes non traversantes (40 mm au plus, après repérage au ferroscan) ;
  - descentes en goulotte 40 × 20 collée, ou derrière le lambris iroko et dans le doublage des niches ;
  - le dégagement est desservi par une goulotte collée en sous-face du linteau de la baie libre V4 (hauteur libre 2,08), sans aucun percement.
- **Bilan de puissance** : 4,91 kW installés et 3,45 kW utilisés. Avec ks = 0,9, la puissance foisonnée est de 3,11 kW, soit 3,45 kVA et 15 A. On propose un **abonnement monophasé de 6 kVA (30 A)**. La chute de tension cumulée est de 0,82 % au plus (circuit P4), pour des limites de 3 % et 5 %.

## 4. Courants faibles (T02)

- Baie 9U existante de la V5 dans le placard : box, panneau 24 RJ45 Cat 6A, switch PoE et onduleur.
- 6 prises RJ45 doubles, soit 12 ports : 2 à l'accueil, 1 à la console d'écoute, 3 en réunion (dont une pour l'écran). S'y ajoute une borne Wi-Fi 6 PoE sous le faux-plafond de la salle de lecture.
- Un chemin CFA 50 × 30 est posé à 5,5 cm du chemin CFO. Au passage de R5, les câbles VDI partagent la dalle C1, munie d'une cloison séparatrice.

## 5. AEP / EU / EV (T03, T04)

| Réseau | Tracé | Diamètre | Pente | Fil d'eau |
|---|---|---|---|---|
| EV WC | Pipe excentrée sur la sortie existante, coude 87°30 à tampon, culotte sur la descente 1 | PVC Ø 100 | 2 % | +0,125 › +0,117 |
| EU lave-mains | Siphon sur la bonde existante, clapet d'admission d'air, 2 coudes à bouchon de dégorgement, culotte 100/40 | PVC Ø 40 | 2 % | +0,560 › +0,497 |
| AEP | Piquage sur la colonne supposée du coffrage 1 ; vanne, filtre, réducteur, compteur divisionnaire et clapet EA sous trappe ; antennes vers le réservoir et le lave-mains | Multicouche 20 et 16 × 2 | — | — |

- **Ventilation** : la ventilation primaire est assurée par la descente de l'immeuble prolongée en toiture (à vérifier). Le branchement EU mesure plus de 2 m : un clapet d'admission d'air (AAV) accessible est posé sous le plan.
- **Visite** : un té de visite Ø 100 est posé sur la descente, face à une trappe acoustique du coffrage. Les coudes sont à tampon ou à bouchon de dégorgement.
- **Condensats** : ils sont relevés par les mini-pompes V5. Le refoulement Ø 6/9 passe dans le faisceau des liaisons, sort par l'imposte de la baie arrière existante et rejoint un regard EP de la courette. Le rejet en EU n'est possible qu'après un siphon à garde d'eau.
- **Coffrages acoustiques** : les coffrages 0,30 × 0,30 de la V5 sont conservés (2 BA13, laine 45 mm autour de la descente, colliers isophoniques, trappe). La descente 2, dans le rangement, n'est pas utilisée par le local.
- **Eau chaude** : le lave-mains est en eau froide seule.

## 6. Hypothèses (non lisibles dans l'IFC, ou absentes)

1. La sortie du WC n'est pas décrite dans l'IFC (représentation mappée, sans port). On suppose une sortie horizontale à l'arrière, à 0,18 de hauteur, au dos du pied de cuvette.
2. Le siphon et la robinetterie du lave-mains ne sont pas modélisés en V4. On suppose la bonde au centre de la vasque et le plan à +0,75.
3. La colonne AEP de l'immeuble est supposée dans le coffrage 1 (Ø 32). Les descentes EU/EV Ø 100 sont celles de la V5, elles aussi en hypothèse.
4. Puissances des prises : usages déclarés. Splits : 0,82 kW électriques chacun (EER 3,2), plus 15 W par pompe.

## 7. Points à relever et points ouverts

1. **Arrivée électrique** : origine dans l'immeuble, cheminement jusqu'au placard, calibre disponible, existence d'une prise de terre (R < 100 Ω) et régime de neutre.
2. **Descentes et colonne AEP** : position réelle dans les coffrages, diamètres, matériaux, pression de l'eau (réducteur si P > 3 bar) et ventilation primaire.
3. **Sortie du WC** (horizontale ou verticale, hauteur) et état du raccordement existant.
4. **R6** : fourreau Ø 50 en plénum dans la cloison placo V4 4350620 (non porteuse), nécessaire pour éclairer le WC. Il a le même statut que R5 : c'est un percement léger d'une cloison V4, à valider par la MOA. La variante sans percement est une goulotte en applique franchissant l'huisserie de la porte du WC.
5. **Spot sous marquise (E6)** : aucun passage existant ne traverse la façade. Il faut valider un passage par le dormant de la porte d'entrée, ou remplacer le spot par un modèle autonome.
6. **Ventilation du WC aveugle** : aucun rejet n'est possible sans percement. À arbitrer : raccordement à une VMC existante de l'immeuble s'il y en a une dans la gaine (à relever), ou gaine en plénum jusqu'à la baie arrière (bloquée par le refend porteur 4350608). Il est interdit de se raccorder sur la descente EV.
7. **Baie arrière** : l'imposte vitrée V4 4350595 est à adapter pour le panneau passe-liaisons. Il faut l'accord de la copropriété pour la courette, les groupes extérieurs, le tube de condensats en façade et le regard EP.
8. **Fixations en sous-face de dalle** (chemins, liaisons, faux-plafond) : chevilles courtes non traversantes à valider par le BET après ferroscan. Le statut porteur des refends agglo est à confirmer.
9. **Abonnement** de 6 kVA à confirmer auprès de la CIE et du syndic. Le compteur divisionnaire d'eau est à faire agréer.
10. Les appareils fixés sur le mobilier (niche banquette) et la hauteur libre de 2,08 sous la goulotte de la baie libre sont à valider avec la MOA.

## 8. Régénérer

```bash
python3 v5/scripts/construire_tech.py
python3 v5/scripts/valider_ifc.py v5/DECIMO_ESQ_V5_tech.ifc v5/technique/validation_V5_tech.txt
python3 v5/scripts/verif_v4_v5.py --v5 v5/DECIMO_ESQ_V5_tech.ifc v5/technique/verif_v4_v5_tech.md
python3 v5/scripts/verif_tech.py v5/technique/verif_technique.md
python3 v5/scripts/dessins_tech.py          # T01 à T05 en PNG, PDF et SVG
```
