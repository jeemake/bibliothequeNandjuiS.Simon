import sys,numpy as np
exec(open('repo/scripts/rendu_ifc.py').read().split('fig = plt.figure')[0].replace('sys.argv[1]','"repo/DECIMO_ESQ_V4.ifc"'))
def one(name,keep,elev,azim,xl,yl,zl):
    fig=plt.figure(figsize=(16,10)); ax=fig.add_subplot(111,projection='3d'); ax.set_proj_type('persp',focal_length=0.6)
    view(ax,keep,elev,azim,xl,yl,zl,''); fig.subplots_adjust(0,0,1,1); fig.savefig('base/'+name,dpi=100); plt.close(fig)
one('ext.png',lambda e,v:v[:,2].min()<3.4,8,-80,(-0.6,7.0),(-3.2,7.6),(0,3.5))
one('int_rdc.png',lambda e,v:v[:,2].min()<3.25 and not (e.is_a("IfcWall") and v[:,1].max()<0.2) and v[:,1].min()>-0.3 and v[:,2].max()<3.6,22,-70,(-0.3,7.0),(0,7.8),(0,3.4))
one('int_r1.png',lambda e,v:v[:,2].min()<3.25 and not (e.is_a("IfcWall") and v[:,0].max()<0.3) and v[:,1].min()>-0.3 and v[:,2].max()<3.6,30,200,(-0.3,7.0),(0,7.8),(0,3.4))
one('plan.png',lambda e,v:v[:,2].min()<1.2,89,-90,(-0.6,7.0),(-3.2,7.8),(0,3.5))
