from pathlib import Path
import io
import pandas as pd
import streamlit as st
from inferencia import cargar,predecir
from preparacion import ENTRADAS

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='Calidad de café arábica',page_icon='☕',layout='wide')
st.title('Calidad de café arábica')
st.write('Estime la puntuación de taza de un lote a partir de su origen, beneficio y calidad física.')

@st.cache_resource
def recursos():return cargar()

try:model,meta=recursos()
except FileNotFoundError:
    st.error('Falta el modelo entrenado. Ejecute entrenar.py antes de abrir la aplicación.');st.stop()

def resultado(datos):
    try:
        tabla,avisos=predecir(datos,model,meta)
        if len(tabla)==1:
            st.metric('Puntuación de taza estimada',f'{tabla.puntaje_estimado.iloc[0]:.2f} / 100')
            st.caption('Estimación previa a la catación. No equivale a una certificación de calidad.')
        else:st.success(f'Se estimaron {len(tabla)} lotes.')
        for aviso in avisos:st.warning(aviso)
        st.dataframe(tabla.round(3),hide_index=True,width='stretch')
        st.download_button('Descargar predicciones',tabla.to_csv(index=False).encode('utf-8'),'predicciones_cafe.csv','text/csv')
    except ValueError as exc:st.error(str(exc))

manual,lotes,evaluacion=st.tabs(['Estimar un lote','Cargar CSV','Resultados del modelo'])
with manual:
    st.caption('Alcance: café arábica con mediciones comparables a las de la base CQI. Las condiciones nuevas requieren validación.')
    with st.form('lote'):
        a,b,c=st.columns(3)
        with a:
            pais=st.selectbox('País de origen',meta['categorias_desarrollo']['pais'],index=meta['categorias_desarrollo']['pais'].index('Colombia'))
            variedad=st.selectbox('Variedad',meta['categorias_desarrollo']['variedad'],index=meta['categorias_desarrollo']['variedad'].index('Caturra'))
            beneficio=st.selectbox('Método de beneficio',meta['categorias_desarrollo']['beneficio'],index=meta['categorias_desarrollo']['beneficio'].index('Washed / Wet'))
            color=st.selectbox('Color del grano',meta['categorias_desarrollo']['color'],index=meta['categorias_desarrollo']['color'].index('Green'))
        with b:
            altitud=st.number_input('Altitud media (m)',min_value=0.0,max_value=6000.0,value=1600.0,step=50.0)
            humedad=st.number_input('Humedad del grano (%)',min_value=0.1,max_value=99.9,value=11.0,step=.1)
            prim=st.number_input('Defectos de categoría uno',min_value=0,value=0,step=1)
            sec=st.number_input('Defectos de categoría dos',min_value=0,value=2,step=1)
        with c:
            sacos=st.number_input('Número de sacos del lote',min_value=1,value=50,step=1)
            peso=st.number_input('Peso de un saco (kg)',min_value=.01,max_value=2000.0,value=60.0,step=1.0)
            anio=st.number_input('Año inicial de la cosecha',min_value=1900,max_value=2026,value=2026,step=1)
            st.caption('Para campañas como 2025/2026, registre 2025. Use conteos de defectos obtenidos con un protocolo comparable al del dataset.')
        enviar=st.form_submit_button('Estimar puntuación',type='primary')
    if enviar:
        datos=pd.DataFrame([[altitud,humedad/100,prim,sec,sacos,peso,anio,pais,variedad,beneficio,color]],columns=ENTRADAS)
        resultado(datos)
with lotes:
    st.subheader('Predicciones para nuevos lotes')
    st.write('El CSV debe contener las 11 columnas de la plantilla. La humedad se expresa como fracción: 0.11 equivale a 11 %.')
    plantilla=(ROOT/'data/entradas_nuevas_ejemplo.csv').read_bytes()
    st.download_button('Descargar plantilla CSV',plantilla,'plantilla_lotes_cafe.csv','text/csv')
    archivo=st.file_uploader('Seleccione el archivo de sus lotes',type=['csv'])
    if archivo is not None:
        try:resultado(pd.read_csv(archivo))
        except (pd.errors.ParserError,UnicodeDecodeError):st.error('No se pudo leer el CSV. Use UTF-8 y coma como separador.')
    if st.button('Probar cinco escenarios de ejemplo'):
        st.info('Son escenarios hipotéticos. No cuentan con una catación de referencia y no demuestran exactitud futura.')
        resultado(pd.read_csv(io.BytesIO(plantilla)))
with evaluacion:
    st.subheader('Desempeño en productores reservados')
    a,b,c=st.columns(3)
    a.metric('RMSE',f"{meta['metricas_prueba']['RMSE']:.3f} puntos")
    b.metric('MAE',f"{meta['metricas_prueba']['MAE']:.3f} puntos")
    c.metric('R²',f"{meta['metricas_prueba']['R2']:.3f}")
    st.write('La prueba usa productores que no participaron en entrenamiento. Estas métricas describen esa prueba; no son un intervalo de confianza de cada lote.')
    st.image(str(ROOT/'figuras/observado_predicho.png'))
    st.caption('Datos: Coffee Quality Institute, recopilación de James LeDoux y distribución en Kaggle. Uso académico.')
