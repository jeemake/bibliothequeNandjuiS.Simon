# K&Démi logo v2 — 3 directions, hand-drawn geometry + outlined free fonts (DM Serif Display OFL, Archivo OFL)
import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.varLib import instancer
import cairosvg
os.chdir('/workspace/decimo_da')
ENC="#2B2420";TC="#B4583E";IRO="#9A6B43";SAB="#E6D6BF";CH="#FBF8F3";TAU="#7D7168"
F={'serif':TTFont('fonts/DMSerifDisplay-Regular.ttf'),'ital':TTFont('fonts/DMSerifDisplay-Italic.ttf'),
   'jost':instancer.instantiateVariableFont(TTFont('fonts/Jost.ttf'),{'wght':500}),
   'blk':instancer.instantiateVariableFont(TTFont('/usr/share/fonts/truetype/sand-box/google/Archivo/Archivo-VariableFont_wdth,wght.ttf'),{'wght':900,'wdth':100})}
def glyph(ch,font,x,y,size):
    f=F[font];gs=f.getGlyphSet();g=f.getBestCmap()[ord(ch)];sc=size/f['head'].unitsPerEm
    pen=SVGPathPen(gs);gs[g].draw(TransformPen(pen,(sc,0,0,-sc,x,y)));return pen.getCommands(),gs[g].width*sc
def text(s,font,x,y,size,fill,track=0):
    out=[];cx=x
    for ch in s:
        d,w=glyph(ch,font,cx,y,size)
        if d: out.append(f'<path d="{d}" fill="{fill}"/>')
        cx+=w+track
    return ''.join(out),cx
def arch(x,y,w,h):
    r=w/2; return f"M{x},{y} V{y-h+r} A{r},{r} 0 0 1 {x+w},{y-h+r} V{y} Z"
# ---------- 1 : ligature K&D (100 high, 112 wide)
def m1(fg,bg):
    p=[]
    p.append("M0,0 H24 V45 H0 Z")                       # fût K haut
    p.append("M0,53 H24 V100 H0 Z")                     # fût bas (entaille seuil 45-53)
    p.append("M24,45 L58,0 H88 L44,45 Z")               # bras du K
    p.append("M24,53 H58 A47,47 0 0 1 58,100 H24 Z")    # panse du D sous le bras (voûte)
    s=f'<path d="{" ".join(p)}" fill="{fg}"/>'
    s+=f'<path d="M38,66 H58 A17,17 0 0 1 58,87 H38 Z" fill="{bg}"/>'  # contreforme du D
    d,_=glyph('&','blk',66,50,62); s+=f'<path d="{d}" fill="{bg}" stroke="{bg}" stroke-width="8" stroke-linejoin="round"/><path d="{d}" fill="{fg}"/>'
    return s,112
# ---------- 2 : portique voûte + claustra + emmarchement (K = pilier gauche, D = rein droit)
def m2(fg,bg):
    s=f'<path d="M0,0 H58 A44,50 0 0 1 58,100 H0 Z" fill="{fg}"/>'
    s+=f'<path d="M12,0 H30 V30 Z" fill="{bg}"/>'              # entaille diagonale du K
    s+=f'<path d="{arch(30,100,38,64)}" fill="{bg}"/>'         # coupe de voûte
    for i in range(3): s+=f'<rect x="{34+i*11}" y="11" width="7" height="7" fill="{bg}"/>'  # claustra
    for i,(x,w) in enumerate([(30,38),(36,26),(42,14)]): s+=f'<rect x="{x}" y="{100-7*(i+1)}" width="{w}" height="7" fill="{fg}"/>'
    return s,102
# ---------- 3 : logotype lourd, é-toit, point du i en arche, & expressif
def m3(fg,bg):
    s='';x=0;y=100;sz=118
    d,w=glyph('K','blk',x,y,sz); s+=f'<path d="{d}" fill="{fg}"/>'; x+=w-3
    d,w=glyph('&','ital',x-2,y+4,138); s+=f'<path d="{d}" fill="{TC if fg!=CH else SAB}" />'.replace(TC if fg!=CH else SAB,fg); x+=w-6
    d,w=glyph('D','blk',x,y,sz); s+=f'<path d="{d}" fill="{fg}"/>'; x+=w-2
    ex=x; d,w=glyph('e','blk',x,y,sz); s+=f'<path d="{d}" fill="{fg}"/>'; cx=ex+w/2; x+=w-2
    s+=f'<path d="M{cx-28},{y-80} L{cx+30},{y-112} L{cx+30},{y-98} L{cx-28},{y-70} Z" fill="{fg}"/><rect x="{cx+18}" y="{y-112}" width="12" height="18" fill="{fg}"/>'  # toit monopente = accent aigu
    d,w=glyph('m','blk',x,y,sz); s+=f'<path d="{d}" fill="{fg}"/>'; x+=w-2
    d,w=glyph('ı','blk',x,y,sz); s+=f'<path d="{d}" fill="{fg}"/>'; ix=x+w/2
    s+=f'<path d="{arch(ix-12,y-84,24,24)}" fill="{fg}"/>'                 # point du i = arche
    x+=w
    return f'<g transform="translate(0,14)">{s}</g>',x
DIRS={'1_ligature':(m1,'Ligature K&D','Fût entaillé d\'un seuil, bras du K et panse du D en voûte, & gravé dans l\'angle.'),
      '2_portique':(m2,'Portique voûte','Coupe de voûte, claustra et 3 marches : le pilier entaillé fait le K, le rein courbe fait le D.'),
      '3_logotype':(m3,'Logotype toit','Archivo 900 redessinée : é coiffé d\'un toit, point du i en arche, & DM Serif italique.')}
