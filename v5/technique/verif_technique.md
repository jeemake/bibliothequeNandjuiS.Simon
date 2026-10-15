# Vérification des lots techniques

- Base : `v5/DECIMO_ESQ_V5.ifc` (231 produits) ; maquette technique : `v5/DECIMO_ESQ_V5_tech.ifc` (309 produits, 78 ajoutés)
- Tolérance géométrique : 1e-06 m ; ifcopenshell 0.9.0

## Produits de la V5 conservés

**231/231 produits V5 identiques dans la maquette technique (classe, attributs, psets, placement, sommets) ; 0 écart(s).**


## Lecture des sanitaires V4

- WC 0UsrJW3tn86Pjy_3YJTo9z lu (bbox [0.187, 6.715, 0.0] - [0.89, 7.085, 0.83]) ; sortie EV non décrite dans l'IFC (représentation mappée sans port) : hypothèse sortie horizontale arrière h 0,18, à relever
- Lave-mains lu : 2 élément(s) V4 (4350631, 4350630), plan à +0.75 ; bonde au centre de la vasque, siphon et robinetterie non modélisés en V4 (hypothèse)

## Règles techniques

| Règle | Mesure | OK |
|---|---|---|
| WC et lave-mains V4 du local 07 lus dans l'IFC | lus : ['LM', 'WC'] ; non lus documentés : 0 | oui |
| Aucun ajout ne pénètre le WC ou le lave-mains V4 (> 2 mm) | 0 pénétration(s) [] | oui |
| EU-LM : pente de chaque tronçon entre 1 et 3 % (DTU 60.11) | 2.00 %, 2.00 %, 2.00 % ; fil d'eau +0.560 > +0.497 | oui |
| EV-WC : pente de chaque tronçon entre 1 et 3 % (DTU 60.11) | 2.00 %, 2.00 % ; fil d'eau +0.125 > +0.117 | oui |
| Diamètres extérieurs : EV Ø 100 (110), EU Ø 40, AEP multicouche 16 / 20 | EV-WC 110 mm, EU-LM 40 mm, AEP-WC 16 mm, AEP-LM 16 mm, AEP-COL 20 mm | oui |
| EV et EU aboutissent sur la descente de l'immeuble (culottes) | EV-WC à -0 mm de la paroi, EU-LM à 4 mm de la paroi | oui |
| EV : départ sur la sortie supposée du WC (dos de la cuvette) | [0.322, 6.9, 0.18] / sortie [0.32, 6.9, 0.18] | oui |
| EU : départ à l'aplomb de la bonde du lave-mains | [2.72, 6.865, 0.58] / bonde (2.720, 6.865) | oui |
| Ventilation et visite : AAV sur le branchement EU, tampons et trappes | 1 AAV, 4 tampons / bouchons, 2 trappes | oui |
| Chemin CFA, suspentes et fourreau R6 dans le plénum (+3,04 à +3,30, sans toucher la dalle) | 6 éléments, 0 hors plénum [] | oui |
| Goulottes arrêtées sous le faux-plafond (descentes sans saignée) | 14 goulottes, 0 au-dessus de +3,00 | oui |
| Les 27 luminaires 2700 K de la V5 sont chacun sur un seul circuit d'éclairage | 27/27 ; défauts [] | oui |
| Circuits d'éclairage ≤ 8 points (BAES compris), 1,5 mm² / 16 A max | E1 8, E2 8, E3 3, E4 5, E5 6, E6 2 | oui |
| Circuits de prises ≤ 8 socles, 2,5 mm² / 20 A max | P1 4, P2 4, P3 7, P4 4, P5 2 | oui |
| Chaque différentiel 30 mA protège ≤ 8 circuits ; éclairage réparti sur ≥ 2 différentiels | ID1 : E1, E4, E6, P2, P4 ; ID2 : E2, E3, E5, P1, P3 ; ID3 : C1, C2, P5 | oui |
| Splits sur circuits spécialisés (1 split + sa mini-pompe par circuit) | C1 16 A 2.5 mm², C2 16 A 2.5 mm² | oui |
| BAES : un BAES à l'issue (< 1 m), tous en hauteur (> 2,0 m) et alimentés par un circuit d'éclairage | 5 BAES ; issue à 0.10 m ; bas : [] ; sans circuit : [] | oui |
| Courants faibles : RJ45 aux postes, réunion, accueil ; borne Wi-Fi au plafond | 6 prises RJ45 doubles (12 ports) ; 1 borne(s) à +2.96 | oui |
| Aucune ouverture IFC ajoutée (ni dans la V4, ni dans la V5) | 0 | oui |

**Résultat global : CONFORME**
