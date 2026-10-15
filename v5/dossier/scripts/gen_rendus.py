import fal_client, urllib.request, sys, concurrent.futures as cf
base="/workspace/decimo_final/pr3/v5/vues_rendu/"
COMMON=("This image is a 3D view rendered directly from the IFC BIM model. Turn it into a photorealistic architectural photograph WITHOUT changing anything: "
"keep the exact same camera, framing, perspective and lens, and keep every element exactly where it is, with the same size, shape and count: walls, openings, arches, doors, columns, ceiling, furniture, shelves, lamps, plants. "
"Do not add, remove, move or resize any architectural element or furniture. Do not add windows, doors, bays, columns or rooms. Only replace the flat colours with real materials and natural light. "
"Materials: sand-coloured lime plaster walls, terracotta earth plaster, oiled iroko wood (shelves, furniture, panelling), light terrazzo floor, matte black steel frames, terracotta clay lattice claustra, indigo accents, warm 2700 K lighting. "
"Soft West African daylight, humid tropical Abidjan atmosphere, realistic books on the shelves. No people, no text, no letters, no signage, no logos, no watermark. ")
V={
"01_devanture":("01_devanture_rue_pieton_ombre.png","Street view of the shopfront of a small ground-floor library under a residential building in Abidjan: keep the wooden pergola, its posts, the terrace tables and chairs, the planters and the bays exactly as drawn. The blank white volume above is the existing residential building: render it as plain off-white painted concrete residential floors with simple balconies, kept in the same outline. Late afternoon light."),
"02_interieur_entree":("02_interieur_depuis_entree_ombre.png","Interior of the small reading room seen from the entrance. Keep in the right foreground the low white reception counter top and, behind it, the large green tropical plant exactly where the green block is; keep the tall white wall pier on the right. In the background keep the solid iroko book tree trunk with its smooth flared iroko canopy (solid wood, not lattice) inside the indigo ceiling oculus, and the two arched iroko niches behind it."),
"03_interieur_devanture":("03_interieur_vers_devanture_ombre.png","Interior looking back towards the arched glazed entrance door and the lattice shop window, daylight coming in through the claustra casting patterned shadows."),
"04_arbre":("04_arbre_a_livres_ombre.png","Close view of the sculptural iroko book tree rising to a flared canopy inside an indigo ceiling oculus with a warm LED ring."),
"05_coin_lecture":("05_coin_lecture_ombre.png","Reading corner by the arched shop window with terracotta lattice claustra, round table, bookshelves full of books, indigo pouf."),
}
def run(k):
    f,extra=V[k]
    u=fal_client.upload_file(base+f)
    r=fal_client.subscribe('fal-ai/nano-banana-pro/edit',arguments={'prompt':COMMON+extra,'image_urls':[u],'num_images':1,'aspect_ratio':'auto','resolution':'2K'})
    out=f"rendus/{k}.png"; urllib.request.urlretrieve(r['images'][0]['url'],out)
    open('/workspace/decimo_da/cost_tally.txt','a').write(f'nano-banana-pro/edit 2K rendu final {k} 0.15\n')
    return out
ks=sys.argv[1:] or list(V)
with cf.ThreadPoolExecutor(5) as ex:
    for o in ex.map(run,ks): print(o)
