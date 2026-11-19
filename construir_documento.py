"""Construye el informe a partir de resultados ejecutados, sin inventar métricas."""
from pathlib import Path
import json,csv
import pandas as pd
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from preparacion import ENTRADAS,NUMERICAS,CATEGORICAS,SENSORIALES

R=Path(__file__).resolve().parent;RES=R/'resultados'
audit=json.loads((RES/'auditoria.json').read_text());meta=json.loads((RES/'resumen.json').read_text());anova=json.loads((RES/'anova.json').read_text())
cv=pd.read_csv(RES/'comparacion_cv.csv');test=pd.read_csv(RES/'evaluacion_prueba.csv');rel=pd.read_csv(RES/'relaciones.csv');imp=pd.read_csv(RES/'importancia_permutacion.csv');new=pd.read_csv(RES/'predicciones_nuevas.csv')
raw=pd.read_csv(R/'data/arabica_data_cleaned.csv');train=pd.read_csv(R/'data/desarrollo_70.csv');hp=json.loads((RES/'hiperparametros_finales.json').read_text())
descripciones={
'Species':'Especie de café declarada','Owner':'Nombre del propietario registrado','Country.of.Origin':'País de origen del lote','Farm.Name':'Nombre de la finca','Lot.Number':'Identificador del lote','Mill':'Beneficiadero o instalación de procesamiento','ICO.Number':'Identificador comercial ICO reportado','Company':'Empresa registrada','Altitude':'Altitud original en texto y unidad reportada','Region':'Región de procedencia','Producer':'Nombre del productor registrado','Number.of.Bags':'Número de sacos del lote','Bag.Weight':'Peso declarado por saco con su unidad','In.Country.Partner':'Entidad colaboradora en el país','Harvest.Year':'Año o campaña de cosecha declarada','Grading.Date':'Fecha de evaluación de la muestra','Owner.1':'Nombre normalizado del propietario','Variety':'Variedad declarada del café','Processing.Method':'Método de beneficio o procesamiento','Aroma':'Puntuación sensorial de aroma','Flavor':'Puntuación sensorial de sabor','Aftertaste':'Puntuación sensorial de sabor residual','Acidity':'Puntuación sensorial de acidez','Body':'Puntuación sensorial de cuerpo','Balance':'Puntuación sensorial de balance','Uniformity':'Puntuación sensorial de uniformidad','Clean.Cup':'Puntuación sensorial de limpieza de taza','Sweetness':'Puntuación sensorial de dulzor','Cupper.Points':'Valoración global del catador','Total.Cup.Points':'Puntuación total de taza','Moisture':'Humedad registrada como fracción','Category.One.Defects':'Conteo de defectos de categoría uno','Quakers':'Conteo reportado de granos quakers','Color':'Color declarado del grano verde','Category.Two.Defects':'Conteo de defectos de categoría dos','Expiration':'Fecha de vencimiento de la evaluación o certificado','Certification.Body':'Organismo certificador','Certification.Address':'Dirección del organismo certificador','Certification.Contact':'Contacto del organismo certificador','unit_of_measurement':'Unidad original de altitud','altitude_low_meters':'Altitud inferior convertida a metros','altitude_high_meters':'Altitud superior convertida a metros','altitude_mean_meters':'Altitud media convertida a metros'}
seleccion={'Country.of.Origin','Variety','Processing.Method','Color','altitude_mean_meters','Moisture','Category.One.Defects','Category.Two.Defects','Number.of.Bags','Bag.Weight','Harvest.Year'}
dic=[]
for c in raw.columns[1:]:
 role='Objetivo' if c=='Total.Cup.Points' else 'Entrada' if c in seleccion else 'Solo agrupación' if c in ('Owner','Owner.1','Farm.Name') else 'Excluir componente del objetivo' if c in SENSORIALES else 'Excluir'
 tipo='Numérica' if pd.api.types.is_numeric_dtype(raw[c]) else 'Texto o categoría'
 unidad='Puntos' if c in SENSORIALES+['Total.Cup.Points'] else 'm' if c.endswith('_meters') else 'Fracción' if c=='Moisture' else 'Conteo' if c in ('Number.of.Bags','Category.One.Defects','Category.Two.Defects','Quakers') else 'Unidad declarada' if c in ('Altitude','Bag.Weight') else 'No aplica'
 dic.append({'variable_original':c,'definicion':descripciones[c],'tipo':tipo,'unidad':unidad,'uso':role,'nulos_originales':int(raw[c].isna().sum())})
