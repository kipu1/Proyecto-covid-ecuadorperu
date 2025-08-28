import pandas as pd

# 1. Cargar dataset (OWID "full" si lo tienes local)
df = pd.read_csv("owid-covid-data.csv")

# 2. Tipos y limpieza básica
df["location"] = df["location"].astype(str).str.strip()
df["date"] = pd.to_datetime(df["date"], errors="coerce")
for col in ["new_cases", "people_vaccinated", "population"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# 3. Filtrar Ecuador y Perú (sin tilde)
paises = ["Ecuador", "Peru"]
df = df[df["location"].isin(paises)]

# 4. Chequeos rápidos
print("Columnas:", df.columns.tolist())
print("\nTipos de datos:\n", df.dtypes)
if not df.empty:
    print("\nRango de fechas:", df["date"].min().date(), "->", df["date"].max().date())
else:
    print("\n⚠️ Tras el filtro de países, el DataFrame quedó vacío.")

# 5. Valores faltantes (si existen las columnas)
faltantes = {}
for c in ["new_cases", "people_vaccinated"]:
    if c in df.columns:
        faltantes[c] = df[c].isna().mean() * 100
print("\nPorcentaje de valores faltantes:", faltantes)

# 6. Mín y Máx de casos diarios
if "new_cases" in df.columns and not df["new_cases"].dropna().empty:
    print("\nMínimo new_cases:", df["new_cases"].min())
    print("Máximo new_cases:", df["new_cases"].max())

# 7. Guardar tabla de perfilado
resumen = {
    "columnas": [len(df.columns)],
    "rango_fechas": [f"{df['date'].min()} -> {df['date'].max()}"] if not df.empty else ["(vacío)"],
    "min_new_cases": [df["new_cases"].min() if "new_cases" in df else None],
    "max_new_cases": [df["new_cases"].max() if "new_cases" in df else None],
    "faltantes_new_cases_%": [faltantes.get("new_cases")],
    "faltantes_people_vaccinated_%": [faltantes.get("people_vaccinated")],
}
pd.DataFrame(resumen).to_csv("tabla_perfilado.csv", index=False)
print("\n✅ Perfilado guardado en tabla_perfilado.csv")

# Bonus: guarda una muestra para comprobar que hay datos
df.sort_values(["location", "date"]).head(50).to_csv("sample_filtrado.csv", index=False)
print("📝 Muestra guardada en sample_filtrado.csv")