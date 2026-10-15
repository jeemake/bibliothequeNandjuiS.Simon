"""Planches A09 à A11 des lots techniques, tirées de v5/DECIMO_ESQ_V5.ifc (psets KDEMI_*, systèmes IFC, directrices).

A09 plan électricité CFO / CFA 1/50 et tableau des circuits
A10 plan plomberie AEP / EU / EV / condensats 1/50, zoom et élévation 1/25
A11 détails techniques 1/10 et 1/20
Usage : python3 v5/scripts/dessins.py A09 A10 A11
"""
import os, sys, re
from collections import defaultdict
import numpy as np
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon as MPoly, FancyArrowPatch
from shapely.geometry import LineString, Point, box as sbox
from shapely.ops import unary_union
import ifcopenshell
import ifcopenshell.util.element as ue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dessins as DS  # noqa
from dessins import (Planche, W, mm, cote, niveau, bulle, label, fr, echelle_graphique, peindre, pocher, est, bb,  # noqa
                     CONTEXTE, GRIS_CLOISON, VERRE)
from commun import (V5_IFC, Z_FP_SOUS, Z_FP_DESSUS, Z_DALLE_SOUS, Z_DALLE_DESSUS, ARBRE, R_OCULUS, INDIGO, POCHE,  # noqa
                    TABLEAU, COFFRAGES, PLACARD_NET, ENCRE, TAUPE, TERRE_CUITE, IROKO, SABLE, SABLE_CLAIR)
from charte_kdemi import OLIVE  # noqa
from charte_kdemi import FP_MEDIUM  # noqa
from scene import role  # noqa
import dessin2d as D  # noqa

VERT = "#3C8D4F"
AEP = "#3F6FA8"
COND = "#5F93A8"
EU_C = OLIVE
EV_C = "#7A4A2A"
GOUL = "#A57650"
FAMILLE = {"E": (TERRE_CUITE, "-"), "E7": (VERT, "-"), "P": (ENCRE, "-"), "CL": (OLIVE, (0, (5, 1.6))), "VDI": (INDIGO, (0, (3.5, 1.2, 1, 1.2)))}
RESEAU = {"AEP": (AEP, "Eau froide AEP (multicouche)"), "EU": (EU_C, "Eaux usées EU (PVC)"), "EV": (EV_C, "Eaux vannes EV (PVC)"),
          "Condensats": (COND, "Condensats (refoulement mini-pompes)"), "VP": ("#8C8C8C", "Ventilation primaire / clapet aérateur")}


def famille(c):
    return "E7" if c == "E7" else "CL" if c.startswith("CL") else "VDI" if c == "VDI" else c[0]


# --- lecture de l'IFC ----------------------------------------------------------------------------
_IFC = {}


def ifc():
    if "f" in _IFC:
        return _IFC["data"]
    f = ifcopenshell.open(V5_IFC)
    prods = {}
    for p in f.by_type("IfcProduct"):
        if p.Representation is None:
            continue
        ps = ue.get_psets(p)
        dirs = []
        for rep in p.Representation.Representations:
            if rep.RepresentationIdentifier != "Body":
                continue
            for it in rep.Items:
                if it.is_a("IfcSweptDiskSolid") and it.Directrix.is_a("IfcPolyline"):
                    dirs.append((np.array([q.Coordinates for q in it.Directrix.Points], float) / 100.0, it.Radius / 100.0))
        prods[p.GlobalId] = dict(classe=p.is_a(), nom=p.Name or "", ps=ps, dirs=dirs, ptype=getattr(p, "PredefinedType", None),
                                 desc=p.Description or "", obj=p)
    circuits = []
    for s in f.by_type("IfcDistributionCircuit"):
        c = ue.get_psets(s).get("KDEMI_Circuit", {})
        membres = [p.GlobalId for r in s.IsGroupedBy for p in r.RelatedObjects]
        circuits.append(dict(c, nom=s.Name, membres=membres))
    reseaux = []
    for s in f.by_type("IfcDistributionSystem"):
        if s.is_a("IfcDistributionCircuit"):
            continue
        membres = [p.GlobalId for r in s.IsGroupedBy for p in r.RelatedObjects]
        reseaux.append(dict(ue.get_psets(s).get("KDEMI_Reseau", {}), nom=s.Name, ptype=s.PredefinedType, membres=membres, desc=s.Description or ""))
    raccords = []
    for r in f.by_type("IfcRelConnectsElements"):
        if r.Name and r.Name.startswith("Raccordement V5"):
            raccords.append((r.RelatingElement.Name, r.RelatedElement.Name, r.RelatedElement.GlobalId, r.Description))
    _IFC["f"] = f
    _IFC["data"] = dict(prods=prods, circuits=circuits, reseaux=reseaux, raccords=raccords)
    return _IFC["data"]


def par_guid(sc):
    return {e["guid"]: e for e in sc}


def centre_xy(e):
    lo, hi = bb(e)
    return np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2])


def nom(sc, n):
    return next(e for e in sc if e["nom"] == n)


NORM = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}


# --- fond de plan estompé ---------------------------------------------------------------------------
def fond_plan(ax, sc, z_coupe=1.0, voile=0.62, rect=None, garder_tech=()):
    v = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0), coupe=((0, 0, 1), z_coupe + 0.0003))
    exclus = ("logements", "fenetre_logt", "sol_ext", "trottoir", "arbre", "voisin", "luminaire")

    def garder(e, r):
        if r in exclus:
            return False
        if r == "technique":
            return e["classe"] in ("IfcDoor", "IfcCovering") or any(m in e["nom"] for m in garder_tech)
        return True
    R = D.calculer(sc, v, garder)
    peindre(ax, R, trait_items=False)
    pocher(ax, [r for r in R if r["role"] not in ("structure", "cloison")], z=20)
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="white", ec="none", alpha=voile, zorder=50))
    pocher(ax, [r for r in R if r["role"] in ("structure", "cloison")], z=60)
    return v, R


# --- symboles (tailles en mm papier) -------------------------------------------------------------------
def sym_pc(ax, c, n, col=ENCRE, z=330, r=1.15):
    a = np.degrees(np.arctan2(n[1], n[0]))
    rr = mm(ax, r)
    ax.add_patch(Wedge(c, rr, a - 90, a + 90, fc="white", ec=col, lw=D.LW[2], zorder=z))
    t = np.array([-n[1], n[0]])
    p0, p1 = c + t * rr * 1.25, c - t * rr * 1.25
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=col, lw=D.LW[2], zorder=z + 0.1, solid_capstyle="butt")
    q = c + np.asarray(n) * rr
    ax.plot([q[0], q[0] + n[0] * rr * 0.55], [q[1], q[1] + n[1] * rr * 0.55], color=col, lw=D.LW[2], zorder=z + 0.1)


def sym_rj(ax, c, n, z=330, r=1.15):
    n = np.asarray(n, float); t = np.array([-n[1], n[0]])
    rr = mm(ax, r)
    pts = [c + t * rr, c - t * rr, c + n * rr * 1.5]
    ax.add_patch(MPoly(pts, closed=True, fc=INDIGO, ec=INDIGO, lw=D.LW[1], zorder=z))


def sym_inter(ax, c, n, kind="simple", z=330, col=ENCRE):
    rr = mm(ax, 0.85)
    ax.add_patch(Circle(c, rr, fc="white", ec=col, lw=D.LW[2], zorder=z))
    n = np.asarray(n, float) if n is not None else np.array([0.0, 1.0])
    d = (n + np.array([-n[1], n[0]])) / np.sqrt(2)
    if kind == "poussoir":
        ax.add_patch(Circle(c, rr * 0.38, fc=col, ec="none", zorder=z + 0.1))
        return
    nb = 2 if kind == "double" else 1
    for k in range(nb):
        o = np.array([-d[1], d[0]]) * rr * 0.5 * (k - (nb - 1) / 2) * 1.6
        p0, p1 = c + d * rr + o, c + d * rr * 2.6 + o
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=col, lw=D.LW[2], zorder=z)
    if kind == "variateur":
        ax.add_patch(MPoly([c + np.array([-rr * 0.5, -rr * 0.45]), c + np.array([rr * 0.5, -rr * 0.45]), c + np.array([rr * 0.5, rr * 0.5])],
                           closed=True, fc=col, ec="none", zorder=z + 0.1))