pd.DataFrame(dic).to_csv(RES/'diccionario_completo.csv',index=False)

activos=[
('altitud_m','altitude_mean_meters','Numérica','m','0 a 6000; fuera de rango se imputa'),
('humedad_fraccion','Moisture','Numérica','Fracción','Mayor que 0 y hasta 1; cero no se interpreta como café sin agua'),
('defectos_primarios','Category.One.Defects','Entera','Conteo','Entero mayor o igual a 0'),
('defectos_secundarios','Category.Two.Defects','Entera','Conteo','Entero mayor o igual a 0'),
('numero_sacos','Number.of.Bags','Entera','Sacos','Entero mayor o igual a 1'),
('peso_saco_kg','Bag.Weight','Numérica','kg','Mayor que 0 y hasta 2000; unidad explícita'),
('anio_cosecha','Harvest.Year','Entera','Año','1900 a 2026; primer año de una campaña'),
('pais','Country.of.Origin','Categórica','No aplica','Nombre no vacío; normalizar espacios'),
('variedad','Variety','Categórica','No aplica','Nombre no vacío; conservar Other como categoría'),
('beneficio','Processing.Method','Categórica','No aplica','Lavado, natural, honey, semilavado u Other según etiqueta original'),
('color','Color','Categórica','No aplica','Green, Blue-Green o Bluish-Green'),
('puntaje_taza','Total.Cup.Points','Numérica objetivo','Puntos','Escala 0 a 100; revisar cataciones totalmente en cero')]
pd.DataFrame(activos,columns=['variable','origen','tipo','unidad','regla']).to_csv(RES/'diccionario_modelo.csv',index=False)

doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=sec.bottom_margin=Inches(.75);sec.left_margin=sec.right_margin=Inches(.8)
normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(11);normal.paragraph_format.space_after=Pt(6)
for n in ('Title','Subtitle','Heading 1','Heading 2','Heading 3'):
 doc.styles[n].font.color.rgb=RGBColor(0,0,0);doc.styles[n].font.name='Calibri'
doc.styles['Title'].font.size=Pt(23);doc.styles['Heading 1'].font.size=Pt(16);doc.styles['Heading 2'].font.size=Pt(12)
footer=sec.footer.paragraphs[0];footer.alignment=2
f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');footer._p.append(f)

def p(t,style=None):return doc.add_paragraph(str(t),style)
def h(t,level=1):return doc.add_heading(t,level)
def expo(t):
 q=p('Para exponer. '+t);q.runs[0].italic=True
def tabla(headers,rows,widths=None):
 t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
 if widths:
  for i,w in enumerate(widths):t.columns[i].width=Inches(w)
 for i,x in enumerate(headers):t.rows[0].cells[i].text=str(x)
 trPr=t.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
 for j,row in enumerate(rows):
  cells=t.add_row().cells
  for i,x in enumerate(row):cells[i].text=str(x)
 for ri,row in enumerate(t.rows):
  cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
  for ci,cell in enumerate(row.cells):
   if widths:cell.width=Inches(widths[ci])
   cell.vertical_alignment=1;tcPr=cell._tc.get_or_add_tcPr();borders=OxmlElement('w:tcBorders')
   for edge in ('top','left','bottom','right'):
    e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
   tcPr.append(borders);sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8EDF1' if ri==0 else 'FFFFFF' if ri%2 else 'F7F8F9');tcPr.append(sh)
   for par in cell.paragraphs:
    par.paragraph_format.space_before=Pt(4);par.paragraph_format.space_after=Pt(4)
    for run in par.runs:run.font.size=Pt(9);run.bold=ri==0
 return t
def fig(name,caption,width=6.2):
 doc.add_picture(str(R/'figuras'/name),width=Inches(width));q=p(caption);q.runs[0].font.size=Pt(9)
def fmt(x):return f'{float(x):.3f}'

