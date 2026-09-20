#!/usr/bin/env python3
"""

Quebec Election pour Fleurdelix
Auteur : Dominique Delaire
Dernière version : 2026.09.20
Génère un KMZ 3D des circonscriptions du Québec avec les résultats
des élections provinciales, pour Google Earth Pro.


- Utilise candidats.csv pour avoir les votes par circonscription
- Fait la jointure sur les NOMS de circonscription
- Normalise les noms pour matcher (accents, tirets, etc.)


Usage :
    python3 quebec_elections_3d_v2.py
"""

import sys
import zipfile
import re
from pathlib import Path

try:
    import requests
    import pandas as pd
    import geopandas as gpd
    import simplekml
    from unidecode import unidecode
except ImportError as e:
    print(f"ERREUR : dependance manquante ({e.name})")
    print("Installe avec : pip install geopandas simplekml pandas requests unidecode")
    sys.exit(1)



# CONFIGURATION


ELECTION = "gen2022-10-03"
CARTE = "2022"

# Facteur de hauteur (en metres). Ajuste selon ton gout :
#   50   = tres discret, presque plat
#   150  = doux et lisible (recommande)
#   300  = bien visible mais raisonnable
#   1000 = enorme, masque la carte
FACTEUR_HAUTEUR = 150

# Ce qui determine la hauteur :
#   "pourcentage_gagnant"  -> % du parti gagnant (donne des hauteurs assez uniformes)
#   "marge"                -> ecart avec le 2e  (donne un relief bien contraste,
#                                                 bastions imprenables = grandes tours,
#                                                 circos serrees = petites collines)
#   "participation"        -> taux de participation
CRITERE_HAUTEUR = "marge"

# Transparence des polygones : 100=tres transparent, 200=moyen, 255=opaque
OPACITE = 160

DOSSIER_DATA = Path("data_quebec")
SORTIE_KMZ = "quebec_elections_3d.kmz"

BASE_CARTES = "https://donnees.electionsquebec.qc.ca/autres/provincial"
BASE_RESULTATS = "https://donnees.electionsquebec.qc.ca/production/provincial/resultats/archives"

URLS = {
    "shapefile": f"{BASE_CARTES}/circonscriptions_electorales_{CARTE}_shapefile.zip",
    "candidats": f"{BASE_RESULTATS}/{ELECTION}/candidats.csv",
    "circonscriptions": f"{BASE_RESULTATS}/{ELECTION}/circonscriptions.csv",
}



# COULEURS PAR PARTI
# Les abreviations exactes dans les CSV DGEQ sont "C.A.Q.-E.F.L.",
# "P.L.Q./Q.L.P.", "Q.S.", "P.Q.", etc. On normalise.


def couleur(rgb_hex, alpha=None):
    if alpha is None:
        alpha = OPACITE
    r = int(rgb_hex[1:3], 16)
    g = int(rgb_hex[3:5], 16)
    b = int(rgb_hex[5:7], 16)
    return f"{alpha:02x}{b:02x}{g:02x}{r:02x}"


COULEURS_PARTIS = {
    "CAQ": couleur("#00A9E0"),  # bleu ciel
    "PLQ": couleur("#E60000"),  # rouge
    "QS":  couleur("#FF6600"),  # orange
    "PQ":  couleur("#003DA5"),  # bleu fonce
    "PCQ": couleur("#663399"),  # violet
    "PVQ": couleur("#4CAF50"),  # vert
    "IND": couleur("#888888"),  # gris
}
COULEUR_DEFAUT = couleur("#CCCCCC")


def simplifier_parti(abrev):
    """Normalise l'abreviation d'un parti pour matcher COULEURS_PARTIS."""
    if not abrev or pd.isna(abrev):
        return "IND"
    a = str(abrev).upper().replace(".", "").replace("-", "").replace("/", "")
    a = a.replace(" ", "")
    # Coalition avenir Quebec
    if a.startswith("CAQ") or "EFL" in a:
        return "CAQ"
    # Parti liberal du Quebec / Quebec Liberal Party
    if a.startswith("PLQ") or "QLP" in a:
        return "PLQ"
    # Quebec solidaire
    if a.startswith("QS"):
        return "QS"
    # Parti quebecois
    if a.startswith("PQ"):
        return "PQ"
    # Parti conservateur du Quebec
    if a.startswith("PCQ") or "CONSERV" in a:
        return "PCQ"
    # Parti vert
    if a.startswith("PVQ") or "VERT" in a:
        return "PVQ"
    return "IND"



# NORMALISATION DES NOMS DE CIRCONSCRIPTIONS


