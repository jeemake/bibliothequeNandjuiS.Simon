#!/usr/bin/env bash
# Régénère toute la V5 à partir de DECIMO_ESQ_V4.ifc (à lancer depuis la racine du dépôt).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 v5/scripts/construire_v5.py
python3 v5/scripts/valider_ifc.py v5/DECIMO_ESQ_V5.ifc v5/rapports/validation_V5.txt
python3 v5/scripts/verif_v4_v5.py v5/rapports/verif_v4_v5.md
python3 v5/scripts/variante_revit.py
python3 v5/scripts/valider_ifc.py v5/DECIMO_ESQ_V5_maille_Revit.ifc v5/rapports/validation_V5_maille_Revit.txt
python3 v5/scripts/vues_rendu.py
python3 v5/scripts/dessins.py
python3 v5/scripts/construire_tech.py
python3 v5/scripts/valider_ifc.py v5/DECIMO_ESQ_V5_tech.ifc v5/technique/validation_V5_tech.txt
python3 v5/scripts/verif_v4_v5.py --v5 v5/DECIMO_ESQ_V5_tech.ifc v5/technique/verif_v4_v5_tech.md
python3 v5/scripts/verif_tech.py v5/technique/verif_technique.md
python3 v5/scripts/dessins_tech.py
