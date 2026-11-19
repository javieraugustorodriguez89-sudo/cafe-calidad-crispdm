"""Validación y predicción de entradas ajenas al entrenamiento."""
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from preparacion import ENTRADAS,NUMERICAS,CATEGORICAS,limpiar_entradas

ROOT=Path(__file__).resolve().parent

def cargar():
    return (joblib.load(ROOT/'modelo/modelo_cafe.joblib'),
            json.loads((ROOT/'modelo/metadata.json').read_text(encoding='utf-8')))

def predecir(df,model,meta):
    faltan=[c for c in ENTRADAS if c not in df]
    if faltan:raise ValueError('Faltan columnas requeridas: '+', '.join(faltan))
    if len(df)==0:raise ValueError('El archivo no contiene filas.')
    x=limpiar_entradas(df);avisos=[]
    for c in NUMERICAS:
        presente=df[c].notna() & df[c].astype(str).str.strip().ne('')
        if (presente & x[c].isna()).any():
            raise ValueError('Valor inválido en '+c+'. Revise la regla de calidad y las unidades.')
        lo,hi=meta['rangos_desarrollo'][c]
        if ((x[c]<lo)|(x[c]>hi)).any():avisos.append(c+': hay valores fuera del intervalo observado al desarrollar el modelo.')
    if (x.notna().sum(axis=1)<7).any():raise ValueError('Cada lote debe informar al menos 7 de las 11 entradas.')
    for c in CATEGORICAS:
        nuevos=x[c].dropna()[~x[c].dropna().isin(meta['categorias_desarrollo'][c])].unique()
        if len(nuevos):avisos.append(c+': categoría no representada en desarrollo ('+', '.join(map(str,nuevos))+').')
    if x.isna().any().any():avisos.append('Se completaron campos faltantes con las reglas aprendidas en entrenamiento.')
    out=df[ENTRADAS].copy();out['puntaje_estimado']=model.predict(x)
    if ((out.puntaje_estimado<0)|(out.puntaje_estimado>100)).any():
        raise ValueError('La predicción está fuera de la escala de puntuación. La muestra requiere revisión.')
    return out,avisos

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('entrada');p.add_argument('--salida',default='predicciones.csv');a=p.parse_args()
    m,meta=cargar();r,w=predecir(pd.read_csv(a.entrada),m,meta);r.to_csv(a.salida,index=False)
    print(r.to_string(index=False))
    for v in w:print('Aviso:',v)