def wrap(inner,w,h,W,H,bg):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W*4}" height="{H*4}">'+(f'<rect width="{W}" height="{H}" fill="{bg}"/>' if bg else '')+inner+'</svg>'
def place(mk,fg,bg,x,y,h):
    s,w=mk(fg,bg); H=128 if mk is m3 else 100; k=h/H
    return f'<g transform="translate({x},{y}) scale({k})">{s}</g>',w*k
def lockup(mk,fg,bg,x,y,h,sub=True):
    g,w=place(mk,fg,bg,x,y,h)
    if mk is m3:
        if sub: t,_=text('ARCHITECTURE · INTÉRIEUR','jost',x+2,y+h+h*0.22,h*0.13,fg if fg==CH else TAU,track=h*0.03); g+=t
        return g,w
    t,cx=text('K&Démi','serif',x+w+h*0.22,y+h*0.62,h*0.55,fg); g+=t
    if sub: t2,_=text('ARCHITECTURE · INTÉRIEUR','jost',x+w+h*0.24,y+h*0.92,h*0.13,fg if fg==CH else TAU,track=h*0.03); g+=t2
    return g,max(w,cx-x)
out='logo_v2'
def save(name,svg):
    open(f'{out}/{name}.svg','w').write(svg); cairosvg.svg2png(bytestring=svg.encode(),write_to=f'{out}/{name}.png')
for key,(mk,title,desc) in DIRS.items():
    for v,fg,bg in [('',ENC,CH),('_inverse',CH,ENC),('_terre',CH,TC)]:
        g,w=lockup(mk,fg,bg,20,20,100); save(f'KDemi_v2_{key}_logo{v}',wrap(g,0,0,int(w+40) if mk is m3 else int(w+60),160 if mk is m3 else 140,bg))
        g,w=place(mk,fg,bg,10,10,100); save(f'KDemi_v2_{key}_symbole{v}',wrap(g,0,0,int(w+20),120 if mk is not m3 else 150,bg))
    # planche 1600x1130
    S=f'<rect width="1600" height="1130" fill="{CH}"/>'
    t,_=text(f'K&Démi — logo v2 · direction {key[0]} : {title}','serif',60,80,40,ENC); S+=t
    t,_=text(desc,'jost',60,118,18,TAU); S+=t
    S+=f'<rect x="60" y="150" width="720" height="380" fill="{CH}" stroke="{SAB}" stroke-width="2"/>'
    g,_=lockup(mk,ENC,CH,100,260,130); S+=g
    S+=f'<rect x="820" y="150" width="720" height="380" fill="{ENC}"/>'
    g,_=lockup(mk,CH,ENC,860,260,130); S+=g
    # tailles réduites
    S+=f'<rect x="60" y="560" width="480" height="200" fill="{SAB}"/>'
    xx=90
    for h in ((90,48,24) if mk is not m3 else (52,30)):
        g,w=place(mk,ENC,SAB,xx,690-h,h); S+=g; xx+=w+40
    t,_=text('Réduction : le plus petit ≈ 8 mm (24 px @ 76 dpi)','jost',80,745,13,ENC); S+=t
    S+=f'<rect x="560" y="560" width="200" height="200" fill="{TC}"/>'
    g,w=place(mk,CH,TC,0,0,90 if mk is not m3 else 34); S+=f'<g transform="translate({660-w/2},{615 if mk is not m3 else 640})">{g}</g>'
    # mockup en-tête A3 (ratio 420x297 -> bande)
    S+=f'<rect x="800" y="560" width="740" height="523" fill="#fff" stroke="{SAB}" stroke-width="2"/>'
    S+=f'<rect x="800" y="560" width="740" height="64" fill="{ENC}"/>'
    g,_=lockup(mk,CH,ENC,820,574,36,sub=False); S+=g
    t,_=text('BIBLIOTHÈQUE DECIMO · ESQ · PLANCHE D.A','jost',1180,598,12,SAB,track=1.5); S+=t
    S+=f'<rect x="830" y="650" width="420" height="400" fill="{SAB}"/><rect x="1270" y="650" width="240" height="190" fill="{SAB}"/><rect x="1270" y="860" width="240" height="190" fill="{SAB}"/>'
    t,_=text('Mockup en-tête A3 paysage','jost',830,1075,12,TAU); S+=t
    # mockup bandeau devanture
    S+=f'<rect x="60" y="790" width="720" height="293" fill="#d9cdbd"/>'
    S+=f'<rect x="60" y="790" width="720" height="40" fill="#cfc2b0"/>'  # dalle immeuble
    for i in range(6): S+=f'<rect x="{90+i*115}" y="800" width="60" height="22" fill="#8c8174"/>'
    S+=f'<rect x="90" y="845" width="660" height="70" fill="{ENC}"/>'
    g,w=lockup(mk,CH,ENC,0,0,48,sub=False); S+=f'<g transform="translate({420-w/2},856)">{g}</g>'
    S+=f'<rect x="90" y="915" width="660" height="168" fill="#5d6a6e"/>'
    for i in range(1,4): S+=f'<rect x="{90+i*165}" y="915" width="6" height="168" fill="{ENC}"/>'
    S+=f'<rect x="300" y="935" width="120" height="148" fill="{TC}"/>'
    t,_=text('Mockup bandeau devanture (RDC immeuble)','jost',70,1105,12,TAU); S+=t
    save(f'Planche_logo_v2_{key}',f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1130" width="3200" height="2260">{S}</svg>')
