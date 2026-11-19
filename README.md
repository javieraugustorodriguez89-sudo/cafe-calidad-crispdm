# Estimación de calidad del café arábica

Proyecto académico CRISP-DM. Estima `Total.Cup.Points` antes de la catación con once entradas de origen, beneficio y calidad física. No utiliza las puntuaciones sensoriales que componen el objetivo.

## Ejecutar

Python 3.12:

```bash
pip install -r requirements.txt
python entrenar.py
streamlit run app.py
```

El modelo ya está entrenado. Para abrir la aplicación basta el último comando después de instalar las dependencias. Para inferencia por consola:

```bash
python inferencia.py data/entradas_nuevas_ejemplo.csv --salida predicciones.csv
```

## Archivos

- `Guia_paso_a_paso.ipynb`: orden de ejecución y lectura para la sustentación.
- `preparacion.py`: reglas de captura, transformaciones deterministas y grupos.
- `entrenar.py`: selección, validación anidada, ajuste de ocho modelos y prueba reservada.
- `vecinos.py`: KNN con distancia Manhattan y desempate numéricamente estable.
- `inferencia.py`: validación de nuevas entradas y predicción.
- `app.py`: aplicación Streamlit individual y por CSV.
- `descargar_datos.py`: descarga local del archivo original seleccionado desde Kaggle, sin modificarlo.
- `data/cafe_preparado.csv`: datos preparados con objetivo y grupos codificados, sin nombres ni contactos.
- `data/desarrollo_70.csv` y `data/prueba_30.csv`: partición por productor, sin grupos compartidos.
- `data/entradas_nuevas_ejemplo.csv`: cinco escenarios hipotéticos nuevos, sin cataciones reales.
- `resultados/`: auditoría, diccionarios, estadística, comparación, ANOVA, Tukey y predicciones.
- `modelo/`: tubería entrenada y metadatos. Cargue únicamente modelos de procedencia confiable.

## Método

De 1311 registros se excluye una catación con todos sus componentes y total en cero. Se reservan 391 muestras de 107 grupos para prueba y se desarrollan los modelos con 919 muestras de 248 grupos. No se comparte productor reconocido entre ambas particiones. La agrupación textual puede contener errores de identificación.

La imputación, el escalado, la codificación y la comparación de PCA se ajustan dentro de cada pliegue. Se utilizan cinco pliegues externos y tres internos por grupos. Se comparan regresión lineal, Ridge, KNN, SVR, árbol, votación, bagging y boosting. La selección se fija con el menor RMSE medio de validación antes de revisar la prueba.

El CSV original incluye datos administrativos de terceros y no se republica en este repositorio. `entrenar.py` lo descarga de Kaggle si no existe localmente. Los CSV del repositorio contienen las variables seleccionadas y códigos de grupo; no incluyen nombres de propietarios, fincas ni contactos.

La comparación estadística incluye ANOVA de bloques y Tukey con el error residual del diseño. Se reporta su carácter exploratorio por el solapamiento de entrenamientos. Los valores p no demuestran superioridad universal. El bajo R² limita la utilidad del modelo.

## Entradas nuevas

Columnas requeridas: `altitud_m`, `humedad_fraccion`, `defectos_primarios`, `defectos_secundarios`, `numero_sacos`, `peso_saco_kg`, `anio_cosecha`, `pais`, `variedad`, `beneficio`, `color`.

En CSV, humedad `0.11` equivale a 11 %. En el formulario se ingresa 11. Para una campaña 2025/2026 se registra 2025. Use medidas y protocolos comparables a los datos de origen. El sistema advierte sobre categorías o valores no representados. Cada fila debe informar al menos siete entradas; las reglas de completitud y calidad se aplican antes de predecir.

Los escenarios de 2026 están fuera del período histórico observado en desarrollo. No constituyen validación prospectiva. Para verificar desempeño en una cosecha nueva se requieren cataciones de referencia independientes.

## Publicar en Streamlit Community Cloud

Seleccionar este repositorio, rama `main`, archivo `app.py` y Python 3.12. No se requiere entrenar al iniciar. La URL y las capturas públicas solo se consideran completas después de comprobar el despliegue. No hay secretos ni credenciales en los archivos del proyecto.

## Fuentes

- Kaggle: https://www.kaggle.com/datasets/volpatto/coffee-quality-database-from-cqi
- Recopilación original de James LeDoux, evaluaciones CQI: https://github.com/jldbc/coffee-quality-database
- Scikit-learn: https://scikit-learn.org/stable/common_pitfalls.html
- SciPy: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.tukey_hsd.html
- Streamlit: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app

Se conserva la atribución de las fuentes. El proyecto no atribuye una nueva licencia a los datos de terceros.