p('Estimación de la calidad del café arábica', 'Title')
p('Trabajo final de análisis de datos con inteligencia artificial','Subtitle')
p('Integrante: Javier Torres\nPrograma: Ingeniería Agroindustrial\nInstitución: Universidad Pontificia Bolivariana\nFecha de elaboración: 19 de noviembre de 2026')
p('Se estima la puntuación de taza de un lote antes de su catación, utilizando origen, beneficio y calidad física. El informe desarrolla CRISP-DM con resultados ejecutados, código reproducible y una aplicación que admite lotes nuevos.')
p(f"Se conservaron {audit['filas_preparadas']} muestras y se evaluaron ocho modelos. El modelo seleccionado fue {meta['modelo_elegido']}, con RMSE de {meta['metricas_prueba']['RMSE']:.3f} puntos y R² de {meta['metricas_prueba']['R2']:.3f} en productores reservados. La capacidad predictiva obtenida es limitada; la aplicación tiene alcance académico.")
p('Orden de sustentación: problema y solución; diccionario y reglas; preparación; comparación de modelos; predicción y despliegue.')
doc.add_page_break()

h('1 Entendimiento del negocio')
h('1 1 Descripción del problema',2)
p('Un productor o comprador dispone de información del origen y de la inspección física de un lote, pero todavía desconoce la puntuación que obtendrá al catarlo. Se busca estimar esa puntuación para apoyar la priorización de evaluaciones. El modelo no sustituye la catación ni certifica café de especialidad.')
p('La unidad de análisis es una muestra o lote evaluado de café arábica. El momento de uso se sitúa después de conocer el beneficio y las características físicas, y antes de disponer de las calificaciones sensoriales. Por ello, el objetivo no es predecir desde la siembra ni recomendar dosis de fertilización.')
p('Objetivo general: comparar modelos que estimen Total.Cup.Points utilizando únicamente datos disponibles antes de la catación, y desplegar el modelo elegido para recibir entradas nuevas.')
p('Objetivos específicos: auditar la base; preparar once entradas; comparar cinco métodos clásicos y tres ensambles; evaluar el modelo en productores reservados; implementar predicción individual y por CSV.')
expo('Primero definimos qué se predice, para quién y en qué momento. Esa definición determina qué variables podemos utilizar sin anticipar información del resultado.')
h('1 2 Diseño de solución',2)
p('Se utiliza regresión supervisada: cada muestra histórica contiene entradas y una puntuación de referencia. El aprendizaje se realiza con aproximadamente 70 % de las muestras; el resto se reserva como prueba. La separación respeta grupos de productores y no utiliza puntuaciones para elegir la partición.')
p('La preparación aprendida y el modelo se guardan juntos. Una entrada nueva pasa por las mismas reglas, imputaciones, escalado y codificación. La aplicación devuelve una estimación en puntos y advierte sobre datos fuera de las condiciones observadas.')
p('Criterio principal: minimizar RMSE en validación cruzada anidada. Se compara además con predecir siempre la media del entrenamiento. No se promete una precisión que los datos no demuestren.')

h('2 Entendimiento de los datos')
h('2 1 Fuente y estructura',2)
p('Fuente de descarga: Coffee Quality database from CQI, publicado por volpatto en Kaggle. Archivo seleccionado: arabica_data_cleaned.csv. El recopilador original es James LeDoux; las evaluaciones proceden del Coffee Quality Institute [1, 2].')
tabla(['Característica','Resultado auditado'],[
('Filas originales','1311'),('Variables originales sin índice','43'),('Entradas seleccionadas','11: siete numéricas y cuatro categóricas'),('Objetivo','Puntuación total de taza'),('Filas después de excluir una catación totalmente en cero',audit['filas_preparadas']),('Duplicados exactos de entradas y objetivo',audit['duplicados_excluidos'])],[3.6,3.2])
p('La base contiene muestras sometidas a evaluación, no una muestra aleatoria de toda la producción mundial. El archivo combina países, variedades y años; esa cobertura condiciona la generalización. El archivo original se conserva sin modificar durante el análisis y su huella SHA-256 queda registrada en auditoria.json. Se obtiene mediante descargar_datos.py desde la fuente citada; los CSV publicados contienen las entradas seleccionadas y grupos codificados, sin nombres ni contactos.')
h('2 2 Diccionario de datos del modelo',2)
p('Variable dependiente: puntaje_taza, tomada de Total.Cup.Points. Es el resultado desconocido antes de catar. Las once variables independientes se describen a continuación. El diccionario completo de las 43 columnas originales se entrega en resultados/diccionario_completo.csv y se resume en el anexo.')
tabla(['Variable','Origen','Tipo y unidad'],[(a,b,c+'; '+d) for a,b,c,d,e in activos],[1.65,3.25,1.9])
p('Defectos de categoría uno y dos son conteos físicos reportados, no calificaciones sensoriales. Deben obtenerse con un protocolo de inspección comparable al de las muestras de referencia. No se inventa un tamaño de muestra física que el CSV no documenta para cada registro.')
expo('El modelo recibe información disponible antes de la catación. La aplicación pide humedad en porcentaje y la convierte a fracción, de modo que 11 % se representa como 0.11.')
h('2 3 Reglas de calidad numéricas',2)
tabla(['Variable','Regla previa al análisis'],[(a,e) for a,b,c,d,e in activos if c!='Categórica'],[1.8,5])
p('Son límites conservadores de plausibilidad y de captura, no los mínimos y máximos observados ni umbrales que certifiquen calidad agronómica. El límite de año corresponde a la fecha de elaboración. La altitud máxima observada de 190164 m se marca como inválida; no se adivina su corrección. Pesos mayores de 2000 kg por saco y números sin unidad explícita se consideran faltantes. Los valores válidos extremos se conservan.')
h('2 4 Reglas de calidad categóricas',2)
p('Se eliminan espacios sobrantes y se interpretan celdas vacías, NA y None como faltantes. Other conserva su significado de categoría residual. Beneficio admite las cinco etiquetas declaradas: Washed / Wet, Natural / Dry, Pulped natural / honey, Semi-washed / Semi-pulped y Other. Color conserva Green, Blue-Green y Bluish-Green. Los nombres de país y variedad se conservan conforme al origen para no inventar equivalencias.')
p('La codificación aprende categorías dentro de cada entrenamiento; las de baja frecuencia se agrupan cuando corresponde. Una categoría externa no provoca un fallo del modelo, pero la aplicación la identifica como no representada.')

