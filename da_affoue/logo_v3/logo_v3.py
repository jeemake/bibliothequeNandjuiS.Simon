# K&Démi logo v3 "startup" — symboles géométriques + wordmark sans outliné (Manrope / Space Grotesk / Inter, OFL)
import os,base64
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.varLib import instancer
import cairosvg
os.chdir('/workspace/decimo_da'); O='logo_v3'
ENC="#2B2420";TC="#B4583E";CH="#FBF8F3";SAB="#E6D6BF";TAU="#7D7168"
G='/usr/share/fonts/truetype/sand-box/google/'
F={'man':instancer.instantiateVariableFont(TTFont(G+'Manrope/Manrope-VariableFont_wght.ttf'),{'wght':700}),
   'spg':instancer.instantiateVariableFont(TTFont(G+'Space Grotesk/SpaceGrotesk-VariableFont_wght.ttf'),{'wght':700}),
   'int':instancer.instantiateVariableFont(TTFont(G+'Inter/Inter-VariableFont_opsz,wght.ttf'),{'wght':700,'opsz':32}),
   'jost':instancer.instantiateVariableFont(TTFont('fonts/Jost.ttf'),{'wght':500})}
def text(s,font,x,y,size,fill,kern=None,acc=None):
    f=F[font];gs=f.getGlyphSet();cm=f.getBestCmap();sc=size/f['head'].unitsPerEm;out='';cx=x
    for i,ch in enumerate(s):
        pen=SVGPathPen(gs);g=cm[ord(ch)];gs[g].draw(TransformPen(pen,(sc,0,0,-sc,cx,y)))
        d=pen.getCommands()
        if d: out+=f'<path d="{d}" fill="{acc if (acc and ch=="&") else fill}"/>'
        cx+=gs[g].width*sc+(kern[i] if kern else 0)*size
    return out,cx-x
def arch(x,y,w,h): r=w/2; return f"M{x},{y} V{y-h+r} A{r},{r} 0 0 1 {x+w},{y-h+r} V{y} Z"
# symboles 100x100, dessinés pour une grille 16 px (traits >= 12.5 u = 2 px)
def sA(fg,bg):  # carré + arche évidée
    return f'<path d="M0,0 H100 V100 H0 Z {arch(31,100,38,62)}" fill="{fg}" fill-rule="evenodd"/>'
def sB(fg,bg):  # un trait + une voûte = K|D
    return f'<rect x="6" y="0" width="22" height="100" fill="{fg}"/><path d="M40,0 H44 A50,50 0 0 1 44,100 H40 Z" fill="{fg}"/>'
def sC(fg,bg):  # arche pleine posée sur un seuil
    return f'<path d="{arch(14,78,72,78)}" fill="{fg}"/><rect x="0" y="88" width="100" height="12" fill="{fg}"/>'
KERN=[-0.02,-0.03,-0.01,0,0,0]
D={'A_arche':(sA,'man','Arche dans le carré','Le portique réduit à une seule arche évidée dans un carré. Manrope 700.'),
   'B_trait_voute':(sB,'spg','Trait + voûte','Un trait (K) et une voûte (D) : le portique ouvert en deux gestes. Space Grotesk 700.'),
   'C_seuil':(sC,'int','Arche sur seuil','Une arche pleine posée sur un seuil. Inter 700.')}
def sym(f,fg,bg,x,y,s): return f'<g transform="translate({x},{y}) scale({s/100})">{f(fg,bg)}</g>'
def word(font,fg,x,y,size,acc=TC): return text('K&Démi',font,x,y,size,fg,KERN,acc)
def lock(f,font,fg,bg,x,y,h,acc=TC):
    w,ww=word(font,fg,x+h*1.35,y+h*0.86,h*0.82,acc); return sym(f,fg,bg,x,y,h)+w,h*1.35+ww
def svg(W,H,body,bg=None,k=4): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W*k}" height="{H*k}">'+(f'<rect width="{W}" height="{H}" fill="{bg}"/>' if bg else '')+body+'</svg>'
def save(n,s,**kw):
    open(f'{O}/{n}.svg','w').write(s); cairosvg.svg2png(bytestring=s.encode(),write_to=f'{O}/{n}.png',**kw)
