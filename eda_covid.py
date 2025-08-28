import pandas as pd

# 1. Cargar dataset
df = pd.read_csv("owid-covid-data.csv")

# 2. Filtrar Ecuador y otro país comparativo (ej: Perú)
paises = ["Ecuador", "Peru"]
df = df[df["location"].isin(paises)]

# 3. Info básica
print("Columnas:", df.columns.tolist())
print("\nTipos de datos:\n", df.dtypes)

# 4. Rango de fechas
print("\nRango de fechas:", df["date"].min(), "->", df["date"].max())

# 5. Valores faltantes
faltantes = df[["new_cases", "people_vaccinated"]].isna().mean() * 100
print("\nPorcentaje de valores faltantes:\n", faltantes)

# 6. Mín y Máx de casos diarios
print("\nMínimo new_cases:", df["new_cases"].min())
print("Máximo new_cases:", df["new_cases"].max())

# 7. Guardar tabla de perfilado
resumen = {
    "columnas": [len(df.columns)],
    "rango_fechas": [f"{df['date'].min()} -> {df['date'].max()}"],
    "min_new_cases": [df["new_cases"].min()],
    "max_new_cases": [df["new_cases"].max()],
    "faltantes_new_cases_%": [faltantes["new_cases"]],
    "faltantes_people_vaccinated_%": [faltantes["people_vaccinated"]],
}
perfilado = pd.DataFrame(resumen)
perfilado.to_csv("tabla_perfilado.csv", index=False)

print("\n✅ Perfilado guardado en tabla_perfilado.csv")
