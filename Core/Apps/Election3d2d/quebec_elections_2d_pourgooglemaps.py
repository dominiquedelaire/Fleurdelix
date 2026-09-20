#!/usr/bin/env python3
"""
Version 2D pour Google My Maps.

Quebec Election pour Fleurdelix
Auteur : Dominique Delaire
Dernière version : 2026.09.20

Objectif : rester sous les 5 Mo de limite d'import Google My Maps
en simplifiant les geometries. Google My Maps ne gerant pas la 3D,
ce script produit une carte plate  par parti gagnant.



Usage :

    python3 quebec_elections_2d_pourgooglemaps.py
"""

import sys
import re
import zipfile
from pathlib import Path

try:
    import pandas as pd
    import geopandas as gpd
    import simplekml
    from unidecode import unidecode
except ImportError as e:
    print(f"ERREUR : dependance manquante ({e.name})")
    sys.exit(1)



# CONFIGURATION

ELECTION = "gen2022-10-03"
CARTE = "2022"
DOSSIER_DATA = Path("data_quebec")
SORTIE_KMZ = "quebec_elections_2d.kmz"

# Facteur d'extrusion (pareil que v2 ameliore)
FACTEUR_HAUTEUR = 150
CRITERE_HAUTEUR = "marge"  # "marge" ou "pourcentage_gagnant"
OPACITE = 180

# Simplification des geometries (en degres decimaux WGS84)
# 0.001 = ~100m au Quebec  -> tres leger
# 0.0005 = ~50m            -> leger et propre
# 0.0002 = ~20m            -> qualite quasi originale
# 0     = pas de simplification
TOLERANCE_SIMPLIFICATION = 0.0005



# COULEURS


def couleur_kml(rgb_hex, alpha=OPACITE):
    r = int(rgb_hex[1:3], 16)
    g = int(rgb_hex[3:5], 16)
    b = int(rgb_hex[5:7], 16)
    return f"{alpha:02x}{b:02x}{g:02x}{r:02x}"


COULEURS_PARTIS = {
    "CAQ": couleur_kml("#00A9E0"),
    "PLQ": couleur_kml("#E60000"),
    "QS":  couleur_kml("#FF6600"),
    "PQ":  couleur_kml("#003DA5"),
    "PCQ": couleur_kml("#663399"),
    "PVQ": couleur_kml("#4CAF50"),
    "IND": couleur_kml("#888888"),
}
COULEUR_DEFAUT = couleur_kml("#CCCCCC")


def simplifier_parti(abrev):
    if not abrev or pd.isna(abrev):
        return "IND"
    a = str(abrev).upper().replace(".", "").replace("-", "").replace("/", "").replace(" ", "")
    if a.startswith("CAQ") or "EFL" in a: return "CAQ"
    if a.startswith("PLQ") or "QLP" in a: return "PLQ"
    if a.startswith("QS"): return "QS"
    if a.startswith("PQ"): return "PQ"
    if a.startswith("PCQ") or "CONSERV" in a: return "PCQ"
    if a.startswith("PVQ") or "VERT" in a: return "PVQ"
    return "IND"


