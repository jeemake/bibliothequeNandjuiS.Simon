# Retouche locale du rendu 01 (sans fal) : efface les balcons inventés sur le bâtiment voisin (IFC = mur plein)
from PIL import Image, ImageFilter
import numpy as np, warnings; warnings.simplefilter('ignore')
im=np.array(Image.open('rendus/01_devanture_fal_brut.png').convert('RGB')).astype(float)
H,W,_=im.shape
x0=1812; ymax=820; ramp=90
mx=im.max(2);mn=im.min(2);sat=(mx-mn)/(mx+1)
ref=im[ymax+ramp:ymax+ramp+40,x0:]; rs=sat[ymax+ramp:ymax+ramp+40,x0:]
xs=np.arange(x0,W); cols=[]
for c in range(3):
    v=np.where(rs<0.12,ref[...,c],np.nan); med=np.nanmedian(v,axis=0)
    ok=~np.isnan(med); cols.append(np.interp(xs,xs[ok],med[ok]))
col=np.stack(cols,1); k=np.ones(61)/61
col=np.stack([np.convolve(np.pad(col[:,c],30,mode='edge'),k,'valid') for c in range(3)],1)
fill=np.zeros_like(im); fill[:,x0:]=col[None]
fill[:ymax+ramp,x0:]*=np.linspace(1.02,1.0,ymax+ramp)[:,None,None]
np.random.seed(1); fill+=np.random.normal(0,1.3,fill.shape)
m=np.zeros((H,W)); m[:ymax,x0:]=1
for i in range(ramp): m[ymax+i,x0:]=((ramp-i)/(ramp+1))**0.8
m[:,x0:x0+6]*=np.linspace(0,1,6)[None,:]
woody=(sat>0.26)&((im[...,0]-im[...,2])>30)
zone=np.zeros((H,W),bool); zone[505:,x0:2170]=True
w=Image.fromarray(((woody&zone)*255).astype(np.uint8))
w=w.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(9))
wz=(np.array(w)>0)&zone
post=np.zeros((H,W),bool); post[:,2072:2116]=True
wz[742:,:]&=post[742:,:]
m[wz]=0
m=np.array(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)))/255.
out=im*(1-m[...,None])+np.clip(fill,0,255)*m[...,None]
o=Image.fromarray(out.astype(np.uint8)); o.save('rendus/01_devanture.png')
o.resize((1400,871)).save('/tmp/r1fix9.jpg'); o.crop((1780,480,2300,1000)).save('/tmp/zoom7.png')
