"""Contrôle d'un IFC : schéma + règles EXPRESS (ifcopenshell.validate) et géométrie de chaque produit (ifcopenshell.geom).

Usage : python3 scripts/verifier_ifc_v5.py v5/DECIMO_ESQ_V5.ifc [v5/DECIMO_ESQ_V5_maillage_Revit.ifc ...]
Code retour non nul si une erreur est trouvée.
"""
import collections, logging, sys
import ifcopenshell, ifcopenshell.geom, ifcopenshell.validate

def check(path):
    f = ifcopenshell.open(path)
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, log, express_rules=True)
    errors = [s for s in log.statements if s.get("level", "ERROR") in ("ERROR", logging.ERROR, "error")]
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    prods = [p for p in f.by_type("IfcProduct") if p.Representation and not p.is_a("IfcOpeningElement")]
    fails, tris = [], 0
    for p in prods:
        try:
            sh = ifcopenshell.geom.create_shape(s, p)
            n = len(sh.geometry.faces) // 3
            if n == 0:
                fails.append((p, "géométrie vide"))
            tris += n
        except Exception as e:  # noqa: BLE001
            fails.append((p, str(e)))
    counts = collections.Counter(p.is_a() for p in f.by_type("IfcProduct"))
    print(f"== {path}  ({f.schema})")
    print(f"   validate : {len(errors)} erreur(s)")
    for e in errors[:20]:
        print("    -", str(e.get("message", e))[:300])
    print(f"   geom     : {len(prods) - len(fails)}/{len(prods)} produits avec géométrie OK, {tris} triangles")
    for p, msg in fails[:20]:
        print(f"    - #{p.id()} {p.is_a()} {p.Name!r} : {msg[:200]}")
    print("   classes  :", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return len(errors) + len(fails)

if __name__ == "__main__":
    bad = sum(check(p) for p in sys.argv[1:])
    sys.exit(1 if bad else 0)
