"""KNN con desempate estable para predicciones reproducibles entre entornos."""
import numpy as np
from scipy.spatial.distance import cdist
from sklearn.neighbors import KNeighborsRegressor
from sklearn.utils.validation import check_is_fitted

class KNNDeterminista(KNeighborsRegressor):
    def predict(self,X):
        check_is_fitted(self)
        # Redondear distancias elimina diferencias de BLAS de orden 1e-14.
        dist=np.round(cdist(np.asarray(X,dtype=float),self._fit_X,metric='cityblock'),8)
        ids=np.argsort(dist,axis=1,kind='stable')[:,:self.n_neighbors]
        ds=np.take_along_axis(dist,ids,axis=1);ys=self._y[ids]
        if self.weights=='uniform':return ys.mean(axis=1)
        out=[]
        for distances,values in zip(ds,ys):
            zero=distances==0
            out.append(values[zero].mean() if zero.any() else np.average(values,weights=1/distances))
        return np.asarray(out)