for key,(f,font,title,desc) in D.items():
    n=f'KDemi_v3_{key}'
    for v,fg,bg,acc in [('',ENC,CH,TC),('_inverse',CH,ENC,TC),('_mono',ENC,CH,ENC)]:
        save(n+'_symbole'+v,svg(140,140,sym(f,fg,bg,20,20,100),bg))
        w,ww=word(font,fg,30,100,82,acc); save(n+'_wordmark'+v,svg(int(ww+60),130,w,bg))
        l,lw=lock(f,font,fg,bg,30,30,80,acc); save(n+'_lockup'+v,svg(int(lw+60),140,l,bg))
    # app icon + favicons
    ic=f'<rect width="100" height="100" rx="22" fill="{TC}"/>'+sym(f,CH,TC,24,24,52)
    save(n+'_appicon',svg(100,100,ic,k=10.24))
    for px in (16,32): save(n+f'_favicon{px}',svg(100,100,f'<rect width="100" height="100" fill="{ENC}"/>'+sym(f,CH,ENC,14,14,72),k=px/100),output_width=px,output_height=px)
    fav16=base64.b64encode(open(f'{O}/{n}_favicon16.png','rb').read()).decode()
    S=f'<rect width="1600" height="1130" fill="{CH}"/>'
    t,_=text(f'K&Démi — logo v3 · {title}','int',60,80,36,ENC); S+=t
    t,_=text(desc,'jost',60,116,18,TAU); S+=t
    # zone 1 : symbole / wordmark / lockup (beaucoup de blanc)
    S+=f'<rect x="60" y="150" width="340" height="340" fill="#fff"/>'+sym(f,ENC,'#fff',150,240,160)
    S+=f'<rect x="420" y="150" width="560" height="160" fill="#fff"/>'; w,_=word(font,ENC,470,262,78); S+=w
    S+=f'<rect x="420" y="330" width="560" height="160" fill="#fff"/>'; l,_=lock(f,font,ENC,'#fff',470,380,62); S+=l
    S+=f'<rect x="1000" y="150" width="540" height="340" fill="{ENC}"/>'; l,lw=lock(f,font,CH,ENC,0,0,80); S+=f'<g transform="translate({1270-lw/2},280)">{l}</g>'
    # app icon mockup
    S+=f'<rect x="60" y="520" width="340" height="560" rx="40" fill="{ENC}"/><rect x="76" y="536" width="308" height="528" rx="28" fill="#3a322d"/>'
    for i in range(8):
        cx=100+(i%4)*70; cy=600+(i//4)*90
        S+=f'<rect x="{cx}" y="{cy}" width="52" height="52" rx="12" fill="#5a5049"/>' if i!=5 else f'<g transform="translate({cx},{cy}) scale(.52)">{ic}</g>'
    t,_=text('K&Démi','jost',165,780,10,CH); S+=t
    t,_=text('App icon','jost',80,1100,12,TAU); S+=t
    # favicon : onglet navigateur, 16 px réel
    S+=f'<rect x="420" y="520" width="560" height="120" fill="#e9e4dc"/><path d="M440,640 V560 Q440,550 450,550 H700 Q710,550 710,560 V640 Z" fill="#fff"/>'
    S+=f'<image x="455" y="587" width="16" height="16" href="data:image/png;base64,{fav16}" style="image-rendering:pixelated"/>'
    t,_=text('K&Démi — Architecture','int',480,600,13,ENC); S+=t
    t,_=text('Favicon 16 px réel (pixels natifs)','jost',740,600,12,TAU); S+=t
    for i,s in enumerate((16,24,32,64)): S+=f'<rect x="{440+i*90}" y="{660}" width="{s}" height="{s}" fill="{ENC}"/>'+sym(f,CH,ENC,440+i*90+s*.14,660+s*.14,s*.72)
    # en-tête A3
    S+=f'<rect x="1000" y="520" width="540" height="381" fill="#fff" stroke="{SAB}" stroke-width="2"/>'
    l,_=lock(f,font,ENC,'#fff',1024,540,22); S+=l
    t,_=text('BIBLIOTHÈQUE DECIMO · ESQ','jost',1330,558,10,TAU); S+=t
    S+=f'<rect x="1024" y="574" width="492" height="1.5" fill="{ENC}"/><rect x="1024" y="590" width="300" height="290" fill="{SAB}"/><rect x="1340" y="590" width="176" height="140" fill="{SAB}"/><rect x="1340" y="740" width="176" height="140" fill="{SAB}"/>'
    t,_=text('En-tête A3 paysage','jost',1000,920,12,TAU); S+=t
    # devanture
    S+=f'<rect x="420" y="760" width="560" height="320" fill="#d9cdbd"/>'
    for i in range(5): S+=f'<rect x="{445+i*110}" y="772" width="60" height="26" fill="#8c8174"/>'
    S+=f'<rect x="440" y="815" width="520" height="70" fill="{ENC}"/>'
    l,lw=lock(f,font,CH,ENC,0,0,38); S+=f'<g transform="translate({700-lw/2},831)">{l}</g>'
    S+=f'<rect x="440" y="885" width="520" height="195" fill="#5d6a6e"/><rect x="610" y="905" width="110" height="175" fill="{TC}"/>'
    for i in range(1,4): S+=f'<rect x="{440+i*130}" y="885" width="5" height="195" fill="{ENC}"/>'
    t,_=text('Bandeau devanture (RDC immeuble)','jost',1000,1080,12,TAU); S+=t
    save(f'Planche_logo_v3_{key}',svg(1600,1130,S,k=2))
