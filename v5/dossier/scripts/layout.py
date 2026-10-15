# -*- coding: utf-8 -*-
"""Dossier Bibliothèque Decimo : modèle de pages unique -> PDF (reportlab) + PPTX A3 (python-pptx)."""
import os, json
from PIL import Image
B = "/workspace/decimo_final"
OUT = B + "/build"
IMG = OUT + "/img"
W, H = 420.0, 297.0
PX = 255.0           # début du panneau (identique aux planches A01-A11)
TX = 263.0; TW = 147.0
X0, Y0, CW, CH = 14.0, 14.0, 227.0, 269.0
G = 5.0
ENCRE="#4A4A4A"; TAUPE="#8C8C8C"; TERRE="#B4583E"; IROKO="#9A6B43"; SABLE="#E6D6BF"; SABLE_CL="#FFFFFF"; CHAUX="#FFFFFF"; OLIVE="#5F7A4B"; INDIGO="#2F3A56"; FILET="#C8C8C8"; GRIS_CL="#F4F4F4"
# charte v2 (15/10/2026) : papier blanc, texte gris, Archivo seule famille, terre cuite en accent
LOGO = B + "/KDemi_v3_A_arche_lockup_mono.png"; LOGO_INV = B + "/KDemi_v3_A_arche_lockup_inverse_gris.png"; LOGO_COL = B + "/KDemi_v3_A_arche_lockup.png"
R = B + "/rendus/"; V = B + "/repo/v5/vues_rendu/"; DES = B + "/repo/v5/dessins/"
TECH = json.load(open(OUT + "/tech.json")) if os.path.exists(OUT + "/tech.json") else {}

def crop(src, w, h, name, focus=(0.5, 0.5), dpi=220):
    """Recadrage 'cover' au ratio de la boîte, export JPEG."""
    im = Image.open(src).convert("RGB"); iw, ih = im.size; r = w / h
    if iw / ih > r:
        nw = int(ih * r); x = int((iw - nw) * focus[0]); im = im.crop((x, 0, x + nw, ih))
    else:
        nh = int(iw / r); y = int((ih - nh) * focus[1]); im = im.crop((0, y, iw, y + nh))
    tw = int(w / 25.4 * dpi)
    if im.size[0] > tw: im = im.resize((tw, int(tw / r)), Image.LANCZOS)
    p = f"{IMG}/{name}.jpg"; im.save(p, quality=86, optimize=True); return p

# éléments : ("rect",x,y,w,h,fill) ("img",path,x,y,w,h) ("text",x,y,w,txt,style) ("line",x1,y1,x2,y2,color,pt) ("pdf",path,png)
ST = {
 "h_cover": dict(font="serif", size=44, color=ENCRE, lead=46),
 "title": dict(font="serif", size=23, color=ENCRE, lead=26),
 "sub": dict(font="jost5", size=10.5, color=ENCRE, lead=14),
 "meta": dict(font="jost4", size=7.2, color=TAUPE, lead=9),
 "head": dict(font="jost5", size=7.4, color=TERRE, lead=10, caps=True),
 "body": dict(font="jost4", size=8.4, color=ENCRE, lead=12),
 "body_l": dict(font="jost3", size=9.5, color=ENCRE, lead=13.5),
 "small": dict(font="jost4", size=7.2, color=ENCRE, lead=9.6),
 "cap": dict(font="jost4", size=6.8, color=TAUPE, lead=8.6),
 "lab": dict(font="jost5", size=6.2, color=TAUPE, lead=8, caps=True),
 "val": dict(font="jost4", size=6.8, color=ENCRE, lead=8),
 "kpi": dict(font="serif", size=24, color=ENCRE, lead=27),
 "col_h": dict(font="serif", size=13, color=ENCRE, lead=16),
 "foot": dict(font="manrope5", size=6.5, color=ENCRE, lead=8),
 "foot_r": dict(font="jost4", size=6.5, color=TAUPE, lead=8, align="right"),
}
def S(name, **kw):
    d = dict(ST[name]); d.update(kw); return d

