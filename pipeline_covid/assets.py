# pipeline_covid/assets.py
import os
import time
import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dagster import asset

# URL oficial OWID (compact dataset)
URL = "https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv"
# Copia local (fallback/evita descargas repetidas)
LOCAL_PATH = "owid.csv"

# Cambia los países de análisis si quieres (p. ej. "Colombia", "Chile")
PAISES_ANALISIS = ["Ecuador", "Peru"]


# -------------------------------
# Utilidades internas
# -------------------------------
def _requests_session() -> requests.Session:
    """Sesión requests con reintentos exponenciales, headers y pool configurado."""
    s = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.5,  # 0s, 1.5s, 3s, 4.5s, 6s...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update(
        {
            "User-Agent": "pipeline-covid/1.0 (+requests; dagster asset)",
            "Accept": "text/csv,application/octet-stream;q=0.9,*/*;q=0.8",
        }
    )
    return s


def _download_with_retries(url: str, dest: str):
    """Descarga por streaming con reintentos. Escribe primero a .part y luego reemplaza atómicamente."""
    sess = _requests_session()
    with sess.get(url, stream=True, timeout=(10, 120)) as r:
        r.raise_for_status()
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 14):  # 16 KiB
                if chunk:
                    f.write(chunk)
        os.replace(tmp, dest)


