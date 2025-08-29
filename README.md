# Proyecto: Pipeline de Datos COVID-19 (Ecuador vs. País Comparativo)

Este proyecto implementa un **pipeline de análisis de datos sobre la pandemia de COVID-19** utilizando el dataset de [Our World in Data (OWID)](https://ourworldindata.org/covid-data).  
El enfoque es **comparar la evolución de la pandemia en Ecuador y otro país de referencia (ej. Perú)** mediante un flujo de procesamiento automatizado con **Dagster** y análisis con **Pandas/DuckDB**.

---

## 📌 Objetivos

- Construir un **pipeline reproducible** de procesamiento de datos.
- Analizar y validar información de casos, muertes, vacunación y población.
- Calcular **métricas epidemiológicas clave**:
  - **Incidencia acumulada a 7 días** por cada 100,000 habitantes.
  - **Factor de crecimiento semanal** de casos.
- Exportar resultados finales a **CSV/Excel** para análisis y reporte.
- Demostrar el uso de **Dagster Assets** y **Asset Checks** en la orquestación de datos.

---

## ⚙️ Tecnologías Utilizadas

- **Python 3.12**
- **Dagster** (orquestación de pipelines)
- **Pandas** (procesamiento de datos)
- **DuckDB** (consultas SQL sobre CSV)
- **OpenPyXL** (exportación a Excel)
- **Requests** (descarga de dataset OWID)

---

## 📂 Estructura del Proyecto

```
proyecto-covid-ecuadorperu/
│
├── pipeline_covid/          # Definición de assets de Dagster
│   ├── assets.py            # Lectura, validación, procesamiento y métricas
│   └── __init__.py
│
├── owid.csv                 # Dataset local (descargado automáticamente si no existe)
├── tabla_perfilado.csv      # Perfilado inicial de los datos
├── reporte_covid.xlsx       # Reporte final con métricas y datos procesados
│
├── requirements.txt         # Dependencias del proyecto
└── README.md                # Este documento
```

---

## 🏗️ Pipeline de Dagster

El pipeline está diseñado como **assets encadenados**:

1. **leer_datos** → Descarga el CSV desde OWID y lo carga en Pandas.
2. **chequeos_entrada** → Validaciones iniciales:
   - No hay fechas futuras.
   - Columnas clave no nulas (`location`, `date`, `population`).
   - Unicidad `(location, date)`.
3. **datos_procesados** → Filtrado y limpieza:
   - Elimina nulos y duplicados.
   - Selecciona solo Ecuador y el país comparativo.
   - Calcula **incidencia diaria**.
4. **metrica_incidencia_7d** → Promedio móvil de 7 días de la incidencia.
5. **metrica_factor_crec_7d** → Comparación de casos entre semanas consecutivas.
6. **chequeos_salida** → Validaciones sobre las métricas calculadas.
7. **reporte_excel_covid** → Exporta resultados finales a Excel/CSV.

---

## 📊 Ejemplo de Resultados

### Incidencia acumulada 7 días (por 100k habitantes)
| Fecha       | País     | Incidencia_7d |
|-------------|---------|---------------|
| 2021-07-01  | Ecuador | 10.6          |
| 2021-07-01  | Perú    | 15.7          |

### Factor de crecimiento semanal
| Semana Fin  | País     | Casos Semana | Factor_Crec_7d |
|-------------|---------|---------------|----------------|
| 2021-07-07  | Ecuador | 12,500        | 1.15           |
| 2021-07-07  | Perú    | 35,000        | 0.92           |

---

## 🚀 Ejecución del Proyecto

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu_usuario/proyecto-covid-ecuadorperu.git
cd proyecto-covid-ecuadorperu
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Levantar Dagster
```bash
dagster dev
```

La interfaz web estará disponible en 👉 [http://localhost:3000](http://localhost:3000)

---

## 📑 Reporte

El informe técnico incluye:
- Arquitectura del pipeline y justificación de diseño.
- Reglas de validación en entrada y salida.
- Consideraciones sobre uso de **Pandas vs. DuckDB**.
- Resultados de las métricas con interpretación.

---

## ✍️ Autores
Proyecto desarrollado en el marco del curso **Análisis en Python 2025 (ISTA)**.  
Inspirado en la necesidad de comprender el impacto de la pandemia de COVID-19 en Ecuador y la región comparativa.

---
