exec(open('repo/scripts/rendu_ifc.py').read().split('fig = plt.figure')[0].replace('sys.argv[1]','"repo/DECIMO_ESQ_V4.ifc"'))
from matplotlib.patches import Rectangle
fig=plt.figure(figsize=(12,16));ax=fig.add_subplot(111,projection='3d');ax.set_proj_type('persp',focal_length=1.2)
view(ax,lambda e,v:v[:,2].min()<3.4 and not any(k in (e.Name or '') for k in ('Pergola','Poteau')) and v[:,1].min()>-0.5,6,-90,(-0.6,7.0),(-3.2,7.6),(0,3.5),'')
fig.subplots_adjust(0,0,1,1);fig.savefig('base/dev_rdc_v2.png',dpi=100)
