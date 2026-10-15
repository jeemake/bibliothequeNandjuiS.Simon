"""Constantes partagées par les scripts V5 (chemins, cotes de l'aménagement, palette).

Repère : celui de la maquette V4 (origine angle intérieur sud-ouest du gros œuvre, x vers l'est,
y de la rue vers le fond, z depuis le sol fini RDC). Toutes les cotes ci-dessous sont en mètres ;
le fichier IFC est en centimètres (unité héritée de la V4).
"""
import os

ICI = os.path.dirname(os.path.abspath(__file__))
V5 = os.path.dirname(ICI)
RACINE = os.path.dirname(V5)
V4_IFC = os.path.join(RACINE, "DECIMO_ESQ_V4.ifc")
V5_IFC = os.path.join(V5, "DECIMO_ESQ_V5.ifc")
V5_REVIT = os.path.join(V5, "DECIMO_ESQ_V5_maille_Revit.ifc")
CACHE = os.path.join(V5, "cache")
DESSINS = os.path.join(V5, "dessins")
VUES = os.path.join(V5, "vues_rendu")
RAPPORTS = os.path.join(V5, "rapports")

# --- niveaux -----------------------------------------------------------------------
Z_SOL = 0.0
Z_FP_SOUS = 3.00          # sous-face du faux-plafond acoustique
Z_FP_DESSUS = 3.04        # dessus des panneaux (ép. 40 mm)
Z_DALLE_SOUS = 3.30       # sous-face de la dalle haute (= arase des murs V4)
Z_DALLE_DESSUS = 3.50     # hypothèse ép. 20 cm, à relever
PLENUM = round(Z_DALLE_SOUS - Z_FP_DESSUS, 3)

# --- arbre à livres V4 et oculus ------------------------------------------------------
ARBRE = (4.75, 5.61)
R_OCULUS = 1.40           # canopée V4 : R 1,30 à +3,28

# --- technique (hypothèses ESQ Ahoua) -------------------------------------------------
PLACARD_EXT = (0.46, 5.16, 1.20, 5.63)    # dans le rangement, adossé à la cloison placo 4350621
PLACARD_NET = (0.53, 5.16, 1.13, 5.56)    # 0,60 x 0,40 net
TABLEAU = (2.66, 0.12, 2.91, 0.72, 1.00, 1.75)   # x0, y0, x1, y1, z0, z1 (0,60 l x 0,25 p)
HABILLAGE_TD = (2.64, 0.10, 2.91, 0.74)
DEGAGEMENT_TD = (1.64, 0.12, 2.64, 0.72)  # 1,00 m libre devant la porte d'habillage
SPLIT1 = (6.285, 4.55, 6.495, 5.35, 2.42, 2.71)  # salle de lecture, mur est, au-dessus des rayonnages
SPLIT2 = (0.09, 3.45, 0.30, 4.25, 2.30, 2.59)    # salle de réunion, mur mitoyen ouest
COFFRAGES = {"EU/EV 1 (WC)": (0.09, 7.11, 0.39, 7.41), "EU/EV 2 (rangement)": (0.09, 5.94, 0.39, 6.24)}
BAIE_ARRIERE = (4.40, 5.05, 2.15, 2.80)   # opening V4 #160 dans le mur 4350589 (y 7,41 - 7,59)
Z_LIAISONS = 3.15
Z_CABLES = 3.24

# --- palette (charte K&Démi + accent indigo) -------------------------------------------
ENCRE = "#4A4A4A"
TAUPE = "#8C8C8C"
TERRE_CUITE = "#B4583E"
IROKO = "#9A6B43"
SABLE = "#E8E8E8"
SABLE_CLAIR = "#F4F4F4"
BLANC_CHAUX = "#FFFFFF"
INDIGO = "#2E3C6E"
POCHE = "#2E2E2E"