h('3 Preparación de datos')
h('3 1 Selección desde el conocimiento del negocio',2)
p('Se seleccionan origen y variedad por su relación potencial con el material vegetal y el entorno; beneficio, humedad y defectos por describir procesamiento y calidad física; altitud y año por aportar contexto; número y peso de sacos por caracterizar el lote. La inclusión inicial no afirma causalidad ni garantiza importancia predictiva.')
p('Se excluyen Aroma, Flavor, Aftertaste, Acidity, Body, Balance, Uniformity, Clean.Cup, Sweetness y Cupper.Points: son valoraciones obtenidas al catar y componentes del resultado que se desea anticipar. Se excluyen nombres, contactos, códigos y certificados como predictores. Owner, Owner.1 y Farm.Name se utilizan exclusivamente para formar grupos de separación. Región se excluye por escritura heterogénea y alta cardinalidad. Altitudes mínima y máxima se excluyen para no repetir la misma información de altitud.')
expo('La selección reduce las 43 columnas a once entradas utilizables antes de catar. No buscamos una buena métrica reconstruyendo la puntuación a partir de sus propios componentes.')
h('3 2 Separación previa a los ajustes aprendidos',2)
p(f"Se forman {audit['grupos']} grupos con país y propietario normalizado; si falta propietario se utiliza finca y, si ambos faltan, un identificador individual. Se generan 100 separaciones con semilla 42 y se conserva la más cercana a 70 % de filas, usando solamente los tamaños. El resultado es {audit['n_desarrollo']} muestras de desarrollo ({100*audit['fraccion_desarrollo']:.2f} %) y {audit['n_prueba']} de prueba; participan {audit['grupos_desarrollo']} y {audit['grupos_prueba']} grupos, respectivamente, sin grupos compartidos.")
p('La agrupación depende de identificadores textuales: si un mismo productor aparece con nombres distintos puede no detectarse la relación. La validación por grupos reduce la repetición reconocible, pero no demuestra independencia perfecta ni reemplaza una validación temporal prospectiva.')
h('3 3 Descripción estadística',2)
desc=train[NUMERICAS+['puntaje_taza']].describe().T
tabla(['Variable','n','Media','DE','Mediana'],[(c,int(desc.loc[c,'count']),fmt(desc.loc[c,'mean']),fmt(desc.loc[c,'std']),fmt(desc.loc[c,'50%'])) for c in desc.index],[2.2,.55,1.25,1.25,1.25])
p('Las estadísticas exploratorias corresponden exclusivamente al conjunto de desarrollo. La dispersión de la puntuación y su concentración alrededor de 82 puntos ayudan a interpretar por qué predecir valores cercanos a la media ya puede producir un error aparentemente pequeño.')
fig('distribucion.png','Figura 1 Distribución de la puntuación en las muestras de desarrollo',5.7)
h('3 4 Limpieza de atípicos',2)
p('Se elimina un registro cuyo total y diez componentes sensoriales son todos cero, tratado como catación no utilizable. No se aplica eliminación automática por desviaciones estándar ni por intervalo intercuartílico a puntuaciones reales bajas. En las entradas, un valor imposible o sin unidad verificable pasa a faltante y se imputa dentro del entrenamiento. Un valor extremo plausible permanece en el análisis.')
h('3 5 Limpieza de nulos',2)
tabla(['Entrada','Faltantes después de las reglas','Acción'],[(c,audit['nulos_entrada'][c],'Mediana e indicador cuando aplica' if c in NUMERICAS else 'Categoría No informado') for c in ENTRADAS],[2.1,2.0,2.7])
p('La mediana se aprende con las filas de entrenamiento de cada pliegue. Se añaden indicadores de ausencia para que el modelo pueda distinguir una medición observada de una imputada. En categorías se utiliza No informado. No se elimina toda fila incompleta: esa práctica reduciría la muestra y podría sesgar la selección. Las medianas y categorías de prueba no intervienen en el ajuste [3].')
expo('Separar antes de imputar impide que el modelo conozca indirectamente la distribución de la prueba. La misma tubería se utiliza para una muestra futura.')
h('3 6 Análisis lineal y no lineal',2)
tabla(['Entrada','Pearson','Spearman','Información mutua'],[(r.variable,fmt(r.Pearson),fmt(r.Spearman),fmt(r.MI)) for r in rel.itertuples()],[2.5,1.2,1.2,1.9])
p('Pearson cuantifica asociación lineal; Spearman evalúa una relación monótona; información mutua explora dependencias más generales. Se calculan sobre observaciones disponibles de cada variable, sin usar la prueba. Las asociaciones son exploratorias y no demuestran efectos causales. Defectos secundarios presenta la mayor asociación lineal negativa entre las entradas numéricas analizadas.')
fig('correlaciones.png','Figura 2 Relaciones lineales en el conjunto de desarrollo',6.1)
h('3 7 Reducción de dimensiones y nuevas variables',2)
p('La primera reducción es la selección de once entradas desde 43 columnas. Se crea peso_saco_kg, convirtiendo libras mediante 0.45359237 kg por libra; un valor sin unidad se marca faltante. Se crea anio_cosecha tomando el primer año de cuatro dígitos de una campaña. Además, se generan indicadores de ausencia y variables binarias mediante One Hot Encoder, con agrupación de categorías presentes en menos de diez filas del entrenamiento.')
p(f"Se compara, dentro de la búsqueda de hiperparámetros, el bloque numérico sin PCA frente a PCA con 95 % de varianza. La configuración final elegida utiliza {'PCA con '+str(meta['n_componentes_PCA'])+' componentes' if meta['n_componentes_PCA'] else 'el bloque numérico sin PCA'} y produce {meta['dimensiones_transformadas']} entradas transformadas en total. Se conserva la configuración elegida en validación, sin forzar una reducción que no mejora ese criterio. La reducción principal es la selección de once entradas desde las 43 columnas. No se confunde la expansión de categorías con reducción de variables.")
h('3 8 Balanceo',2)
p('No aplica balanceo de clases porque el objetivo es continuo y el ejercicio es de regresión. No se convierte arbitrariamente la puntuación en clases ni se aplica SMOTE a un resultado continuo. Las muestras de baja puntuación se conservan y su escasez se reconoce como limitación.')