def panel(els, code, title, sub, meta, sections, planche, echelle="sans échelle", dark=False):
    els.append(("line", PX, 8, PX, H - 8, FILET, 0.4))
    els.append(("img", LOGO_INV if dark else LOGO, TX, 12, 46, 46 * 814 / 2400))
    els.append(("text", TX, 40, TW, title, S("title")))
    els.append(("text", TX, 52.5, TW, sub, S("sub")))
    if meta: els.append(("text", TX, 59.5, TW, meta, S("meta")))
    els.append(("line", TX, 64, TX + 18, 64, TERRE, 0.9)); els.append(("line", TX + 18, 64, TX + TW, 64, FILET, 0.4))
    y = 70.0
    for head, body, kind in sections:
        els.append(("text", TX, y, TW, head, S("head"))); y += 5.2
        if kind == "rows":     # tableau 2 colonnes
            for a, b in body:
                els.append(("text", TX, y, TW - 30, a, S("small"))); els.append(("text", TX + TW - 30, y, 30, b, S("small", align="right"))); y += 4.3
            y += 3.5
        elif kind == "list":
            for i, t in enumerate(body):
                els.append(("text", TX, y, 6, f"{i+1:02d}", S("small", color=TERRE)))
                hgt = els_text_height(t, S("small"), TW - 7)
                els.append(("text", TX + 7, y, TW - 7, t, S("small"))); y += hgt + 1.2
            y += 3.0
        else:
            hgt = els_text_height(body, S("body"), TW)
            els.append(("text", TX, y, TW, body, S("body"))); y += hgt + 4.5
    # cartouche
    els.append(("line", TX, 246, TX + TW, 246, FILET, 0.3))
    rows = [("Projet", "Bibliothèque Decimo · RDC sous logements, Deux Plateaux, Abidjan"), ("Phase", "ESQ V5 · aménagement sur existant V4"),
            ("Planche", planche), ("Échelle", echelle + " · format A3 paysage"), ("Maquette", "v5/DECIMO_ESQ_V5.ifc (IFC4)"), ("Date", "15 octobre 2026 · indice C")]
    yy = 249.5
    for a, b in rows:
        els.append(("text", TX, yy, 22, a, S("lab"))); els.append(("text", TX + 22, yy, TW - 22, b, S("val"))); yy += 4.6
    els.append(("text", TX, 289, 40, "K&Démi", S("foot", color=CHAUX if dark else ENCRE)))
    els.append(("text", TX + TW - 60, 289, 60, f"{code} · ESQ V5 · Octobre 2026", S("foot_r")))

_measure = None

# ---------------- planches techniques (Ahoua, T01-T05) : planche réelle si présente, sinon réserve propre
TDIR = B + "/repo/v5/technique/"
TPAGES = [
 ("T01", "Électricité, courants forts", "A02_plan_faux_plafond_reseaux",
  ["Prises 2P+T 16 A : banque d'accueil, tables de lecture, salle de réunion, ménage", "Circuits dédiés : 2 splits 9 000 BTU/h, mini-pompes de relevage des condensats", "Cheminements sous faux-plafond, descentes en goulotte iroko", "Tableau divisionnaire raccordé à l'arrivée de l'immeuble"],
  [("Tableau divisionnaire", "1 · 1,00 m dégagé"), ("Splits muraux 9 000 BTU/h", "2"), ("TGBT, groupe électrogène", "aucun, côté immeuble"), ("Distance tableau / WC", "5,92 m")]),
 ("T02", "Courants faibles, éclairage et BAES", "A02_plan_faux_plafond_reseaux",
  ["RJ45 cat. 6 : accueil, tables de travail, salle de réunion, point d'accès Wi-Fi en plafond", "Baie de brassage murale dans le placard technique", "Éclairage 2700 K : downlights, suspensions terre cuite, anneau LED de l'oculus, réglette de vitrine", "Commandes par zone et détection au WC"],
  [("Luminaires IfcLightFixture", "27"), ("Température de couleur", "2700 K"), ("Placard technique net", "0,60 × 0,40 m"), ("Plénum sous dalle", "0,26 m")]),
 ("T03", "AEP, EU, EV", "A01_plan_RDC",
  ["Alimentation eau froide depuis l'attente de l'immeuble, vanne d'arrêt et compteur divisionnaire", "WC 4350629 et lave-mains 4350630/4350631 de la V4 conservés", "EU/EV vers les descentes existantes en coffrage 0,30 × 0,30", "Condensats des splits relevés par mini-pompes vers EU"],
  [("Appareils sanitaires", "WC + lave-mains (V4)"), ("Coffrages EU/EV", "2 · à relever sur site"), ("Réservations Ø 0,10", "5 · hors structure"), ("Pénétration dans la structure", "0")]),
 ("T04", "Détails techniques", "A03_coupe_AA",
  ["Fixation non traversante de l'arbre à livres et de l'oculus sous dalle", "Faux-plafond acoustique +3,00 et trappes de visite des splits", "Châssis acier noir dans les baies cintrées V4, inserts claustra Adinkra", "Passage des liaisons frigorifiques par la baie arrière existante"],
  [("Faux-plafond", "+3,00 / +3,04"), ("Sous-face de dalle (hypothèse)", "+3,30"), ("Liaisons frigorifiques", "2 faisceaux"), ("Intersections structure", "0")]),
 ("T05", "Schéma unifilaire et bilan de puissance", "A02_plan_faux_plafond_reseaux",
  ["Schéma unifilaire du tableau divisionnaire : interrupteurs différentiels 30 mA, départs par usage", "Bilan de puissance : éclairage, prises, climatisation, informatique", "Puissance à demander au syndic et section du câble d'alimentation", "Note technique et contrôle V4/V5 à 0 écart"],
  [("Départs clim dédiés", "2"), ("Protection des personnes", "DDR 30 mA"), ("Puissance souscrite", "à confirmer"), ("Écart V4/V5", "0")]),
]

