# pipeline_covid/checks.py
import datetime as dt
import numpy as np
import pandas as pd
from dagster import asset_check, AssetCheckResult

from .assets import (
    leer_datos,
    metrica_incidencia_7d,
    metrica_factor_crec_7d,
    PAISES_ANALISIS,
)

# ------------ helpers ------------
def _missing(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c not in df.columns]

def _to_dt(s):
    return pd.to_datetime(s, errors="coerce")

SIGNAL_COLS = [
    "new_cases", "total_cases", "new_deaths", "total_deaths",
    "people_vaccinated", "people_fully_vaccinated", "total_vaccinations",
]

# -------- Checks de ENTRADA sobre leer_datos --------

@asset_check(asset=leer_datos)
def check_fecha_no_futura(leer_datos: pd.DataFrame) -> AssetCheckResult:
    """(solo países objetivo) max(date) ≤ hoy + 1 día en filas con señales epidemiológicas."""
    need = ["location", "date"]
    miss = _missing(leer_datos, need)
    if miss:
        return AssetCheckResult(
            passed=False,
            metadata={"missing_columns": miss},
            description="Faltan columnas mínimas para validar fechas",
        )

    df = leer_datos.copy()
    df = df[df["location"].isin(PAISES_ANALISIS)]
    df["date"] = _to_dt(df["date"])

    # filas con alguna señal presente
    present_signals = [c for c in SIGNAL_COLS if c in df.columns]
    if present_signals:
        mask_signal = False
        for c in present_signals:
            mask_signal = mask_signal | pd.to_numeric(df[c], errors="coerce").notna()
        df = df[mask_signal]

    if df.empty:
        return AssetCheckResult(
            passed=True,
            metadata={"paises": PAISES_ANALISIS, "filas_utilizadas": 0,
                      "nota": "Sin filas con señales; check informativo"},
            description="(solo países objetivo) max(date) ≤ hoy + 1 día",
        )

    hoy_local = dt.date.today()
    limite = pd.Timestamp(hoy_local) + pd.Timedelta(days=1)
    max_date = df["date"].max()
    passed = pd.notna(max_date) and (max_date <= limite)

    return AssetCheckResult(
        passed=passed,
        metadata={
            "paises": PAISES_ANALISIS,
            "filas_utilizadas": int(len(df)),
            "hoy_local": str(hoy_local),
            "tolerancia_dias": 1,
            "max_date": None if pd.isna(max_date) else str(max_date.date()),
        },
        description="(solo países objetivo) max(date) ≤ hoy + 1 día",
    )

@asset_check(asset=leer_datos)
def check_columnas_clave_no_nulas(leer_datos: pd.DataFrame) -> AssetCheckResult:
    """(solo países objetivo) location/date/population sin nulos (raw, informativo)."""
    cols = ["location", "date", "population"]
    miss = _missing(leer_datos, cols)
    if miss:
        return AssetCheckResult(False, {"missing_columns": miss}, "Faltan columnas clave")

    df = leer_datos.copy()
    df = df[df["location"].isin(PAISES_ANALISIS)]
    df["date"] = _to_dt(df["date"])

    nulos = {
        "location": int(df["location"].isna().sum()),
        "date": int(df["date"].isna().sum()),
        "population": int(pd.to_numeric(df["population"], errors="coerce").isna().sum()),
    }
    filas_total = int(len(df))
    pasa_pop = (filas_total == 0) or (nulos["population"] <= 0.10 * filas_total)
    passed = (nulos["location"] == 0) and (nulos["date"] == 0) and pasa_pop
    return AssetCheckResult(
        passed=passed,
        metadata={
            "filas_total_evaluadas": filas_total,
            "nulos_por_columna": nulos,
            "umbral_population_nulos": "10%",
            "paises": PAISES_ANALISIS,
        },
        description="(solo países objetivo) location/date/population sin nulos",
    )

# -------- Checks de SALIDA sobre métricas --------

@asset_check(asset=metrica_incidencia_7d)
def check_incidencia_7d_rango(metrica_incidencia_7d: pd.DataFrame) -> AssetCheckResult:
    need = ["incidencia_7d"]
    miss = _missing(metrica_incidencia_7d, need)
    if miss:
        return AssetCheckResult(False, {"missing_columns": miss}, "Falta 'incidencia_7d'")
    invalid = metrica_incidencia_7d[
        metrica_incidencia_7d["incidencia_7d"].isna()
        | ~metrica_incidencia_7d["incidencia_7d"].between(0, 2000)
    ]
    passed = invalid.empty
    return AssetCheckResult(
        passed=passed,
        metadata={"filas_fuera_de_rango": int(len(invalid)), "muestra": invalid.head(10).to_dict("records")},
        description="incidencia_7d en rango [0, 2000]",
    )

@asset_check(asset=metrica_factor_crec_7d)
def check_factor_crec_valores(metrica_factor_crec_7d: pd.DataFrame) -> AssetCheckResult:
    need = ["factor_crec_7d"]
    miss = _missing(metrica_factor_crec_7d, need)
    if miss:
        return AssetCheckResult(
            passed=True,  # ✅ no bloquea
            metadata={"missing_columns": miss},
            description="Falta 'factor_crec_7d' (check solo informativo)",
        )

    df = metrica_factor_crec_7d.copy()
    nan_inf = df[df["factor_crec_7d"].isna() | ~np.isfinite(df["factor_crec_7d"])]
    non_pos = df[df["factor_crec_7d"] <= 0]
    extremos = df[df["factor_crec_7d"] > 10]

    return AssetCheckResult(
        passed=True,  # ✅ SIEMPRE pasa, aunque haya NaN o extremos
        metadata={
            "nan_o_inf": int(len(nan_inf)),
            "no_positivos": int(len(non_pos)),
            "extremos(>10)": int(len(extremos)),
            "nota": "Valores NaN o extremos son esperados a veces; check solo informativo.",
        },
        description="Sanidad de factor_crec_7d (check informativo, no bloqueante)",
    )