h('4 Modelamiento y evaluación')
h('4 1 Configuración y selección de métodos',2)
tabla(['Grupo','Modelo','Función en la comparación'],[
('Clásico','Regresión lineal','Referencia lineal multivariable'),('Clásico','Ridge','Regularización de coeficientes'),('Clásico','KNN','Predicción por similitud entre muestras'),('Clásico','SVR','Relaciones no lineales con núcleo RBF'),('Clásico','Árbol de decisión','Reglas e interacciones no lineales'),('Ensamble','Votación','Promedio ponderado de Ridge, SVR y KNN'),('Ensamble','Bagging','Promedio de 100 árboles sobre remuestras'),('Ensamble','Boosting','Corrección secuencial de errores mediante árboles')],[1,1.65,4.15])
p('Los modelos comparten imputación, escalado y codificación. KNN utiliza distancia Manhattan y desempate estable de distancias para mantener reproducibilidad entre ejecución y aplicación. La referencia adicional DummyRegressor predice la media del desarrollo; no se cuenta entre los ocho modelos exigidos.')
h('4 2 Métrica e hiperparámetros',2)
p('RMSE es la métrica principal porque expresa el error en puntos de taza y penaliza con mayor fuerza errores grandes. MAE informa el error absoluto típico y R² compara la variación explicada con una predicción constante. También se registra el sesgo medio definido como predicho menos observado. Ninguna métrica se presenta como certificación comercial.')
tabla(['Modelo','Valores explorados'],[
('Todos','Sin PCA o PCA al 95 % en el bloque numérico'),('Lineal','Sin hiperparámetros estructurales adicionales'),('Ridge','alpha: 1, 10 y 100'),('KNN','Vecinos: 7, 21 y 45; pesos uniformes o por distancia'),('SVR','C: 1 y 10; epsilon: 0.1 y 0.5; RBF'),('Árbol','Profundidad: 3 y 6; mínimo por hoja: 10 y 25'),('Votación','Pesos Ridge, SVR, KNN: 1 1 1 o 1 2 1'),('Bagging','Fracción de muestras: 0.7 o 1; fracción de variables: 0.8 o 1'),('Boosting','Árboles: 100 o 200; aprendizaje: 0.03 o 0.1; profundidad: 2')],[1.25,5.55])
p('Se usa validación anidada por grupos dentro del 70 %: cinco pliegues externos estiman el desempeño del procedimiento de ajuste; tres pliegues internos eligen hiperparámetros. Así, el pliegue evaluado no participa en elegir su configuración. Al finalizar, se ajusta cada modelo con búsqueda de cinco pliegues sobre todo el desarrollo y se evalúa una sola vez en la prueba reservada. Se ajustan los tres ensambles, resolviendo la inconsistencia del formato que menciona dos en una línea y tres en la rúbrica.')
p('Configuraciones elegidas al ajustar sobre todo el desarrollo:')
tabla(['Modelo','Configuración final'],[(name,'; '.join(k.replace('modelo__','').replace('preparar__numericas__pca','PCA')+' = '+str(v) for k,v in params.items())) for name,params in hp.items()],[1.2,5.6])
expo('Los pliegues externos son externos al ajuste interno, pero siguen perteneciendo al 70 % de desarrollo. La prueba final es el 30 % separado y no decide qué modelo gana.')
h('4 3 Resultados de validación cruzada',2)
tabla(['Modelo','RMSE medio','DE RMSE','MAE medio','R² medio'],[(r.modelo,fmt(r.RMSE_media),fmt(r.RMSE_sd),fmt(r.MAE_media),fmt(r.R2_media)) for r in cv.itertuples()],[1.5,1.35,1.25,1.35,1.05])
fig('comparacion_modelos.png','Figura 3 RMSE medio y desviación estándar entre los cinco pliegues externos',6.2)
p(f"Se elige {meta['modelo_elegido']} porque obtiene el menor RMSE medio, {cv.iloc[0].RMSE_media:.3f} puntos. Esta regla se fija antes de consultar la prueba. La desviación estándar describe variación entre particiones, no un intervalo de confianza de una predicción.")
h('4 4 ANOVA y Tukey',2)
p('Hipótesis nula: los ocho procedimientos presentan el mismo error medio. Se utiliza ANOVA de bloques, donde cada partición externa es un bloque y cada modelo es un tratamiento, porque los modelos se evalúan sobre las mismas particiones. Nivel de referencia: 0.05.')
tabla(['Resultado','Valor'],[('F de modelos',fmt(anova['F_modelo'])),('Grados de libertad de modelos',anova['gl_modelo']),('Grados de libertad del error',anova['gl_error']),('p de ANOVA',f"{anova['p_modelo']:.5f}"),('p Shapiro de residuos',f"{anova['Shapiro_residuos_p']:.5f}"),('p Levene',f"{anova['Levene_p']:.5f}")],[4,2.8])
p('Tukey se calcula con el cuadrado medio residual del diseño de bloques y la distribución del rango studentizado [4]. Las 28 comparaciones, sus intervalos y sus valores p están en resultados/tukey.csv. Al no rechazarse la hipótesis global al 5 %, las comparaciones se reportan como exploratorias y no autorizan afirmar superioridad estadística del ganador. Como sensibilidad se entregan comparaciones pareadas con corrección por solapamiento y ajuste de Holm.')
p('Los entrenamientos de los pliegues comparten muestras. Por eso, incluso el análisis por bloques conserva dependencia y sus valores p no constituyen evidencia confirmatoria independiente. Shapiro y Levene no verifican esa independencia. La selección se fundamenta en menor error medio, no en una diferencia significativa inexistente.')
expo('Votación fue el mejor por promedio, pero los datos no demostraron que sea estadísticamente superior a todos los demás. Ese matiz evita exagerar el resultado.')
h('4 5 Evaluación con el conjunto de prueba',2)
tabla(['Modelo','RMSE','MAE','R²'],[(r.modelo,fmt(r.RMSE),fmt(r.MAE),fmt(r.R2)) for r in test.itertuples()],[2.3,1.5,1.5,1.5])
rm=meta['metricas_prueba'];base=float(test.loc[test.modelo=='Referencia_media','RMSE'].iloc[0]);mejora=100*(base-rm['RMSE'])/base
p(f"El modelo elegido alcanza RMSE {rm['RMSE']:.3f}, MAE {rm['MAE']:.3f}, R² {rm['R2']:.3f} y sesgo {rm['sesgo_pred_menos_real']:.3f} puntos. Frente al RMSE {base:.3f} de la media, reduce el error aproximadamente {mejora:.1f} %. El intervalo bootstrap de RMSE, remuestreando productores completos 1000 veces, es {meta['RMSE_bootstrap_grupos_IC95'][0]:.3f} a {meta['RMSE_bootstrap_grupos_IC95'][1]:.3f} puntos. Ese intervalo describe incertidumbre del error global, no de cada lote.")
p('Algunos modelos obtienen menor error en esta prueba que el ganador elegido por validación. No se cambia de ganador después de conocer esos resultados, pues hacerlo convertiría la prueba en otro conjunto de selección. La baja proporción de variación explicada y la sobreestimación media limitan la utilidad operativa de la aplicación.')
fig('observado_predicho.png','Figura 4 Puntuaciones observadas y predichas en productores reservados',5.8)
p('La importancia por permutación se calcula después de congelar la selección y se usa únicamente para interpretar el ajuste. País y defectos secundarios figuran entre las entradas más relevantes en esta prueba. Su importancia no prueba causalidad y no se utiliza para reajustar con la prueba.')