def sym_clavier(ax, c, z=330):
    s = mm(ax, 1.1)
    ax.add_patch(Rectangle((c[0] - s, c[1] - s), 2 * s, 2 * s, fc="white", ec=ENCRE, lw=D.LW[2], zorder=z))
    for dx in (-0.45, 0.45):
        for dy in (-0.45, 0.45):
            ax.add_patch(Circle((c[0] + dx * s, c[1] + dy * s), s * 0.2, fc=ENCRE, ec="none", zorder=z + 0.1))


def sym_detect(ax, c, z=330):
    rr = mm(ax, 1.0)
    ax.add_patch(Circle(c, rr, fc="white", ec=ENCRE, lw=D.LW[2], zorder=z))
    ax.add_patch(Circle(c, rr * 1.8, fc="none", ec=ENCRE, lw=D.LW[1], ls=(0, (1.2, 1.2)), zorder=z))
    label(ax, c[0], c[1], "P", size=3.6, z=z + 0.2)


def sym_baes(ax, c, z=335):
    w, h = mm(ax, 1.9), mm(ax, 0.9)
    ax.add_patch(Rectangle((c[0] - w, c[1] - h), 2 * w, 2 * h, fc=VERT, ec=ENCRE, lw=D.LW[1], zorder=z))
    ax.add_patch(Rectangle((c[0] - w * 0.45, c[1] - h * 0.4), w * 0.9, h * 0.8, fc="white", ec="none", zorder=z + 0.1))


def sym_lum(ax, c, z=320, col=ENCRE):
    rr = mm(ax, 0.9)
    ax.add_patch(Circle(c, rr, fc="white", ec=col, lw=D.LW[1], zorder=z))
    k = rr * 0.7
    ax.plot([c[0] - k, c[0] + k], [c[1] - k, c[1] + k], color=col, lw=D.LW[1], zorder=z + 0.1)
    ax.plot([c[0] - k, c[0] + k], [c[1] + k, c[1] - k], color=col, lw=D.LW[1], zorder=z + 0.1)


def sym_bsol(ax, g, z=330):
    D.patch(ax, g, fc="white", ec=ENCRE, lw=D.LW[2], z=z)
    x0, y0, x1, y1 = g.bounds
    ax.plot([x0, x1], [y0, y1], color=ENCRE, lw=D.LW[1], zorder=z + 0.1)


def sym_wifi(ax, c, z=330):
    rr = mm(ax, 1.0)
    ax.add_patch(Circle(c, rr, fc=INDIGO, ec=INDIGO, lw=D.LW[1], zorder=z))
    for k in (1.6, 2.2):
        ax.add_patch(Wedge(c, rr * k, 30, 150, width=0, fc="none", ec=INDIGO, lw=D.LW[1], zorder=z))


def sym_vanne(ax, c, d=(1, 0), col=AEP, z=340, r=1.0, plein=False):
    d = np.asarray(d, float); d /= np.linalg.norm(d); t = np.array([-d[1], d[0]])
    rr = mm(ax, r)
    for s in (1, -1):
        ax.add_patch(MPoly([c, c + s * d * rr + t * rr * 0.7, c + s * d * rr - t * rr * 0.7], closed=True,
                           fc=col if plein else "white", ec=col, lw=D.LW[1], zorder=z))


def sym_compteur(ax, c, col=AEP, z=340, r=1.05):
    rr = mm(ax, r)
    ax.add_patch(Circle(c, rr, fc="white", ec=col, lw=D.LW[2], zorder=z))
    tag(ax, c[0], c[1], "M", size=3.8, col=col, z=z + 0.1)


def sym_clapet(ax, c, d=(1, 0), col=AEP, z=340):
    d = np.asarray(d, float); d /= max(np.linalg.norm(d), 1e-9); t = np.array([-d[1], d[0]])
    rr = mm(ax, 0.95)
    ax.add_patch(MPoly([c - t * rr, c + d * rr * 0.9, c + t * rr], closed=True, fc=col, ec=col, lw=D.LW[1], zorder=z))


def sym_tee(ax, c, col=ENCRE, z=340):
    rr = mm(ax, 0.55)
    ax.add_patch(Circle(c, rr, fc=col, ec=col, lw=D.LW[1], zorder=z))


def sym_siphon(ax, c, col=EU_C, z=340):
    rr = mm(ax, 0.85)
    ax.add_patch(Wedge(c, rr, 200, 340, width=rr * 0.55, fc="white", ec=col, lw=D.LW[2], zorder=z))


LOT_P = "Technique - plomberie (hyp. ESQ Ahoua)"


def elements_plom(sc):
    I = ifc()
    G = par_guid(sc)
    out = []
    for g, p in I["prods"].items():
        pl = p["ps"].get("KDEMI_Plomberie")
        if not pl or g not in G:
            continue
        out.append(dict(p, guid=g, e=G[g], reseau=pl.get("Reseau", ""), materiau=pl.get("Materiau", ""),
                        dn=pl.get("DN_mm", ""), dext=pl.get("Diametre_ext_mm", ""), pente=pl.get("Pente_pct", ""),
                        pmin=pl.get("Pente_min_pct", ""), typ=pl.get("Type", "")))
    return out


def trace_tuyau(ax, pts, reseau, plenum_seuil=2.0, z=220, lw=None):
    col, _ = RESEAU.get(reseau, (ENCRE, reseau))
    ls = "-"
    if reseau == "Condensats":
        ls = (0, (3, 1.2))
    if pts[:, 2].min() > plenum_seuil:
        ls = (0, (4, 1.5)) if ls == "-" else ls
    ax.plot(pts[:, 0], pts[:, 1], color=col, lw=lw or D.LW[2], ls=ls, zorder=z, solid_capstyle="round")


def sym_organe_plom(ax, x, classe, reseau, n=None):
    c = centre_xy(x["e"]) if "e" in x else centre_xy(x)
    col, _ = RESEAU.get(reseau, (AEP, ""))
    if classe == "IfcValve":
        t = "clapet" if x.get("ptype") in ("CHECK", "ANTIVACUUM") or "clapet" in (x.get("nom") or "").lower() else "vanne"
        if t == "clapet":
            sym_clapet(ax, c, (1, 0) if n is None else n, col=COND if reseau == "VP" else col)
        else:
            sym_vanne(ax, c, (1, 0) if n is None else n, col=col)
    elif classe == "IfcFlowMeter":
        sym_compteur(ax, c, col=col)
    elif classe == "IfcPipeFitting":
        sym_tee(ax, c, col=col if reseau != "EV" else EV_C)
    elif classe == "IfcWasteTerminal":
        sym_siphon(ax, c, col=col if reseau != "Condensats" else COND)
    return c


def longueur_reseaux(I, sc):
    G = par_guid(sc)
    par = defaultdict(lambda: {"L": 0.0, "dn": set(), "mat": set(), "pmin": []})
    for g, p in I["prods"].items():
        pl = p["ps"].get("KDEMI_Plomberie")
        if not pl or p["classe"] != "IfcPipeSegment" or g not in G:
            continue
        r = pl.get("Reseau", "?")
        for d in p["dirs"]:
            par[r]["L"] += LineString(d[0]).length
        par[r]["dn"].add(str(pl.get("DN_mm", "")))
        par[r]["mat"].add(pl.get("Materiau", ""))
        if pl.get("Pente_min_pct") not in (None, "", 0):
            par[r]["pmin"].append(float(pl["Pente_min_pct"]))
    return par


def legende_symboles(p, entrees, ech=50):
    """Légende des symboles dessinés (petits axes à l'échelle du plan)."""
    for fn, lib in entrees:
        x = p.px + 8
        ax = p.fig.add_axes([x / W, 1 - (p.y + 3.0) / DS.H, 9 / W, 3.0 / DS.H])
        w = 9 * ech / 1000
        ax.set_xlim(0, w); ax.set_ylim(0, w / 3); ax.set_aspect("equal"); ax.axis("off")
        ax.ech = ech
        fn(ax, np.array([w / 2, w / 6]))
        p.T(x + 11.5, p.y + 0.1, lib, 5.7)
        p.y += 3.8
    p.y += 1.2


