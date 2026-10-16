import fal_client,urllib.request
T=['base/plan.png']+[f'repo/textures/{t}.png' for t in ['claustra_terre_cuite','iroko_huile','gres_cerame_sable','enduit_chaux_sable','tissu_terre_cuite','acier_noir_mat']]
urls=[fal_client.upload_file(t) for t in T]
p=("Top-down flat-lay photograph of a physical architecture material sample board on a raw lime-plaster table. Place real physical samples matching the reference textures (images 2-7): a terracotta claustra lattice block, an oiled iroko wood plank, a sand porcelain stoneware tile, a sand lime plaster sample, a folded terracotta wool fabric swatch, a matte black steel strip; plus an indigo hand-dyed cotton swatch, a woven raffia sample, a strelitzia leaf and a fern frond. "
"In the top-left corner, a small printed copy of the floor plan (image 1) as a paper sheet. Grid-like restrained composition, soft daylight from the left, precise small shadows. No text, no labels, no logos, no gradients.")
r=fal_client.subscribe('fal-ai/nano-banana-pro/edit',arguments={'prompt':p,'image_urls':urls,'num_images':1,'aspect_ratio':'3:2','resolution':'2K'})
urllib.request.urlretrieve(r['images'][0]['url'],'visuels/mood.png')
open('cost_tally.txt','a').write('nano-banana-pro/edit 2K mood v2 (retry) 0.15\n')
