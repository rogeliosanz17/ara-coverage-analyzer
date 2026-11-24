#!/usr/bin/env python3
"""
Analizador de cobertura 5G rural — datasets ARA (IEEE DataPort).

Lee los dos CSV de mediciones RF de campo de ARA Wireless Living Lab
(Iowa State University, Iowa rural, infraestructura Ericsson COTS 5G, banda n77)
y produce un informe de cobertura en Markdown (informe.md):

  Set 1 (DOI 10.21227/7np5-4e05) — RSRP espacio-temporal, 56,122 muestras:
    * Rejilla geográfica de ~0.005° x 0.005° con mediana de RSRP por celda.
    * Zonas débiles: celdas con mediana < -110 dBm y >= 30 muestras.
    * % de muestras por clase de cobertura (sobre las 56,122 muestras;
      el RSRP no tiene faltantes en este set).

  Set 2 (DOI 10.21227/p2a8-f326) — mediciones de UE, 7,144 filas:
    * Distribución por clase de SINR (n numérico efectivo; hay filas sin
      bloque de radio y 11 placeholders '-' por diseño de campaña).
    * Cruce SINR -> throughput mediano (downlink y uplink por separado)
      usando solo filas con ambos datos; se reporta el n de cada clase.

QUÉ NO ES: no es una rApp ni una xApp. Los datos son mediciones RF por
muestra de un UE en campo, NO contadores PM de 15 minutos ni alarmas FM
de operador. Esta herramienta no valida rApps.

Uso:
    python3 analizador.py [--salida informe.md]
Las rutas de los CSV están fijadas a la biblioteca local de datasets;
se pueden sobreescribir con las variables de entorno ARA_SET1_CSV y
ARA_SET2_CSV.
"""

import argparse
import os
import sys

import pandas as pd

HOME = os.path.expanduser("~")
SET1_CSV = os.environ.get(
    "ARA_SET1_CSV",
    os.path.join(
        HOME,
        "workspace/datasets/ara-cots-5g-rsrp/extraido/"
        "ARA_COTS_5G_NR_Spatio_Temperal_Dataset/"
        "ARA_COTS_5G_NR_Spatio_Temporal_Dataset.csv",
    ),
)
SET2_CSV = os.environ.get(
    "ARA_SET2_CSV",
    os.path.join(
        HOME,
        "workspace/datasets/ara-cots-5g-ue-channel/extraido/"
        "ARA_Rural_COTS_5G_Dataset/COTS.csv",
    ),
)

CELDA = 0.005          # ~0.005 grados lat/lon (~550 m x ~460 m en Iowa)
UMBRAL_DEBIL = -110.0  # dBm, mediana de celda
MIN_MUESTRAS = 30      # mínimo de muestras por celda para declarar zona débil

CLASES_RSRP = [
    ("Excelente", lambda s: s >= -80),
    ("Buena", lambda s: (s >= -90) & (s < -80)),
    ("Regular", lambda s: (s >= -100) & (s < -90)),
    ("Débil", lambda s: (s >= -110) & (s < -100)),
    ("Muy débil", lambda s: s < -110),
]

CLASES_SINR = [
    ("Excelente", lambda s: s >= 20),
    ("Buena", lambda s: (s >= 10) & (s < 20)),
    ("Regular", lambda s: (s >= 0) & (s < 10)),
    ("Mala", lambda s: s < 0),
]


def fmt(x, dec=2):
    return f"{x:,.{dec}f}"


def analizar_set1(ruta):
    df = pd.read_csv(ruta)
    total = len(df)
    rsrp = pd.to_numeric(df["RSRP"], errors="coerce").dropna()

    # --- Clases de cobertura sobre todas las muestras con RSRP ---
    clases = []
    for nombre, cond in CLASES_RSRP:
        n = int(cond(rsrp).sum())
        clases.append((nombre, n, 100.0 * n / len(rsrp)))

    # --- Rejilla geográfica (solo filas georreferenciadas) ---
    geo = df.dropna(subset=["Latitude", "Longitude"]).copy()
    geo["RSRP"] = pd.to_numeric(geo["RSRP"], errors="coerce")
    geo = geo.dropna(subset=["RSRP"])
    import math
    geo["lat_bin"] = geo["Latitude"].apply(lambda v: math.floor(v / CELDA) * CELDA)
    geo["lon_bin"] = geo["Longitude"].apply(lambda v: math.floor(v / CELDA) * CELDA)
    rejilla = (
        geo.groupby(["lat_bin", "lon_bin"])["RSRP"]
        .agg(["median", "count", "min", "max"])
        .reset_index()
        .rename(columns={"median": "rsrp_mediana", "count": "muestras",
                         "min": "rsrp_min", "max": "rsrp_max"})
    )
    rejilla["lat_centro"] = (rejilla["lat_bin"] + CELDA / 2).round(5)
    rejilla["lon_centro"] = (rejilla["lon_bin"] + CELDA / 2).round(5)

    zonas = rejilla[
        (rejilla["rsrp_mediana"] < UMBRAL_DEBIL) & (rejilla["muestras"] >= MIN_MUESTRAS)
    ].sort_values(["rsrp_mediana", "muestras"], ascending=[True, False])

    return {
        "total": total,
        "n_rsrp": len(rsrp),
        "n_geo": len(geo),
        "clases": clases,
        "n_celdas": len(rejilla),
        "zonas": zonas,
        "rejilla": rejilla,
    }


