from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.varLib import instancer
import cairosvg
ENC="#2B2420";TC="#B4583E";SAB="#E6D6BF";CH="#FBF8F3";TAU="#7D7168";IRO="#9A6B43"
F={'serif':TTFont('fonts/DMSerifDisplay-Regular.ttf'),'ital':TTFont('fonts/DMSerifDisplay-Italic.ttf'),
   'jost':instancer.instantiateVariableFont(TTFont('fonts/Jost.ttf'),{'wght':500})}
def text(s,font,x,y,size,fill,track=0):
    f=F[font];gs=f.getGlyphSet();cmap=f.getBestCmap();upm=f['head'].unitsPerEm;sc=size/upm;out=[];cx=x
    for ch in s:
        g=cmap.get(ord(ch));
        if g is None: continue
        pen=SVGPathPen(gs);gs[g].draw(TransformPen(pen,(sc,0,0,-sc,cx,y)))
        d=pen.getCommands()
        if d: out.append(f'<path d="{d}" fill="{fill}"/>')
        cx+=gs[g].width*sc+track
    return ''.join(out),cx
def arch(x,y,w,h):  # base-left x,y(bottom), width, total height
    r=w/2; return f"M{x},{y} V{y-h+r} A{r},{r} 0 0 1 {x+w},{y-h+r} V{y} Z"
def save(name,body,W,H,bg=None):
    s=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W*4}" height="{H*4}">'+(f'<rect width="{W}" height="{H}" fill="{bg}"/>' if bg else '')+body+'</svg>'
    open(f'logo/{name}.svg','w').write(s); cairosvg.svg2png(bytestring=s.encode(),write_to=f'logo/{name}.png')
def word(x,y,ink,size=56,sub=True):
    a,cx=text('K','serif',x,y,size,ink); b,cx=text('&','ital',cx+2,y,size,TC); c,cx=text('Démi','serif',cx+2,y,size,ink)
    d='';
    if sub: d,_=text('ARCHITECTURE · INTÉRIEUR','jost',x+2,y+24,10.5,TAU,track=2.6)
    return a+b+c+d
# A — Arche-seuil : arche évidée + seuil à 3 marches + claustra
def markA(x,y,s=1,fg=TC,inner=SAB):
    g=f'<g transform="translate({x},{y}) scale({s})">'
    g+=f'<path d="{arch(0,80,52,80)} {arch(10,80,32,70)}" fill="{fg}" fill-rule="evenodd"/>'
    for i,(dx,w) in enumerate([(10,32),(14,24),(18,16)]): g+=f'<rect x="{dx}" y="{80-6*(i+1)}" width="{w}" height="6" fill="{fg}" opacity="{1 if i==0 else 1}"/>'
    for r in range(3):
        for c in range(3): g+=f'<rect x="{17+c*7}" y="{24+r*7}" width="4" height="4" fill="{fg}"/>'
    return g+'</g>'
# B — Monogramme KD : fût du K + D en demi-arche
def markB(x,y,s=1,fg=ENC,acc=TC):
    g=f'<g transform="translate({x},{y}) scale({s})">'
    g+=f'<rect x="0" y="0" width="12" height="80" fill="{fg}"/>'
    g+=f'<path d="M12,40 L46,0 H60 L26,40 L60,80 H46 Z" fill="{fg}"/>'
    g+=f'<path d="M66,0 H74 A40,40 0 0 1 74,80 H66 Z M78,12 V68 A28,28 0 0 0 78,12 Z" fill="{acc}" fill-rule="evenodd"/>'
    return g+'</g>'
# C — Module claustra : arche dans un carré de brique
def markC(x,y,s=1,fg=TC):
    g=f'<g transform="translate({x},{y}) scale({s})">'
    g+=f'<path d="M0,0 H80 V80 H0 Z {arch(22,80,36,58)}" fill="{fg}" fill-rule="evenodd"/>'
    for c in range(4): g+=f'<circle cx="{14+c*17.3}" cy="11" r="3.2" fill="{CH}"/>'
    return g+'</g>'
for n,m in [('A',markA),('B',markB),('C',markC)]:
    mk=m(20,22)
    save(f'KDemi_logo_{n}',mk+word(150 if n=='B' else 100,82,ENC),(450 if n=='B' else 420),130,CH)
    save(f'KDemi_logo_{n}_inverse',(markA(20,22,fg=TC,inner=IRO) if n=='A' else markB(20,22,fg=CH) if n=='B' else markC(20,22))+word(150 if n=='B' else 100,82,CH),(450 if n=='B' else 420),130,ENC)
    save(f'KDemi_symbole_{n}',m(10,10),(110 if n=='B' else 100),100)
