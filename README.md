# 🦠 Pipeline COVID-19 con Dagster

Este proyecto implementa un **pipeline de análisis de COVID-19** usando [Dagster](https://dagster.io/), con datos de **Our World in Data (OWID)**.  
Permite descargar datos, procesarlos, calcular métricas epidemiológicas y exportar reportes en **Excel y CSV**, asegurando calidad mediante **asset checks**.

---

## 📂 Estructura del proyecto

```
pipeline_covid/
│
├── assets.py        # Definición de assets (leer, procesar, métricas, exportar)
├── checks.py        # Validaciones de calidad de datos (asset checks)
├── __init__.py      # Configuración de Dagster
├── owid.csv         # Copia local de respaldo (descargada automáticamente)
└── reporte_covid.xlsx  # Salida con hojas comparativas
```

---

## ⚙️ Instalación

1. Clonar el repo o descargar el proyecto:
   ```bash
   git clone <url>
   cd pipeline_covid
   ```

2. Crear y activar un entorno virtual (opcional pero recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

   Dependencias principales:
   - `dagster`, `dagit`
   - `pandas`, `openpyxl`
   - `requests`

---

## ▶️ Uso

1. **Levantar el servidor de Dagster**
   ```bash
   dagster dev -f pipeline_covid
   ```

   Por defecto se abrirá en:  
   👉 [http://127.0.0.1:3000](http://127.0.0.1:3000)

2. **Materializar assets**
   - Desde la UI de Dagster, ejecuta todo el pipeline.
   - Los datos se descargarán de OWID (o se usará `owid.csv` local si ya existe).
   - Se generarán las métricas y el archivo `reporte_covid.xlsx`.

---

## 📊 Assets principales

1. **`leer_datos`**
   - Descarga OWID COVID dataset.
   - Normaliza columnas clave: `location`, `date`, `population`, `new_cases`, `people_vaccinated`.

2. **`datos_procesados`**
   - Limpieza: conversión de tipos, eliminación de duplicados/nulos.
   - Filtra solo los países definidos en `PAISES_ANALISIS`.

3. **`metrica_incidencia_7d`**
   - Calcula incidencia diaria y promedio móvil 7d por cada 100k habitantes.

4. **`metrica_factor_crec_7d`**
   - Calcula el factor de crecimiento semanal (`casos últimos 7 días / casos 7 días previos`).

5. **`reporte_excel_covid`**
   - Exporta resultados a `reporte_covid.xlsx` con varias hojas:
     - `datos_puros`
     - `incidencia_7d`
     - `factor_crec_7d`
     - `comp_incidencia_7d` (comparativa entre países)
     - `comp_factor_7d`
     - `resumen_ultimos_valores`

---

## ✅ Asset Checks implementados

- **`check_columnas_clave_no_nulas`**  
  Verifica que `location`, `date` y `population` no tengan nulos (≤10% permitido en población).

- **`check_fecha_no_futura`**  
  Garantiza que la última fecha disponible no sea futura (máx. hoy + 1 día).  
  Solo se consideran los países definidos en `PAISES_ANALISIS` y filas con señales epidemiológicas.

- **`check_poblacion_y_casos`**  
  - `population > 0`
  - Reporta si hay valores negativos en `new_cases`.

- **`check_unicidad_location_date`**  
  Valida que `(location, date)` sea único.

- **Checks sobre métricas (`metrica_incidencia_7d`, `metrica_factor_crec_7d`)**  
  - Rango válido para `incidencia_7d`.  
  - `factor_crec_7d` debe ser >0, finito y no extremo (>10).

---

## 📌 Parámetros configurables

En `assets.py` puedes definir qué países analizar:

```python
PAISES_ANALISIS = ["Ecuador", "Peru"]
```

---

## 📤 Salidas principales

- **Excel**: `reporte_covid.xlsx`
- **CSVs**:  
  - `datos_puros.csv`  
  - `incidencia_7d.csv`  
  - `factor_crec_7d.csv`  
  - `comp_incidencia_7d.csv`  
  - `comp_factor_7d.csv`  
  - `resumen_ultimos_valores.csv`

---

## 🚀 Próximos pasos

- Agregar más países a comparar.  
- Crear visualizaciones automáticas (gráficos de tendencias).  
- Dockerizar el proyecto para despliegue más sencillo.
