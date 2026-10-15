"""Quantitatif des lots techniques (électricité, plomberie, fixations) tiré de v5/DECIMO_ESQ_V5.ifc."""
import os, sys, csv
from collections import defaultdict
import numpy as np
from shapely.geometry import LineString
import ifcopenshell
import ifcopenshell.util.element as ue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import V5_IFC, RACINE

LOTS = ("Technique - électricité (hyp. ESQ Ahoua)", "Technique - plomberie (hyp. ESQ Ahoua)", "Technique - fixations (hyp. ESQ Ahoua)")
OUT_MD = os.path.join(RACINE, "v5", "rapports", "quantites_lots_techniques.md")
OUT_CSV = os.path.join(RACINE, "v5", "rapports", "quantites_lots_techniques.csv")


def directrices(p):
    out = []
    if p.Representation is None:
        return out
    for rep in p.Representation.Representations:
        if rep.RepresentationIdentifier != "Body":
            continue
        for it in rep.Items:
            if it.is_a("IfcSweptDiskSolid") and it.Directrix.is_a("IfcPolyline"):
                out.append(np.array([q.Coordinates for q in it.Directrix.Points], float) / 100.0)
    return out


def longueur(dirs):
    return sum(LineString(d).length for d in dirs)


def collect():
    f = ifcopenshell.open(V5_IFC)
    by_lot = defaultdict(list)
    circuits = []
    cables = defaultdict(float)
    pipes = defaultdict(lambda: defaultdict(float))
    fittings = defaultdict(int)
    for p in f.by_type("IfcProduct"):
        lot = ue.get_psets(p).get("KDEMI_Esquisse", {}).get("Lot") or ""
        if lot not in LOTS:
            continue
        by_lot[lot].append(p)
        dirs = directrices(p)
        ps_e = ue.get_psets(p).get("KDEMI_Electricite", {})
        if p.is_a("IfcCableSegment") and ps_e.get("Circuit"):
            cables[ps_e["Circuit"]] += longueur(dirs)
        ps_p = ue.get_psets(p).get("KDEMI_Plomberie", {})
        if p.is_a("IfcPipeSegment") and ps_p.get("Reseau"):
            key = (ps_p["Reseau"], str(ps_p.get("DN_mm", "")))
            pipes[ps_p["Reseau"]][key[1]] += longueur(dirs)
        if p.is_a() in ("IfcValve", "IfcPipeFitting", "IfcFlowMeter", "IfcWasteTerminal"):
            fittings[p.is_a()] += 1
    for s in f.by_type("IfcDistributionCircuit"):
        c = ue.get_psets(s).get("KDEMI_Circuit", {})
        circuits.append(c.get("Code", s.Name))
    counts = {}
    for lot, els in by_lot.items():
        counts[lot] = defaultdict(int)
        for p in els:
            counts[lot][p.is_a()] += 1
    pc = sum(1 for p in by_lot[LOTS[0]] if p.is_a("IfcOutlet") and getattr(p, "PredefinedType", None) != "DATAOUTLET")
    rj = sum(1 for p in by_lot[LOTS[0]] if p.is_a("IfcOutlet") and getattr(p, "PredefinedType", None) == "DATAOUTLET")
    sw = sum(1 for p in by_lot[LOTS[0]] if p.is_a("IfcSwitchingDevice"))
    baes = sum(1 for p in by_lot[LOTS[0]] if p.is_a("IfcLightFixture") and getattr(p, "PredefinedType", None) == "SECURITYLIGHTING")
    return dict(counts=counts, circuits=sorted(set(circuits)), cables=cables, pipes=pipes, fittings=fittings,
                pc=pc, rj=rj, sw=sw, baes=baes, cab_total=sum(cables.values()))


def ecrire(data):
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    lines = ["# Quantitatif — lots techniques V5 (hyp. ESQ Ahoua)\n", f"Source : `{V5_IFC}`\n"]
    lines.append("## Électricité\n")
    lines.append(f"- Circuits IFC : **{len(data['circuits'])}** ({', '.join(data['circuits'])})\n")
    lines.append(f"- Prises PC 16 A : **{data['pc']}** · RJ45 : **{data['rj']}** · Commandes : **{data['sw']}** · BAES : **{data['baes']}**\n")
    lines.append(f"- Longueur câbles (directrices, tous tronçons) : **{data['cab_total']:.1f} m**\n")
    for c, L in sorted(data["cables"].items()):
        lines.append(f"  - {c} : {L:.1f} m\n")
    lines.append("\n## Plomberie (longueurs tuyaux)\n")
    for reseau, dns in sorted(data["pipes"].items()):
        tot = sum(dns.values())
        lines.append(f"- **{reseau}** : {tot:.2f} m\n")
        for dn, L in sorted(dns.items(), key=lambda x: -x[1]):
            lines.append(f"  - DN {dn} mm : {L:.2f} m\n")
    lines.append("\n## Fixations et autres\n")
    for lot, d in data["counts"].items():
        lines.append(f"### {lot}\n")
        for cls, n in sorted(d.items(), key=lambda x: -x[1]):
            lines.append(f"- {cls} : {n}\n")
    with open(OUT_MD, "w", encoding="utf-8") as fo:
        fo.writelines(lines)
    rows = [["Lot", "Classe", "Quantite", "Detail", "Valeur"]]
    for lot, d in data["counts"].items():
        for cls, n in sorted(d.items()):
            rows.append([lot, cls, n, "", ""])
    rows.append(["Électricité", "Longueur câbles totale", "", "m", f"{data['cab_total']:.2f}"])
    for c, L in sorted(data["cables"].items()):
        rows.append(["Électricité", f"Câble circuit {c}", "", "m", f"{L:.2f}"])
    for reseau, dns in sorted(data["pipes"].items()):
        for dn, L in sorted(dns.items()):
            rows.append(["Plomberie", reseau, "", f"DN {dn} mm · m", f"{L:.2f}"])
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fo:
        csv.writer(fo, delimiter=";").writerows(rows)
    return OUT_MD, OUT_CSV


if __name__ == "__main__":
    paths = ecrire(collect())
    print(*paths, sep="\n")
