"""Variante maillée de DECIMO_ESQ_V5.ifc pour import Revit.

Chaque représentation « Body » est remplacée par des IfcTriangulatedFaceSet (un par style de surface),
calculés par ifcopenshell.geom avec les ouvertures déjà soustraites. Les IfcOpeningElement et leurs
relations (IfcRelVoidsElement / IfcRelFillsElement) sont supprimés pour que Revit ne tente pas de
recalculer les booléens sur un maillage. Les représentations Axis / Annotation sont conservées,
de même que la hiérarchie, les Psets, les quantités, les matériaux et les classifications.

Usage : python3 scripts/maillage_revit_v5.py v5/DECIMO_ESQ_V5.ifc v5/DECIMO_ESQ_V5_maillage_Revit.ifc
"""
import sys
import multiprocessing
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue

SRC = sys.argv[1] if len(sys.argv) > 1 else "v5/DECIMO_ESQ_V5.ifc"
DST = sys.argv[2] if len(sys.argv) > 2 else "v5/DECIMO_ESQ_V5_maillage_Revit.ifc"

f = ifcopenshell.open(SRC)
body_ctx = next(c for c in f.by_type("IfcGeometricRepresentationSubContext") if c.ContextIdentifier == "Body")

styles = {s.Name: s for s in f.by_type("IfcSurfaceStyle")}
made = {}

by_rendering = {r.id(): s for s in styles.values() for r in s.Styles}

def style_for(mat):
    name = mat.name or ""
    tail = name.rsplit("-", 1)[-1]
    if tail.isdigit() and int(tail) in by_rendering:
        return by_rendering[int(tail)]
    for key in (name, name.replace("surface-style-", "")):
        if key in styles:
            return styles[key]
    for s in styles.values():
        if s.Name and s.Name in name:
            return s
    key = tuple(np.round(mat.diffuse.components, 3)) + (round(float(mat.transparency or 0), 3),)
    if key not in made:
        rgb = f.createIfcColourRgb(None, *[float(c) for c in mat.diffuse.components])
        shading = f.createIfcSurfaceStyleRendering(rgb, float(mat.transparency or 0), None, None, None, None, None, None, "NOTDEFINED")
        made[key] = f.createIfcSurfaceStyle(f"Maillage {name}".strip(), "BOTH", [shading])
    return made[key]

settings = ifcopenshell.geom.settings()
settings.set("convert-back-units", True)
settings.set("weld-vertices", True)

products = [p for p in f.by_type("IfcProduct") if p.Representation and not p.is_a("IfcOpeningElement")]
it = ifcopenshell.geom.iterator(settings, f, multiprocessing.cpu_count(), include=products)
shapes = {}
if it.initialize():
    while True:
        s = it.get()
        shapes[s.id] = s
        if not it.next():
            break

done, skipped, tris = 0, [], 0
for p in products:
    s = shapes.get(p.id())
    if s is None:
        skipped.append(p)
        continue
    g = s.geometry
    v = np.array(g.verts, dtype=float).reshape(-1, 3)
    fa = np.array(g.faces, dtype=int).reshape(-1, 3)
    mids = np.array(g.material_ids, dtype=int) if len(g.material_ids) else np.zeros(len(fa), int)
    items = []
    for mid in sorted(set(mids.tolist())):
        sel = fa[mids == mid]
        if not len(sel):
            continue
        used, inv = np.unique(sel.ravel(), return_inverse=True)
        pts = f.createIfcCartesianPointList3D([tuple(map(float, q)) for q in v[used]])
        fs = f.createIfcTriangulatedFaceSet(pts, None, True, [tuple(int(i) + 1 for i in t) for t in inv.reshape(-1, 3)], None)
        if mid >= 0 and mid < len(g.materials):
            f.createIfcStyledItem(fs, [style_for(g.materials[mid])], None)
        items.append(fs)
        tris += len(sel)
    if not items:
        skipped.append(p)
        continue
    new_body = f.createIfcShapeRepresentation(body_ctx, "Body", "Tessellation", items)
    others = [r for r in p.Representation.Representations if r.RepresentationIdentifier != "Body"]
    old = p.Representation
    p.Representation = f.createIfcProductDefinitionShape(None, None, [new_body] + others)
    ue.remove_deep2(f, old)
    done += 1

for t in f.by_type("IfcTypeProduct"):
    maps = t.RepresentationMaps or ()
    t.RepresentationMaps = None
    for m in maps:
        if not f.get_total_inverses(m):
            ue.remove_deep2(f, m)

for rel in list(f.by_type("IfcRelFillsElement")) + list(f.by_type("IfcRelVoidsElement")):
    f.remove(rel)
for o in list(f.by_type("IfcOpeningElement")):
    for rel in list(o.ContainedInStructure or []) + list(o.IsDefinedBy or []):
        if rel.is_a("IfcRelDefinesByProperties") and len(rel.RelatedObjects) > 1:
            rel.RelatedObjects = [x for x in rel.RelatedObjects if x != o]
        elif rel.is_a("IfcRelContainedInSpatialStructure") and len(rel.RelatedElements) > 1:
            rel.RelatedElements = [x for x in rel.RelatedElements if x != o]
        else:
            f.remove(rel)
    rep = o.Representation
    o.Representation = None
    f.remove(o)
    if rep is not None:
        ue.remove_deep2(f, rep)

proj = f.by_type("IfcProject")[0]
proj.Description = (proj.Description or "") + " — variante maillée (IfcTriangulatedFaceSet) pour import Revit"
f.write(DST)
print(f"écrit {DST} : {done} produits maillés, {tris} triangles, {len(skipped)} sans géométrie")
for p in skipped:
    print("  sans géométrie :", p.is_a(), p.Name)