h('5 Despliegue')
h('5 1 Predicción de entradas nuevas',2)
p('La aplicación admite valores introducidos por el usuario y CSV externos, sin depender de buscar una fila conocida. El archivo entradas_nuevas_ejemplo.csv contiene cinco escenarios hipotéticos construidos después del ajuste y ajenos a entrenamiento, validación y prueba. No cuentan con catación real; sirven para demostrar inferencia y no permiten calcular exactitud futura.')
tabla(['País y variedad','Altitud m','Humedad %','Año','Puntuación estimada'],[(r.pais+' / '+r.variedad,int(r.altitud_m),f'{100*r.humedad_fraccion:.1f}',int(r.anio_cosecha),f'{r.puntaje_estimado:.2f}') for r in new.itertuples()],[2.7,.9,.9,.6,1.7])
p('Los años de ejemplo, 2026, están fuera de los años de desarrollo, 2009 a 2018. La aplicación los acepta como captura válida y advierte que representan extrapolación temporal. Un resultado alrededor de 82 puntos expresa la estimación del modelo, no una calidad comprobada ni una predicción prospectiva ya validada. El conjunto de prueba reservado aporta la evaluación cuantitativa disponible.')
h('5 2 Preparación y validación de las nuevas entradas',2)
p('Se requieren las once columnas canónicas del diccionario. Se validan nombres, valores y unidades; se rechazan valores numéricos imposibles y filas con menos de siete entradas informadas. Los faltantes permitidos se completan con parámetros aprendidos. Categorías nuevas o valores fuera de los intervalos observados generan advertencias. Se devuelve un CSV con las entradas y puntaje_estimado. La humedad del CSV se expresa como fracción; el formulario la convierte desde porcentaje.')
p('La regla de completitud de la aplicación admite 88.2 % de las muestras de la prueba. Las métricas principales se calcularon con toda la prueba reservada, usando imputación; la aplicación restringe además entradas excesivamente incompletas para su uso interactivo.')
expo('Una muestra nueva no necesita su puntuación real para recibir una estimación. Sí necesita variables comparables. Para demostrar que el modelo funciona en una nueva cosecha, después habría que catar esas muestras y medir el error.')
h('5 3 Aplicación Streamlit',2)
p('app.py incorpora tres vistas: estimación individual, carga de CSV y resultados del modelo. inferencia.py carga la tubería guardada y aplica las validaciones. El código no entrena con los archivos subidos por el usuario ni modifica el modelo al predecir. Las pruebas automatizadas se registran en resultados/pruebas_app.json y resultados/verificacion.json.')
deployment=R/'resultados/despliegue.json'
dep=json.loads(deployment.read_text()) if deployment.exists() else {}
p('Repositorio: '+dep.get('repositorio','Preparado para publicación en GitHub.'))
if dep.get('url'):
 p('URL publicada: '+dep['url'])
 for image in sorted((R/'evidencias').glob('app_*.png')):
  doc.add_picture(str(image),width=Inches(6.2));p('Evidencia de la aplicación funcionando en '+dep['url'])
