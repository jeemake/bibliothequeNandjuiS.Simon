import fal_client,urllib.request,sys
p=("Turn this massing elevation (rendered from the IFC model) into a photorealistic street photograph of the shopfront of a small library on the ground floor of a plain four-storey residential apartment building in Abidjan, Cote d'Ivoire. "
"Keep the exact storefront width and the exact position of the entrance: the arched glazed double door sits slightly right of centre, framed by a tall terracotta-plaster portal. "
"Left of the entrance: one large glazed shop window with a slim matte black steel frame, showing the warm 2700 K lit interior with wooden shelves and the oiled iroko book tree with its flared terracotta canopy. "
"The two other arched bays are filled with terracotta lattice claustra. A sand lime-plaster fascia band runs above the shopfront, blank. A shallow oiled iroko slatted canopy over the terrace, masonry planters with tropical plants, small café tables. "
"Above: three plain residential floors in off-white painted render with simple concrete balconies, black steel railings, a few air-conditioner units and laundry, slightly weathered, ordinary Abidjan street, sidewalk and kerb, dusk blue hour. "
"Camera at eye level from across the street, slight perspective, show the ground floor and the floors above. No people, no text, no letters, no signage, no logos, no gradients, no CGI look.")
u=fal_client.upload_file('base/devanture_input.png')
r=fal_client.subscribe('fal-ai/nano-banana-pro/edit',arguments={'prompt':p,'image_urls':[u],'num_images':1,'aspect_ratio':'4:3','resolution':'2K'})
urllib.request.urlretrieve(r['images'][0]['url'],'visuels/devanture.png')
open('cost_tally.txt','a').write(f'nano-banana-pro/edit 2K devanture {sys.argv[1]} 0.15\n')
