#!/usr/bin/env python3
"""
Version 2D pour Google My Maps.
Auteur : Dominique Delaire
Dernière version : 2026.09.20
- Inclut les noms des 2 premiers candidats par circonscription et les scores
Objectif : rester sous les 5 Mo de limite d'import Google My Maps
en simplifiant les geometries. Google My Maps ne gerant pas la 3D,
ce script produit une carte plate coloree par parti gagnant.

Prerequis (deja installes) :
    geopandas simplekml pandas unidecode

Usage :

    python3 quebec_elections_2d_pourgooglemapsavecnomcandidat.py
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

    # Colonnes optionnelles pour les noms de candidats
    has_noms = "Nom" in df.columns and "Prénom" in df.columns

    def format_candidat(row):
        if not has_noms:
            return ""
        prenom = str(row.get("Prénom", "") or "").strip()
        nom = str(row.get("Nom", "") or "").strip()
        return f"{prenom} {nom}".strip()

    resultats = []
    for num, groupe in df.groupby("Numéro de la circonscription"):
        total = groupe["Nombre total de votes"].sum()
        if total == 0:
            continue

        # Trier par votes decroissants pour recuperer le nom du candidat
        groupe_trie = groupe.sort_values(
            "Nombre total de votes", ascending=False
        ).reset_index(drop=True)

        gagnant = groupe_trie.iloc[0]
        votes_g = float(gagnant["Nombre total de votes"])
        pct = (votes_g / total) * 100
        parti_g_brut = str(gagnant["Abréviation du parti politique"])

        if len(groupe_trie) > 1:
            deuxieme = groupe_trie.iloc[1]
            votes_d = float(deuxieme["Nombre total de votes"])
            pct2 = (votes_d / total) * 100
            parti_d_brut = str(deuxieme["Abréviation du parti politique"])
            candidat_d = format_candidat(deuxieme)
        else:
            votes_d = 0
            pct2 = 0
            parti_d_brut = ""
            candidat_d = ""

        resultats.append({
            "num_circo": str(num).strip(),
            "parti_gagnant": simplifier_parti(parti_g_brut),
            "candidat_gagnant": format_candidat(gagnant),
            "pourcentage_gagnant": pct,
            "votes_gagnant": int(votes_g),
            "parti_deuxieme": simplifier_parti(parti_d_brut) if parti_d_brut else "",
            "candidat_deuxieme": candidat_d,
            "pourcentage_deuxieme": pct2,
            "votes_deuxieme": int(votes_d),
            "marge": pct - pct2,
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

    # STYLES NOMMES au niveau du document : Google My Maps les reconnait
    # mieux que les styles inline sur chaque polygone.
    styles_kml = {}
    for parti_code, couleur_hex in COULEURS_PARTIS.items():
        style = simplekml.Style()
        style.polystyle.color = couleur_hex
        style.polystyle.fill = 1
        style.polystyle.outline = 1
        style.linestyle.color = couleur_kml("#FFFFFF", alpha=140)
        style.linestyle.width = 0.8
        styles_kml[parti_code] = style

    # Style pour les circonscriptions sans resultat
    style_defaut = simplekml.Style()
    style_defaut.polystyle.color = COULEUR_DEFAUT
    style_defaut.polystyle.fill = 1
    style_defaut.linestyle.color = couleur_kml("#FFFFFF", alpha=140)
    style_defaut.linestyle.width = 0.8

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

        # Nouvelles infos
        candidat_g_raw = row.get("candidat_gagnant")
        candidat_g = str(candidat_g_raw) if pd.notna(candidat_g_raw) and candidat_g_raw else "-"

        parti_2_raw = row.get("parti_deuxieme")
        parti_2 = str(parti_2_raw) if pd.notna(parti_2_raw) and parti_2_raw else "-"

        candidat_2_raw = row.get("candidat_deuxieme")
        candidat_2 = str(candidat_2_raw) if pd.notna(candidat_2_raw) and candidat_2_raw else "-"

        pct_2 = float(row.get("pourcentage_deuxieme") or 0)
        votes_2 = int(row.get("votes_deuxieme") or 0)

        val = marge if CRITERE_HAUTEUR == "marge" else pct
        hauteur = max(50, val * FACTEUR_HAUTEUR)

        # Description enrichie avec 1er et 2e
        desc = (
            f"<![CDATA["
            f"<b>🥇 1er - {parti}</b><br>"
            f"{candidat_g}<br>"
            f"{pct:.1f}% ({votes_g:,} votes)<br><br>"
            f"<b>🥈 2e - {parti_2}</b><br>"
            f"{candidat_2}<br>"
            f"{pct_2:.1f}% ({votes_2:,} votes)<br><br>"
            f"<b>Marge :</b> {marge:.1f} pts<br>"
            f"<b>Total :</b> {votes_t:,} votes"
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

            # Application du style : d'abord la reference au style nomme,
            # puis on force aussi le style inline (double securite pour
            # les visualiseurs qui ignorent l'un ou l'autre)
            style_a_utiliser = styles_kml.get(parti, style_defaut)
            pol.style = style_a_utiliser

            n_polys += 1

    print(f"  {n_polys} polygones crees (une seule couche)")
    return kml



# programme principal main dom


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
