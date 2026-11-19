"""Ejecuta CRISP-DM de forma reproducible. Desde esta carpeta: python entrenar.py."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from pathlib import Path
import json, hashlib, platform, time, itertools
import numpy as np
import pandas as pd
import scipy, sklearn, joblib
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.decomposition import PCA
from sklearn.model_selection import GroupShuffleSplit,GroupKFold,GridSearchCV
from sklearn.metrics import mean_absolute_error,root_mean_squared_error,r2_score
from sklearn.linear_model import LinearRegression,Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import VotingRegressor,BaggingRegressor,GradientBoostingRegressor
from sklearn.dummy import DummyRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.inspection import permutation_importance
from preparacion import *
from vecinos import KNNDeterminista

ROOT=Path(__file__).resolve().parent
RES=ROOT/'resultados';FIG=ROOT/'figuras';MOD=ROOT/'modelo';DATA=ROOT/'data'
for p in (RES,FIG,MOD,DATA):p.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})

def savejson(name,obj):
    (RES/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=lambda o:float(o)),encoding='utf-8')

def pipeline(model):
    num=Pipeline([('imputar',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)),
                  ('escalar',StandardScaler()),('pca','passthrough')])
    cat=Pipeline([('imputar',SimpleImputer(strategy='constant',fill_value='No informado')),
                  ('codificar',OneHotEncoder(handle_unknown='infrequent_if_exist',min_frequency=10,sparse_output=False))])
    return Pipeline([('preparar',ColumnTransformer([('numericas',num,NUMERICAS),('categoricas',cat,CATEGORICAS)])),('modelo',model)])

def modelos():
    pca={'preparar__numericas__pca':['passthrough',PCA(n_components=0.95,svd_solver='full')]}
    defs={
      'Lineal':(LinearRegression(),{}),
      'Ridge':(Ridge(),{'modelo__alpha':[1,10,100]}),
      'KNN':(KNNDeterminista(algorithm='brute',metric='manhattan'),{'modelo__n_neighbors':[7,21,45],'modelo__weights':['uniform','distance']}),
      'SVR':(SVR(),{'modelo__C':[1,10],'modelo__epsilon':[0.1,0.5]}),
      'Arbol':(DecisionTreeRegressor(random_state=42),{'modelo__max_depth':[3,6],'modelo__min_samples_leaf':[10,25]}),
      'Votacion':(VotingRegressor([('ridge',Ridge(alpha=10)),('svr',SVR(C=10,epsilon=.5)),('knn',KNNDeterminista(n_neighbors=21,weights='distance',algorithm='brute',metric='manhattan'))]),{'modelo__weights':[(1,1,1),(1,2,1)]}),
      'Bagging':(BaggingRegressor(estimator=DecisionTreeRegressor(max_depth=6,min_samples_leaf=10),n_estimators=100,random_state=42,n_jobs=1),{'modelo__max_samples':[.7,1.0],'modelo__max_features':[.8,1.0]}),
      'Boosting':(GradientBoostingRegressor(random_state=42),{'modelo__n_estimators':[100,200],'modelo__learning_rate':[.03,.1],'modelo__max_depth':[2]})
    }
    return {n:(pipeline(m),dict(pca,**grid)) for n,(m,grid) in defs.items()}

def metricas(y,p):
    return {'RMSE':float(root_mean_squared_error(y,p)),'MAE':float(mean_absolute_error(y,p)),
            'R2':float(r2_score(y,p)),'sesgo_pred_menos_real':float(np.mean(p-y))}

def comparar_estadistica(cv,names):
    tab=cv.pivot(index='fold',columns='modelo',values='RMSE')[names]
    a=tab.to_numpy();b,k=a.shape;grand=a.mean()
    ssmodelo=b*((a.mean(0)-grand)**2).sum();ssbloque=k*((a.mean(1)-grand)**2).sum()
    residual=a-a.mean(0)[None,:]-a.mean(1)[:,None]+grand
    sse=(residual**2).sum();df=(b-1)*(k-1);mse=sse/df;f=(ssmodelo/(k-1))/mse
    an={'diseno':'ANOVA de bloques completos; bloque = partición externa de validación cruzada',
        'F_modelo':f,'p_modelo':stats.f.sf(f,k-1,df),'gl_modelo':k-1,'gl_error':df,'MSE':mse,
        'Shapiro_residuos_p':stats.shapiro(residual.ravel()).pvalue,
        'Levene_p':stats.levene(*[a[:,j] for j in range(k)],center='median').pvalue,
        'limite':'Los entrenamientos de CV se superponen. P-valores exploratorios, no prueba confirmatoria de superioridad universal.'}
    pairs=[]
    for i,j in itertools.combinations(range(k),2):
        delta=a[:,i].mean()-a[:,j].mean();se=np.sqrt(mse/b)
        p=float(stats.studentized_range.sf(abs(delta)/se,k,df))
        q=stats.studentized_range.ppf(.95,k,df)
        pairs.append({'modelo_A':names[i],'modelo_B':names[j],'diferencia_RMSE_A_menos_B':delta,
                      'p_Tukey':p,'IC95_inferior':delta-q*se,'IC95_superior':delta+q*se,'significativa_005':p<.05})
    pd.DataFrame(pairs).to_csv(RES/'tukey.csv',index=False);savejson('anova.json',an)
    # Sensibilidad pareada con varianza corregida por solapamiento (aproximación de Nadeau-Bengio).
    winner=tab.mean().idxmin();corr=[]
    for other in names:
        if other==winner:continue
        d=(tab[winner]-tab[other]).to_numpy();se=np.sqrt((1/b+1/(b-1))*np.var(d,ddof=1))
        t=float(np.mean(d)/se) if se>0 else 0
        corr.append({'mejor_media':winner,'comparador':other,'delta_RMSE':float(d.mean()),'p_t_corregida':float(2*stats.t.sf(abs(t),b-1))})
    c=pd.DataFrame(corr).sort_values('p_t_corregida');adjust=np.maximum.accumulate(c.p_t_corregida.to_numpy()*np.arange(len(c),0,-1))
    c['p_Holm']=np.minimum(1,adjust);c.to_csv(RES/'comparaciones_corregidas.csv',index=False)

def main():
    if not (DATA/'arabica_data_cleaned.csv').exists():
        from descargar_datos import descargar
        descargar()
    t=time.time();raw=pd.read_csv(DATA/'arabica_data_cleaned.csv');d,audit=preparar_original(raw)
    audit['sha256_original']=hashlib.sha256((DATA/'arabica_data_cleaned.csv').read_bytes()).hexdigest()
    d.to_csv(DATA/'cafe_preparado.csv',index=False)
    # El criterio de elección solo usa número de filas: no usa y ni resultados de modelos.
    splitter=GroupShuffleSplit(n_splits=100,test_size=.30,random_state=42)
    tr,te=min(splitter.split(d,groups=d.grupo),key=lambda z:abs(len(z[0])/len(d)-.70))
    train=d.iloc[tr].copy();test=d.iloc[te].copy()
    assert set(train.grupo).isdisjoint(set(test.grupo))
    train.to_csv(DATA/'desarrollo_70.csv',index=False);test.to_csv(DATA/'prueba_30.csv',index=False)
    audit.update({'n_desarrollo':len(train),'n_prueba':len(test),'fraccion_desarrollo':len(train)/len(d),
                  'grupos_desarrollo':train.grupo.nunique(),'grupos_prueba':test.grupo.nunique(),'grupos_compartidos':0})
    savejson('auditoria.json',audit)
    X=train[ENTRADAS];y=train[OBJETIVO];g=train.grupo
    X.describe().T.to_csv(RES/'descripcion_numericas.csv');y.describe().to_csv(RES/'descripcion_objetivo.csv')
    cats=[]
    for c in CATEGORICAS:
        for v,n in X[c].fillna('No informado').value_counts().items():cats.append({'variable':c,'categoria':v,'frecuencia':n})
    pd.DataFrame(cats).to_csv(RES/'frecuencias_categoricas.csv',index=False)
    rel=[]
    for c in NUMERICAS:
        a=pd.to_numeric(X[c],errors='coerce');ok=a.notna()
        rel.append({'variable':c,'Pearson':a.corr(y),'Spearman':a.corr(y,method='spearman'),
                    'n_observados':int(ok.sum()),'MI':float(mutual_info_regression(a.loc[ok].to_numpy().reshape(-1,1),y.loc[ok],random_state=42)[0])})
    pd.DataFrame(rel).to_csv(RES/'relaciones.csv',index=False)
    cols=NUMERICAS+[OBJETIVO];corr=train[cols].corr()
    fig,ax=plt.subplots(figsize=(8,6));im=ax.imshow(corr,vmin=-1,vmax=1,cmap='RdBu_r');ax.set_xticks(range(len(cols)),cols,rotation=55,ha='right',fontsize=8);ax.set_yticks(range(len(cols)),cols,fontsize=8);fig.colorbar(im,ax=ax,label='Correlación de Pearson');fig.tight_layout();fig.savefig(FIG/'correlaciones.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,3.5));ax.hist(y,bins=25,color='#78513b',edgecolor='white');ax.set(xlabel='Puntuación de taza',ylabel='Lotes de desarrollo');fig.tight_layout();fig.savefig(FIG/'distribucion.png',dpi=170);plt.close(fig)
    outer=list(GroupKFold(n_splits=5,shuffle=True,random_state=42).split(X,y,g))
    scores=[];oof=[];hyper=[];definitions=modelos()
    for name,(est,grid) in definitions.items():
        print('Modelo',name,flush=True)
        for fold,(a,b) in enumerate(outer,1):
            inner=GroupKFold(n_splits=3,shuffle=True,random_state=100+fold)
            search=GridSearchCV(est,grid,scoring='neg_root_mean_squared_error',cv=inner,n_jobs=2,error_score='raise')
            search.fit(X.iloc[a],y.iloc[a],groups=g.iloc[a]);pred=search.predict(X.iloc[b])
            scores.append({'modelo':name,'fold':fold,**metricas(y.iloc[b],pred)})
            oof.extend({'modelo':name,'fold':fold,'id_muestra':train.iloc[b[j]].id_muestra,'real':float(y.iloc[b[j]]),'predicho':float(pred[j])} for j in range(len(b)))
            hyper.append({'modelo':name,'fold':fold,'mejores_parametros':str(search.best_params_)})
        pd.DataFrame(scores).to_csv(RES/'validacion_cruzada.csv',index=False)
    cv=pd.DataFrame(scores);summary=cv.groupby('modelo').agg(RMSE_media=('RMSE','mean'),RMSE_sd=('RMSE','std'),MAE_media=('MAE','mean'),R2_media=('R2','mean')).sort_values('RMSE_media').reset_index()
    summary.to_csv(RES/'comparacion_cv.csv',index=False);pd.DataFrame(oof).to_csv(RES/'predicciones_oof.csv',index=False);pd.DataFrame(hyper).to_csv(RES/'hiperparametros_anidados.csv',index=False)
    winner=summary.iloc[0]['modelo'];comparar_estadistica(cv,list(definitions))
    # A partir de aquí se congela la selección. El set de prueba no elige el ganador.
    final={};bestparams={};tests=[]
    for name,(est,grid) in definitions.items():
        gs=GridSearchCV(est,grid,scoring='neg_root_mean_squared_error',cv=GroupKFold(n_splits=5,shuffle=True,random_state=42),n_jobs=2,error_score='raise')
        gs.fit(X,y,groups=g);final[name]=gs.best_estimator_;bestparams[name]={k:str(v) for k,v in gs.best_params_.items()}
        pred=gs.predict(test[ENTRADAS]);tests.append({'modelo':name,**metricas(test[OBJETIVO],pred)})
    dummy=DummyRegressor().fit(X,y);tests.append({'modelo':'Referencia_media',**metricas(test[OBJETIVO],dummy.predict(test[ENTRADAS]))})
    pd.DataFrame(tests).to_csv(RES/'evaluacion_prueba.csv',index=False);savejson('hiperparametros_finales.json',bestparams)
    model=final[winner];joblib.dump(model,MOD/'modelo_cafe.joblib',compress=3)
    pred=model.predict(test[ENTRADAS]);testpred=test[['id_muestra',OBJETIVO]].copy();testpred['prediccion']=pred;testpred['error_pred_menos_real']=pred-test[OBJETIVO].to_numpy();testpred.to_csv(RES/'predicciones_prueba.csv',index=False)
    rng=np.random.default_rng(42);boot=[]
    groups=test.grupo.unique()
    for _ in range(1000):
        chosen=rng.choice(groups,size=len(groups),replace=True);idx=np.concatenate([np.flatnonzero(test.grupo.to_numpy()==v) for v in chosen]);boot.append(root_mean_squared_error(test[OBJETIVO].to_numpy()[idx],pred[idx]))
    ci=np.quantile(boot,[.025,.975]);importance=permutation_importance(model,test[ENTRADAS],test[OBJETIVO],scoring='neg_root_mean_squared_error',n_repeats=10,random_state=42,n_jobs=2)
    pd.DataFrame({'variable':ENTRADAS,'aumento_RMSE_media':importance.importances_mean,'sd':importance.importances_std}).sort_values('aumento_RMSE_media',ascending=False).to_csv(RES/'importancia_permutacion.csv',index=False)
    fig,ax=plt.subplots(figsize=(7,4));ax.barh(summary.modelo[::-1],summary.RMSE_media[::-1],xerr=summary.RMSE_sd[::-1],color='#78513b',capsize=3);ax.set(xlabel='RMSE de validación cruzada anidada (puntos)',ylabel='Modelo');fig.tight_layout();fig.savefig(FIG/'comparacion_modelos.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(5.5,4.4));ax.scatter(test[OBJETIVO],pred,s=18,alpha=.6,color='#78513b');lo=min(test[OBJETIVO].min(),pred.min());hi=max(test[OBJETIVO].max(),pred.max());ax.plot([lo,hi],[lo,hi],'k--',lw=1);ax.set(xlabel='Puntuación observada',ylabel='Puntuación predicha',title='Prueba reservada por productor');fig.tight_layout();fig.savefig(FIG/'observado_predicho.png',dpi=170);plt.close(fig)
    # Escenarios ilustrativos, NO resultados futuros medidos ni evidencia de exactitud externa.
    new=pd.DataFrame([
      [1600,.11,0,2,50,60,2026,'Colombia','Caturra','Washed / Wet','Green'],
      [1800,.12,0,1,30,60,2026,'Colombia','Bourbon','Washed / Wet','Green'],
      [1200,.11,1,8,100,60,2026,'Brazil','Mundo Novo','Natural / Dry','Green'],
      [1500,.10,0,3,40,69,2026,'Guatemala','Bourbon','Washed / Wet','Bluish-Green'],
      [1700,.12,0,4,25,69,2026,'Costa Rica','Catuai','Pulped natural / honey','Green']
    ],columns=ENTRADAS)
    new.to_csv(DATA/'entradas_nuevas_ejemplo.csv',index=False);results=new.copy();results['puntaje_estimado']=model.predict(limpiar_entradas(new));results['tipo_dato']='Escenario hipotético sin catación de referencia';results.to_csv(RES/'predicciones_nuevas.csv',index=False)
    # Primer ejemplo observado del set de prueba para prueba funcional, identificado como tal.
    test[ENTRADAS].head(1).to_csv(DATA/'ejemplo_observado_prueba.csv',index=False)
    pca=model.named_steps['preparar'].named_transformers_['numericas'].named_steps['pca']
    info={'modelo_elegido':winner,'criterio':'Menor RMSE medio de validación cruzada anidada por grupos',
          'metricas_prueba':metricas(test[OBJETIVO],pred),'RMSE_bootstrap_grupos_IC95':ci.tolist(),
          'n_componentes_PCA':int(pca.n_components_) if hasattr(pca,'n_components_') else None,
          'dimensiones_transformadas':int(model.named_steps['preparar'].transform(X.head(1)).shape[1]),
          'num_entradas':len(ENTRADAS),'rangos_desarrollo':{c:[float(X[c].min()),float(X[c].max())] for c in NUMERICAS},
          'categorias_desarrollo':{c:sorted(X[c].dropna().unique().tolist()) for c in CATEGORICAS},
          'anio_max_desarrollo':int(X.anio_cosecha.max()),'puntaje_medio_desarrollo':float(y.mean()),
          'versiones':{'python':platform.python_version(),'scikit-learn':sklearn.__version__,'pandas':pd.__version__,'numpy':np.__version__,'scipy':scipy.__version__},
          'duracion_segundos':time.time()-t}
    savejson('resumen.json',info);(MOD/'metadata.json').write_text(json.dumps(info,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'auditoria':audit,'resultado':info},indent=2,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