def normaliser_nom(nom):
    """
    Normalise un nom de circonscription pour la jointure :
    - Retire les accents
    - Passe en minuscules
    - Remplace tirets et espaces par un separateur unique
    - Retire les caracteres speciaux
    """
    if not nom or pd.isna(nom):
        return ""
    s = unidecode(str(nom))            # accents
    s = s.lower().strip()
    s = re.sub(r"[\s\-\–\—']+", "-", s)  # tirets/espaces/apostrophes → tiret unique
    s = re.sub(r"[^a-z0-9\-]", "", s)   # retire tout le reste
    s = re.sub(r"-+", "-", s).strip("-")
    return s



# TELECHARGEMENT


def telecharger(url, dest):
    if dest.exists():
        print(f"  [OK] Deja present : {dest.name}")
        return dest
    print(f"  [DL] {dest.name}")
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"       -> {dest.stat().st_size / 1024:.0f} Ko")
    return dest


def preparer_fichiers():
    print(f"\n=== Telechargement des donnees ({ELECTION}) ===")
    DOSSIER_DATA.mkdir(exist_ok=True)

    # Shapefile
    shp_zip = DOSSIER_DATA / f"circonscriptions_{CARTE}.zip"
    telecharger(URLS["shapefile"], shp_zip)

    shp_dir = DOSSIER_DATA / f"circonscriptions_{CARTE}"
    if not shp_dir.exists():
        with zipfile.ZipFile(shp_zip) as z:
            z.extractall(shp_dir)

    shp = next(shp_dir.rglob("*.shp"))

    # CSV candidats (votes par candidat/parti/circo, mais avec numero DGEQ seulement)
    csv_candidats = DOSSIER_DATA / f"candidats_{ELECTION}.csv"
    telecharger(URLS["candidats"], csv_candidats)

    # CSV circonscriptions (contient numero + NOM, pour la jointure)
    csv_circo = DOSSIER_DATA / f"circonscriptions_{ELECTION}.csv"
    telecharger(URLS["circonscriptions"], csv_circo)

    return {
        "shapefile": shp,
        "candidats": csv_candidats,
        "circonscriptions": csv_circo,
    }



# TRAITEMENT DES RESULTATS


def lire_csv_dgeq(chemin):
    """Lit un CSV DGEQ (encodage ISO 8859-1, separateur ';')."""
    return pd.read_csv(chemin, encoding="iso-8859-1", sep=";", dtype=str)


def preparer_resultats(csv_candidats):
    """
    Depuis candidats.csv (une ligne par candidat), calcule pour chaque
    circonscription le parti gagnant, son pourcentage et la marge.
    """
    print(f"\n=== Analyse des resultats par candidat ===")
    df = lire_csv_dgeq(csv_candidats)
    print(f"  [CSV] {len(df)} lignes, colonnes : {list(df.columns)}")

    # Noms EXACTS des colonnes dans candidats.csv du DGEQ
    # (verifiés via diagnostic sur les donnees reelles 2022)
    col_circo_num = "Numéro de la circonscription"
    col_parti = "Abréviation du parti politique"
    col_votes = "Nombre total de votes"

    # Verifier que les colonnes existent
    for nom, col in [("circo", col_circo_num), ("parti", col_parti), ("votes", col_votes)]:
        if col not in df.columns:
            print(f"ERREUR : colonne '{col}' introuvable")
            print(f"Colonnes disponibles : {list(df.columns)}")
            sys.exit(1)

    print(f"  [OK] Colonnes utilisees : circo={col_circo_num}, parti={col_parti}, votes={col_votes}")

    df[col_votes] = pd.to_numeric(df[col_votes], errors="coerce").fillna(0)

    # On groupe par NUMERO de circo (unique) puis on garde le nom associe
    # via le CSV circonscriptions pour faire la jointure sur nom apres
    # Mais ici on n'a que le numero. On va donc joindre le shapefile
    # sur le numero de circo apres avoir telecharge circonscriptions.csv
    # qui contient la correspondance numero <-> nom.
    resultats = []
    for num_circo, groupe in df.groupby(col_circo_num):
        total = groupe[col_votes].sum()
        if total == 0:
            continue

        agg = groupe.groupby(col_parti)[col_votes].sum().sort_values(ascending=False)
        if len(agg) == 0:
            continue

        parti_gagnant_brut = agg.index[0]
        votes_gagnant = agg.iloc[0]
        pct_gagnant = (votes_gagnant / total) * 100
        pct_deuxieme = (agg.iloc[1] / total * 100) if len(agg) > 1 else 0

        resultats.append({
            "num_circo": str(num_circo).strip(),
            "parti_gagnant": simplifier_parti(parti_gagnant_brut),
            "parti_gagnant_brut": parti_gagnant_brut,
            "pourcentage_gagnant": pct_gagnant,
            "marge": pct_gagnant - pct_deuxieme,
            "votes_gagnant": int(votes_gagnant),
            "votes_totaux": int(total),
        })

    df_res = pd.DataFrame(resultats)
    print(f"  [RES] {len(df_res)} circonscriptions traitees")
    print(f"  [RES] Repartition des gagnants :")
    for p, n in df_res["parti_gagnant"].value_counts().items():
        print(f"        {p} : {n}")

    return df_res