else:
 p('Estado de publicación: aplicación construida y probada localmente; la URL pública y las capturas del servicio publicado se incorporan una vez completado el acceso a Streamlit Community Cloud. Este requisito de la rúbrica permanece pendiente; no se presenta una URL ficticia ni capturas simuladas.')
p('Publicación: seleccionar el repositorio del proyecto en Streamlit Community Cloud, rama main, archivo app.py y Python 3.12. Instalar las dependencias de requirements.txt. La aplicación usa el modelo y metadata incluidos; no requiere volver a ejecutar la comparación durante el arranque [5].')

h('6 Guía de ejecución y sustentación')
tabla(['Paso','Archivo o acción','Resultado a mostrar'],[
('1','data/arabica_data_cleaned.csv','Base original, filas y variables'),('2','preparacion.py y auditoria.json','Reglas, exclusión y separación por productor'),('3','diccionario_completo.csv y diccionario_modelo.csv','Significado, rol y unidades'),('4','descripcion_numericas.csv y relaciones.csv','Estadística y asociaciones'),('5','entrenar.py','Cinco clásicos y tres ensambles con ajuste anidado'),('6','comparacion_cv.csv, anova.json y tukey.csv','Selección y límites estadísticos'),('7','evaluacion_prueba.csv','Resultados de productores reservados'),('8','app.py y entradas_nuevas_ejemplo.csv','Predicción individual y de lotes externos')],[.5,3.2,3.1])
p('Ejecución desde la carpeta del proyecto: instalar requirements.txt; ejecutar python entrenar.py para reproducir el análisis; ejecutar streamlit run app.py para abrir la aplicación. Para predicción por consola: python inferencia.py data/entradas_nuevas_ejemplo.csv --salida predicciones.csv. El cuaderno Guia_paso_a_paso.ipynb presenta las salidas en el mismo orden del informe.')
p('Conclusión para sustentar: se desarrolló un procedimiento sin componentes sensoriales como predictores y con separación por productor. Votación logró el menor RMSE medio en validación, pero la mejora frente a la media es modesta y no se demostró superioridad estadística. La siguiente validación necesaria es una cosecha nueva con puntuaciones de referencia, sin alterar el modelo después de ver sus resultados.')

h('Anexo Diccionario de columnas originales')
tabla(['Columna original','Definición','Uso'],[(r['variable_original'],r['definicion'],r['uso']) for r in dic],[1.75,3.45,1.6])
h('Referencias')
for t in [
'[1] Kaggle. Coffee Quality database from CQI. https://www.kaggle.com/datasets/volpatto/coffee-quality-database-from-cqi',
'[2] LeDoux, J. Coffee Quality Database. Repositorio y documentación de recopilación. https://github.com/jldbc/coffee-quality-database',
'[3] Scikit-learn. Common pitfalls and recommended practices. https://scikit-learn.org/stable/common_pitfalls.html',
'[4] SciPy. tukey_hsd. Supuestos y comparación de medias. https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.tukey_hsd.html',
'[5] Streamlit. Prep and deploy your app on Community Cloud. https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app']:
 p(t)
doc.core_properties.title='Estimación de la calidad del café arábica';doc.core_properties.author='Javier Torres'
for root in (doc.element,doc.styles.element):
 for border in list(root.iter(qn('w:pBdr'))):border.getparent().remove(border)
out=R/'Trabajo_Final_Cafe_CRISP_DM.docx';doc.save(out);print(out)
