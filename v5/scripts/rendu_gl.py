"""Moteur de rendu OpenGL hors écran (EGL / Mesa llvmpipe) pour les vues IFC.

- vue ombrée : couleurs matériaux, soleil avec carte d'ombres, ciel/sol hémisphérique,
  occlusion ambiante par masquage de profondeur, matériaux « lumière » émissifs, verre transparent ;
- vue au trait : silhouettes (changement d'objet, saut de profondeur) et arêtes vives (normales).
Perspective (fov vertical) ou orthographique (axonométries).
"""
import numpy as np
import moderngl
from PIL import Image
from scipy import ndimage

_CTX = None


def ctx():
    global _CTX
    if _CTX is None:
        _CTX = moderngl.create_standalone_context(backend="egl", libegl="libEGL.so.1", require=330)
    return _CTX


def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = map(lambda a: np.asarray(a, float), (eye, target, up))
    fwd = target - eye; fwd /= np.linalg.norm(fwd)
    side = np.cross(fwd, up); side /= np.linalg.norm(side)
    u = np.cross(side, fwd)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = side, u, -fwd
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspective(fovy_deg, aspect, near, far):
    t = 1 / np.tan(np.radians(fovy_deg) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = t / aspect, t
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def ortho(w, h, near, far):
    m = np.eye(4)
    m[0, 0], m[1, 1] = 2 / w, 2 / h
    m[2, 2], m[2, 3] = -2 / (far - near), -(far + near) / (far - near)
    return m


VS = """
#version 330
uniform mat4 mvp; uniform mat4 view; uniform mat4 light_mvp;
in vec3 in_pos; in vec3 in_nrm; in vec4 in_col; in float in_id;
out vec3 v_nrm; out vec4 v_col; out vec3 v_vnrm; out vec4 v_lpos; out vec3 v_wpos; flat out float v_id;
void main(){
  gl_Position = mvp*vec4(in_pos,1.0);
  v_nrm = in_nrm; v_vnrm = mat3(view)*in_nrm; v_col = in_col; v_id = in_id;
  v_lpos = light_mvp*vec4(in_pos,1.0); v_wpos = in_pos;
}"""
FS = """
#version 330
uniform vec3 sun; uniform vec3 sun_col; uniform vec3 sky_col; uniform vec3 gnd_col; uniform sampler2D shadow;
uniform int use_shadow; uniform vec3 eye; uniform float emissive_lum; uniform vec3 fill_dir; uniform float fill_k;
in vec3 v_nrm; in vec4 v_col; in vec3 v_vnrm; in vec4 v_lpos; in vec3 v_wpos; flat in float v_id;
layout(location=0) out vec4 o_col; layout(location=1) out vec4 o_nrm; layout(location=2) out float o_id;
void main(){
  vec3 n = normalize(v_nrm);
  vec3 vdir = normalize(eye - v_wpos);
  if (dot(n, vdir) < 0.0) n = -n;
  float sh = 1.0;
  if (use_shadow == 1){
    vec3 p = v_lpos.xyz/v_lpos.w*0.5+0.5;
    if (p.x>0.0 && p.x<1.0 && p.y>0.0 && p.y<1.0){
      float acc = 0.0;
      for (int i=-1;i<=1;i++) for (int j=-1;j<=1;j++){
        float d = texture(shadow, p.xy + vec2(i,j)/4096.0).r;
        acc += (p.z - 0.0015 > d) ? 0.0 : 1.0;
      }
      sh = acc/9.0;
    }
  }
  vec3 base = v_col.rgb;
  vec3 lum;
  bool emis = (base.r > 0.98 && base.g > 0.86 && base.g < 0.92 && base.b > 0.66 && base.b < 0.72);
  if (emis) lum = base*emissive_lum;
  else {
    float hemi = 0.5 + 0.5*n.z;
    vec3 amb = mix(gnd_col, sky_col, hemi);
    float diff = max(dot(n, sun), 0.0)*sh;
    float fill = max(dot(n, fill_dir), 0.0)*fill_k;
    lum = base*(amb + sun_col*diff + vec3(fill));
  }
  o_col = vec4(lum, v_col.a);
  o_nrm = vec4(normalize(v_vnrm)*0.5+0.5, 1.0);
  o_id = v_id;
}"""
VS_D = """
#version 330
uniform mat4 light_mvp; in vec3 in_pos;
void main(){ gl_Position = light_mvp*vec4(in_pos,1.0); }"""
FS_D = """
#version 330
void main(){}"""


def _normals(tri):
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    return n / (np.linalg.norm(n, axis=1)[:, None] + 1e-12)


def render(tri, col, ids, cam, size=(2560, 1600), ss=2, sun_dir=(-0.35, -0.55, 0.76), shadows=True,
           sky=(0.78, 0.80, 0.84), ground=(0.42, 0.37, 0.32), sun_col=(1.0, 0.93, 0.82), emissive=1.15,
           fill_dir=(0.3, -0.8, 0.5), fill_k=0.0, background=(0.93, 0.91, 0.88), exposure=1.0, ao=0.55):
    """cam : dict(position, target, up, fov_v | ortho_h, near, far). Renvoie (image ombrée PIL, image traits PIL, buffers)."""
    c = ctx()
    W, H = size[0] * ss, size[1] * ss
    n = len(tri)
    nrm = np.repeat(_normals(tri), 3, axis=0)
    data = np.hstack([tri.reshape(-1, 3), nrm, np.repeat(col, 3, axis=0), np.repeat(ids.astype(float) + 1, 3)[:, None]]).astype("f4")
    opaque = np.repeat(col[:, 3] > 0.97, 3)
    view = look_at(cam["position"], cam["target"], cam.get("up", (0, 0, 1)))
    if "ortho_h" in cam:
        proj = ortho(cam["ortho_h"] * W / H, cam["ortho_h"], cam.get("near", 0.1), cam.get("far", 200))
    else:
        proj = perspective(cam["fov_v"], W / H, cam.get("near", 0.05), cam.get("far", 200))
    mvp = (proj @ view).astype("f4")

    # carte d'ombres (soleil orthographique sur l'emprise de la scène)
    sun = np.asarray(sun_dir, float); sun /= np.linalg.norm(sun)
    pts = tri.reshape(-1, 3)
    ctr = (pts.min(0) + pts.max(0)) / 2
    rad = np.linalg.norm(pts.max(0) - pts.min(0)) / 2
    lview = look_at(ctr + sun * rad * 2, ctr, (0, 0, 1) if abs(sun[2]) < 0.99 else (0, 1, 0))
    lmvp = (ortho(2 * rad, 2 * rad, 0.1, 4 * rad) @ lview).astype("f4")
    prog = c.program(vertex_shader=VS, fragment_shader=FS)
    progd = c.program(vertex_shader=VS_D, fragment_shader=FS_D)
    shadow_tex = c.depth_texture((4096, 4096))
    shadow_tex.compare_func = ""
    shadow_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    fbd = c.framebuffer(depth_attachment=shadow_tex)
    vb_all = c.buffer(data.tobytes())
    if shadows:
        fbd.use(); fbd.clear(depth=1.0); c.enable(moderngl.DEPTH_TEST)
        progd["light_mvp"].write(lmvp.T.tobytes())
        vb_op = c.buffer(data[opaque].tobytes())
        c.vertex_array(progd, [(vb_op, "3f 3x4 4x4 1x4", "in_pos")]).render()

    col_t = c.texture((W, H), 4, dtype="f2")
    nrm_t = c.texture((W, H), 4, dtype="f1")
    id_t = c.texture((W, H), 1, dtype="f4")
    dep = c.depth_texture((W, H))
    fb = c.framebuffer(color_attachments=[col_t, nrm_t, id_t], depth_attachment=dep)
    fb.use()
    fb.clear(*background, 1.0, depth=1.0)
    id_t_clear = np.zeros((H, W), "f4")
    id_t.write(id_t_clear.tobytes())
    c.enable(moderngl.DEPTH_TEST)
    c.disable(moderngl.CULL_FACE)
    for k, v in (("mvp", mvp.T), ("view", view.astype("f4").T), ("light_mvp", lmvp.T)):
        prog[k].write(np.ascontiguousarray(v).tobytes())
    prog["sun"].value = tuple(sun); prog["sun_col"].value = tuple(np.asarray(sun_col) * exposure)
    prog["sky_col"].value = tuple(np.asarray(sky) * exposure); prog["gnd_col"].value = tuple(np.asarray(ground) * exposure)
    prog["use_shadow"].value = 1 if shadows else 0
    prog["eye"].value = tuple(map(float, cam["position"]))
    prog["emissive_lum"].value = emissive
    fd = np.asarray(fill_dir, float); fd /= np.linalg.norm(fd)
    prog["fill_dir"].value = tuple(fd); prog["fill_k"].value = fill_k * exposure
    shadow_tex.use(0); prog["shadow"].value = 0
    vb_op = c.buffer(data[opaque].tobytes())
    c.vertex_array(prog, [(vb_op, "3f 3f 4f 1f", "in_pos", "in_nrm", "in_col", "in_id")]).render()
    depth_op = np.frombuffer(dep.read(), "f4").reshape(H, W).copy()
    ids_op = np.frombuffer(id_t.read(), "f4").reshape(H, W).copy()
    nrm_op = np.frombuffer(nrm_t.read(), "u1").reshape(H, W, 4)[..., :3].astype(np.float32) / 255 * 2 - 1
    col_op = np.frombuffer(col_t.read(), "f2").reshape(H, W, 4)[..., :3].astype(np.float32)

    # occlusion ambiante : masquage de profondeur (unsharp mask sur la profondeur linéaire)
    if "ortho_h" in cam:
        lin = depth_op.copy()
        scale = 1.0
    else:
        near, far = cam.get("near", 0.05), cam.get("far", 200)
        z = depth_op * 2 - 1
        lin = 2 * near * far / (far + near - z * (far - near))
        scale = 1.0
    bg = depth_op >= 1.0
    lin_f = np.where(bg, np.nan, lin)
    occ = np.zeros_like(lin)
    if ao > 0:
        filled = np.where(bg, np.nanmax(lin_f) if np.isfinite(np.nanmax(lin_f)) else 1, lin)
        for sig in (6 * ss, 18 * ss):
            blur = ndimage.gaussian_filter(filled, sig)
            d = np.clip((lin - blur) / np.maximum(lin, 0.3) * 6 * scale, 0, 1)
            occ = np.maximum(occ, d)
        occ[bg] = 0
    shade = col_op * (1 - ao * occ[..., None])

    # verre (transparence) par-dessus
    if (~opaque).any():
        c.enable(moderngl.BLEND)
        c.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        fb2 = c.framebuffer(color_attachments=[c.texture((W, H), 4, dtype="f2")], depth_attachment=dep)
        fb2.use()
        tex = fb2.color_attachments[0]
        tex.write(np.dstack([shade, np.ones((H, W))]).astype("f2").tobytes())
        c.depth_mask = False
        vb_tr = c.buffer(data[~opaque].tobytes())
        prog2 = c.program(vertex_shader=VS, fragment_shader=FS.replace("layout(location=1) out vec4 o_nrm; layout(location=2) out float o_id;", "vec4 o_nrm; float o_id;"))
        for k, v in (("mvp", mvp.T), ("view", view.astype("f4").T), ("light_mvp", lmvp.T)):
            if k in prog2:
                prog2[k].write(np.ascontiguousarray(v).tobytes())
        for k in ("sun", "sun_col", "sky_col", "gnd_col", "use_shadow", "eye", "emissive_lum", "fill_dir", "fill_k"):
            if k in prog2:
                prog2[k].value = prog[k].value
        shadow_tex.use(0); prog2["shadow"].value = 0
        c.vertex_array(prog2, [(vb_tr, "3f 3f 4f " + ("1f" if "in_id" in prog2 else "4x"), "in_pos", "in_nrm", "in_col", *(["in_id"] if "in_id" in prog2 else []))]).render()   # in_id peut être éliminé par le compilateur GLSL (llvmpipe)
        c.depth_mask = True
        c.disable(moderngl.BLEND)
        shade = np.frombuffer(tex.read(), "f2").reshape(H, W, 4)[..., :3].astype(np.float32)

    img = np.clip(shade, 0, 1) ** (1 / 1.12)
    img = np.flipud(img)
    shaded = Image.fromarray((img * 255).astype(np.uint8)).resize(size, Image.LANCZOS)

    # traits
    ids_i = np.flipud(ids_op).astype(np.int64)
    nn = np.flipud(nrm_op)
    ll = np.flipud(np.where(bg, np.inf, lin))
    sil = np.zeros(ids_i.shape, bool)
    crease = np.zeros(ids_i.shape, bool)
    lf = np.where(np.isfinite(ll), ll, 1e3)
    for sh in ((0, 1), (1, 0), (1, 1), (1, -1)):
        ib = np.roll(ids_i, sh, axis=(0, 1))
        lb = np.roll(lf, sh, axis=(0, 1))
        nb = np.roll(nn, sh, axis=(0, 1))
        jump = np.abs(lf - lb) > 0.03 * np.minimum(lf, lb) + 0.01
        es = (ids_i != ib) | jump
        sil |= es
        crease |= (np.sum(nn * nb, axis=-1) < 0.82) & ~es
    sil = ndimage.binary_dilation(sil, iterations=max(1, ss))
    lines = np.ones(ids_i.shape, np.float32)
    lines[crease] = 0.35
    lines[sil] = 0.0
    lines = ndimage.gaussian_filter(lines, 0.6 * ss / 2)
    trait = Image.fromarray((np.clip(lines, 0, 1) * 255).astype(np.uint8)).resize(size, Image.LANCZOS)
    for o in (fb, fbd, col_t, nrm_t, id_t, dep, shadow_tex, vb_all, prog, progd):
        o.release()
    return shaded, trait


def camera_info(cam, size):
    """Paramètres reproductibles : position, cible, haut, fov H/V, focale équivalente 24 x 36."""
    W, H = size
    d = {"position_m": [round(float(a), 4) for a in cam["position"]], "cible_m": [round(float(a), 4) for a in cam["target"]],
         "haut": list(cam.get("up", (0, 0, 1))), "resolution_px": [W, H]}
    if "ortho_h" in cam:
        d.update(projection="orthographique", hauteur_cadre_m=cam["ortho_h"], largeur_cadre_m=round(cam["ortho_h"] * W / H, 4))
    else:
        fv = cam["fov_v"]
        fh = 2 * np.degrees(np.arctan(np.tan(np.radians(fv) / 2) * W / H))
        d.update(projection="perspective", fov_vertical_deg=round(fv, 3), fov_horizontal_deg=round(float(fh), 3),
                 focale_equivalente_24x36_mm=round(float(18 / np.tan(np.radians(fh) / 2)), 2),
                 near_m=cam.get("near", 0.05), far_m=cam.get("far", 200))
    return d