# GEOMETRIE + JOINTURE


def charger_geometries(shapefile, df_resultats, csv_circonscriptions):
    print(f"\n=== Geometries ===")
    gdf = gpd.read_file(shapefile)
    print(f"  [GEO] {len(gdf)} circonscriptions, colonnes : {list(gdf.columns)}")

    # Reprojection WGS84
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        print(f"  [GEO] Reprojection {gdf.crs} -> WGS84")
        gdf = gdf.to_crs(epsg=4326)

    # Etape 1 : joindre le CSV circonscriptions au df_resultats pour recuperer les NOMS
    print(f"  [JOIN] Lecture de circonscriptions.csv pour matcher numero <-> nom")
    df_circo = lire_csv_dgeq(csv_circonscriptions)
    col_num = "Numéro de la circonscription"
    col_nom = "Nom de la circonscription"

    if col_num not in df_circo.columns or col_nom not in df_circo.columns:
        print(f"ERREUR : colonnes manquantes dans circonscriptions.csv")
        print(f"Colonnes : {list(df_circo.columns)}")
        sys.exit(1)

    df_circo["num_circo"] = df_circo[col_num].astype(str).str.strip()
    df_circo["nom_circo_norm"] = df_circo[col_nom].apply(normaliser_nom)
    correspondance = df_circo[["num_circo", "nom_circo_norm", col_nom]].rename(
        columns={col_nom: "nom_circo_csv"}
    )

    df_resultats["num_circo"] = df_resultats["num_circo"].astype(str).str.strip()
    df_resultats = df_resultats.merge(correspondance, on="num_circo", how="left")
    print(f"  [JOIN] Correspondance numero->nom : "
          f"{df_resultats['nom_circo_norm'].notna().sum()}/{len(df_resultats)}")

    # Etape 2 : normaliser les noms du shapefile
    gdf["nom_circo_norm"] = gdf["NM_CEP"].apply(normaliser_nom)

    # Etape 3 : jointure finale shapefile <-> resultats sur nom normalise
    gdf = gdf.merge(df_resultats, on="nom_circo_norm", how="left")

    nb_ok = gdf["parti_gagnant"].notna().sum()
    print(f"  [JOIN] Final : {nb_ok}/{len(gdf)} circos avec resultats")

    if nb_ok < len(gdf):
        manquantes = gdf[gdf["parti_gagnant"].isna()]["NM_CEP"].tolist()
        print(f"  [WARN] Noms shapefile sans match : {manquantes[:10]}")
        # Debug : afficher quelques exemples de normalisation
        print(f"  [DEBUG] Exemples shapefile normalises : "
              f"{gdf['nom_circo_norm'].head(5).tolist()}")
        print(f"  [DEBUG] Exemples CSV normalises : "
              f"{df_resultats['nom_circo_norm'].head(5).tolist()}")

    return gdf



# GENERATION KML


