import fal_client, urllib.request, sys, concurrent.futures as cf
base="/workspace/decimo_final/repo/v5/vues_rendu/"
COMMON=("This image is a 3D view rendered directly from the IFC BIM model of a small existing ground-floor library (6.78 x 7.68 m unit under a residential building, Abidjan). "
"Turn it into a warm, cosy, photorealistic lifestyle photograph WITHOUT changing the architecture: keep the exact same camera, framing, perspective and lens; keep every wall, opening, arch, door, column, ceiling, pergola, shelf and piece of furniture exactly where it is, same size, shape and count. "
"Do not add windows, doors, balconies, columns, benches or rooms. Do not move or resize anything. "
"Materials: sand-coloured lime plaster, terracotta earth plaster, oiled iroko wood, light terrazzo floor, matte black steel frames, terracotta clay lattice claustra with Adinkra circle motifs, indigo cotton accents, raffia. "
"Lighting is warm 2700 K, soft and golden, cosy and inviting, never cold, never minimalist or brutalist. Realistic books. Natural, editorial Instagram-style photo, slight film grain, no watermark, no logos. ")
V={
"G1_rue_crepuscule":("01_devanture_rue_pieton_ombre.png",
 "Blue-hour dusk, just after sunset, sky deep blue-violet. The shop glows warmly from inside. Keep the wooden pergola with its curved slatted roof, its four posts, the two small round terrace tables with chairs, the two terracotta jars on white plinths, the three arched bays with terracotta claustra and the central arched glazed door exactly as drawn. "
 "Under the pergola slats hang a few strands of warm 2700 K festoon light bulbs (guinguette string lights) glowing softly. "
 "The green blocks along the façade are LOW WHITE MASONRY PLANTERS (not benches, nobody sits on them) generously planted with real tropical plants: fiddle-leaf fig (ficus lyrata) and bird of paradise (strelitzia) with large glossy leaves. "
 "Through the left arched shop window, behind the claustra, a warm lit reading nook with a small stack of books on display. "
 "The pergola roof slats follow the gentle double wave drawn in the model (not a flat roof). Planting exists ONLY in the low planters directly along the façade behind the tables, between the façade and the tables: there are no planters, plants or pots beyond the two outer pergola posts, outside the pergola there is only the plain pavement and the existing neighbouring walls as drawn. There are no benches and no seat cushions along the façade: only the planters. Nobody sits inside the shop window. The upper windows keep their simple square openings with no visible mullions. The pale volume above is the existing residential building: plain off-white painted concrete wall with exactly the two small square window openings shown (same size and position), NO balconies, nothing added. The brown cylinder at the top right is NOT an object: it is the leafy canopy of the street tree, render it entirely as dark green tree foliage. "
 "Two or three young adults (aged 20 to 25, casual colourful clothes) sit at the terrace tables reading and one takes a photo with a phone; faces turned away or in soft shadow, not identifiable. No text, no signage."),
"G2_vitrine_coin_lecture":("05_coin_lecture_ombre.png",
 "Late afternoon golden light filtering through the claustra, casting patterned Adinkra shadows. "
 "The low wooden podium under the tall arched window (behind the round table) is dressed as a cosy window seat; it is exactly as wide as that arched window and stops at its edges, it does NOT extend along the left wall: below the oval window on the left there is only plain lime-plaster wall down to the floor, no seat, no ledge, no cushions there: a thick terracotta cushion, a folded indigo and terracotta handwoven throw, a few raffia and indigo cushions, a small brass reading lamp with a warm glow, and a neat stack of 5 books with a small handwritten kraft card on top reading 'coup de cœur'. "
 "Keep the round table, the shelves full of books on the right, the terracotta pendant lamp at the top and the indigo pouf at the bottom right. No people."),
"G3_accueil_vignette":("06_accueil_vignette_ombre.png",
 "Close lifestyle vignette of the iroko reception counter. Keep the counter, its light top, the blue chair back behind it and the arched claustra window on the right exactly as drawn. "
 "The dark cube on the counter becomes a dark iroko wooden box holding a wrapped stack. The white sheet on the counter becomes a small stack of kraft paper bookmarks next to a wooden rubber date stamp and an indigo ink pad; one bookmark in front is freshly stamped with a round stamp reading 'DECIMO' and '15 OCT 2026'. "
 "On the counter, a small raffia basket of 'blind date' surprise books, each wrapped in brown kraft paper tied with twine, with three handwritten words in black marker on each, for example 'mer · secret · Abidjan'. "
 "On the terracotta wall on the left, a long narrow oiled iroko picture ledge at eye level holds a row of kraft and cream cards handwritten in French in blue and black ink (readers' favourite book recommendations, short sentences, a first name signature, no printed headers) leaning against the wall, a couple of book covers among them. "
 "Warm 2700 K light, shallow depth of field. No people."),
"G4_arbre_photo":("02_interieur_depuis_entree_ombre.png",
 "Evening, warm 2700 K. The book tree is the key object: a freestanding CYLINDRICAL trunk about 1 m in diameter made of circular iroko shelves full of books (round in plan, curved shelves, like a tree trunk), standing in the middle of the room in front of the back wall, rising into a smooth flared canopy made of smooth oiled iroko wood veneer (warm reddish-brown solid wood, NOT woven, NOT straw, NOT rattan, NOT bamboo). Keep it and LED ring inside the indigo ceiling oculus, the two arched iroko niches behind it, the round table and terracotta armchairs, the terracotta pendant lamp, the long low iroko console on the left and the white counter at the bottom right exactly as drawn. The tall green box at the right edge is NOT furniture: it is a single large potted ficus lyrata plant, about 1.6 m tall, in a round terracotta pot; there is no green cabinet, panel or box. The long low iroko console on the left keeps a closed solid front. "
 "Add two young adults (aged 20 to 25, clearly adults, casual, one with braids, colourful outfits) seen from behind standing near the round table: one holds a phone up to photograph the book tree and the glowing oculus, the other holds a kraft-wrapped book. Faces not visible, not identifiable. No text."),
}
def run(k):
    f,extra=V[k]
    u=fal_client.upload_file(base+f)
    r=fal_client.subscribe('fal-ai/nano-banana-pro/edit',arguments={'prompt':COMMON+extra,'image_urls':[u],'num_images':1,'aspect_ratio':'auto','resolution':'2K'})
    tag=sys.argv[0]
    n=len([l for l in open('/workspace/decimo_da/cost_tally.txt') if 'genz' in l])
    out=f"{k}_try{n+1}.png"; urllib.request.urlretrieve(r['images'][0]['url'],out)
    open('/workspace/decimo_da/cost_tally.txt','a').write(f'nano-banana-pro/edit 2K genz {k} 0.15\n')
    return out
ks=sys.argv[1:] or list(V)
with cf.ThreadPoolExecutor(4) as ex:
    for o in ex.map(run,ks): print(o)