def normaliser_nom(nom):
    if not nom or pd.isna(nom):
        return ""
    s = unidecode(str(nom)).lower().strip()
    s = re.sub(r"[\s\-\–\—']+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    return re.sub(r"-+", "-", s).strip("-")


def lire_csv_dgeq(chemin):
    return pd.read_csv(chemin, encoding="iso-8859-1", sep=";", dtype=str)



# PREPARATION DES DONNEES


def preparer_donnees():
    shp_dir = DOSSIER_DATA / f"circonscriptions_{CARTE}"
    if not shp_dir.exists():
        shp_zip = DOSSIER_DATA / f"circonscriptions_{CARTE}.zip"
        if shp_zip.exists():
            with zipfile.ZipFile(shp_zip) as z:
                z.extractall(shp_dir)
        else:
            print("ERREUR : lance d'abord quebec_elections_3d_v2.py")
            sys.exit(1)

    shp = next(shp_dir.rglob("*.shp"))
    csv_candidats = DOSSIER_DATA / f"candidats_{ELECTION}.csv"
    csv_circo = DOSSIER_DATA / f"circonscriptions_{ELECTION}.csv"

    print("Analyse des resultats...")
    df = lire_csv_dgeq(csv_candidats)
    df["Nombre total de votes"] = pd.to_numeric(
        df["Nombre total de votes"], errors="coerce"
    ).fillna(0)

    resultats = []
    for num, groupe in df.groupby("Numéro de la circonscription"):
        total = groupe["Nombre total de votes"].sum()
        if total == 0:
            continue
        agg = groupe.groupby("Abréviation du parti politique")[
            "Nombre total de votes"
        ].sum().sort_values(ascending=False)
        pct = (agg.iloc[0] / total) * 100
        pct2 = (agg.iloc[1] / total * 100) if len(agg) > 1 else 0
        resultats.append({
            "num_circo": str(num).strip(),
            "parti_gagnant": simplifier_parti(agg.index[0]),
            "pourcentage_gagnant": pct,
            "marge": pct - pct2,
            "votes_gagnant": int(agg.iloc[0]),
            "votes_totaux": int(total),
        })
    df_res = pd.DataFrame(resultats)

    df_circo = lire_csv_dgeq(csv_circo)
    df_circo["num_circo"] = df_circo["Numéro de la circonscription"].astype(str).str.strip()
    df_circo["nom_circo_norm"] = df_circo["Nom de la circonscription"].apply(normaliser_nom)
    df_res = df_res.merge(
        df_circo[["num_circo", "nom_circo_norm"]], on="num_circo", how="left"
    )

    print("Chargement du shapefile...")
    gdf = gpd.read_file(shp)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # SIMPLIFICATION DES GEOMETRIES (etape clef pour la taille)
    if TOLERANCE_SIMPLIFICATION > 0:
        print(f"Simplification des geometries (tolerance={TOLERANCE_SIMPLIFICATION})...")
        avant = sum(len(g.exterior.coords) if g.geom_type == "Polygon"
                    else sum(len(p.exterior.coords) for p in g.geoms)
                    for g in gdf.geometry)
        gdf["geometry"] = gdf.geometry.simplify(
            TOLERANCE_SIMPLIFICATION, preserve_topology=True
        )
        apres = sum(len(g.exterior.coords) if g.geom_type == "Polygon"
                    else sum(len(p.exterior.coords) for p in g.geoms)
                    for g in gdf.geometry)
        print(f"  Points reduits : {avant:,} -> {apres:,} ({apres/avant*100:.1f}%)")

    gdf["nom_circo_norm"] = gdf["NM_CEP"].apply(normaliser_nom)
    gdf = gdf.merge(df_res, on="nom_circo_norm", how="left")

    return gdf



# GENERATION KML LIGHT (une seule couche 3D)


def creer_kml_light(gdf):
    print(f"\nGeneration KML light (une seule couche 3D)...")
    kml = simplekml.Kml(name=f"Elections Quebec {CARTE}")
    kml.document.description = (
        f"Resultats {ELECTION}. Hauteur des extrusions = {CRITERE_HAUTEUR}."
    )

    dossiers = {}
    n_polys = 0

    for _, row in gdf.iterrows():
        parti_raw = row.get("parti_gagnant")
        parti = parti_raw if isinstance(parti_raw, str) else "AUCUN"

        pct = float(row.get("pourcentage_gagnant") or 0)
        marge = float(row.get("marge") or 0)
        votes_g = int(row.get("votes_gagnant") or 0)
        votes_t = int(row.get("votes_totaux") or 0)
        nom = row.get("NM_CEP", "?")

        val = marge if CRITERE_HAUTEUR == "marge" else pct
        hauteur = max(50, val * FACTEUR_HAUTEUR)

        col = COULEURS_PARTIS.get(parti, COULEUR_DEFAUT)

        # Description compacte
        desc = (
            f"<![CDATA["
            f"<b>{parti}</b> - {pct:.1f}% (marge {marge:.1f} pts)<br>"
            f"Votes : {votes_g:,} / {votes_t:,}"
            f"]]>"
        )

        if parti not in dossiers:
            dossiers[parti] = kml.newfolder(name=parti)

        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
        for poly in polys:
            coords = [(x, y, hauteur) for x, y in poly.exterior.coords]
            pol = dossiers[parti].newpolygon(name=str(nom), description=desc)
            pol.outerboundaryis = coords
            for interior in poly.interiors:
                pol.innerboundaryis = [(x, y, hauteur) for x, y in interior.coords]

            pol.extrude = 1
            pol.altitudemode = simplekml.AltitudeMode.relativetoground
            pol.tessellate = 1
            pol.style.polystyle.color = col
            pol.style.polystyle.fill = 1
            pol.style.polystyle.outline = 1
            pol.style.linestyle.color = couleur_kml("#FFFFFF", alpha=140)
            pol.style.linestyle.width = 0.5

            n_polys += 1

    print(f"  {n_polys} polygones crees (une seule couche)")
    return kml



# programme principal main


def main():
    print("=" * 60)
    print(" QUEBEC ELECTIONS - VERSION LIGHT POUR GOOGLE MY MAPS")
    print("=" * 60)
    print(f" Simplification : tolerance={TOLERANCE_SIMPLIFICATION}")
    print(f" Hauteur : critere={CRITERE_HAUTEUR}, facteur={FACTEUR_HAUTEUR}")

    gdf = preparer_donnees()
    print(f"  {len(gdf)} circonscriptions")

    kml = creer_kml_light(gdf)

    print(f"\nSauvegarde...")
    kml.savekmz(SORTIE_KMZ)
    taille_ko = Path(SORTIE_KMZ).stat().st_size / 1024
    taille_mo = taille_ko / 1024
    print(f"  [OK] {SORTIE_KMZ}")
    print(f"       -> {taille_ko:.0f} Ko ({taille_mo:.2f} Mo)")

    if taille_mo > 5:
        print(f"\n  [WARN] Toujours au-dessus de 5 Mo pour Google My Maps.")
        print(f"  Augmente TOLERANCE_SIMPLIFICATION dans le script :")
        print(f"    0.001 = ~100m (plus leger)")
        print(f"    0.002 = ~200m (encore plus leger)")
    else:
        print(f"\n  [OK] Sous 5 Mo, compatible Google My Maps !")

    print(f"\n{'=' * 60}")
    print(f" IMPORT DANS GOOGLE MY MAPS :")
    print(f"   1. Va sur https://mymaps.google.com")
    print(f"   2. Cree une nouvelle carte")
    print(f"   3. Calque -> Importer -> glisse {SORTIE_KMZ}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
