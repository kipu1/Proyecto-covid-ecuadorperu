# Proyecto COVID Ecuador - Perú

## 📌 Descripción

Este proyecto implementa un **pipeline de datos en Python** utilizando **Dagster** para la recolección, transformación y análisis de información sobre el **COVID-19** en los países de **Ecuador** y **Perú**.

El sistema descarga datos oficiales desde **Our World in Data (OWID)**, los procesa y genera activos (`assets`) que permiten realizar análisis comparativos entre ambos países.

## 🚀 Funcionalidades principales

- **Extracción de datos** desde OWID en formato CSV.
- **Fallback local**: en caso de fallo de descarga, se utiliza una copia local (`owid.csv`).
- **Procesamiento de datos** con `pandas` y `numpy`.
- **Pipeline orquestado** con **Dagster**, que permite:
  - Definir activos de datos (`@asset`).
  - Automatizar la ejecución y monitoreo del flujo.
- **Análisis comparativo** entre Ecuador y Perú:
  - Casos confirmados.
  - Muertes registradas.
  - Evolución temporal.

## 🛠️ Tecnologías utilizadas

- **Python 3.10+**
- **Dagster** (orquestador de pipelines de datos)
- **Pandas & Numpy** (procesamiento de datos)
- **Requests** (descarga de datos con reintentos)

## 📂 Estructura del proyecto

```
Pipeline_covid
│── pipeline_covid/
│   ├── assets.py        # Definición de activos Dagster
│   ├── __init__.py      # Inicialización del módulo
│── owid.csv             # Copia local del dataset OWID
│── workspace.yaml       # Configuración de Dagster
│── README.md            # Este archivo
```

## ▶️ Ejecución

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Levantar el entorno de Dagster:
   ```bash
   dagster dev
   ```
3. Abrir el navegador en [http://localhost:3000](http://localhost:3000) para visualizar y ejecutar el pipeline
   dagster dev -m pipeline_covid.

## 📊 Resultados esperados

- Datos procesados para Ecuador y Perú.
- Gráficas y reportes que permiten comparar la evolución del COVID-19 en ambos países.
- Posibilidad de ampliar el análisis a otros países configurando la lista `PAISES_ANALISIS` en `assets.py`.

## 👨‍💻 Autor Kevin Ortiz en colaboracion de GPT

Proyecto desarrollado con fines **académicos** y de **análisis de datos**, utilizando tecnologías modernas de orquestación y procesamiento en Python.
