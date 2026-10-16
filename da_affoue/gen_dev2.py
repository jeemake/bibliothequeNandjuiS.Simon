import fal_client,urllib.request,sys
p=("Turn this massing elevation (rendered from the IFC model) into a photorealistic street photograph of a small library shopfront on the ground floor of a plain four-storey residential apartment building in Abidjan. "
"The shopfront has EXACTLY these openings, left to right, matching the input positions and sizes, and nothing else: "
"(1) far left, one large arched opening as a shop window, slim matte black steel frame, showing the warm 2700 K lit interior with oiled iroko shelves and the iroko book tree with a flared terracotta canopy; "
"(2) one small narrow arched bay filled with terracotta lattice claustra; "
"(3) the arched glazed double entrance door slightly right of centre, framed by a tall terracotta-plaster portal; "
"(4) right of the door, one arched bay filled with terracotta lattice claustra. Solid sand lime-plaster wall between openings. "
"No other bays. No pergola, no posts or columns in front of the facade. Only a very shallow flat matte black steel canopy (40 cm deep) above the openings. A blank sand lime-plaster fascia band above. Low masonry planters with tropical plants at the base. "
"Above: three plain residential floors in off-white painted render with simple concrete balconies, black steel railings, a few air-conditioner units, slightly weathered; neighbouring buildings at both sides; sidewalk and kerb, dusk blue hour. "
"Wide frame from across the street at eye level: the whole building is visible, ground floor and all three floors above, with some sky. No people, no text, no letters, no signage, no logos, no gradients, no CGI look.")
u=fal_client.upload_file('base/devanture_input_v2.png')
r=fal_client.subscribe('fal-ai/nano-banana-pro/edit',arguments={'prompt':p,'image_urls':[u],'num_images':1,'aspect_ratio':'3:2','resolution':'2K'})
urllib.request.urlretrieve(r['images'][0]['url'],'visuels/devanture_v2.png')
open('cost_tally.txt','a').write(f'nano-banana-pro/edit 2K devanture {sys.argv[1]} 0.15\n')
