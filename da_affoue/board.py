from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor as C
from reportlab.lib.utils import ImageReader
for n,p in [('Serif','DMSerifDisplay-Regular'),('SerifI','DMSerifDisplay-Italic'),('Jost','Jost-400'),('JostM','Jost-500')]: pdfmetrics.registerFont(TTFont(n,f'fonts/{p}.ttf'))
W,H=420*mm,297*mm; M=15*mm; COLS=12; G=5*mm; CW=(W-2*M-11*G)/12
def col(i): return M+i*(CW+G)
def span(n): return n*CW+(n-1)*G
ENC,TAU,TC,IRO,SAB,SC,CH,OL,IND='#2B2420','#7D7168','#B4583E','#9A6B43','#E6D6BF','#F4EDE2','#FBF8F3','#5F7A4B','#2F3A56'
c=canvas.Canvas('Decimo_DA_Affoue_A3_light_v5.pdf',pagesize=(W,H)); c.setTitle('Bibliothèque Decimo, D.A Affoué, K&Démi')
def T(x,y,s,f='Jost',sz=9,col=ENC):
    c.setFont(f,sz);c.setFillColor(C(col));c.drawString(x,y,s)
import io,os
from PIL import Image as PI
def jpg(p,w,h):
    im=PI.open(p); alpha=im.mode in('RGBA','LA','P') and p.startswith('logo')
    tw,th=w/72*200,h/72*200; r=min(1,max(tw/im.width,th/im.height))
    im=im.resize((max(1,int(im.width*r)),max(1,int(im.height*r))),PI.LANCZOS)
    if alpha: return p if r==1 else im.convert('RGBA')
    b=io.BytesIO(); im.convert('RGB').save(b,'JPEG',quality=80); b.seek(0); return b
def img(p,x,y,w,h,fit=True):
    ir=ImageReader(jpg(p,w,h));iw,ih=ir.getSize()
    if fit:
        r=min(w/iw,h/ih);dw,dh=iw*r,ih*r;c.drawImage(ir,x+(w-dw)/2,y+(h-dh)/2,dw,dh,mask='auto')
    else:  # cover crop
        r=max(w/iw,h/ih);c.saveState();p_=c.beginPath();p_.rect(x,y,w,h);c.clipPath(p_,stroke=0,fill=0);c.drawImage(ir,x+(w-iw*r)/2,y+(h-ih*r)/2,iw*r,ih*r);c.restoreState()
def frame(title,sub,num):
    c.setFillColor(C(CH));c.rect(0,0,W,H,fill=1,stroke=0)
    img('logo_v3_tr/KDemi_v3_A_arche_lockup.png',M-3*mm,H-M-15*mm,44*mm,15*mm)
    img('logo_v3_tr/KDemi_v3_A_arche_lockup.png',W/2-12.5*mm,M-2.5*mm,25*mm,8.5*mm)
    T(col(4),H-M-6*mm,title,'Serif',22); T(col(4),H-M-12*mm,sub,'Jost',9,TAU)
    c.setStrokeColor(C(TC));c.setLineWidth(1.2);c.line(M,H-M-17*mm,W-M,H-M-17*mm)
    c.setStrokeColor(C(SAB));c.setLineWidth(0.5);c.line(M,M+8*mm,W-M,M+8*mm)
    T(M,M,'K&Démi  ·  Bibliothèque Decimo  ·  D.A  ·  Octobre 2026','Jost',7.5,TAU); T(W-M-20*mm,M,f'Planche {num} / 3','JostM',7.5,TC)
def sw(x,y,w,h,hexc,name,use):
    c.setFillColor(C(hexc));c.setStrokeColor(C(SAB));c.rect(x,y,w,h,fill=1,stroke=1)
    T(x,y-4.5*mm,name,'JostM',8); T(x,y-8.5*mm,hexc+'  ·  '+use,'Jost',7,TAU)
# ---------- P1 charte agence
frame('Identité K&Démi','Logo revu, palette, typographies, grille',1)
top=H-M-24*mm
T(M,top,'LOGO K&DÉMI v3 · L’ARCHE DANS LE CARRÉ, MOT-SYMBOLE MANROPE','JostM',8,TC)
c.setStrokeColor(C(SAB));c.setLineWidth(0.6);c.rect(M,top-70*mm,span(7),64*mm,fill=0,stroke=1)
img('logo_v3_tr/KDemi_v3_A_arche_lockup.png',M+10*mm,top-66*mm,span(7)-20*mm,56*mm)
T(M,top-75*mm,'Version principale : encre sur blanc chaux, & terre cuite. Fichiers SVG et PNG transparents.','Jost',7.5,TAU)
vy=top-82*mm; w3=(span(7)-2*4*mm)/3
for i,(f,lab) in enumerate([('lockup_inverse','Inversée, fond encre'),('lockup_mono','Une couleur (encre)'),(None,'Icône d’app et favicons 32 / 16 px')]):
    x=M+i*(w3+4*mm)
    if f: img('logo_v3_tr/KDemi_v3_A_arche_'+f+'.png',x,vy-24*mm,w3,24*mm)
    else:
        img('logo_v3_tr/KDemi_v3_A_arche_appicon.png',x+2*mm,vy-24*mm,24*mm,24*mm); img('logo_v3_tr/KDemi_v3_A_arche_favicon32.png',x+30*mm,vy-14*mm,11.3*mm,11.3*mm); img('logo_v3_tr/KDemi_v3_A_arche_favicon16.png',x+44*mm,vy-10*mm,5.6*mm,5.6*mm)
    T(x,vy-28*mm,lab,'Jost',7.5,TAU)