# --- NORMALIZACIÓN ROBUSTA ---
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Pasa todos los nombres de columnas a minúsculas y '_' (sin espacios)
    - Mapea alias -> nombres estándar: location, date, population, new_cases, people_vaccinated
    """
    df = df.copy()

    # normaliza nombres: minusculas + underscores
    norm = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df.rename(columns=norm, inplace=True)

    # alias -> estándar
    alias = {
        # location
        "entity": "location",
        "location_name": "location",
        "country": "location",
        "country_name": "location",
        # date
        "fecha": "date",
        # population
        "pop": "population",
        "poblacion": "population",
        # cases
        "newcases": "new_cases",
        "nuevos_casos": "new_cases",
    }
    for src, dst in alias.items():
        if src in df.columns and dst not in df.columns:
            df.rename(columns={src: dst}, inplace=True)

    # columnas mínimas para las métricas
    for col in ["location", "date", "population", "new_cases"]:
        if col not in df.columns:
            df[col] = pd.NA

    # vacunación: opcional (busca alternativas)
    if "people_vaccinated" not in df.columns:
        for alt in ["people_fully_vaccinated", "total_vaccinations", "vaccinations"]:
            if alt in df.columns:
                df.rename(columns={alt: "people_vaccinated"}, inplace=True)
                break
        if "people_vaccinated" not in df.columns:
            df["people_vaccinated"] = pd.NA

    return df


# -------------------------------
# ASSET 1: Lectura de datos (raw)
# -------------------------------
@asset
def leer_datos() -> pd.DataFrame:
    """Descarga el CSV de OWID con reintentos y fallback a archivo local si existe.
    Devuelve DataFrame con columnas normalizadas mínimas.
    """
    # 1) Fallback rápido: si ya existe una copia local razonable, úsala
    if os.path.exists(LOCAL_PATH) and os.path.getsize(LOCAL_PATH) > 1024:  # >1KB
        try:
            df_local = pd.read_csv(LOCAL_PATH)
            return _normalize_columns(df_local)
        except Exception:
            # si el local está corrupto, continuamos a re-descargar
            pass

    # 2) Descarga robusta con reintentos (maneja cortes chunked)
    try:
        _download_with_retries(URL, LOCAL_PATH)
    except requests.exceptions.ChunkedEncodingError:
        time.sleep(2)
        _download_with_retries(URL, LOCAL_PATH)
    except requests.exceptions.RequestException as e:
        # si falla la red y NO hay local previo usable: error claro
        raise RuntimeError(
            f"Fallo de red descargando OWID: {e}. "
            "Si el problema persiste, coloca manualmente 'owid.csv' en la raíz y reintenta."
        )

    # 3) Cargar + normalizar
    df = pd.read_csv(LOCAL_PATH)
    df = _normalize_columns(df)
    return df


# -----------------------------------------------
# ASSET 2: Procesamiento (limpieza + filtro país)
# -----------------------------------------------
@asset
def datos_procesados(leer_datos: pd.DataFrame) -> pd.DataFrame:
    df = leer_datos.copy()

    # columnas realmente necesarias para tus métricas
    required = ["location", "date", "new_cases", "population"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise Exception(f"Faltan columnas tras normalizar: {missing}")

    # limpia strings y tipos
    df["location"] = df["location"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for num_col in ["new_cases", "population", "people_vaccinated"]:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce")

    # orden y duplicados
    df = df.sort_values(["location", "date"]).drop_duplicates(subset=["location", "date"])

    # FILTRO DE PAÍSES
    df = df[df["location"].isin(PAISES_ANALISIS)]

    # quita nulos solo de lo esencial para las métricas
    df = df.dropna(subset=["location", "date", "new_cases", "population"])

    # vacunación opcional
    if "people_vaccinated" in df.columns:
        df["people_vaccinated"] = df["people_vaccinated"].fillna(0)

    # columnas finales
    cols = ["location", "date", "new_cases", "population"]
    if "people_vaccinated" in df.columns:
        cols.append("people_vaccinated")

    df = df[cols].reset_index(drop=True)

    # LOG útil
    if df.empty:
        print("[datos_procesados] VACÍO. Revisa PAISES_ANALISIS o columnas source.")
        try:
            sample = (leer_datos.get("location") or leer_datos.get("entity"))
            if sample is not None:
                print("[debug] ejemplos location:", list(pd.Series(sample).astype(str).str.strip().unique())[:20])
        except Exception:
            pass
    else:
        print(
            f"[datos_procesados] Filas={len(df)} | "
            f"Rango fechas: {df['date'].min().date()} → {df['date'].max().date()} | "
            f"Países={sorted(df['location'].unique().tolist())}"
        )
    return df


# -------------------------------------------------------
# ASSET 3: Métrica A — Incidencia 7d por 100k habitantes
# -------------------------------------------------------
@asset
def metrica_incidencia_7d(datos_procesados: pd.DataFrame) -> pd.DataFrame:
    """Calcula incidencia_diaria y su promedio móvil 7d por 100k."""
    df = datos_procesados.copy()
    df = df.sort_values(["location", "date"])
    df["incidencia_diaria"] = (df["new_cases"] / df["population"]) * 100_000
    df["incidencia_7d"] = (
        df.groupby("location", group_keys=False)["incidencia_diaria"]
        .rolling(7, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )
    return df[["location", "date", "incidencia_diaria", "incidencia_7d"]].reset_index(drop=True)


# -----------------------------------------------------
# ASSET 4: Métrica B — Factor de crecimiento semanal 7d
# -----------------------------------------------------
@asset
def metrica_factor_crec_7d(datos_procesados: pd.DataFrame) -> pd.DataFrame:
    df = datos_procesados.copy()
    df = df.sort_values(["location", "date"])
    df["casos_7d"] = (
        df.groupby("location", group_keys=False)["new_cases"]
        .rolling(7, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
    )
    df["casos_7d_prev"] = df.groupby("location")["casos_7d"].shift(7)

    # División segura: solo dividimos cuando el denominador > 0
    denom = df["casos_7d_prev"]
    num = df["casos_7d"]
    df["factor_crec_7d"] = np.where(denom > 0, num / denom, np.nan)

    # Limpiar inf/-inf (si quedaran)
    df["factor_crec_7d"] = df["factor_crec_7d"].replace([np.inf, -np.inf], np.nan)

    return df[["location", "date", "casos_7d", "casos_7d_prev", "factor_crec_7d"]].reset_index(drop=True)


# --------------------------------------------
# ASSET 5: Exportación de resultados a Excel
# --------------------------------------------
@asset
def reporte_excel_covid(
    datos_procesados: pd.DataFrame,
    metrica_incidencia_7d: pd.DataFrame,
    metrica_factor_crec_7d: pd.DataFrame,
) -> str:
    """Exporta resultados finales con hojas comparativas robustas."""
    def ensure_datetime(df, col="date"):
        if df is not None and col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def safe_pivot(df, value_col):
        needed = {"date", "location", value_col}
        if df is None or df.empty or not needed.issubset(set(df.columns)):
            return pd.DataFrame(columns=["date"])
        tmp = df[["date", "location", value_col]].copy()
        tmp = ensure_datetime(tmp, "date").sort_values("date")
        wide = (
            tmp.pivot_table(index="date", columns="location", values=value_col, aggfunc="last")
            .reset_index()
            .sort_values("date")
        )
        num_cols = wide.select_dtypes("number").columns
        if len(num_cols):
            wide[num_cols] = wide[num_cols].round(3)
        return wide

    def last_values(datos, metrica_inc, metrica_fac):
        if datos is None or datos.empty or "location" not in datos or "date" not in datos:
            return pd.DataFrame(
                columns=[
                    "location", "ultima_fecha_datos",
                    "fecha_incidencia", "incidencia_7d",
                    "fecha_factor", "factor_crec_7d", "casos_7d", "casos_7d_prev",
                ]
            )
        base = datos[["location", "date"]].copy()
        base = ensure_datetime(base, "date")
        last_dates = base.groupby("location", as_index=False)["date"].max().rename(columns={"date": "ultima_fecha_datos"})

        # Incidencia última
        if metrica_inc is not None and not metrica_inc.empty and {"location", "date", "incidencia_7d"}.issubset(
            set(metrica_inc.columns)
        ):
            inc = ensure_datetime(metrica_inc[["location", "date", "incidencia_7d"]], "date")
            last_inc = inc.sort_values("date").groupby("location", as_index=False).tail(1)
        else:
            last_inc = last_dates.assign(incidencia_7d=pd.NA, date=pd.NaT).rename(columns={"date": "fecha_incidencia"})

        # Factor última
        if metrica_fac is not None and not metrica_fac.empty and {
            "location", "date", "factor_crec_7d", "casos_7d", "casos_7d_prev",
        }.issubset(set(metrica_fac.columns)):
            fac = ensure_datetime(metrica_fac[["location", "date", "factor_crec_7d", "casos_7d", "casos_7d_prev"]], "date")
            last_fac = fac.sort_values("date").groupby("location", as_index=False).tail(1)
        else:
            last_fac = last_dates.assign(factor_crec_7d=pd.NA, casos_7d=pd.NA, casos_7d_prev=pd.NA, date=pd.NaT)\
                                 .rename(columns={"date": "fecha_factor"})

        out = last_dates.merge(last_inc.rename(columns={"date": "fecha_incidencia"}), on="location", how="left")\
                        .merge(last_fac.rename(columns={"date": "fecha_factor"}), on="location", how="left")

        for c in ["incidencia_7d", "factor_crec_7d"]:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce").round(3)

        return out[
            ["location", "ultima_fecha_datos", "fecha_incidencia", "incidencia_7d",
             "fecha_factor", "factor_crec_7d", "casos_7d", "casos_7d_prev"]
        ].sort_values("location").reset_index(drop=True)

    # Asegurar tipos
    datos_procesados = ensure_datetime(datos_procesados, "date")
    metrica_incidencia_7d = ensure_datetime(metrica_incidencia_7d, "date")
    metrica_factor_crec_7d = ensure_datetime(metrica_factor_crec_7d, "date")

    # Comparativas
    inc_wide = safe_pivot(metrica_incidencia_7d, "incidencia_7d")
    fac_wide = safe_pivot(metrica_factor_crec_7d, "factor_crec_7d")

    resumen = last_values(datos_procesados, metrica_incidencia_7d, metrica_factor_crec_7d)

    excel_path = "reporte_covid.xlsx"
    try:
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            datos_procesados.to_excel(excel_writer=writer, sheet_name="datos_puros", index=False)
            metrica_incidencia_7d.to_excel(excel_writer=writer, sheet_name="incidencia_7d", index=False)
            metrica_factor_crec_7d.to_excel(excel_writer=writer, sheet_name="factor_crec_7d", index=False)
            inc_wide.to_excel(excel_writer=writer, sheet_name="comp_incidencia_7d", index=False)
            fac_wide.to_excel(excel_writer=writer, sheet_name="comp_factor_7d", index=False)
            resumen.to_excel(excel_writer=writer, sheet_name="resumen_ultimos_valores", index=False)
    except PermissionError:
        from datetime import datetime
        alt = f"reporte_covid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with pd.ExcelWriter(alt, engine="openpyxl") as writer:
            datos_procesados.to_excel(excel_writer=writer, sheet_name="datos_puros", index=False)
            metrica_incidencia_7d.to_excel(excel_writer=writer, sheet_name="incidencia_7d", index=False)
            metrica_factor_crec_7d.to_excel(excel_writer=writer, sheet_name="factor_crec_7d", index=False)
            inc_wide.to_excel(excel_writer=writer, sheet_name="comp_incidencia_7d", index=False)
            fac_wide.to_excel(excel_writer=writer, sheet_name="comp_factor_7d", index=False)
            resumen.to_excel(excel_writer=writer, sheet_name="resumen_ultimos_valores", index=False)
        excel_path = alt

    # CSV opcionales (best-effort)
    try:
        datos_procesados.to_csv("datos_puros.csv", index=False)
        metrica_incidencia_7d.to_csv("incidencia_7d.csv", index=False)
        metrica_factor_crec_7d.to_csv("factor_crec_7d.csv", index=False)
        inc_wide.to_csv("comp_incidencia_7d.csv", index=False)
        fac_wide.to_csv("comp_factor_7d.csv", index=False)
        resumen.to_csv("resumen_ultimos_valores.csv", index=False)
    except Exception:
        pass

    print(f"[reporte_excel_covid] Excel generado: {os.path.abspath(excel_path)}")
    return excel_path