def tableau(p, x, y, cols, rows, size=4.7, dy=3.35, entete=TERRE_CUITE, w_total=None):
    """Tableau texte : cols = [(titre, largeur_mm, align)]."""
    xs = np.cumsum([0] + [c[1] for c in cols])
    w_total = w_total or xs[-1]
    for k, (t, wc, al) in enumerate(cols):
        p.T(x + xs[k] + (wc - 1 if al == "right" else 0), y, t.upper(), size - 0.5, entete, fontproperties=FP_MEDIUM,
            ha="right" if al == "right" else "left")
    p.fig.add_artist(DS.Line2D([x / W, (x + w_total) / W], [1 - (y + 2.9) / DS.H] * 2, color=TAUPE, lw=0.4))
    yy = y + 3.6
    for row in rows:
        gras = isinstance(row, tuple) and len(row) and row[0] == "__total__"
        cells = row[1:] if gras else row
        for k, (t, wc, al) in enumerate(cols):
            s = cells[k] if k < len(cells) else ""
            kw = dict(fontproperties=FP_MEDIUM) if gras else {}
            p.T(x + xs[k] + (wc - 1 if al == "right" else 0), yy, str(s), size, ENCRE, ha="right" if al == "right" else "left", **kw)
        yy += dy
    p.fig.add_artist(DS.Line2D([x / W, (x + w_total) / W], [1 - (yy - 0.6) / DS.H] * 2, color=TAUPE, lw=0.3))
    return yy


def tag(ax, x, y, s, size=3.7, col=ENCRE, z=425, **kw):
    kw.setdefault("ha", "center"); kw.setdefault("va", "center")
    return ax.text(x, y, s, fontsize=size, color=col, zorder=z, bbox=dict(boxstyle="square,pad=0.12", fc="white", ec="none", alpha=0.85), **kw)


def court(s, n):
    return s if len(s) <= n else s[:n - 1].rstrip(" ,-(") + "…"


def fleche(ax, p0, p1, col, z=360, lw=None):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>,head_length=2.2,head_width=1.1", color=col, lw=lw or D.LW[1], zorder=z,
                                 shrinkA=0, shrinkB=0, mutation_scale=1))


# =====================================================================================================
def elements_elec(sc):
    I = ifc()
    G = par_guid(sc)
    out = []
    for g, p in I["prods"].items():
        el = p["ps"].get("KDEMI_Electricite")
        if not el or g not in G:
            continue
        out.append(dict(p, guid=g, e=G[g], circuit=el.get("Circuit", ""), type=el.get("Type", ""), h=el.get("Hauteur_axe_m"),
                        n=NORM.get(el.get("Normale", "")), socles=el.get("Socles", 1), commande=el.get("Commande", "")))
    return out


