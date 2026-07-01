import numpy as np
import pandas as pd
import requests
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans


class EducacionClustering:
    """Motor de clustering para datos de educación en Colombia"""
    
    def __init__(self, n_clusters=5):
        self.scaler = StandardScaler()
        self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.n_clusters = n_clusters
        self.features = []
        self.df_processed = None
        self.DATASET_URL = "https://www.datos.gov.co/resource/nudc-7mev.json"

    def consultar_datos_colombia(self, url=None, limit=1000000):
        """Consulta datos desde datos.gov.co"""
        try:
            url = url or self.DATASET_URL
            response = requests.get(f"{url}?$limit={limit}", timeout=30)
            response.raise_for_status()
            df = pd.DataFrame(response.json())
            return df
        except Exception as e:
            raise Exception(f"Error al cargar datos: {str(e)}")

    def preparar_datos(self, df):
        """Limpia y prepara datos para clustering"""
        df_copy = df.copy()
        
        # Convertir columnas a numéricas
        for col in df_copy.columns:
            if col not in ['municipio', 'departamento', 'a_o', 'etc']:
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')

        # Seleccionar features numéricos relevantes
        self.features = df_copy.select_dtypes(include=[np.number]).dropna(axis=1, how='all').columns.tolist()
        self.features = [f for f in self.features if f not in ['c_digo_municipio', 'c_digo_dpto', 'c_digo_etc', 'a_o']]

        # Limpieza: rellenar con la media
        df_clean = df_copy.dropna(subset=['municipio'])
        df_numeric = df_clean[self.features].fillna(df_clean[self.features].mean())

        return df_clean, df_numeric

    def entrenar(self, df=None):
        """Entrena el modelo de clustering"""
        if df is None:
            df = self.consultar_datos_colombia()
        
        df_clean, df_numeric = self.preparar_datos(df)
        scaled_data = self.scaler.fit_transform(df_numeric)
        df_clean['cluster'] = self.model.fit_predict(scaled_data)
        self.df_processed = df_clean
        return df_clean

    def interpretar_clusters(self):
        """Retorna el perfil promedio de cada cluster"""
        resumen = self.df_processed.groupby('cluster')[self.features].mean()
        return resumen.to_dict(orient='index')

    def obtener_municipios_cluster(self, cluster_id):
        """Obtiene todos los municipios en un cluster específico"""
        if self.df_processed is None:
            raise ValueError("El modelo no ha sido entrenado")
        
        municipios = self.df_processed[self.df_processed['cluster'] == cluster_id][
            ['municipio', 'departamento', 'cluster']
        ].to_dict(orient='records')
        return municipios