def ghost(code):
    p = f"{IMG}/ghost_{code}.jpg"
    if not os.path.exists(p):
        im = Image.open(DES + code + ".png").convert("RGB"); w, h = im.size
        im = im.crop((0, 0, int(w * PX / W), h))
        im = Image.blend(im, Image.new("RGB", im.size, SABLE_CL), 0.86)
        tw = 1600; im = im.resize((tw, int(tw * im.size[1] / im.size[0])), Image.LANCZOS); im.save(p, quality=80)
    return p

def tech_page(i, code, nom, base, contenu, donnees):
    n = f"{16+i:02d}"
    real = [f for f in (os.listdir(TDIR) if os.path.isdir(TDIR) else []) if f.startswith(code) and f.endswith(".pdf")]
    if real:
        f = TDIR + real[0]; png = f[:-4] + ".png"
        return ("pdf", f, png if os.path.exists(png) else None, code)
    e = []
    e.append(("img", ghost(base), 0, 0, PX, H))
    bx, bw = X0 + 30, CW - 60
    ch = sum(_measure(t, S("small", size=7.8, lead=10), bw - 27) + 2 for t in contenu)
    bh = 60 + ch + 8; by = (H - bh) / 2 - 6
    e.append(("rect", bx, by, bw, bh, CHAUX))
    for a in [(bx, by, bx + bw, by), (bx, by + bh, bx + bw, by + bh), (bx, by, bx, by + bh), (bx + bw, by, bx + bw, by + bh)]: e.append(("line",) + a + (TERRE, 0.5))
    e.append(("text", bx + 10, by + 10, bw - 20, f"PLANCHE {code} · EN COURS", S("lab", color=TERRE, size=7)))
    e.append(("text", bx + 10, by + 17, bw - 20, nom, S("title", size=24)))
    e.append(("text", bx + 10, by + 31, bw - 20, "Planche d'Ahoua, ingénieur bâtiment, tirée de la maquette IFC V5. Elle prend cette page dès la fusion de la branche des lots techniques.", S("body_l", size=9, lead=12.5)))
    e.append(("line", bx + 10, by + 50, bx + bw - 10, by + 50, TAUPE, 0.3))
    e.append(("text", bx + 10, by + 54, bw - 20, "Contenu prévu", S("head")))
    y = by + 60
    for j, t in enumerate(contenu):
        e.append(("text", bx + 10, y, 6, f"{j+1:02d}", S("small", color=TERRE)))
        e.append(("text", bx + 17, y, bw - 27, t, S("small", size=7.8, lead=10)))
        y += _measure(t, S("small", size=7.8, lead=10), bw - 27) + 2
    caption(e, X0, 270, CW, f"En fond : planche {base[:3]} de la maquette V5, à titre de repère")
    panel(e, n, nom, "Proposition technique", f"{code} · Ahoua, ingénieur bâtiment",
          [("Déjà fixé dans la maquette V5", donnees, "rows"),
           ("Cadre", "Local commercial unique en RDC sous logements. L'immeuble porte le TGBT, le groupe et les colonnes : le projet part de ses attentes. Rien ne traverse la structure existante.", "p")],
          f"{n} · {code} {nom}")
    return ("page", e, code)
def els_text_height(txt, st, w):
    return _measure(txt, st, w)

def caption(els, x, y, w, t):
    els.append(("text", x, y, w, t, S("cap")))

