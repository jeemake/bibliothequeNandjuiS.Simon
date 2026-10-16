import fal_client,sys,json,urllib.request
COMMON=("Keep the exact geometry, proportions, camera angle and layout of the input massing model: same walls, openings, furniture positions. "
"Photorealistic architectural photograph, natural light, restrained contemporary West African design, Abidjan humid tropical climate. "
"Materials: lime plaster in warm sand colour (#E6D6BF), terracotta claustra screens with lattice pattern, oiled iroko wood, matte black steel, sand porcelain stoneware floor, terracotta wool textiles, small accents of indigo hand-dyed cotton. "
"No text, no lettering, no signage text, no logos, no people, no gradients, no CGI look, no oversaturation.")
J={
'ext':"Turn this IFC massing render into an exterior street photograph of the small library facade at late afternoon: the parametric iroko timber pergola with wavy slats over the covered terrace, three tall arched openings filled with terracotta lattice claustra, central arched glazed double door framed in terracotta, masonry planters with tropical plants (strelitzia, dracaena, ferns), small round tables with curved wood chairs on the terrace, a bougainvillea, red laterite ground at the edge, soft cast shadows from the slats. Remove the cut-away box edges; make it a real street.",
'int_rdc':"Turn this IFC cut-away render into an interior photograph at eye level of the ground-floor reading room: the curved arched entry door, terracotta claustra baies filtering patterned sunlight onto the sand stoneware floor, the book tree at the back (an iroko trunk with circular shelves crowned by a flared terracotta canopy), iroko shelving, round tables, curved iroko chairs, a long upholstered bench in terracotta wool, black steel track lights. Calm, warm, quiet.",
'int_r1':"Turn this IFC cut-away render into an interior photograph of the upper reading plateau (R+1) of the same library, built on the same footprint: view looking down toward the flared terracotta canopy of the book tree rising through a double-height void with a black steel and iroko guardrail, low iroko shelves along the walls, a study table with paper lamps, a reading armchair in terracotta wool, lime plaster vault-like curved niches, daylight from the claustra, a potted ficus lyrata.",
'mood':"Turn this IFC floor plan into a top-down flat-lay material moodboard photographed on a lime-plaster table, arranged following the plan zones: a terracotta claustra block sample, an oiled iroko plank, a sand porcelain stoneware tile, a matte black steel strip, a sand lime plaster sample, a terracotta wool fabric swatch, an indigo hand-dyed cotton swatch, a woven raffia sample, a strelitzia leaf and a fern frond, a brass-free black steel lamp detail. Soft daylight, real samples, clean composition, small precise shadows.",
}
SRC={'ext':'ext','int_rdc':'int_rdc','int_r1':'int_r1','mood':'plan'}
for k in sys.argv[1:]:
    url=fal_client.upload_file(f'base/{SRC[k]}.png')
    r=fal_client.subscribe('fal-ai/nano-banana-pro/edit',arguments={'prompt':J[k]+' '+COMMON,'image_urls':[url],'num_images':1,'aspect_ratio':'3:2' ,'resolution':'2K'})
    u=r['images'][0]['url']; urllib.request.urlretrieve(u,f'visuels/{k}.png')
    open('cost_tally.txt','a').write(f'nano-banana-pro/edit 2K {k} 0.15\n'); print(k,'ok')
