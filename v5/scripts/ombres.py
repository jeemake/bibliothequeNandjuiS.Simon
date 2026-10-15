"""Ombres portées des planches A01-A06 : soleil conventionnel, aplat gris neutre, contours nets.

Calcul exact par carte d'ombres (OpenGL hors écran, projection orthogonale) sur la géométrie IFC
réellement dessinée dans la vue : la surface vue en premier plan est ombrée si un autre objet
s'interpose entre elle et le soleil. Le masque est ensuite converti en polygones (isoligne 0,5)
et peint sous les traits, objet par objet, dans l'ordre du peintre.

Soleil défini dans le repère de la vue (u, v, profondeur d) : un point situé à une profondeur t
devant la surface qui reçoit l'ombre la projette de (ku·t, kv·t) sur le dessin.
  plan (et plan réfléchi) : 45° depuis le haut-gauche, ombres courtes (0,25 m par m de hauteur) ;
  coupes et élévations (mode "elev" façade, "int" intérieur) : 45° depuis le haut-gauche, profondeur d'ombre = profondeur réelle
  du débord (convention 1:1 de la géométrie descriptive).
"""
import numpy as np
import shapely
from shapely.geometry import Polygon
from scipy import ndimage
import contourpy

import dessin2d as D

OMBRE_ALPHA = 0.15          # noir à 15 % : aplat neutre, sans dégradé
SOLEIL_PLAN = (0.25, -0.25)
SOLEIL_ELEV = (1.0, -1.0)

VS = """
#version 330
uniform mat4 mvp; uniform mat4 lmvp;
in vec3 in_pos;
out vec3 v_pos; out vec4 v_l;
void main(){ gl_Position = mvp*vec4(in_pos,1.0); v_pos = in_pos; v_l = lmvp*vec4(in_pos,1.0); }"""
FS_DEPTH = """
#version 330
out vec4 o; void main(){ o = vec4(1.0); }"""
FS_MASK = """
#version 330
uniform sampler2D smap; uniform vec3 to_sun; uniform float bias; uniform float texel; uniform float maxd;
in vec3 v_pos; in vec4 v_l;
out vec4 o;
void main(){
  vec3 n = normalize(cross(dFdx(v_pos), dFdy(v_pos)));
  if (n.z > 0.0) n = -n;                       // normale tournée vers l'observateur (profondeur décroissante)
  float ndl = dot(n, to_sun);
  vec3 p = v_l.xyz / v_l.w * 0.5 + 0.5;
  float sh = 0.0;
  if (ndl <= 0.02) sh = 1.0;                   // face tournée à l'opposé du soleil
  else {
    float b = bias + texel * 1.5 * sqrt(max(1.0 - ndl*ndl, 0.0)) / max(ndl, 0.05);
    float d = texture(smap, p.xy).r;
    if (p.z - b > d && p.z - d < maxd) sh = 1.0;   // occultant pas trop éloigné de la surface reçue
  }
  o = vec4(sh, 1.0, 0.0, 1.0);
}"""


def _ortho(lo, hi):
    m = np.eye(4)
    for i in range(3):
        m[i, i] = 2 / (hi[i] - lo[i]); m[i, 3] = -(hi[i] + lo[i]) / (hi[i] - lo[i])
    return m


def triangles_vue(R, vue, porteurs):
    """Triangles en repère vue (u, v, d) : récepteurs = tout ce qui est dessiné, porteurs = ce qui porte ombre."""
    rec, por = [], []
    M = np.stack([vue.u, vue.v, vue.d])
    for r in R:
        if r["role"] == "vitrage":
            continue
        e = r["e"]
        T = np.concatenate([e["verts"][fc] for fc, _ in e["items"]]) if e["items"] else np.zeros((0, 3, 3))
        if vue.coupe is not None and len(T):
            T = D.couper_demi_espace(T, *vue.coupe)
        if not len(T):
            continue
        Tv = T @ M.T
        rec.append(Tv)
        if porteurs(r):
            por.append(Tv)
    cat = lambda L: np.concatenate(L).astype("f4") if L else np.zeros((0, 3, 3), "f4")
    return cat(rec), cat(por)