def creer_kml(gdf):
    print(f"\n=== Generation KML ===")
    kml = simplekml.Kml(name=f"Elections Quebec {CARTE} - 3D")
    kml.document.description = (
        f"Resultats provinciaux du {ELECTION} en 3D. "
        f"Hauteur = {CRITERE_HAUTEUR}, facteur = {FACTEUR_HAUTEUR} m."
    )

    # DEUX couches :
    # 1. Couche "plate au sol" : colorie clairement le territoire (toujours visible)
    # 2. Couche "3D extrudee" : donne le relief selon les resultats
    dossier_2d = kml.newfolder(name="Couche 2D - Vue plate (base)")
    dossier_2d.description = "Circonscriptions colorees par parti gagnant, au sol"

    dossier_3d = kml.newfolder(name="Couche 3D - Reliefs (extrusion)")
    dossier_3d.description = f"Hauteur des tours selon '{CRITERE_HAUTEUR}'"

    # Sous-dossiers par parti dans chaque couche (permet de filtrer)
    dossiers_2d = {}
    dossiers_3d = {}
    n_polys = 0

    for _, row in gdf.iterrows():
        parti_raw = row.get("parti_gagnant")
        parti = parti_raw if isinstance(parti_raw, str) else "AUCUN"

        pct = row.get("pourcentage_gagnant")
        pct = float(pct) if pd.notna(pct) else 0.0

        marge = row.get("marge")
        marge = float(marge) if pd.notna(marge) else 0.0

        votes_g = row.get("votes_gagnant")
        votes_g = int(votes_g) if pd.notna(votes_g) else 0

        votes_t = row.get("votes_totaux")
        votes_t = int(votes_t) if pd.notna(votes_t) else 0

        nom = row.get("NM_CEP", "?")
        code = row.get("CO_CEP", "?")

        # Choisir critere de hauteur
        val = marge if CRITERE_HAUTEUR == "marge" else pct
        hauteur = max(50, val * FACTEUR_HAUTEUR)  # minimum 50m pour toujours voir

        col_kml = COULEURS_PARTIS.get(parti, COULEUR_DEFAUT)
        col_bordure_kml = couleur("#FFFFFF", alpha=200)  # bordure blanche semi-opaque

        desc = (
            f"<![CDATA["
            f"<h3>{nom}</h3>"
            f"<p><b>Code CEP :</b> {code}</p>"
            f"<p><b>Parti gagnant :</b> {parti}</p>"
            f"<p><b>Pourcentage :</b> {pct:.1f}%</p>"
            f"<p><b>Marge de victoire :</b> {marge:.1f} points</p>"
            f"<p><b>Votes du gagnant :</b> {votes_g:,}</p>"
            f"<p><b>Total votes exprimes :</b> {votes_t:,}</p>"
            f"]]>"
        )

        # Sous-dossiers par parti
        if parti not in dossiers_2d:
            dossiers_2d[parti] = dossier_2d.newfolder(name=f"{parti}")
            dossiers_3d[parti] = dossier_3d.newfolder(name=f"{parti}")

        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)

        for poly in polys:
            coords_2d = list(poly.exterior.coords)
            coords_3d = [(x, y, hauteur) for x, y in coords_2d]

            # --- Couche 2D (plate au sol) ---
            pol_2d = dossiers_2d[parti].newpolygon(name=str(nom), description=desc)
            pol_2d.outerboundaryis = coords_2d
            for interior in poly.interiors:
                pol_2d.innerboundaryis = list(interior.coords)
            pol_2d.altitudemode = simplekml.AltitudeMode.clamptoground
            pol_2d.tessellate = 1
            pol_2d.style.polystyle.color = couleur(
                # meme couleur mais plus opaque au sol
                f"#{COULEURS_PARTIS.get(parti, COULEUR_DEFAUT)[6:8]}"
                f"{COULEURS_PARTIS.get(parti, COULEUR_DEFAUT)[4:6]}"
                f"{COULEURS_PARTIS.get(parti, COULEUR_DEFAUT)[2:4]}",
                alpha=140,
            ) if False else col_kml
            pol_2d.style.polystyle.fill = 1
            pol_2d.style.polystyle.outline = 1
            pol_2d.style.linestyle.color = col_bordure_kml
            pol_2d.style.linestyle.width = 1.5

            # --- Couche 3D (extrudee) ---
            pol_3d = dossiers_3d[parti].newpolygon(name=str(nom), description=desc)
            pol_3d.outerboundaryis = coords_3d
            for interior in poly.interiors:
                pol_3d.innerboundaryis = [(x, y, hauteur) for x, y in interior.coords]
            pol_3d.extrude = 1
            pol_3d.altitudemode = simplekml.AltitudeMode.relativetoground
            pol_3d.tessellate = 1
            pol_3d.style.polystyle.color = col_kml
            pol_3d.style.polystyle.fill = 1
            pol_3d.style.polystyle.outline = 1
            pol_3d.style.linestyle.color = couleur("#FFFFFF", alpha=120)
            pol_3d.style.linestyle.width = 0.5

            n_polys += 1

    print(f"  [KML] {n_polys} polygones (x2 = couche 2D + 3D)")
    return kml



# program principal main


def main():
    print("=" * 60)
    print(" QUEBEC ELECTIONS 3D - v2 (avec noms de circo)")
    print("=" * 60)

    fichiers = preparer_fichiers()
    df_res = preparer_resultats(fichiers["candidats"])
    gdf = charger_geometries(fichiers["shapefile"], df_res, fichiers["circonscriptions"])
    kml = creer_kml(gdf)

    print(f"\n=== Sauvegarde ===")
    kml.savekmz(SORTIE_KMZ)
    print(f"  [OK] {SORTIE_KMZ} ({Path(SORTIE_KMZ).stat().st_size / 1024:.0f} Ko)")

    print(f"\n{'=' * 60}")
    print(f" Ouvre {SORTIE_KMZ} dans Google Earth Pro Desktop")
    print(f" (pas la version web qui n'affiche pas la 3D correctement)")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