def pages():
    P = []
    # ---------------- 01 couverture
    e = []
    e.append(("img", crop(R + "04_arbre.png", CW + X0 - 4, H - 2 * Y0, "cover", focus=(0.52, 0.5)), X0, Y0, CW, H - 2 * Y0))
    e.append(("line", PX, 8, PX, H - 8, FILET, 0.4))
    e.append(("img", LOGO, TX, 14, 52, 52 * 814 / 2400))
    e.append(("text", TX, 104, TW, "Bibliothèque\nDecimo", S("h_cover")))
    e.append(("line", TX, 144, TX + 18, 144, TERRE, 1.0))
    e.append(("text", TX, 150, TW, "Esquisse V5 · aménagement intérieur et devanture", S("sub", size=11.5, lead=15)))
    e.append(("text", TX, 160, TW, "Local en rez-de-chaussée sous logements\nDeux Plateaux, Abidjan", S("body_l", color=TAUPE, size=10, lead=14)))
    e.append(("line", TX, 242, TX + TW, 242, FILET, 0.3))
    e.append(("text", TX, 246, TW, "DOSSIER DE PRÉSENTATION", S("lab", size=6.8)))
    e.append(("text", TX, 251, TW, "D.A · plans · coupe · élévations · vues 3D · axonométries · électricité · plomberie · détails techniques", S("small")))
    e.append(("text", TX, 263, TW, "15 octobre 2026 · indice C", S("small")))
    e.append(("text", TX, 274, TW, "En couverture : l'arbre à livres sous l'oculus indigo, rendu tiré de la vue 04 de la maquette IFC V5", S("cap")))
    e.append(("text", TX, 289, 60, "K&Démi · architecture · intérieur", S("foot")))
    e.append(("text", TX + TW - 60, 289, 60, "01", S("foot_r")))
    P.append(("page", e, "Couverture"))
    # ---------------- 02 le projet
    e = []
    e.append(("img", crop(R + "01_devanture.png", CW, 150, "p02_dev", focus=(0.5, 0.55)), X0, Y0, CW, 150))
    caption(e, X0, 166, CW, "La devanture sous la pergola conservée de la V4, rendu tiré de la vue 01 de la maquette")
    cw3 = (CW - 2 * G) / 3
    cols = [("Le lieu", "Un local commercial de 6,78 × 7,68 m au rez-de-chaussée d'un immeuble de logements, à Deux Plateaux. Poteaux, voiles et dalle haute appartiennent à l'immeuble et restent intacts : le projet est un aménagement, pas une construction."),
            ("Le programme", "Une bibliothèque de quartier : une salle de lecture autour de l'arbre à livres, un coin lecture en vitrine, une salle de réunion, un seul WC, un rangement et un placard technique. La terrasse couverte prolonge la lecture sur la rue."),
            ("Le parti", "Terre, ombre et bois. La claustra en terre cuite filtre le soleil, l'iroko habille tout ce qui se touche et la chaux tout ce qui se voit. L'arbre à livres et son oculus indigo sont le seul objet fort de la salle.")]
    for i, (h, t) in enumerate(cols):
        x = X0 + i * (cw3 + G)
        e.append(("line", x, 176, x + cw3, 176, FILET, 0.4))
        e.append(("text", x, 180, cw3, h, S("col_h")))
        e.append(("text", x, 188, cw3, t, S("body_l", size=9, lead=13)))
    cw4 = (CW - 3 * G) / 4
    kp = [("43,55 m²", "surface intérieure, 7 espaces"), ("15,74 m²", "terrasse couverte sous pergola"), ("3,00 m", "hauteur sous faux-plafond"), ("141 / 141", "éléments existants V4 conservés à l'identique")]
    for i, (k, l) in enumerate(kp):
        x = X0 + i * (cw4 + G)
        e.append(("line", x, 244, x + cw4, 244, FILET, 0.3))
        e.append(("text", x, 248, cw4, k, S("kpi")))
        e.append(("text", x, 260, cw4, l, S("cap", size=7.4, lead=9.4)))
    som = [("Couverture", "01"), ("Le projet", "02"), ("Identité K&Démi", "03"), ("D.A de la bibliothèque", "04"),
           ("A01 Plan du RDC, aménagement", "05"), ("A02 Faux-plafond et réseaux", "06"), ("A03 Coupe AA", "07"), ("A04 Élévation de la devanture", "08"),
           ("A05 Élévations intérieures Est, Nord", "09"), ("A06 Élévations intérieures Sud, Ouest", "10"), ("A07 Vues 3D de la maquette", "11"), ("A08 Axonométries", "12"),
           ("R1 Rendu de la devanture", "13"), ("R2 Rendus intérieurs", "14"), ("R3 L'arbre à livres", "15")]
    som += [(f"{c} {t}", f"{16+i:02d}") for i, (c, t, *_r) in enumerate(TPAGES)]
    som += [("Cohérence et points ouverts", f"{16+len(TPAGES):02d}")]
    esp = [("01 Salle de lecture", "24,07 m²"), ("02 Coin lecture, vitrine", "6,68 m²"), ("03 Salle de réunion", "7,21 m²"), ("04 Rangement", "1,37 m²"),
           ("05 Placard technique", "0,24 m²"), ("06 Dégagement", "1,11 m²"), ("07 WC", "2,87 m²"), ("Total intérieur", "43,55 m²"), ("08 Terrasse couverte", "15,74 m²")]
    panel(e, "02", "Le projet", "Une salle de lecture fraîche en pied d'immeuble", "Esquisse V5 · existant V4 inchangé",
          [("Sommaire", som, "rows"), ("Espaces (IfcSpace de la maquette)", esp, "rows")], "02 · Le projet")
    P.append(("page", e, "Le projet"))
    # ---------------- 03 identité
    e = []
    for a_ in [(X0, Y0, X0 + CW, Y0), (X0, Y0 + 112, X0 + CW, Y0 + 112)]: e.append(("line",) + a_ + (FILET, 0.3))
    lw = 118; e.append(("img", LOGO_COL, X0 + (CW - lw) / 2, Y0 + (112 - lw * 814 / 2400) / 2, lw, lw * 814 / 2400))
    caption(e, X0, 130, CW, "Version principale sur papier blanc, « & » en terre cuite. Zone de protection : la moitié de la hauteur du carré tout autour.")
    sw = [("Gris texte", ENCRE, "titres, texte"), ("Gris clair", TAUPE, "texte 2, cotes"), ("Filet", FILET, "filets, grille"), ("Gris aplat", GRIS_CL, "tableaux"),
          ("Papier", "#FFFFFF", "fond unique"), ("Terre cuite", TERRE, "accent, rare"), ("Indigo", INDIGO, "accent, très rare"), ("Iroko", IROKO, "matière bois")]
    sww = (CW - 7 * G) / 8
    for i, (n, c, u) in enumerate(sw):
        x = X0 + i * (sww + G)
        e.append(("rect", x, 142, sww, 30, c))
        if c in ("#FFFFFF", GRIS_CL):
            for a_ in [(x,142,x+sww,142),(x,172,x+sww,172),(x,142,x,172),(x+sww,142,x+sww,172)]: e.append(("line",)+a_+(FILET,0.3))
        e.append(("text", x, 175, sww, n, S("small", font="jost5")))
        e.append(("text", x, 179.2, sww, f"{c} · {u}", S("cap", size=6.2, lead=7.6)))
    hw = (CW - G) / 2
    e.append(("line", X0, 194, X0 + hw, 194, FILET, 0.4))
    e.append(("text", X0, 198, hw, "Archivo SemiBold", S("title", size=24)))
    e.append(("text", X0, 210, hw, "Titres et chiffres clés, 18 à 36 pt, approche serrée", S("cap")))
    e.append(("text", X0, 222, hw, "Archivo Regular", S("title", font="jost4", size=22)))
    e.append(("text", X0, 233, hw, "Texte 8 à 10 pt, légendes 7 pt, capitales en Archivo Medium", S("cap")))
    e.append(("text", X0, 246, hw, "Manrope", S("title", font="manrope5", size=22)))
    e.append(("text", X0, 257, hw, "Réservée au nom K&Démi dans le logo", S("cap")))
    x2 = X0 + hw + G
    e.append(("rect", x2, 194, hw, 42, "#3A3A3A")); e.append(("img", LOGO_INV, x2 + (hw - 60) / 2, 194 + (42 - 60 * 814 / 2400) / 2, 60, 60 * 814 / 2400))
    for a_ in [(x2,241,x2+hw,241),(x2,283,x2+hw,283),(x2,241,x2,283),(x2+hw,241,x2+hw,283)]: e.append(("line",)+a_+(FILET,0.3))
    e.append(("img", LOGO, x2 + (hw - 60) / 2, 241 + (42 - 60 * 814 / 2400) / 2, 60, 60 * 814 / 2400))
    panel(e, "03", "Identité K&Démi", "L'arche dans le carré", "Logo v3 A, charte v2 du 15 octobre 2026",
          [("Le logo", "Une arche découpée dans un carré, lue comme une porte. Le nom est composé en Manrope, l'esperluette en terre cuite. C'est le seuil de la devanture Decimo ramené à un signe.", "p"),
           ("Règles d'usage", ["Le nom est toujours posé à côté du symbole. Le symbole seul est réservé à l'icône d'application et au favicon.",
                               "30 mm minimum en impression, 120 px à l'écran.",
                               "Version mono sur papier blanc, inversée sur fond sombre. Pas de déformation, d'ombre ni de dégradé."], "list"),
           ("La page", "Papier blanc, texte gris, une seule famille, Archivo. Toutes les pages partagent la grille et le panneau de droite des planches de dessin : 12 colonnes, marges de 14 mm, gouttières de 5 mm.", "p")],
          "03 · Identité K&Démi")
    P.append(("page", e, "Identité"))
    # ---------------- 04 D.A bibliothèque
    e = []
    e.append(("img", crop(B + "/../decimo_da/visuels/mood.png", CW, 165, "mood"), X0, Y0, CW, 165))
    caption(e, X0, 181, CW, "Planche matière : claustra en terre cuite, iroko huilé, chaux sable, enduit terre, grès cérame, acier noir, laine terre cuite, coton indigo, raphia")
    pal = [("Terre cuite", TERRE), ("Iroko", IROKO), ("Sable", SABLE), ("Chaux", CHAUX), ("Encre", ENCRE), ("Indigo", INDIGO), ("Olive", OLIVE)]
    pw = (CW - 6 * G) / 7
    for i, (n, c) in enumerate(pal):
        x = X0 + i * (pw + G)
        e.append(("rect", x, 189, pw, 14, c))
        if c == CHAUX:
            for a in [(x,189,x+pw,189),(x,203,x+pw,203),(x,189,x,203),(x+pw,189,x+pw,203)]: e.append(("line",)+a+(TAUPE,0.3))
        e.append(("text", x, 205, pw, f"{n} {c}", S("cap", size=6.4)))
    cw4 = (CW - 3 * G) / 4
    cols = [("Matériaux", "Terrazzo clair au sol, parquet iroko dans la salle de lecture, enduit terre et chaux sable aux murs, lambris iroko à claire-voie, acier noir mat pour les châssis et la marquise."),
            ("Mobilier", "Iroko sur mesure : arbre à livres, rayonnages, banque d'accueil, banquettes. Chaises courbes, assises en raphia, coussins indigo artisanaux."),
            ("Lumière", "Tout en 2700 K. Anneau LED sous la canopée de l'arbre, downlights encastrés, suspensions terre cuite au-dessus des tables, réglette de vitrine, spot IP65 sous marquise."),
            ("Végétal", "Ficus lyrata, strelitzia, fougères et dracaena en jardinières sur la terrasse. Le vert reste rare à l'intérieur pour laisser la terre et le bois parler.")]
    for i, (h, t) in enumerate(cols):
        x = X0 + i * (cw4 + G)
        e.append(("line", x, 216, x + cw4, 216, FILET, 0.4))
        e.append(("text", x, 220, cw4, h, S("col_h", size=12.5)))
        e.append(("text", x, 227.5, cw4, t, S("small", size=7.8, lead=10.8)))
    panel(e, "04", "D.A de la bibliothèque", "Terre, ombre et bois", "Direction artistique d'Affoué, visée le 14 octobre 2026",
          [("Principes", ["Un seuil cintré centré sur la rue cadre l'arbre à livres.",
                          "Les baies en claustra terre cuite, à motifs inspirés des Adinkra Adinkrahene et Eban, filtrent le soleil de l'après-midi.",
                          "La canopée de l'arbre et son oculus indigo sont le seul objet fort de la salle.",
                          "Iroko pour tout ce qui se touche, chaux pour tout ce qui se voit.",
                          "Ventilation traversante par la claustra et la terrasse, deux splits en appoint dont les unités extérieures vont en courette."], "list"),
           ("Ambiance", "Une pénombre fraîche, une lumière tamisée par la claustra le jour et 2700 K le soir. Aucun dégradé, aucun motif plaqué : les motifs naissent de la matière.", "p")],
          "04 · D.A de la bibliothèque")
    P.append(("page", e, "D.A"))
    # ---------------- A01-A08
    for code, nom in [("A01_plan_RDC", "A01"), ("A02_plan_faux_plafond_reseaux", "A02"), ("A03_coupe_AA", "A03"), ("A04_elevation_devanture", "A04"),
                      ("A05_elevations_interieures_est_nord", "A05"), ("A06_elevations_interieures_sud_ouest", "A06"), ("A07_vues_3D", "A07"), ("A08_axonometries", "A08")]:
        P.append(("pdf", DES + code + ".pdf", DES + code + ".png", nom))
    # ---------------- R1
    e = []
    e.append(("img", crop(R + "01_devanture.png", CW, 160, "r1"), X0, Y0, CW, 160))
    caption(e, X0, 176.5, CW, "R1 · Devanture sur rue, vue piéton depuis le trottoir opposé, œil à 1,60 m")
    hw = (CW - G) / 2
    e.append(("img", crop(V + "01_devanture_rue_pieton_ombre.png", hw, 69, "r1_s1"), X0, 186, hw, 69))
    e.append(("img", crop(V + "01_devanture_rue_pieton_traits.png", hw, 69, "r1_s2"), X0 + hw + G, 186, hw, 69))
    caption(e, X0, 257, hw, "Vue source 01 : maquette IFC V5 ombrée, même caméra")
    caption(e, X0 + hw + G, 257, hw, "Vue source 01 : traits et silhouettes")
    panel(e, "13", "La devanture", "Le seuil cintré sous la pergola", "Rendu tiré de la maquette IFC V5",
          [("Ce que l'on voit", "Les quatre baies existantes de la V4 gardent leur forme. La vitrine en arche et son châssis en acier noir se posent dans la baie A, la porte vitrée dans le portail en enduit terre cuite. Les deux baies de claustra reçoivent les inserts Adinkra. La pergola en bois de la V4 abrite la terrasse de lecture.", "p"),
           ("Contrôle", "Même caméra, mêmes baies, même pergola que la vue source. Le rendu ajoute la matière et la lumière. Les balcons qu'il avait inventés sur l'immeuble voisin ont été retirés : la maquette y montre un mur plein. Écart restant : les jardinières basses de la terrasse sont rendues comme des banquettes. La maquette fait foi.", "p"),
           ("Méthode", "Chaque rendu part d'une vue exportée de l'IFC (v5/vues_rendu, position, cible et focale enregistrées). L'image est retravaillée en matière et lumière sans rien ajouter ni déplacer, puis comparée à sa vue source avant d'entrer au dossier.", "p")],
          "13 · R1 Rendu de la devanture")
    P.append(("page", e, "R1"))
    # ---------------- R2
    e = []
    e.append(("img", crop(R + "02_interieur_entree.png", CW, 141, "r2a"), X0, Y0, CW, 141))
    caption(e, X0, 157.5, CW, "R2a · Depuis l'entrée : la banque d'accueil, la salle de lecture et l'arbre à livres au fond")
    hw = (CW - G) / 2
    e.append(("img", crop(R + "03_interieur_devanture.png", hw, 98, "r2b"), X0, 166, hw, 98))
    e.append(("img", crop(R + "05_coin_lecture.png", hw, 98, "r2c"), X0 + hw + G, 166, hw, 98))
    caption(e, X0, 266.5, hw, "R2b · Vers la devanture : la porte cintrée et la claustra")
    caption(e, X0 + hw + G, 266.5, hw, "R2c · Le coin lecture en vitrine, banquette et rayonnages iroko")
    panel(e, "14", "Les intérieurs", "Une pénombre fraîche, du bois et des livres", "Rendus tirés des vues 02, 03 et 05 de la maquette",
          [("Matières", "Terrazzo clair au sol, enduit terre et chaux aux murs, iroko huilé pour la banque d'accueil, les rayonnages et les banquettes. Le faux-plafond acoustique à +3,00 garde 0,26 m de plénum sous la dalle de l'immeuble.", "p"),
           ("Lumière", "Downlights 2700 K encastrés, suspensions en terre cuite au-dessus des tables, lumière du jour filtrée par la claustra. Les splits sont posés en hauteur sur des murs pleins, jamais au-dessus des tables.", "p"),
           ("Contrôle", "Comparés à leurs vues sources : murs, baies, mobilier et luminaires sont à leur place. Seuls les livres sur les étagères et la végétation sont ajoutés au rendu.", "p")],
          "14 · R2 Rendus intérieurs")
    P.append(("page", e, "R2"))
    # ---------------- R3
    e = []
    bw = 118
    e.append(("img", crop(R + "04_arbre.png", bw, CH - 8, "r3", focus=(0.5, 0.5)), X0, Y0, bw, CH - 8))
    caption(e, X0, Y0 + CH - 5, bw, "R3 · L'arbre à livres et l'oculus indigo de 2,80 m, anneau LED 2700 K")
    sx = X0 + bw + G; sw = CW - bw - G; sh = 65
    for i, (f, t) in enumerate([("02_interieur_depuis_entree_traits.png", "Vue source 02, traits"), ("03_interieur_vers_devanture_traits.png", "Vue source 03, traits"), ("04_arbre_a_livres_traits.png", "Vue source 04, traits")]):
        y = Y0 + i * (sh + 11)
        e.append(("img", crop(V + f, sw, sh, f"r3_s{i}"), sx, y, sw, sh)); caption(e, sx, y + sh + 1.8, sw, t)
    e.append(("text", sx, 246, sw, "Les vues sources sont recalculées depuis l'IFC par v5/scripts/vues_rendu.py, avec la position, la cible et la focale enregistrées pour chaque caméra.", S("small", color=TAUPE)))
    panel(e, "15", "L'arbre à livres", "Le seul objet fort de la salle", "Rendu tiré de la vue 04 de la maquette",
          [("L'objet", "Un fût d'iroko porte des étagères circulaires et s'évase en canopée sous un oculus de 2,80 m. La sous-face de dalle est laquée indigo et un anneau LED indirect dessine le bord de l'oculus.", "p"),
           ("Dans la maquette", "Modélisé en IfcFurniture sculptural au centre de la salle de lecture, avec l'oculus en IfcCovering et l'anneau en IfcLightFixture. Il est fixé sous la dalle sans la traverser : la charge, l'ancrage et la réaction au feu restent à valider par le BET.", "p")],
          "15 · R3 L'arbre à livres")
    P.append(("page", e, "R3"))
    # ---------------- technique
    for i, tp in enumerate(TPAGES):
        P.append(tech_page(i, *tp))
    # ---------------- cohérence
    e = []
    cols = [("Élément", 58), ("D.A", 26), ("Maquette IFC V5", 66), ("Plans", 44), ("Rendus", 23)]
    rows = TECH.get("coherence") or [
        ("Devanture : 4 baies V4, vitrine en arche, portail terre cuite, claustra Adinkra", "p. 04", "IfcWindow, IfcDoor, IfcMember dans les baies V4", "A01, A04", "R1"),
        ("Arbre à livres et oculus indigo Ø 2,80", "p. 04", "IfcFurniture, IfcCovering, anneau IfcLightFixture", "A01, A02, A03", "R2, R3"),
        ("Matériaux : terrazzo, iroko, enduit terre, chaux, acier noir", "p. 04", "IfcMaterial et styles de surface D.A", "A05, A06", "R1 à R3"),
        ("Lumière 2700 K", "p. 04", "27 IfcLightFixture", "A02", "R2, R3"),
        ("Programme du 14/10 : un seul WC, salle de réunion", "", "IfcSpace 03 et 07", "A01", ""),
        ("Climatisation : 2 splits 9 000 BTU/h sur murs pleins, hors tables", "p. 04", "2 IfcUnitaryEquipment, 2 mini-pompes", "A02", "R2"),
        ("Tableau divisionnaire, 1,00 m dégagé, loin de l'eau", "", "IfcElectricDistributionBoard", "A01, A02", ""),
        ("Placard technique 0,60 × 0,40, porte pleine", "", "IfcSpace 05 et IfcDoor", "A01, A02", ""),
        ("Descentes EU/EV de l'immeuble en coffrage 0,30 × 0,30", "", "Coffrages « à relever sur site »", "A02", ""),
        ("Existant V4 : murs, poteau, ouvertures, emprise 6,78 × 7,68", "", "141 / 141 identiques, 0 pénétration", "toutes", "toutes"),
        ("Lots techniques : électricité, CFA, AEP, EU, EV, détails", "", "DECIMO_ESQ_V5_tech.ifc : 141/141 V4, 231/231 V5, 0 pénétration", "T01 à T05", ""),
    ]
    y = Y0
    x = X0
    for n, wdt in cols:
        e.append(("text", x, y, wdt - 2, n, S("lab", color=TERRE, size=6.6))); x += wdt + 2.5
    y += 5; e.append(("line", X0, y, X0 + CW, y, ENCRE, 0.4)); y += 2.2
    for r in rows:
        x = X0; hmax = 0
        for (n, wdt), v in zip(cols, r):
            hmax = max(hmax, els_text_height(v or "·", S("body"), wdt - 2))
            e.append(("text", x, y, wdt - 2, v or "·", S("body", color=ENCRE if v else TAUPE))); x += wdt + 2.5
        y += hmax + 1.6; e.append(("line", X0, y, X0 + CW, y, FILET, 0.25)); y += 2.0
    y += 5
    e.append(("text", X0, y, CW, "Points ouverts, à lever en APS", S("col_h"))); y += 8
    pts = TECH.get("points") or [
        "Relevé de l'existant : dalle haute (épaisseur 0,20 et sous-face +3,30 en hypothèse), descentes EU/EV, arrivée électrique de l'immeuble.",
        "BET : statut porteur des refends en agglos, fixations non traversantes sous dalle, charge et ancrage de l'arbre à livres et de l'oculus.",
        "Copropriété : sortie des liaisons de clim et des unités extérieures en courette, adaptation de l'imposte de la baie arrière.",
        "MOA : maintien des claustras V4 devant la vitrine de la baie A, fabrication des inserts Adinkra avec l'artisan.",
        "APS : reprise des rails et suspensions V4 qui tombent dans le plénum, condensats relevés par mini-pompes faute de pente gravitaire.",
        "Accessibilité PMR du WC et réaction au feu des éléments en bois à vérifier.",
        "Lots techniques (note d'Ahoua) : arrivée électrique de l'immeuble, position réelle des descentes EU/EV et de la colonne AEP, ventilation du WC aveugle, fourreau R6 dans la cloison placo V4 à valider ou remplacer par une goulotte, abonnement 6 kVA à confirmer.",
        "Rendu R1 : jardinières de la terrasse rendues en banquettes, à reprendre pour coller à la maquette.",
    ]
    hw = (CW - G) / 2
    yl = y; yr = y
    for i, t in enumerate(pts):
        col = 0 if i < (len(pts) + 1) // 2 else 1
        xx = X0 + col * (hw + G); yy = yl if col == 0 else yr
        e.append(("text", xx, yy, 6, f"{i+1:02d}", S("body", color=TERRE)))
        hh = els_text_height(t, S("body"), hw - 7)
        e.append(("text", xx + 7, yy, hw - 7, t, S("body")))
        if col == 0: yl += hh + 2
        else: yr += hh + 2
    cw4 = (CW - 3 * G) / 4
    for i, (k, l) in enumerate(TECH.get("kpis") or [("0 erreur", "validation IFC4, natif et variante Revit"), ("141 / 141", "produits V4 identiques en V5"), ("0", "pénétration d'un ajout dans la structure"), ("8", "espaces IfcSpace nommés et métrés")]):
        x = X0 + i * (cw4 + G)
        e.append(("line", x, 250, x + cw4, 250, FILET, 0.3)); e.append(("text", x, 254, cw4, k, S("kpi"))); e.append(("text", x, 266, cw4, l, S("cap", size=7.4, lead=9.4)))
    panel(e, f"{16+len(TPAGES):02d}", "Cohérence", "D.A, maquette, plans et technique", "Contrôle croisé du 15 octobre 2026",
          [("Validations", TECH.get("validations", "IFC4 natif et variante maillée pour Revit : 0 erreur au validateur ifcopenshell 0.9.0, schéma et règles EXPRESS. Contre-vérification indépendante sur main : les 141 produits V4 sont retrouvés par GlobalId, placements et géométries identiques (écart 0), emprise 6,78 × 7,68 m, WC 4350629 et lave-mains 4350630/4350631 conservés."), "p"),
           ("Livrables", TECH.get("livrables", "Maquettes v5/DECIMO_ESQ_V5.ifc, DECIMO_ESQ_V5_tech.ifc et variante maillée pour Revit, planches A01 à A08 et T01 à T05 en PDF, PNG et SVG, note technique, vues de rendu avec leurs caméras, rapports de vérification. Tout est sur la branche main du dépôt jeemake/bibliothequeNandjuiS.Simon."), "p"),
           ("Lecture", "Les cotes et surfaces sont indicatives au stade de l'esquisse. L'existant V4 reste à relever sur site avant l'APS.", "p")],
          f"{16+len(TPAGES):02d} · Cohérence et points ouverts")
    P.append(("page", e, "Cohérence"))
    return P