def masque(rec, por, xlim, ylim, k, px_m=220, smap=8192, portee=1e3):
    import rendu_gl
    ctx = rendu_gl.ctx()
    L = np.array([k[0], k[1], 1.0]); L /= np.linalg.norm(L)        # sens de propagation de la lumière
    a = np.cross(L, [0, 0, 1.0] if abs(L[2]) < 0.9 else [1.0, 0, 0]); a /= np.linalg.norm(a)
    b = np.cross(L, a)
    B = np.stack([a, b, L])                                          # repère lumière (profondeur = L)
    allp = np.concatenate([rec.reshape(-1, 3), por.reshape(-1, 3)]) @ B.T
    lo, hi = allp.min(0) - 0.05, allp.max(0) + 0.05
    lb = np.eye(4); lb[:3, :3] = B
    lmvp = (_ortho(lo, hi) @ lb).astype("f4")
    prog_d = ctx.program(vertex_shader=VS, fragment_shader=FS_DEPTH)
    prog_m = ctx.program(vertex_shader=VS, fragment_shader=FS_MASK)
    # passe 1 : carte de profondeur depuis le soleil
    dtex = ctx.depth_texture((smap, smap))
    fbo = ctx.framebuffer(depth_attachment=dtex)
    fbo.use(); fbo.clear(depth=1.0)
    ctx.enable(ctx.DEPTH_TEST); ctx.disable(ctx.CULL_FACE)
    if len(por):
        vbo = ctx.buffer(por.reshape(-1, 3).tobytes())
        vao = ctx.vertex_array(prog_d, [(vbo, "3f", "in_pos")])
        prog_d["mvp"].write(lmvp.T.tobytes())
        vao.render()
        vao.release(); vbo.release()
    # passe 2 : vue orthogonale, masque d'ombre sur la surface vue
    W_ = int((xlim[1] - xlim[0]) * px_m); H_ = int((ylim[1] - ylim[0]) * px_m)
    dmin, dmax = rec[..., 2].min() - 0.1, rec[..., 2].max() + 0.1
    mvp = _ortho((xlim[0], ylim[0], dmin), (xlim[1], ylim[1], dmax))
    mvp = mvp.astype("f4")
    col = ctx.texture((W_, H_), 4); dep = ctx.depth_texture((W_, H_))
    fbo2 = ctx.framebuffer(color_attachments=[col], depth_attachment=dep)
    fbo2.use(); fbo2.clear(0, 0, 0, 0, depth=1.0)
    vbo = ctx.buffer(rec.reshape(-1, 3).tobytes())
    vao = ctx.vertex_array(prog_m, [(vbo, "3f", "in_pos")])
    prog_m["mvp"].write(mvp.T.tobytes()); prog_m["lmvp"].write(lmvp.T.tobytes())
    prog_m["to_sun"].value = tuple(-L)
    texel = float(max(hi[0] - lo[0], hi[1] - lo[1]) / smap)
    prog_m["texel"].value = texel / (hi[2] - lo[2])
    prog_m["bias"].value = 0.004 / (hi[2] - lo[2])
    prog_m["maxd"].value = float(portee / (hi[2] - lo[2]))
    dtex.compare_func = ""
    dtex.use(0); prog_m["smap"].value = 0
    vao.render()
    img = np.frombuffer(col.read(), "u1").reshape(H_, W_, 4)
    for o in (vao, vbo, col, dep, fbo2, fbo, dtex, prog_d, prog_m):
        o.release()
    m = (img[..., 0] > 127) & (img[..., 1] > 127)
    m = ndimage.binary_opening(m, iterations=1)                     # supprime l'acné d'ombre
    lab, n = ndimage.label(m)
    if n:
        taille = ndimage.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, 1 + np.where(taille >= 0.0004 * px_m * px_m)[0])   # taches < 2 × 2 cm écartées
    lab, n = ndimage.label(~m)                                        # petites taches de lumière dans une ombre
    if n:
        taille = ndimage.sum(~m, lab, range(1, n + 1))
        m = m | np.isin(lab, 1 + np.where(taille < 0.012 * px_m * px_m)[0])  # (< 11 × 11 cm) comblées : aplat lisible
    return m


def polygones(m, xlim, ylim):
    H_, W_ = m.shape
    x = np.linspace(xlim[0], xlim[1], W_); y = np.linspace(ylim[0], ylim[1], H_)
    z = np.pad(m.astype(float), 1)
    x = np.concatenate([[x[0] - 1e-6], x, [x[-1] + 1e-6]]); y = np.concatenate([[y[0] - 1e-6], y, [y[-1] + 1e-6]])
    gen = contourpy.contour_generator(x, y, z, fill_type=contourpy.FillType.OuterOffset)
    pts, offs = gen.filled(0.5, 2.0)
    polys = []
    for P, O in zip(pts, offs):
        rings = [P[O[i]:O[i + 1]] for i in range(len(O) - 1)]
        if len(rings[0]) >= 4:
            polys.append(Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]).buffer(0))
    if not polys:
        return None
    g = shapely.union_all(polys).simplify(0.6 / 220)
    return g


PORTEE_INT = 1.0   # m le long du rayon : en intérieur, seuls les objets proches de la paroi y portent ombre
PORTEE_FACADE = 1.6   # façade : débords, tableaux, claustras, marquise ; pas de taches lointaines au fond des baies


def calculer_ombres(R, vue, xlim, ylim, mode="plan", px_m=220):
    """Polygones d'ombre (shapely, repère du dessin) pour les résultats R d'une vue."""
    if mode == "plan":
        k, porte = SOLEIL_PLAN, (lambda r: r["role"] not in ("sol", "sol_ext", "trottoir"))
    elif mode == "int":
        # coupes et élévations intérieures : l'enveloppe (porteurs, cloisons, plafonds, sols, revêtements) reçoit
        # les ombres mais n'en porte pas, sinon les retours de murs hors cadre noieraient toute l'élévation
        k = SOLEIL_ELEV
        porte = lambda r: r["role"] not in ("structure", "cloison", "plafond", "sol", "revetement", "arbre", "logements",
                                            "fenetre_logt", "voisin", "sol_ext", "trottoir")
    else:
        k = SOLEIL_ELEV
        # en élévation, le cadre coupé (murs, dalles, plafonds) ne fait pas écran : le soleil vient du côté de l'observateur
        porte = lambda r: not (r["coupe"] is not None and r["role"] in ("structure", "cloison", "plafond", "sol", "revetement")) \
            and r["role"] not in ("arbre", "logements", "fenetre_logt")
    rec, por = triangles_vue(R, vue, porte)
    if not len(rec):
        return None
    m = masque(rec, por, xlim, ylim, k, px_m=px_m, portee={"int": PORTEE_INT, "elev": PORTEE_FACADE}.get(mode, 1e3))
    return polygones(m, xlim, ylim)
