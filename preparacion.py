"""Reglas deterministas compartidas por entrenamiento y aplicación."""
import re
import unicodedata
import numpy as np
import pandas as pd

NUMERICAS = ['altitud_m','humedad_fraccion','defectos_primarios','defectos_secundarios',
             'numero_sacos','peso_saco_kg','anio_cosecha']
CATEGORICAS = ['pais','variedad','beneficio','color']
ENTRADAS = NUMERICAS + CATEGORICAS
OBJETIVO = 'puntaje_taza'
MAPA = {'Country.of.Origin':'pais','Variety':'variedad','Processing.Method':'beneficio',
        'Color':'color','altitude_mean_meters':'altitud_m','Moisture':'humedad_fraccion',
        'Category.One.Defects':'defectos_primarios','Category.Two.Defects':'defectos_secundarios',
        'Number.of.Bags':'numero_sacos','Total.Cup.Points':OBJETIVO}
LIMITES = {'altitud_m':(0,6000),'humedad_fraccion':(0,1),
           'defectos_primarios':(0,None),'defectos_secundarios':(0,None),
           'numero_sacos':(1,None),'peso_saco_kg':(0,2000),'anio_cosecha':(1900,2026)}
SENSORIALES = ['Aroma','Flavor','Aftertaste','Acidity','Body','Balance','Uniformity',
              'Clean.Cup','Sweetness','Cupper.Points']

def texto(v):
    if pd.isna(v) or str(v).strip().lower() in ('','na','nan','none','n/a'): return np.nan
    return re.sub(r'\s+',' ',str(v).strip())

def normalizar(v):
    v=texto(v)
    if pd.isna(v): return ''
    return ''.join(c for c in unicodedata.normalize('NFKD',v.lower()) if not unicodedata.combining(c))

def anio(v):
    if pd.isna(v): return np.nan
    m=re.findall(r'(?<!\d)(?:19|20)\d{2}(?!\d)',str(v))
    return float(m[0]) if m else np.nan

def peso(v):
    if pd.isna(v): return np.nan
    s=str(v).lower().strip();m=re.search(r'\d+(?:\.\d+)?',s)
    if not m: return np.nan
    val=float(m[0])
    if 'lb' in s: return val*0.45359237
    if 'kg' in s: return val
    return np.nan  # No se adivina la unidad de un número sin etiqueta.

def limpiar_entradas(df):
    """No aprende estadísticos. La imputación se aprende dentro del Pipeline."""
    x=df.copy()
    for c in ENTRADAS:
        if c not in x: x[c]=np.nan
    for c in NUMERICAS:
        x[c]=pd.to_numeric(x[c],errors='coerce')
        lo,hi=LIMITES[c]
        inval=(x[c]<lo) | ~np.isfinite(x[c])
        if hi is not None: inval |= x[c]>hi
        if c in ('humedad_fraccion','peso_saco_kg'): inval |= x[c]<=0
        if c in ('defectos_primarios','defectos_secundarios','numero_sacos','anio_cosecha'):
            inval |= x[c].notna() & ((x[c]-x[c].round()).abs()>1e-8)
        x.loc[inval,c]=np.nan
    for c in CATEGORICAS: x[c]=x[c].map(texto)
    return x[ENTRADAS]

def preparar_original(raw):
    d=raw.rename(columns=MAPA).copy()
    d['anio_cosecha']=raw['Harvest.Year'].map(anio)
    d['peso_saco_kg']=raw['Bag.Weight'].map(peso)
    x=limpiar_entradas(d)
    x[OBJETIVO]=pd.to_numeric(d[OBJETIVO],errors='coerce')
    x['id_muestra']=raw.iloc[:,0].astype(str)
    grupos=[]
    for i,r in raw.iterrows():
        pais=normalizar(r.get('Country.of.Origin'))
        owner=normalizar(r.get('Owner.1')) or normalizar(r.get('Owner'))
        farm=normalizar(r.get('Farm.Name'))
        grupos.append(pais+'|'+('productor:'+owner if owner else 'finca:'+farm if farm else 'muestra:'+str(i)))
    # Códigos opacos: no se exportan nombres de productores o fincas.
    codigos={v:'G'+str(i+1).zfill(4) for i,v in enumerate(sorted(set(grupos)))}
    x['grupo']=[codigos[v] for v in grupos]
    # Se elimina el registro de catación con TODOS los componentes y total en cero.
    cero=raw[SENSORIALES].fillna(-1).eq(0).all(axis=1)&x[OBJETIVO].eq(0)
    valido=x[OBJETIVO].between(0,100)&~cero
    x=x.loc[valido].copy()
    # Una entrada idéntica con el mismo resultado no cruza entre subconjuntos.
    duplicado=x.duplicated(ENTRADAS+[OBJETIVO],keep='first')
    ndup=int(duplicado.sum());x=x.loc[~duplicado].reset_index(drop=True)
    return x, {'filas_originales':len(raw),'columnas_sin_indice':raw.shape[1]-1,
               'cataciones_cero_excluidas':int(cero.sum()),'objetivos_invalidos':int((~valido&~cero).sum()),
               'duplicados_excluidos':ndup,'filas_preparadas':len(x),
               'nulos_entrada':x[ENTRADAS].isna().sum().astype(int).to_dict(),
               'grupos':int(x.grupo.nunique())}