def A09(sc):
    I = ifc()
    p = Planche("A09", "Électricité — courants forts et faibles", "Plan CFO / CFA  ·  Échelle 1/50 (A3)  ·  Coupe à +1,00, réseaux du plénum projetés", px=290)
    xl, yl = (-0.45, 7.05), (-0.85, 7.95)
    ax = p.axes(6, 12, xl, yl, 50)
    v, R = fond_plan(ax, sc)
    EL = elements_elec(sc)
    # chemins de câbles (plénum) et goulottes
    for e in sc:
        if e["classe"] != "IfcCableCarrierSegment":
            continue
        for fc, _ in e["items"]:
            g = D.silhouette(v.to2d(e["verts"][fc]))
            if est(e, "Chemin de câbles"):
                D.patch(ax, g, fc="none", ec=TAUPE, lw=D.LW[1], z=110, ls=(0, (3, 1.5)))
            elif est(e, "Conduit sous sol"):
                D.patch(ax, g, fc="none", ec=ENCRE, lw=D.LW[1], z=112, ls=(0, (1.2, 1.2)))
            else:
                D.patch(ax, g, fc=GOUL, ec=ENCRE, lw=D.LW[1], z=112)
    # cheminements par famille de circuits (directrice principale de chaque câble)
    fam = defaultdict(list)
    for x in EL:
        if x["classe"] != "IfcCableSegment" or not x["dirs"]:
            continue
        pts = x["dirs"][0][0]
        if len(pts) > 1 and pts[:, 2].min() > 2.0:
            fam[famille(x["circuit"])].append(LineString(pts[:, :2]))
    dec = {"E": -0.05, "E7": -0.025, "P": 0.0, "CL": 0.025, "VDI": 0.05}
    for fm, ls in fam.items():
        u = unary_union(ls).simplify(0.002)
        col, sty = FAMILLE[fm]
        for s in getattr(u, "geoms", [u]):
            try:
                s2 = s.offset_curve(dec[fm], join_style=2, mitre_limit=3) if s.length > 0.1 else s
            except Exception:
                s2 = s
            for q in getattr(s2, "geoms", [s2]):
                if q.is_empty:
                    continue
                ax.plot(*np.asarray(q.coords).T, color=col, lw=D.LW[2], ls=sty, zorder=150, solid_capstyle="round")
    # arrivée immeuble -> TD
    arr = next(x for x in I["prods"].values() if x["nom"].startswith("Liaison disjoncteur"))
    pts = np.concatenate([d[0] for d in arr["dirs"]])
    ax.plot(pts[:, 0] - 0.075, pts[:, 1], color=TERRE_CUITE, lw=D.LW[4], zorder=149, alpha=0.55, solid_capstyle="butt")
    ext = next(x for x in I["prods"].values() if "partie extérieure" in x["nom"])
    q = ext["dirs"][0][0]
    ax.plot(q[:, 0], q[:, 1], color=TERRE_CUITE, lw=D.LW[2], ls=(0, (1.5, 1)), zorder=150)
    # équipements
    td = nom(sc, "Tableau divisionnaire (encastré dans l'habillage)")
    g = D.contour_complet(td, v)
    D.patch(ax, g, fc="white", ec=ENCRE, lw=D.LW[2], z=300, hatch="//////")
    ax.add_patch(Rectangle((1.64, 0.12), 1.0, 0.60, fc="none", ec=OLIVE, lw=D.LW[1], ls=(0, (2, 2)), zorder=290))
    label(ax, 2.14, 0.42, "1,00 m libre\ndevant le TD", size=3.8, col=OLIVE, z=420)
    label(ax, 2.785, 0.80, "TD", size=5.2, z=420, fontproperties=FP_MEDIUM)
    for n_, txt, fc in (("Coffret arrivée électrique immeuble (disjoncteur de branchement)", "AGCP", "white"),
                        ("Coffret liaisons clim (alimentation et bus des 2 splits)", "", "white"),
                        ("Baie informatique murale 9U", "9U", INDIGO)):
        e = nom(sc, n_)
        D.patch(ax, D.contour_complet(e, v), fc=fc, ec=ENCRE if fc == "white" else INDIGO, lw=D.LW[2], z=300 if fc != INDIGO else 299,
                hatch="xxxx" if txt == "AGCP" else None, alpha=1 if fc == "white" else 0.85)
    label(ax, 0.66, 5.45, "9U", size=3.4, col="white", z=420)
    for k in (1, 2):
        e = nom(sc, f"Split mural 9 000 BTU/h - unité intérieure {k}")
        D.patch(ax, D.contour_complet(e, v), fc="white", ec=OLIVE, lw=D.LW[2], z=300, ls=(0, (4, 1.5)))
        c = centre_xy(e)
        label(ax, c[0], c[1], f"CL{k}", size=3.8, col=OLIVE, z=420, rotation=90)
    # boîtes de sol / nourrices (avec leurs socles)
    jb = [x for x in EL if x["classe"] == "IfcJunctionBox"]
    contenus = defaultdict(list)
    out_libres = []
    for x in EL:
        if x["classe"] != "IfcOutlet":
            continue
        c = centre_xy(x["e"])
        hote = next((j for j in jb if sbox(*bb(j["e"])[0][:2], *bb(j["e"])[1][:2]).buffer(0.04).contains(Point(*c))), None)
        if hote is not None and abs(bb(x["e"])[0][2] - bb(hote["e"])[0][2]) < 0.2:
            contenus[hote["guid"]].append(x)
        else:
            out_libres.append(x)
    POS_JB = {"Nourrice de goulotte - banque d'accueil": (5.92, 2.12, "right"), "Boîte de sol - salon de lecture": (5.22, 3.15, "center"),
              "Nourrice de goulotte - poste catalogue et écoute (console)": (3.35, 2.40, "left"),
              "Boîte de sol - table du coin lecture": (1.12, 1.33, "center")}
    for j in jb:
        g = D.contour_complet(j["e"], v)
        if "sol" in j["nom"]:
            sym_bsol(ax, g)
        else:
            D.patch(ax, g.buffer(0.03, join_style=2), fc=GOUL, ec=ENCRE, lw=D.LW[2], z=330)
        cs = contenus[j["guid"]]
        npc = sum(1 for x in cs if x["ptype"] != "DATAOUTLET")
        nrj = sum(1 for x in cs if x["ptype"] == "DATAOUTLET")
        circ = sorted({x["circuit"] for x in cs if x["circuit"] != "VDI"})
        x_, y_, ha = POS_JB[j["nom"]]
        tag(ax, x_, y_, f"{npc} PC + {nrj} RJ45\n{'/'.join(circ)} · VDI", ha=ha)
    # prises isolées (regroupées par position)
    grp = []
    for x in out_libres:
        c = centre_xy(x["e"])
        kind = "RJ" if x["ptype"] == "DATAOUTLET" else "PC"
        g_ = next((g for g in grp if g[0] == kind and g[1] == x["n"] and np.linalg.norm(centre_xy(g[2][0]["e"]) - c) < 0.16), None)
        if g_ is None:
            grp.append((kind, x["n"], [x]))
        else:
            g_[2].append(x)
    LBL = {}
    for k, _, xs in grp:
        if xs[0]["n"] is None:          # RJ45 en plénum (borne Wi-Fi)
            continue
        c = np.mean([centre_xy(x["e"]) for x in xs], axis=0)
        n = np.asarray(xs[0]["n"], float)
        t = np.array([-n[1], n[0]])
        s = c + n * mm(ax, 1.4)
        if k == "RJ":
            s = s + t * mm(ax, 2.6)
            sym_rj(ax, s, n)
        else:
            sym_pc(ax, s, n)
        LBL[xs[0]["nom"]] = (s, n, xs[0]["circuit"] + (f" ×{len(xs)}" if len(xs) > 1 else ""))
    DEC = {"PC 16 A ménage salle de lecture (pilier)": (-0.17, -0.13), "PC 16 A baie informatique 1": (-0.17, 0.15), "PC 16 A poste catalogue 1": (0.22, -0.14), "RJ45 poste catalogue": (0.18, 0.13),
           "PC 16 A + USB niche banquette": (0.25, 0.0), "PC 16 A podium de vitrine": (0.22, 0.0), "PC 16 A réunion A1": (0.24, 0.0),
           "RJ45 réunion A": (0.22, 0.0), "PC 16 A réunion B1": (0.24, 0.0), "RJ45 réunion B": (0.22, 0.0), "PC 16 A ménage dégagement": (-0.22, 0.0),
           "PC 16 A WC (hors volumes)": (0.0, 0.17), "PC 16 A rangement": (-0.10, 0.15)}
    for nm, (s, n, t_) in LBL.items():
        d = DEC.get(nm, tuple(n * 0.2))
        tag(ax, s[0] + d[0], s[1] + d[1], t_)
    # commandes, détecteur, BAES, borne Wi-Fi
    for x in EL:
        c = centre_xy(x["e"])
        n = np.asarray(x["n"], float) if x["n"] is not None else None
        if x["classe"] == "IfcSwitchingDevice":
            s = c + n * mm(ax, 1.6)
            code = x["nom"].split(" ")[0]
            if code == "S1":
                sym_clavier(ax, s)
            else:
                kind = "poussoir" if "poussoir" in x["type"].lower() else "variateur" if "variateur" in x["type"].lower() else \
                    "double" if "double" in x["type"].lower() else "simple"
                sym_inter(ax, s, n, kind)
            dd = {"S1": (0.0, 0.17), "S2": (0.17, 0.10), "S3": (-0.17, 0.10), "S4": (-0.17, 0.10), "S5": (-0.06, -0.15), "S6": (-0.30, -0.12)}[code]
            tag(ax, s[0] + dd[0], s[1] + dd[1], f"{code}·{x['circuit']}", fontproperties=FP_MEDIUM)
        elif x["classe"] == "IfcSensor":
            sym_detect(ax, c)
            tag(ax, c[0] + 0.25, c[1] - 0.12, "D1·E5", fontproperties=FP_MEDIUM)
        elif x["classe"] == "IfcLightFixture" and x["ptype"] == "SECURITYLIGHTING":
            k = x["nom"].split(" ")[1]
            s = c + (n * mm(ax, 1.4) if n is not None else 0)
            sym_baes(ax, s)
            dd = {"1": (0.0, 0.15), "2": (-0.10, -0.15), "3": (-0.12, 0.15), "4": (0.0, -0.15)}[k]
            tag(ax, s[0] + dd[0], s[1] + dd[1], f"BAES {k}", size=3.6, col=VERT, fontproperties=FP_MEDIUM)
        elif x["classe"] == "IfcCommunicationsAppliance" and "Wi-Fi" in x["nom"]:
            sym_wifi(ax, c)
            tag(ax, c[0], c[1] - 0.17, "Wi-Fi · VDI", size=3.6, col=INDIGO)
    # luminaires 2700 K V5 (conservés), avec leur circuit
    for x in EL:
        if x["classe"] != "IfcLightFixture" or x["ptype"] == "SECURITYLIGHTING":
            continue
        e = x["e"]
        lo, hi = bb(e)
        c = centre_xy(e)
        if max(hi[0] - lo[0], hi[1] - lo[1]) > 0.35:
            D.patch(ax, D.contour_complet(e, v), fc="none", ec=TERRE_CUITE, lw=D.LW[1] * 0.8, z=318, ls=(0, (1.2, 1.6)), alpha=0.8)
            if "Anneau LED indirect" in x["nom"]:
                c = np.array([ARBRE[0] - 0.95, ARBRE[1] + 1.18])
            elif "canopée" in x["nom"]:
                c = np.array([ARBRE[0] + 0.62, ARBRE[1] - 0.25])
            tag(ax, c[0], c[1], x["circuit"], size=3.5, col=TERRE_CUITE)
            continue
        sym_lum(ax, c)
        tag(ax, c[0] + 0.13, c[1] + 0.11, x["circuit"], size=3.3, col=TERRE_CUITE)
    # points singuliers numérotés
    P = lambda n_: centre_xy(nom(sc, n_))
    moul = next(e for e in sc if est(e, "moulure du passage"))
    sing = [(1, "Arrivée immeuble : disjoncteur de branchement (placard), 3G10 vers le TD", P("Coffret arrivée électrique immeuble (disjoncteur de branchement)"), (0.20, 4.75)),
            (2, "TD encastré (habillage iroko), nappe des départs vers le plénum", P("Tableau divisionnaire (encastré dans l'habillage)"), (2.30, -0.40)),
            (3, "Baie VDI 9U murale (onduleur, P6), départs RJ45 cat. 6A en étoile", P("Baie informatique murale 9U"), (1.45, 5.00)),
            (4, "R5 Ø 0,10 : cloison placo 4350621, placard -> réunion (plénum)", P("Réservation R5 Ø 0,10 - Passage câbles placard -> réunion (cloison placo 4350621)"), (1.05, 4.70)),
            (5, "Passage du galandage au-dessus de la retombée BA13 (plénum)", np.array([2.91, 1.10]), (2.60, 1.75)),
            (6, "R7 Ø 0,04 : cloison placo 4350620, dégagement -> WC", P("Réservation R7 Ø 0,04 - Passage câbles dégagement -> WC (cloison placo 4350620)"), (2.10, 5.95)),
            (7, "R6 Ø 0,04 : entrée du conduit dans le doublage V4 (niche)", P("Réservation R6 Ø 0,04 - Entrée conduit dans le doublage V4 (niche banquette)"), (4.40, 7.70)),
            (8, "Baie libre V4 : moulure sous linteau, goulotte sur le lambris", centre_xy(moul), (3.55, 6.25)),
            (9, "Fourreau existant de l'enseigne V4 (traversée de façade sans percement)", np.array([4.10, -0.23]), (4.75, -0.55)),
            (10, "Chemin de câbles C3 80 × 40 en plénum (chevilles 40 mm)", np.array([3.20, 4.0]), (3.55, 3.55))]
    for n_, _, c, b in sing:
        bulle(ax, b[0], b[1], n_, fc=TERRE_CUITE, vers=tuple(c))
    # repères divers
    label(ax, 3.92, -0.30, "ENTRÉE", size=4.4, col=TERRE_CUITE, z=420)
    for (x_, y_, s) in ((4.55, 2.60, "SALLE DE LECTURE"), (1.25, 0.62, "COIN LECTURE"), (1.40, 4.00, "RÉUNION"), (1.25, 5.85, "RANGEMENT"),
                        (1.20, 6.55, "WC"), (2.55, 5.55, "DÉG.")):
        label(ax, x_, y_, s, size=4.6, col=TAUPE, z=405)
    cote(ax, -0.09, 6.69, 7.80, "6,78", ext=7.59)
    echelle_graphique(ax, 5.0, -0.65, 2, 1.0)
    # --- tableau des circuits ---
    C = sorted(I["circuits"], key=lambda c: (["E", "P", "C", "V"].index(c["Code"][0]), c["Code"]))
    PR = I["prods"]
    rows = []
    for c in C:
        mem = [PR[g] for g in c["membres"] if g in PR]
        pts = [m for m in mem if m["classe"] in ("IfcOutlet", "IfcLightFixture", "IfcSwitchingDevice", "IfcSensor", "IfcCommunicationsAppliance", "IfcUnitaryEquipment", "IfcPump")]
        cab = [m for m in mem if m["classe"] == "IfcCableSegment" and m["nom"].startswith("Câble circuit") and "extérieure" not in m["nom"]]
        lp = cab[0]["ps"]["KDEMI_Electricite"].get("Longueur_plenum_m", "") if cab else ""
        npc = sum(1 for m in pts if m["classe"] == "IfcOutlet")
        nl = sum(1 for m in pts if m["classe"] == "IfcLightFixture")
        nc = sum(1 for m in pts if m["classe"] in ("IfcSwitchingDevice", "IfcSensor"))
        desc = []
        if nl:
            desc.append(f"{nl} lum.")
        if npc:
            desc.append(f"{npc} {'RJ45' if c['Code'] == 'VDI' else 'PC'}")
        if nc:
            desc.append(f"{nc} cde")
        others = len(pts) - npc - nl - nc
        if others:
            desc.append(f"{others} app.")
        prot = c["Protection"].replace("courbe ", "")
        rows.append([c["Code"], court(c["Designation"], 55), prot, c["Differentiel"].split(" ")[0], c["Cable"].replace("U/FTP cat. 6A", "cat. 6A"),
                     " + ".join(desc), fr(float(lp), 1) if lp != "" else ""])
    x0 = 164
    p.T(x0, 12, "TABLEAU DES CIRCUITS — TD (HYPOTHÈSE ESQ, NF C 15-100)", 6.4, TERRE_CUITE, fontproperties=FP_MEDIUM)
    yy = tableau(p, x0, 18, [("Circ.", 8, "left"), ("Désignation", 50, "left"), ("Protection", 14.5, "left"), ("ID", 6.5, "left"),
                             ("Câble", 11, "left"), ("Points", 19, "left"), ("L m", 7, "right")], rows, size=4.45, dy=3.25)
    yy += 1.0
    for s in ["ID1 interrupteur différentiel 40 A 30 mA type AC (éclairage, BAES) · ID2 40 A 30 mA type A",
              "(prises, baie VDI) · ID3 40 A 30 mA type A (ménage, splits). DJ courbe C, splits courbe D.",
              "L m : longueur en plénum mesurée sur la directrice IFC (hors descentes). Réserve TD 20 % mini.",
              "Arrivée : U1000 R2V 3G10 depuis le disjoncteur de branchement CIE (placard technique)."]:
        p.T(x0, yy, s, 4.5, TAUPE); yy += 3.0
    # hauteurs de pose et quantitatif
    yy += 2.5
    p.T(x0, yy, "HAUTEURS DE POSE (AXE, DEPUIS LE SOL FINI) ET QUANTITÉS TIRÉES DE L'IFC", 6.0, TERRE_CUITE, fontproperties=FP_MEDIUM)
    q = defaultdict(lambda: [0, set()])
    for x in EL:
        if x["classe"] in ("IfcCableSegment", "IfcCableCarrierSegment") or (x["classe"] == "IfcLightFixture" and x["ptype"] != "SECURITYLIGHTING"):
            continue
        typ = x["type"]
        if x["classe"] == "IfcOutlet":
            typ = ("RJ45 cat. 6A" if x["ptype"] == "DATAOUTLET" else "PC 16 A 2P+T") + (" en boîte de sol" if "boîte de sol" in x["type"] else
                                                                                       " en plénum" if "plénum" in x["type"] else "")
        elif x["classe"] == "IfcSwitchingDevice":
            typ = "Commandes (interrupteurs, poussoirs, clavier)"
        elif x["classe"] == "IfcJunctionBox":
            typ = "Boîtes de sol" if "Boîte de sol" in x["nom"] else "Nourrices de goulotte"
        q[typ][0] += 1
        if x["h"] is not None:
            q[typ][1].add(fr(float(x["h"])))
    rows = []
    for typ, (n_, hs) in sorted(q.items(), key=lambda t: -t[1][0]):
        hs = sorted(hs, key=lambda s: float(s.replace(",", ".")))
        rows.append([court(typ, 52), str(n_), " / ".join(hs[:5]) + (" …" if len(hs) > 5 else "")])
    lum = sum(1 for x in EL if x["classe"] == "IfcLightFixture" and x["ptype"] != "SECURITYLIGHTING")
    rows.append(["Luminaires LED 2700 K de la V5 (conservés, raccordés)", str(lum), "plafond / suspension"])
    gl = [e for e in sc if e["classe"] == "IfcCableCarrierSegment" and e["lot"].startswith("Technique - ") and not est(e, "Chemin", "Conduit")]
    lg = sum(max(bb(e)[1] - bb(e)[0]) for e in gl)
    cab = sum(LineString(d[0]).length for x in EL if x["classe"] == "IfcCableSegment" for d in x["dirs"])
    rows.append(["Goulottes iroko et moulures (longueur cumulée)", f"{fr(lg, 1)} m", f"{len(gl)} tronçons"])
    rows.append(["Câbles (directrices IFC, descentes comprises)", f"{fr(cab, 0)} m", "hors réserve de raccordement"])
    tableau(p, x0, yy + 5.5, [("Ouvrage", 70, "left"), ("Qté", 13, "right"), ("Hauteur d'axe (m)", 34, "left")], rows, size=4.45, dy=3.2)
    # --- panneau de droite ---
    p.intertitre("Symboles")
    nd = np.array([0.0, 1.0])
    legende_symboles(p, [
        (lambda a, c: sym_pc(a, c - np.array([0, mm(a, 0.6)]), nd), "Prise de courant 16 A 2P+T (circuit P, ×n)"),
        (lambda a, c: sym_rj(a, c - np.array([0, mm(a, 0.8)]), nd), "Prise RJ45 cat. 6A (VDI)"),
        (lambda a, c: (D.patch(a, sbox(c[0] - mm(a, 2), c[1] - mm(a, 0.8), c[0] + mm(a, 2), c[1] + mm(a, 0.8)), fc=GOUL, ec=ENCRE, lw=D.LW[2], z=5)),
         "Nourrice / goulotte iroko en applique"),
        (lambda a, c: sym_bsol(a, sbox(c[0] - mm(a, 1.1), c[1] - mm(a, 1.1), c[0] + mm(a, 1.1), c[1] + mm(a, 1.1))), "Boîte de sol (dans la chape du sol fini)"),
        (lambda a, c: sym_inter(a, c, (0, 1), "simple"), "Interrupteur (S5, S6) — double : S3"),
        (lambda a, c: sym_inter(a, c, (0, 1), "poussoir"), "Bouton-poussoir sur télérupteur (S2, va-et-vient)"),
        (lambda a, c: sym_inter(a, c, (0, 1), "variateur"), "Interrupteur variateur (S4)"),
        (lambda a, c: sym_clavier(a, c), "Clavier de commande éclairage (S1, accueil)"),
        (lambda a, c: sym_detect(a, c), "Détecteur de présence (WC)"),
        (lambda a, c: sym_baes(a, c), "BAES évacuation / balisage SATI 1 h (E7)"),
        (lambda a, c: sym_lum(a, c), "Luminaire LED 2700 K V5 conservé (circuit)"),
        (lambda a, c: sym_wifi(a, c), "Point d'accès Wi-Fi PoE plafond"),
    ])
    for fm, lib in (("E", "Éclairage E1-E6"), ("E7", "BAES E7"), ("P", "Prises P1-P6"), ("CL", "Splits CL1-CL2"), ("VDI", "Courants faibles VDI")):
        col, sty = FAMILLE[fm]
        p.symbole("trait", f"{lib} : câbles en plénum", color=col, ls=sty, lw=D.LW[2])
    p.symbole("trait", "Chemin de câbles 80 × 40 (plénum)", color=TAUPE, ls=(0, (3, 1.5)))
    p.symbole("trait", "Conduit sous le sol fini (boîtes de sol)", color=ENCRE, ls=(0, (1.2, 1.2)))
    p.y += 1.0
    p.intertitre("Points singuliers")
    for n_, s, _, _ in sing:
        p.pastille(str(n_), court(s, 74), TERRE_CUITE)
    p.y += 1.0
    p.intertitre("Principes (hypothèses ESQ Ahoua)")
    for s in ["Réseau de l'immeuble seul : pas de TGBT, pas de groupe électrogène.",
              "Aucun percement de poteau, voile ni dalle : descentes en goulottes",
              "iroko en applique, câbles en plénum (+3,24) sur chemins de câbles ;",
              "R5 à R8 dans des cloisons et doublages V4 non porteurs.",
              "Boîtes de sol dans l'épaisseur du sol fini (chape 7 cm, à relever) :",
              "aucun carottage du dallage existant.",
              "Éclairage : 27 luminaires 2700 K V5 conservés, 6 circuits E1-E6 ;",
              "fond de salle en va-et-vient (télérupteur, S1 / S2), WC sur détecteur.",
              "BAES SATI 1 h : sortie au-dessus de la porte, balisage dégagement,",
              "coin lecture et circulation (télécommande de mise au repos au TD).",
              "Prise du WC à 1,03 m du lave-mains (hors volumes 0 à 2).",
              "Courants faibles : baie 9U, RJ45 cat. 6A en étoile, Wi-Fi PoE."]:
        p.ligne(s, 5.6, dy=3.3)
    p.cartouche("1/50")
    p.enregistrer("plan_electricite_CFO_CFA")


