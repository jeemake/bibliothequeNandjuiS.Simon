import csv,openpyxl
H=['Lot','Code','Désignation','Type / référence produit','Zone','Base de calcul (IFC V4)','Quantité','Unité','Prix unitaire','Source prix']
R=[
('Revêtements','REV-01','Enduit chaux teinté sable #E6D6BF, finition talochée fine','Enduit chaux aérienne NHL/CL90, 2 couches, pigments minéraux','Murs intérieurs','Murs périph. 28,2 ml + cloisons 13,1 ml x 2 faces, h 3,30, moins baies',120,'m²'),
('Revêtements','REV-02','Enduit chaux blanc #FBF8F3 (plafonds)','Enduit chaux ou peinture minérale silicate mat','Plafonds RDC','Surface utile intérieure 43,0 m²',43,'m²'),
('Revêtements','REV-03','Enduit terre cuite #B4583E (niches cintrées, portail)','Enduit chaux pigmenté oxyde rouge, ciré','Mur du fond, portail','Doublage cintré 3,42 x 3,30 + portail 1,80 x 3,30',17,'m²'),
('Revêtements','REV-04','Enduit chaux sable façade sud','Enduit chaux hydraulique NHL 3,5 + badigeon','Façade','6,42 x 3,30 moins baies et portail',11,'m²'),
('Sols','SOL-01','Grès cérame teinte sable, mat, 60x60','Grès cérame pleine masse R10, rectifié','Intérieur','43,0 m² + 10 % chutes',47.3,'m²'),
('Sols','SOL-02','Grès cérame sable antidérapant extérieur','Grès cérame R11 ép. 20 mm sur plots ou collé','Terrasse','18,1 m² + 10 %',20,'m²'),
('Façade','FAC-01','Claustra terre cuite, motif losange','Bloc claustra terre cuite 20x20x10 (fabrication locale)','Baies A, B, C','1,20x2,10 + 0,70x1,50 + 1,10x1,90 = 5,66 m² + 10 %',155,'u'),
('Façade','FAC-02','Vitrage clair derrière claustra','Double vitrage 4/12/4 sur menuiserie alu noir mat','Baies A, B, C','IFC IfcWindow x3',5.7,'m²'),
('Façade','FAC-03','Porte d’entrée cintrée double 0,90 + 0,60','Menuiserie acier noir mat vitrée, imposte cintrée','Entrée','IfcDoor',1,'u'),
('Façade','FAC-04','Pergola bois paramétrique, lames ondulées','Iroko massif huilé, lames 40x120, poteaux acier 80x80','Terrasse','Emprise 6,70 x 2,65',17.8,'m²'),
('Façade','FAC-05','Jardinières maçonnées','Agglo enduit chaux sable, étanchéité intérieure','Terrasse','2,60 ml + 1,40 ml',4,'ml'),
('Menuiserie','MEN-01','Rayonnage bibliothèque 800','Iroko huilé sur mesure, 0,33 x 0,80 x 2,25','Salle de lecture','IFC DECIMO_B01 x5',5,'u'),
('Menuiserie','MEN-02','Arbre à livres Ø 0,90, canopée Ø 2,60','Fût iroko lamellé-collé, tablettes circulaires, canopée terre cuite (coque enduite)','Fond de salle','IFC DECIMO_L01',1,'u'),
('Menuiserie','MEN-03','Niches cintrées bibliothèque','Iroko + doublage cintré enduit terre cuite','Mur du fond','IFC DECIMO_N01 x2',2,'u'),
('Menuiserie','MEN-04','Niche banquette lames bois','Iroko, assise tapissée laine terre cuite','Mur du fond','IFC DECIMO_N02',1,'u'),
('Menuiserie','MEN-05','Comptoir d’accueil','Iroko + plateau acier noir mat, 1,83 m','Accueil','IFC DECIMO_C02',1,'u'),
('Menuiserie','MEN-06','Console vinyles P40','Iroko huilé, 2,15 m','Salon de lecture','IFC DECIMO_M01',1,'u'),
('Mobilier','MOB-01','Chaise courbe','Chaise bois courbé iroko ou frêne teinté, assise tissée raphia (artisanat local)','Salles','IFC DECIMO_C01 x8',8,'u'),
('Mobilier','MOB-02','Table ronde Ø 65','Plateau iroko, piètement acier noir','Lecture / terrasse','IFC DECIMO_T02 x4',4,'u'),
('Mobilier','MOB-03','Table de réunion 130','Iroko massif','Salle de réunion','IFC DECIMO_T01',1,'u'),
('Mobilier','MOB-04','Fauteuil de lecture','Fauteuil bas tapissé laine terre cuite, coussin indigo','Coin lecture','IFC DECIMO_A01 x2',2,'u'),
('Mobilier','MOB-05','Banquette 140','Tapissée laine terre cuite','Salon','IFC DECIMO_B02',1,'u'),
('Mobilier','MOB-06','Pouf','Pouf tressé raphia ou cuir naturel','Coin lecture','IFC DECIMO_P01',1,'u'),
('Mobilier','MOB-07','Tableau mural 1,80 x 1,20','Panneau liège ou ardoise sur cadre iroko','Salle de réunion','IFC DECIMO_TB01',1,'u'),
('Mobilier','MOB-08','Mobilier terrasse (4 tables, 8 chaises)','Bois exotique huilé ou acier thermolaqué, usage extérieur','Terrasse','Plan V4 terrasse',12,'u'),
('Textiles','TEX-01','Tissu laine terre cuite (assises)','Tissu d’ameublement laine, classement feu M1','Assises','Banquette + niche + 2 fauteuils, estimation',12,'ml'),
('Textiles','TEX-02','Coussins coton indigo teint à la main','Pagne indigo / bogolan, artisanat ivoirien ou malien','Assises','Estimation',10,'u'),
('Luminaires','LUM-01','Rail lumineux noir mat','Rail 3 allumages ou 48 V, 3,80 m','Salle de lecture','IFC Rail lumineux x2',2,'u'),
('Luminaires','LUM-02','Spots orientables sur rail','LED 2700 K, IRC > 90, UGR < 19, ~10 W','Salle de lecture','6 par rail (proposition)',12,'u'),
('Luminaires','LUM-03','Anneau LED intégré sous canopée','Ruban LED 2700 K diffusant, profilé courbe','Arbre à livres','Proposition D.A',1,'u'),
('Luminaires','LUM-04','Suspensions papier / raphia','Suspension diffusante Ø 40-50, 2700 K','Salle de réunion','Au-dessus table 130',2,'u'),
('Luminaires','LUM-05','Appliques de niche','Applique linéaire LED encastrée, 2700 K','Niches cintrées','3 niches',3,'u'),
('Luminaires','LUM-06','Lampes de lecture à poser','Lampe à poser LED, abat-jour tissu','Tables / fauteuils','Proposition',4,'u'),
('Luminaires','LUM-07','Appliques extérieures IP65','Applique terre cuite ou acier noir, IP65, 2700 K','Terrasse / façade','Proposition',4,'u'),
('Luminaires','LUM-08','Rétroéclairage enseigne','LED IP65 derrière lettres découpées (enseigne IFC 0,96 x 0,24)','Façade','IFC Enseigne',1,'u'),
('Végétal','VEG-01','Ficus lyrata en pot terre cuite','H 1,60, pot terre cuite Ø 50','Salon','IFC DECIMO_V01',1,'u'),
('Végétal','VEG-02','Strelitzia nicolai / reginae','Sujet 1,2 à 1,5 m','Jardinières','2,60 + 1,40 ml, 1 sujet / 0,6 ml',7,'u'),
('Végétal','VEG-03','Fougère Nephrolepis + Dracaena','Couvre-sol / sous-étage','Jardinières','Estimation',10,'u'),
('Végétal','VEG-04','Bougainvillier sur poteau de pergola','Grimpante, tuteurage câble inox','Terrasse','Poteaux de pergola x2',2,'u'),
]
with open('liste_chiffrable_decimo.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f,delimiter=';');w.writerow(H);[w.writerow(list(r)+['','']) for r in R]
wb=openpyxl.Workbook();ws=wb.active;ws.title='Liste D.A';ws.append(H);[ws.append(list(r)+['','']) for r in R]
from openpyxl.styles import Font,PatternFill
for c in ws[1]: c.font=Font(bold=True,color='FBF8F3');c.fill=PatternFill('solid',fgColor='2B2420')
for col,wd in zip('ABCDEFGHIJ',[12,9,44,52,20,46,10,7,12,14]): ws.column_dimensions[col].width=wd
wb.save('liste_chiffrable_decimo.xlsx');print(len(R))