my=vy-38*mm; T(M,my,'TAILLE MINIMALE','JostM',8,TC)
img('logo_v3_tr/KDemi_v3_A_arche_lockup.png',M-1*mm,my-11*mm,30*mm,10.2*mm); T(M,my-15*mm,'Logo complet : 30 mm en impression, 120 px à l’écran.','Jost',7.5)
img('logo_v3_tr/KDemi_v3_A_arche_lockup.png',M+80*mm,my-10*mm,25*mm,8.5*mm); T(M+80*mm,my-15*mm,'25 mm : pied de page seulement, jamais moins.','Jost',7.5,TAU)
T(M,my-24*mm,'RÈGLE D’USAGE','JostM',8,TC)
T(M,my-29*mm,'Le nom K&Démi est toujours posé à côté du symbole. Le symbole seul est réservé à l’icône d’app et au favicon.','Jost',7.5)
T(M,my-33.5*mm,'Zone de protection : la moitié de la hauteur du carré tout autour. Pas de déformation, pas d’ombre, pas de dégradé.','Jost',7.5,TAU)
T(col(8),top,'PALETTE AGENCE','JostM',8,TC)
P=[(ENC,'Encre','texte, traits'),(TC,'Terre cuite','signature'),(IRO,'Iroko','bois, repères'),(SAB,'Sable','aplats'),(SC,'Sable clair','fonds'),(CH,'Blanc chaux','page'),(TAU,'Taupe','texte 2'),(OL,'Olive','végétal, rare')]
for i,(h,n,u) in enumerate(P):
    sw(col(8)+(i%4)*(span(4)/4),top-24*mm-(i//4)*36*mm,span(4)/4-3*mm,20*mm,h,n,u)
ty=top-92*mm; T(col(8),ty,'TYPOGRAPHIES (LIBRES, GOOGLE FONTS, OFL)','JostM',8,TC)
T(col(8),ty-12*mm,'DM Serif Display','Serif',24); T(col(8),ty-17*mm,'Titres, logo, chiffres clés  ·  corps 18 à 36 pt','Jost',7.5,TAU)
T(col(8),ty-28*mm,'Jost Regular / Medium','Jost',16); T(col(8),ty-33*mm,'Texte 8 à 10 pt, légendes 7 pt, capitales espacées +12 %','Jost',7.5,TAU)
gy=M+14*mm; T(col(8),gy+44*mm,'GRILLE A3 PAYSAGE','JostM',8,TC)
for i in range(12):
    c.setFillColor(C(SC));c.rect(col(8)+i*(span(4)/12),gy+6*mm,span(4)/12-1*mm,32*mm,fill=1,stroke=0)
T(col(8),gy,'12 colonnes · marges 15 mm · gouttière 5 mm · bandeau titre 17 mm · pied 6 mm','Jost',7.5,TAU)
c.showPage()
# ---------- P2 page type
frame('Bibliothèque Decimo','Page type du dossier : plan du rez-de-chaussée, esquisse V4, échelle 1/50',2)
img('base/plan_page_v3logo.png',M,M+10*mm,span(8),H-2*M-38*mm)
x=col(8);y=H-M-30*mm
T(x,y,'PRINCIPES','JostM',8,TC)
L=['Un seul seuil cintré, centré sur la rue, cadre l’arbre à livres.','Trois baies en claustra terre cuite filtrent le soleil de l’après-midi.','La canopée terre cuite de l’arbre est le seul objet fort de la salle.','Bois iroko pour tout ce qui se touche, chaux pour tout ce qui se voit.','Ventilation traversante : claustra + pergola, pas de baie fermée au sud.']
for i,l in enumerate(L):
    c.setFillColor(C(TC));c.circle(x+2*mm,y-10*mm-i*9*mm+1*mm,2.2*mm,fill=1,stroke=0); T(x+1.1*mm,y-10*mm-i*9*mm,str(i+1),'JostM',7,CH); T(x+7*mm,y-10*mm-i*9*mm,l,'Jost',8)
y2=y-62*mm;T(x,y2,'SURFACES (IFC V4)','JostM',8,TC)
S=[('Salle de lecture','24,2 m²'),('Salle de réunion','7,3 m²'),('Coin lecture','6,7 m²'),('WC','3,0 m²'),('Rangement','1,8 m²'),('Terrasse couverte','18,1 m²')]
for i,(a,b) in enumerate(S):
    yy=y2-8*mm-i*6.5*mm
    if i%2==0: c.setFillColor(C(SC));c.rect(x,yy-2*mm,span(4),6.5*mm,fill=1,stroke=0)
    T(x+2*mm,yy,a,'Jost',8); T(x+span(4)-20*mm,yy,b,'JostM',8)
c.setFillColor(C(SAB));c.rect(x,M+10*mm,span(4),28*mm,fill=1,stroke=0)
for i,(a,b) in enumerate([('Projet','Bibliothèque Decimo, Abidjan'),('Phase','Esquisse V4'),('Échelle','1/50 en A3'),('Date','Octobre 2026'),('Agence','K&Démi, architecture · intérieur')]):
    T(x+3*mm,M+32*mm-i*4.8*mm,a.upper(),'JostM',6.5,TAU); T(x+24*mm,M+32*mm-i*4.8*mm,b,'Jost',8)
c.showPage()
# ---------- P3 DA bibliothèque
frame('D.A de la bibliothèque','Terre, ombre et bois : une salle de lecture fraîche sous le soleil d’Abidjan',3)
top=H-M-21*mm; h1=118*mm
img('visuels/devanture_v2.png',M,top-h1,span(6),h1,fit=False); img('visuels/int_rdc.png',col(6),top-h1,span(6),h1,fit=False)
T(M+2*mm,top-h1-4*mm,'Devanture : local en pied d’immeuble, portail terre cuite, vitrine, claustra','Jost',7,TAU)
T(col(6)+2*mm,top-h1-4*mm,'RDC : vue depuis l’entrée vers l’arbre à livres','Jost',7,TAU)
h2=88*mm; y2=top-h1-9*mm-h2
img('visuels/mood.png',M,y2,span(4),h2,fit=False); T(M+2*mm,y2-4*mm,'Maquette matière sur le plan V4','Jost',7,TAU)
img('base/plan.png',col(4),y2,span(3),h2); T(col(4)+2*mm,y2-4*mm,'Plan RDC issu de l’IFC V4 (local commercial, logements au-dessus)','Jost',7,TAU)
x=col(7); T(x,y2+h2-3*mm,'MATÉRIAUX','JostM',8,TC)
TX=[('claustra_terre_cuite','Claustra terre cuite'),('iroko_huile','Iroko huilé'),('enduit_chaux_sable','Chaux sable'),('enduit_terre_cuite','Enduit terre cuite'),('gres_cerame_sable','Grès cérame sable'),('acier_noir_mat','Acier noir mat'),('tissu_terre_cuite','Laine terre cuite')]
for i,(t,n) in enumerate(TX):
    xx=x+(i%4)*(span(2)/2+0*mm)*1.0; 
    xx=x+(i%4)*15*mm; yy=y2+h2-23*mm-(i//4)*26*mm
    img(f'repo/textures/{t}.png',xx,yy,13*mm,13*mm,fit=False); T(xx,yy-3.5*mm,n,'Jost',5.6,ENC)
c.setFillColor(C(IND));c.rect(x+45*mm,y2+h2-49*mm,13*mm,13*mm,fill=1,stroke=0);T(x+45*mm,y2+h2-52.5*mm,'Indigo #2F3A56','Jost',5.6)
P=[(TC,'#B4583E'),(IRO,'#9A6B43'),(SAB,'#E6D6BF'),(CH,'#FBF8F3'),(ENC,'#2B2420'),(IND,'#2F3A56'),(OL,'#5F7A4B')]
T(x,y2+28*mm,'PALETTE INTÉRIEURE','JostM',8,TC)
for i,(h,n) in enumerate(P):
    c.setFillColor(C(h));c.setStrokeColor(C(SAB));c.rect(x+i*8.6*mm,y2+12*mm,8*mm,12*mm,fill=1,stroke=1);c.saveState();c.translate(x+i*8.6*mm+1*mm,y2+2*mm);T(0,0,n,'Jost',5,TAU);c.restoreState()
x=col(10)+3*mm;yy=y2+h2-3*mm
for head,items in [('AMBIANCE',['Pénombre fraîche, lumière tamisée','par la claustra, 2700 K le soir','Aucun dégradé, aucun motif plaqué']),('MOBILIER',['Iroko sur mesure, chaises courbes','assises raphia, laine terre cuite','coussins indigo artisanaux']),('LUMINAIRES',['Rails noirs + spots IRC 90','anneau LED sous canopée','suspensions papier, appliques IP65']),('VÉGÉTAL',['Ficus lyrata, Strelitzia','fougères, Dracaena','bougainvillier sur pergola'])]:
    T(x,yy,head,'JostM',8,TC); 
    for j,it in enumerate(items): T(x,yy-5*mm-j*4.2*mm,it,'Jost',7.2)
    yy-=22*mm
c.showPage();c.save()