def analizar_set2(ruta):
    df = pd.read_csv(ruta)
    total = len(df)
    # SINR/RSRQ traen placeholders '-' -> coerción a numérico
    sinr = pd.to_numeric(df["sinr"], errors="coerce")
    dl = pd.to_numeric(df["downlink"], errors="coerce")
    ul = pd.to_numeric(df["uplink"], errors="coerce")

    clases = []
    for nombre, cond in CLASES_SINR:
        n = int(cond(sinr).sum())
        clases.append((nombre, n, 100.0 * n / int(sinr.notna().sum())))

    # --- Cruce SINR -> throughput mediano (solo filas con ambos datos) ---
    cruce = []
    for nombre, cond in CLASES_SINR:
        mascara = cond(sinr)
        fila = {"clase": nombre}
        for etiqueta, serie in (("downlink", dl), ("uplink", ul)):
            ambos = serie[mascara & serie.notna()]
            fila[f"n_{etiqueta}"] = int(len(ambos))
            fila[f"med_{etiqueta}"] = float(ambos.median()) if len(ambos) else float("nan")
        cruce.append(fila)

    return {
        "total": total,
        "n_sinr": int(sinr.notna().sum()),
        "clases": clases,
        "cruce": cruce,
    }


def generar_informe(s1, s2, ruta_salida):
    L = []
    L.append("# Informe de cobertura 5G rural — datasets ARA")
    L.append("")
    L.append("Generado por `analizador.py` sobre los archivos reales descargados de IEEE DataPort.")
    L.append("")
    L.append("- **Set 1:** ARA COTS 5G NR Spatio-Temporal RSRP Measurement Dataset — DOI 10.21227/7np5-4e05")
    L.append("- **Set 2:** ARA Rural COTS 5G NR UE Measurement Dataset — DOI 10.21227/p2a8-f326")
    L.append("- **Origen de los datos:** mediciones RF de campo de ARA Wireless Living Lab (Iowa State University), red Ericsson COTS 5G, banda n77. No son datos de un operador ni contadores PM.")
    L.append("")
    L.append("## Set 1 — Cobertura por RSRP (muestras puntuales de UE)")
    L.append("")
    L.append(f"- Muestras totales: **{s1['total']:,}** (todas con RSRP válido: {s1['n_rsrp']:,}; georreferenciadas: {s1['n_geo']:,})")
    L.append("")
    L.append("| Clase de cobertura | Rango RSRP (dBm) | Muestras | % |")
    L.append("|---|---|---:|---:|")
    rangos = {"Excelente": "≥ −80", "Buena": "−90 a −80", "Regular": "−100 a −90",
              "Débil": "−110 a −100", "Muy débil": "< −110"}
    for nombre, n, pct in s1["clases"]:
        L.append(f"| {nombre} | {rangos[nombre]} | {n:,} | {pct:.2f} % |")
    L.append("")
    L.append(f"## Set 1 — Rejilla geográfica ({CELDA}° × {CELDA}°)")
    L.append("")
    L.append(f"- Celdas con al menos una muestra georreferenciada: **{s1['n_celdas']:,}**")
    L.append(f"- Criterio de zona débil: mediana de celda < {UMBRAL_DEBIL:.0f} dBm y ≥ {MIN_MUESTRAS} muestras.")
    L.append(f"- **Zonas débiles encontradas: {len(s1['zonas'])}**")
    L.append("")
    if len(s1["zonas"]):
        L.append("| # | Lat centro | Lon centro | Mediana RSRP (dBm) | Muestras | RSRP mín | RSRP máx |")
        L.append("|---:|---:|---:|---:|---:|---:|---:|")
        for i, (_, z) in enumerate(s1["zonas"].iterrows(), 1):
            L.append(f"| {i} | {z['lat_centro']:.5f} | {z['lon_centro']:.5f} | "
                     f"{z['rsrp_mediana']:.1f} | {int(z['muestras']):,} | "
                     f"{z['rsrp_min']:.1f} | {z['rsrp_max']:.1f} |")
        L.append("")
    L.append("## Set 2 — Calidad de enlace por SINR (mediciones de UE)")
    L.append("")
    L.append(f"- Filas totales: **{s2['total']:,}** · filas con SINR numérico: **{s2['n_sinr']:,}** "
             f"(el resto no trae bloque de radio o trae placeholder, por diseño de la campaña)")
    L.append("")
    L.append("| Clase SINR | Rango (dB) | Filas | % (de n con SINR) |")
    L.append("|---|---|---:|---:|")
    rangos_s = {"Excelente": "≥ 20", "Buena": "10 a 20", "Regular": "0 a 10", "Mala": "< 0"}
    for nombre, n, pct in s2["clases"]:
        L.append(f"| {nombre} | {rangos_s[nombre]} | {n:,} | {pct:.2f} % |")
    L.append("")
    L.append("## Set 2 — Cruce SINR → throughput mediano")
    L.append("")
    L.append("Solo filas que traen SINR **y** throughput a la vez; se reporta el n de cada celda. "
             "El throughput se midió con iperf contra un servidor del centro de datos de ARA (según el README del dataset).")
    L.append("")
    L.append("| Clase SINR | n (SINR+downlink) | Downlink mediano (Mbps) | n (SINR+uplink) | Uplink mediano (Mbps) |")
    L.append("|---|---:|---:|---:|---:|")
    for f in s2["cruce"]:
        med_dl = f"{f['med_downlink']:.1f}" if f["n_downlink"] else "—"
        med_ul = f"{f['med_uplink']:.1f}" if f["n_uplink"] else "—"
        L.append(f"| {f['clase']} | {f['n_downlink']:,} | {med_dl} | {f['n_uplink']:,} | {med_ul} |")
    L.append("")
    L.append("## Límites honestos")
    L.append("")
    L.append("- Mediciones RF por muestra de un UE en movimiento; **no** son contadores PM de 15 minutos ni alarmas FM.")
    L.append("- Esta herramienta **no valida rApps ni xApps**; describe cobertura y calidad medidas en campo.")
    L.append("- Set 1: el 6.912 % de las filas no trae coordenadas; la rejilla usa solo las georreferenciadas.")
    L.append("- Set 2: ~40 % de las filas no trae bloque de radio y ~56 % no trae throughput; cada tabla declara su n efectivo.")
    L.append("- Las clases de cobertura/SINR son umbrales de ingeniería habituales, no una certificación de ningún tipo.")
    L.append("")

    with open(ruta_salida, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return ruta_salida


def main():
    ap = argparse.ArgumentParser(description="Analizador de cobertura 5G rural — datasets ARA")
    ap.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "informe.md"))
    args = ap.parse_args()

    for ruta in (SET1_CSV, SET2_CSV):
        if not os.path.isfile(ruta):
            print(f"ERROR: no se encontró el CSV: {ruta}", file=sys.stderr)
            return 1

    s1 = analizar_set1(SET1_CSV)
    s2 = analizar_set2(SET2_CSV)
    generar_informe(s1, s2, args.salida)

    print("=== SET 1 — clases de cobertura (RSRP) ===")
    for nombre, n, pct in s1["clases"]:
        print(f"{nombre:10s} {n:7,}  {pct:6.2f} %")
    print(f"Celdas en rejilla: {s1['n_celdas']:,} · Zonas débiles: {len(s1['zonas'])}")
    for _, z in s1["zonas"].iterrows():
        print(f"  zona débil: lat {z['lat_centro']:.5f}, lon {z['lon_centro']:.5f} · "
              f"mediana {z['rsrp_mediana']:.1f} dBm · {int(z['muestras']):,} muestras")
    print("=== SET 2 — clases de SINR ===")
    for nombre, n, pct in s2["clases"]:
        print(f"{nombre:10s} {n:7,}  {pct:6.2f} %")
    print("=== SET 2 — cruce SINR -> throughput mediano ===")
    for f in s2["cruce"]:
        print(f"{f['clase']:10s} DL n={f['n_downlink']:,} med={f['med_downlink']:.1f} Mbps · "
              f"UL n={f['n_uplink']:,} med={f['med_uplink']:.1f} Mbps")
    print(f"Informe escrito en: {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