def A10(sc):
    I = ifc()
    PL = elements_plom(sc)
    p = Planche("A10", "Plomberie — AEP, EU, EV et condensats", "Plan sanitaire  ·  Échelle 1/50 et 1/25 (A3)  ·  Coupe à +1,00", px=290)
    xl, yl = (-0.45, 7.05), (-0.85, 7.95)
    ax = p.axes(6, 12, xl, yl, 50)
    v, R = fond_plan(ax, sc, garder_tech=("Descente", "Coffrage", "Split", "Mini-pompe", "WC", "lave-mains", "Réservation R8"))
    for x in PL:
        if x["classe"] != "IfcPipeSegment" or not x["dirs"]:
            continue
        for d in x["dirs"]:
            trace_tuyau(ax, d[0], x["reseau"])
    for e in sc:
        if est(e, "Descente EU/EV"):
            lo, hi = bb(e)
            cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            ax.add_patch(Rectangle((lo[0], lo[1]), hi[0] - lo[0], hi[1] - lo[1], fc="none", ec=OLIVE, lw=D.LW[2], zorder=280))
            ax.plot([cx, cx], [lo[1], hi[1]], color=EV_C, lw=D.LW[4], zorder=281, solid_capstyle="butt")
            label(ax, cx + 0.18, cy, "Ø 100\nhyp.", size=3.5, col=OLIVE, z=420)
        if est(e, "Coffrage acoustique descente"):
            g = D.contour_complet(e, v)
            D.patch(ax, g, fc="none", ec=TAUPE, lw=D.LW[2], z=275, ls=(0, (2, 2)))
            c = centre_xy(e)
            tag(ax, c[0] + 0.22, c[1], "À relever\nsur site", size=3.5, ha="left")
    for e in sc:
        if est(e, "Split mural") and "intérieure" in e["nom"]:
            D.patch(ax, D.contour_complet(e, v), fc="white", ec=OLIVE, lw=D.LW[1], z=290, ls=(0, (3, 1.5)))
        if est(e, "Mini-pompe de relevage"):
            c = centre_xy(e)
            sym_tee(ax, c, col=COND)
            k = "1" if "split 1" in e["nom"] else "2"
            tag(ax, c[0] + 0.12, c[1], f"P{k}", size=3.4, col=COND)
    for x in PL:
        if x["classe"] in ("IfcValve", "IfcFlowMeter", "IfcPipeFitting", "IfcWasteTerminal"):
            sym_organe_plom(ax, x, x["classe"], x["reseau"])
    cof = next(e for e in sc if est(e, "Coffret de comptage AEP"))
    D.patch(ax, D.contour_complet(cof, v), fc="white", ec=AEP, lw=D.LW[2], z=300, hatch="////")
    for x in PL:
        if x["classe"] != "IfcPipeSegment" or not x["dirs"]:
            continue
        r, dn = x["reseau"], x.get("dn", "")
        if r in ("EU", "EV") and dn:
            pts = x["dirs"][0][0]
            mid = pts[len(pts) // 2]
            txt = f"PVC Ø {int(dn) if float(dn) == int(float(dn)) else dn} · 2 %"
            tag(ax, mid[0] + 0.08, mid[1], txt, size=3.3, col=RESEAU[r][0])
            if r == "EV":
                p0, p1 = pts[-2], pts[-1]
                d = p1[:2] - p0[:2]; d /= max(np.linalg.norm(d), 1e-9)
                fleche(ax, p0[:2] + d * 0.05, p0[:2] + d * 0.22, EV_C)
        if r == "AEP" and dn in (12, 15, "12", "15"):
            pts = x["dirs"][0][0]
            mid = pts[len(pts) // 2]
            tag(ax, mid[0], mid[1] + 0.06, f"MC {int(dn) + 4}", size=3.3, col=AEP)
        if r == "Condensats":
            pts = x["dirs"][0][0]
            if pts[:, 2].min() > 2.0:
                mid = pts[len(pts) // 2]
                tag(ax, mid[0], mid[1], "PVC cristal\n10 × 14", size=3.2, col=COND)
    r8 = nom(sc, "Réservation R8 Ø 0,04 - Passage condensats réunion -> rangement (cloison placo 4350621)")
    c8 = centre_xy(r8)
    D.patch(ax, D.contour_complet(r8, v), fc="none", ec=COND, lw=D.LW[1], z=320, ls=(0, (2, 2)))
    tag(ax, c8[0] + 0.12, c8[1], "R8", size=3.8, col=COND, fontproperties=FP_MEDIUM)
    sing = [(1, "Colonne / piquage AEP immeuble (position, DN, pression à relever)", np.array([0.20, 7.18]), (0.55, 7.75)),
            (2, "Coffret de comptage (vanne, compteur, clapet EA, réducteur si P > 3 bar)", np.array([1.20, 7.34]), (1.55, 7.75)),
            (3, "WC V4 conservé (4350629), alimentation flexible — non dupliqué", np.array([0.45, 7.05]), (0.15, 6.55)),
            (4, "Lave-mains V4 conservé (plan 4350630, vasque 4350631), robinet temporisé", np.array([2.78, 7.02]), (3.15, 6.55)),
            (5, "Siphon lave-mains + clapet aérateur Ø 40 sur antenne EU", np.array([2.72, 7.22]), (3.05, 7.55)),
            (6, "Culotte / piquage Ø 40 sur descente EU/EV 1 (à relever)", np.array([0.35, 7.31]), (0.05, 7.55)),
            (7, "Mini-pompe condensats split 1 (refoulement vers collecteur)", np.array([6.42, 5.25]), (6.75, 5.55)),
            (8, "Mini-pompe condensats split 2", np.array([0.15, 4.18]), (-0.15, 4.45)),
            (9, "R8 Ø 0,04 : passage condensats (cloison placo non porteuse)", c8, (0.55, 4.85)),
            (10, "Siphon sec condensats + piquage sur descente EU/EV 2", np.array([0.26, 6.02]), (0.55, 6.35))]
    for n_, _, c, b in sing:
        bulle(ax, b[0], b[1], n_, fc=TERRE_CUITE, vers=tuple(c))
    for (x_, y_, s) in ((4.55, 2.60, "SALLE DE LECTURE"), (1.25, 6.55, "WC"), (1.25, 5.85, "RANGEMENT"), (2.55, 5.55, "DÉG.")):
        label(ax, x_, y_, s, size=4.4, col=TAUPE, z=405)
    cote(ax, -0.09, 6.69, 7.80, "6,78", ext=7.59)
    echelle_graphique(ax, 5.0, -0.65, 2, 1.0)
    # zoom WC 1/25
    p.T(162, 12, "ZOOM WC / RANGEMENT — 1/25", 6.0, TERRE_CUITE, fontproperties=FP_MEDIUM)
    axz = p.axes(162, 22, (0.0, 3.0), (5.0, 7.5), 25)
    fond_plan(axz, sc, z_coupe=1.0, voile=0.72, garder_tech=("Descente", "Coffrage", "WC", "lave-mains"))
    for x in PL:
        if x["classe"] != "IfcPipeSegment" or not x["dirs"]:
            continue
        pts = x["dirs"][0][0]
        if pts[:, 0].max() < 3.05 and pts[:, 1].min() > 4.9:
            for d in x["dirs"]:
                trace_tuyau(axz, d[0], x["reseau"], z=220)
    for x in PL:
        if x["classe"] in ("IfcValve", "IfcFlowMeter", "IfcPipeFitting", "IfcWasteTerminal"):
            c = centre_xy(x["e"])
            if c[0] < 3.05 and c[1] > 4.9:
                sym_organe_plom(axz, x, x["classe"], x["reseau"])
    echelle_graphique(axz, 2.35, 5.05, 1, 1.0)
    # élévation mur nord WC 1/25
    p.T(162, 88, "ÉLÉVATION MUR NORD WC — 1/25 (V4 conservé)", 6.0, TERRE_CUITE, fontproperties=FP_MEDIUM)
    axe = p.axes(162, 98, (0.0, 3.0), (-0.1, 3.4), 25)
    vn = D.Vue((0, 1, 0), (1, 0, 0), (0, 0, 1), coupe=((0, -1, 0), -6.4003))
    Rn = D.calculer(sc, vn, lambda e, r: r not in ("logements", "fenetre_logt", "sol_ext", "trottoir", "arbre", "voisin") and bb(e)[1][1] >= 6.3)
    peindre(axe, Rn, trait_items=False)
    pocher(axe, [r for r in Rn if r["role"] in ("structure", "cloison")], z=60)
    for x in PL:
        if x["classe"] != "IfcPipeSegment" or not x["dirs"]:
            continue
        for d in x["dirs"]:
            pts = d[0]
            if pts[:, 1].max() < 6.5 and pts[:, 0].max() < 3.1:
                col, _ = RESEAU.get(x["reseau"], (ENCRE, ""))
                axe.plot(pts[:, 0], pts[:, 2], color=col, lw=D.LW[2], ls=(0, (4, 1.5)) if pts[:, 2].min() > 2 else "-", zorder=200)
    for zz, t in ((0.32, "+0,32 réservoir"), (0.52, "+0,52 siphon LM"), (1.10, "+1,10 AEP")):
        niveau(axe, 2.85, zz, t, size=4.0)
    echelle_graphique(axe, 2.35, -0.05, 1, 1.0)
    # tableau réseaux
    x0, y0 = 6, 118
    p.T(x0, y0, "RÉSEAUX (IFC — KDEMI_Reseau / KDEMI_Plomberie)", 6.2, TERRE_CUITE, fontproperties=FP_MEDIUM)
    lr = longueur_reseaux(I, sc)
    rows = []
    for s in I["reseaux"]:
        lib = s.get("nom", "")
        rkey = next((k for k in lr if k in lib or lib.startswith(k)), None)
        L = lr.get(rkey or "", {}).get("L", 0)
        info = lr.get(rkey or "", {})
        dn = " / ".join(sorted({str(x) for x in info.get("dn", []) if x}))
        mat = court(" / ".join(sorted({str(x) for x in info.get("mat", []) if x})), 42)
        pente = f"{min(info['pmin']):.1f} %" if info.get("pmin") else "—"
        rows.append([lib.split("(")[0].strip(), fr(L, 1) + " m", dn or "—", mat, pente, s.get("Statut", "—")])
    yy = tableau(p, x0, y0 + 6, [("Réseau", 42, "left"), ("L tuyaux", 14, "right"), ("DN mm", 12, "left"), ("Matériau", 38, "left"),
                                  ("Pente mini", 14, "left"), ("Statut", 22, "left")], rows, size=4.35, dy=3.15)
    for s in I["raccords"]:
        p.T(x0, yy + 2, f"Raccordement V5 : {court(s[0], 35)} → {court(s[1], 35)}", 4.3, TAUPE); yy += 3.0
    p.intertitre("Symboles")
    for rk, (_, lib) in RESEAU.items():
        col = RESEAU[rk][0]
        ls = (0, (3, 1.2)) if rk == "Condensats" else "-"
        p.symbole("trait", lib, color=col, ls=ls, lw=D.LW[2])
    p.symbole("trait", "Tronçon en plénum (z > 2,00) : tirets", color=TAUPE, ls=(0, (4, 1.5)))
    legende_symboles(p, [
        (lambda a, c: sym_vanne(a, c, (1, 0)), "Vanne / robinet d'arrêt"),
        (lambda a, c: sym_compteur(a, c), "Compteur divisionnaire"),
        (lambda a, c: sym_clapet(a, c, (1, 0)), "Clapet (EA, aérateur)"),
        (lambda a, c: sym_tee(a, c), "Té / culotte / piquage"),
        (lambda a, c: sym_siphon(a, c), "Siphon / siphon sec"),
    ], ech=25)
    p.intertitre("Points singuliers")
    for n_, s, _, _ in sing:
        p.pastille(str(n_), court(s, 72), TERRE_CUITE)
    p.intertitre("Principes")
    for s in ["Pas de chauffe-eau : un seul lave-mains, eau froide réseau (26-30 °C à Abidjan),",
              "pas de circuit 20 A dédié ni de stockage d'eau chaude (légionelles).",
              "WC et lave-mains V4 conservés, non dupliqués : raccordements V5 via",
              "IfcRelConnectsElements « Raccordement V5 sur appareil V4 conservé ».",
              "Branchements immeuble / descentes EU·EV : position et diamètres à relever.",
              "Réducteur de pression posé seulement si P mesurée > 3 bar.",
              "Condensats refoulés par mini-pompes vers la descente EU/EV 2 (siphon sec)."]:
        p.ligne(s, 5.6, dy=3.2)
    p.cartouche("1/50 et 1/25")
    p.enregistrer("plan_plomberie_AEP_EU_EV_condensats")


def _detail(p, x, y, titre, ech, sc, vue, ulim, vlim, garder=None, notes=(), z_niv=()):
    garder = garder or (lambda e, r: r not in ("logements", "fenetre_logt", "sol_ext", "trottoir", "arbre", "voisin"))
    ax = p.axes(x, y, ulim, vlim, ech)
    R = D.calculer(sc, vue, garder)
    peindre(ax, R, trait_items=False)
    pocher(ax, [r for r in R if r["role"] in ("structure", "cloison")], z=55)
    pocher(ax, [r for r in R if r["role"] not in ("structure", "cloison") and role(r["e"]) != "technique"], z=45)
    for u, v, t in z_niv:
        niveau(ax, ulim[1] - 0.08 * (ulim[1] - ulim[0]), v, t, size=3.8)
    for pu, pv, txt, du, dv in notes:
        ax.plot([pu, pu + du], [pv, pv + dv], color=ENCRE, lw=D.LW[1], zorder=400)
        label(ax, pu + du * 1.05, pv + dv * 1.05, txt, size=3.6, z=410, ha="left" if du >= 0 else "right")
    p.T(x, y - 4, titre, 5.8, ENCRE, fontproperties=FP_MEDIUM)
    p.T(x + 2, y - 7.5, f"Échelle 1/{ech}", 4.8, TAUPE)
    echelle_graphique(ax, ulim[0] + 0.05 * (ulim[1] - ulim[0]), vlim[0] + 0.04 * (vlim[1] - vlim[0]), 1, 1.0)
    return ax, R


def A11(sc):
    I = ifc()
    p = Planche("A11", "Détails techniques", "Coupe et élévations tirées de l'IFC  ·  Échelles 1/10 et 1/20 (A3)", px=290)
    # D1 plénum
    v1 = D.Vue((0, 1, 0), (1, 0, 0), (0, 0, 1), coupe=((0, -1, 0), -3.0003))
    ax1, _ = _detail(p, 8, 18, "D1 — Faux-plafond acoustique et plénum", 10, sc, v1, (2.75, 3.95), (2.80, 3.58),
                      lambda e, r: r in ("structure", "cloison", "plafond", "technique") or est(e, "Chemin de câbles", "Wi-Fi", "Suspente"),
                      notes=[(3.20, 3.24, "Chemin C3 80×40", 0.0, 0.08), (3.75, 3.22, "AP Wi-Fi PoE", 0.0, 0.08),
                             (3.55, 3.30, "Suspente M6 · 40 mm\n(non traversante)", 0.12, 0.0)],
                      z_niv=[(0, 3.00, "+3,00 FP"), (0, 3.30, "+3,30 dalle")])
    label(ax1, 3.35, 3.02, "FP acoustique\n40 mm", size=3.5, col=TAUPE)
    # D5 seuil vitrine
    v5 = D.Vue((1, 0, 0), (0, 1, 0), (0, 0, 1), coupe=((-1, 0, 0), -1.1503))
    _detail(p, 8, 108, "D5 — Seuil de vitrine baie A", 10, sc, v5, (-0.55, 0.50), (0.15, 0.85),
            lambda e, r: r not in ("logements", "voisin", "arbre") and (bb(e)[0][0] < 1.2 or est(e, "Seuil", "Podium", "Vitrine", "Châssis")),
            notes=[(0.05, 0.48, "Tôle pliée acier noir 30/10", 0.15, 0.0), (0.35, 0.55, "Appui existant", 0.0, 0.08),
                   (-0.35, 0.42, "Podium iroko", 0.0, -0.08), (0.25, 0.72, "Allège V4 : pas de fixation", 0.12, 0.0)])
    # D2 coffrage descente 1
    v2 = D.Vue((0, 0, -1), (1, 0, 0), (0, 1, 0), coupe=((0, 0, 1), 0.6003))
    ax2, _ = _detail(p, 8, 198, "D2 — Coffrage acoustique descente EU/EV 1", 10, sc, v2, (-0.10, 0.75), (6.85, 7.55),
                     lambda e, r: r in ("structure", "cloison", "technique") or est(e, "Coffrage", "Descente"),
                     notes=[(0.35, 7.26, "Coffrage 0,30×0,30\n2×BA13 hydro 25 + laine 25", 0.0, 0.12),
                            (0.24, 7.18, "Colonne AEP (hyp.)", 0.10, 0.0), (0.15, 7.38, "Trappe 0,20×0,20", -0.08, 0.0)])
    tag(ax2, 0.55, 7.48, "À relever sur site", size=3.5)
    # D3 placard technique
    v3 = D.Vue((0, -1, 0), (-1, 0, 0), (0, 0, 1), coupe=((0, 1, 0), 5.555))
    _detail(p, 135, 18, "D3 — Placard technique (vue sud)", 20, sc, v3, (0.36, 1.30), (-0.05, 3.40),
            lambda e, r: r not in ("logements", "fenetre_logt") and bb(e)[1][0] < 1.35,
            notes=[(0.55, 1.15, "Disjoncteur branchement", 0.0, 0.10), (0.95, 1.55, "Coffret clim", 0.0, 0.08),
                   (1.05, 2.05, "Baie 9U + PC P6", 0.0, 0.08), (0.70, 2.85, "Chemin câbles → plénum", 0.10, 0.0)],
            z_niv=[(0, 0.0, "±0,00"), (0, 3.00, "+3,00")])
    # D4 fixations oculus
    v4 = D.Vue((0, 1, 0), (1, 0, 0), (0, 0, 1), coupe=((0, -1, 0), -5.6103))
    _detail(p, 203, 18, "D4 — Fixations non traversantes (oculus / canopée)", 10, sc, v4, (5.74, 6.55), (2.85, 3.55),
            lambda e, r: r in ("structure", "technique") or est(e, "Platine", "Suspente", "canopée", "oculus"),
            notes=[(6.05, 3.28, "Platine canopée\nancrage 50 mm", 0.0, 0.10), (6.20, 3.05, "Suspente bandeau oculus\n40 mm, aucune traversée", 0.0, -0.10),
                   (6.35, 2.95, "Dalle 200 mm hyp.", 0.12, 0.0)])
    # inset pied arbre
    ax4 = p.axes(248, 72, (5.85, 6.45), (2.92, 3.08), 10)
    for e in sc:
        if est(e, "Platine de pied de l'arbre"):
            lo, hi = bb(e)
            if lo[0] > 5.8:
                g = sbox(lo[0], lo[2], hi[0], hi[2])
                D.patch(ax4, g, fc="white", ec=ENCRE, lw=D.LW[2], z=10)
    label(ax4, 6.15, 3.02, "Pied arbre : 30 mm\ndallage 100 mm hyp.", size=3.4)
    # D6 panneau passe-liaisons
    v6 = D.Vue((1, 0, 0), (0, 1, 0), (0, 0, 1), coupe=((-1, 0, 0), -4.6003))
    _detail(p, 203, 118, "D6 — Panneau passe-liaisons (baie arrière V4)", 10, sc, v6, (7.00, 7.81), (2.40, 3.55),
            lambda e, r: r not in ("voisin",) and (bb(e)[0][0] > 4.3 or est(e, "Panneau passe", "Réservation R3", "Réservation R4", "Liaison")),
            notes=[(7.44, 2.68, "Panneau acier 40 mm\n(y 7,415-7,455)", 0.0, 0.10), (7.52, 2.85, "R3 / R4 Ø 0,10\ndans le panneau", 0.10, 0.0),
                   (7.35, 3.15, "Liaisons frigorifiques", 0.0, 0.08), (7.55, 2.45, "Ouverture V4 inchangée", 0.0, -0.08)])
    p.intertitre("Liste des détails")
    for t in ("D1 — Plénum acoustique, chemin C3, suspentes 40 mm", "D2 — Coffrage descente EU/EV 1 (50 mm, trappe)",
              "D3 — Placard technique (AGCP, clim, 9U, TD)", "D4 — Fixations canopée / oculus / pied arbre (KDEMI_Fixation)",
              "D5 — Seuil tôle acier baie A", "D6 — Panneau passe-liaisons imposte baie arrière"):
        p.pastille(t[:2], t, TERRE_CUITE)
    p.intertitre("Principes")
    fast = [x for x in I["prods"].values() if x["ps"].get("KDEMI_Fixation")]
    anc = sorted({int(x["ps"]["KDEMI_Fixation"]["Ancrage_mm"]) for x in fast})
    for s in ["Aucun percement de poteau, voile ni dalle porteuse.",
              f"Fixations : chevilles non traversantes, ancrage au plus 1/3 du support ({', '.join(map(str, anc))} mm dans l'IFC).",
              "Valeurs lues sur KDEMI_Fixation (Traversant = False).",
              "Réseaux : voir A09 (électricité), A10 (plomberie)."]:
        p.ligne(s, 5.7, dy=3.3)
    p.cartouche("1/10 et 1/20")
    p.enregistrer("details_techniques")


PLANCHES = {"A09": A09, "A10": A10, "A11": A11}
