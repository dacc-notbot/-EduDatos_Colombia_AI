from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import logging
from app.clustering import EducacionClustering

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="EduDatos Colombia API",
    description="API de clustering educativo para análisis de educación en Colombia",
    version="1.0.0",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class MunicipioInfo(BaseModel):
    municipio: str
    departamento: str
    cluster: int
    tasa_matriculacion: Optional[float] = None
    cobertura_neta: Optional[float] = None

class ClusterPerfil(BaseModel):
    cluster: int
    descripcion: str
    indicadores_promedio: dict

class RecomendacionCluster(BaseModel):
    municipio: str
    departamento: str
    cluster: int
    recomendacion: str
    acciones_prioritarias: List[str]

# Motor global
engine = None

def inicializar_engine():
    """Inicializa y entrena el motor de clustering"""
    global engine
    try:
        logger.info("Inicializando motor de clustering...")
        engine = EducacionClustering(n_clusters=5)
        engine.entrenar()
        logger.info(f"Motor entrenado. Clusters: {engine.n_clusters}")
    except Exception as e:
        logger.error(f"Error al inicializar: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    """Inicializa la aplicación"""
    inicializar_engine()

@app.get("/", tags=["Health"])
def root():
    """Endpoint raíz"""
    return {
        "mensaje": "Bienvenido a EduDatos Colombia API",
        "documentacion": "/docs",
        "openapi": "/openapi.json"
    }

@app.get("/health", tags=["Health"])
def health():
    """Verifica el estado de la API"""
    return {
        "status": "healthy",
        "mensaje": "API de clustering educativo funcionando correctamente"
    }

@app.get("/metadata", tags=["Info"])
def get_metadata():
    """Obtiene metadatos del modelo"""
    if engine is None:
        raise HTTPException(status_code=500, detail="Motor no inicializado")
    
    return {
        "dataset": "Estadísticas educación preescolar, básica y media Colombia",
        "fuente": "https://www.datos.gov.co",
        "modelo": "K-Means Clustering",
        "clusters": engine.n_clusters,
        "variables": engine.features,
        "total_registros": len(engine.df_processed) if engine.df_processed is not None else 0
    }

@app.get("/municipios", tags=["Datos"])
def listar_municipios(
    departamento: Optional[str] = Query(None, description="Filtrar por departamento"),
    cluster: Optional[int] = Query(None, description="Filtrar por cluster (0-4)")
):
    """Lista municipios con su información de clustering"""
    if engine is None or engine.df_processed is None:
        raise HTTPException(status_code=500, detail="Motor no inicializado")
    
    df = engine.df_processed.copy()
    
    if departamento:
        df = df[df['departamento'].str.contains(departamento, case=False, na=False)]
    
    if cluster is not None:
        if cluster < 0 or cluster >= engine.n_clusters:
            raise HTTPException(status_code=400, detail=f"Cluster debe estar entre 0 y {engine.n_clusters-1}")
        df = df[df['cluster'] == cluster]
    
    if df.empty:
        return {"total": 0, "municipios": []}
    
    municipios = df[[
        'municipio', 'departamento', 'cluster',
        'tasa_matriculaci_n_5_16', 'cobertura_neta'
    ]].drop_duplicates().to_dict(orient='records')
    
    return {
        "total": len(municipios),
        "municipios": municipios
    }

@app.get("/municipio/cluster", tags=["Consultas"])
def obtener_cluster_municipio(
    municipio: str = Query(..., description="Nombre del municipio"),
    departamento: str = Query(..., description="Nombre del departamento")
):
    """Obtiene el cluster asignado a un municipio específico"""
    if engine is None or engine.df_processed is None:
        raise HTTPException(status_code=500, detail="Motor no inicializado")
    
    df = engine.df_processed
    match = df[(df['municipio'].str.contains(municipio, case=False, na=False)) &
               (df['departamento'].str.contains(departamento, case=False, na=False))]
    
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Municipio '{municipio}' en {departamento} no encontrado")
    
    row = match.iloc[0]
    cluster_id = int(row['cluster'])
    
    return {
        "municipio": row['municipio'],
        "departamento": row['departamento'],
        "cluster": cluster_id,
        "poblacion_5_16": float(row['poblaci_n_5_16']) if 'poblaci_n_5_16' in row and pd.notna(row['poblaci_n_5_16']) else None,
        "tasa_matriculacion": float(row['tasa_matriculaci_n_5_16']) if 'tasa_matriculaci_n_5_16' in row and pd.notna(row['tasa_matriculaci_n_5_16']) else None,
        "cobertura_neta": float(row['cobertura_neta']) if 'cobertura_neta' in row and pd.notna(row['cobertura_neta']) else None
    }

@app.get("/cluster/{cluster_id}/perfil", tags=["Análisis"])
def obtener_perfil_cluster(
    cluster_id: int = Query(..., ge=0, le=4, description="ID del cluster (0-4)")
):
    """Obtiene el perfil promedio de un cluster"""
    if engine is None:
        raise HTTPException(status_code=500, detail="Motor no inicializado")
    
    if cluster_id < 0 or cluster_id >= engine.n_clusters:
        raise HTTPException(status_code=400, detail=f"Cluster debe estar entre 0 y {engine.n_clusters-1}")
    
    perfiles = engine.interpretar_clusters()
    perfil = perfiles.get(cluster_id, {})
    
    # Descripción según el cluster
    descripciones = {
        0: "Municipios con desafíos en retención escolar en secundaria",
        1: "Municipios con necesidad de infraestructura tecnológica",
        2: "Municipios con énfasis en educación inicial",
        3: "Municipios con buena transición a educación superior",
        4: "Municipios con ratios docente-estudiante a mejorar"
    }
    
    return {
        "cluster": cluster_id,
        "descripcion": descripciones.get(cluster_id, ""),
        "indicadores_promedio": {k: float(v) if pd.notna(v) else None for k, v in perfil.items()},
        "municipios_total": len(engine.df_processed[engine.df_processed['cluster'] == cluster_id])
    }

@app.get("/cluster/{cluster_id}/municipios", tags=["Análisis"])
def municipios_por_cluster(
    cluster_id: int = Query(..., ge=0, le=4, description="ID del cluster (0-4)"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de resultados")
):
    """Lista todos los municipios en un cluster específico"""
    if engine is None or engine.df_processed is None:
        raise HTTPException(status_code=500, detail="Motor no inicializado")
    
    if cluster_id < 0 or cluster_id >= engine.n_clusters:
        raise HTTPException(status_code=400, detail=f"Cluster debe estar entre 0 y {engine.n_clusters-1}")
    
    municipios = engine.obtener_municipios_cluster(cluster_id)[:limit]
    
    return {
        "cluster": cluster_id,
        "total": len(municipios),
        "municipios": municipios
    }

@app.get("/recomendaciones", tags=["Consultas"])
def obtener_recomendaciones(
    municipio: str = Query(..., description="Nombre del municipio"),
    departamento: str = Query(..., description="Nombre del departamento")
):
    """Obtiene recomendaciones personalizadas para un municipio"""
    if engine is None or engine.df_processed is None:
        raise HTTPException(status_code=500, detail="Motor no inicializado")
    
    # Obtener cluster del municipio
    df = engine.df_processed
    match = df[(df['municipio'].str.contains(municipio, case=False, na=False)) &
               (df['departamento'].str.contains(departamento, case=False, na=False))]
    
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Municipio '{municipio}' no encontrado")
    
    cluster = int(match.iloc[0]['cluster'])
    
    # Recomendaciones por cluster
    recomendaciones_por_cluster = {
        0: {
            "titulo": "Fortalecer Retención Escolar",
            "acciones": [
                "Implementar programas de apoyo emocional en secundaria",
                "Mejorar comunicación entre familia y escuela",
                "Crear incentivos para permanencia estudiantil",
                "Reforzar orientación vocacional"
            ]
        },
        1: {
            "titulo": "Mejorar Infraestructura Tecnológica",
            "acciones": [
                "Priorizar conexión a internet en sedes educativas",
                "Equipar laboratorios de informática",
                "Capacitar docentes en herramientas digitales",
                "Implementar plataformas de educación virtual"
            ]
        },
        2: {
            "titulo": "Expandir Educación Inicial",
            "acciones": [
                "Aumentar cobertura de preescolar",
                "Mejorar calidad de educación inicial",
                "Invertir en formación de docentes de preescolar",
                "Fortalecer vínculos familia-escuela desde edad temprana"
            ]
        },
        3: {
            "titulo": "Potenciar Transición a Educación Superior",
            "acciones": [
                "Mantener y mejorar indicadores actuales",
                "Expandir programas técnicos y tecnológicos",
                "Fortalecer alianzas con universidades",
                "Aumentar becas para estudiantes de pregrado"
            ]
        },
        4: {
            "titulo": "Optimizar Recursos Docentes",
            "acciones": [
                "Reducir ratio docente-estudiante",
                "Mejorar capacitación docente continua",
                "Optimizar distribución de maestros",
                "Incrementar incentivos para docentes rurales"
            ]
        }
    }
    
    recom = recomendaciones_por_cluster.get(cluster, {})
    
    return RecomendacionCluster(
        municipio=municipio,
        departamento=departamento,
        cluster=cluster,
        recomendacion=recom.get("titulo", ""),
        acciones_prioritarias=recom.get("acciones", [])
    )

@app.get("/comparar", tags=["Análisis"])
def comparar_municipios(
    municipios: str = Query(..., description="Municipios separados por coma: 'Bogotá,Medellín'"),
    departamentos: str = Query(..., description="Departamentos separados por coma: 'Cundinamarca,Antioquia'")
):
    """Compara indicadores entre múltiples municipios"""
    if engine is None or engine.df_processed is None:
        raise HTTPException(status_code=500, detail="Motor no inicializado")
    
    municipios_list = [m.strip() for m in municipios.split(',')]
    departamentos_list = [d.strip() for d in departamentos.split(',')]
    
    if len(municipios_list) != len(departamentos_list):
        raise HTTPException(status_code=400, detail="Número de municipios y departamentos debe coincidir")
    
    comparacion = []
    for mun, dep in zip(municipios_list, departamentos_list):
        df = engine.df_processed
        match = df[(df['municipio'].str.contains(mun, case=False, na=False)) &
                   (df['departamento'].str.contains(dep, case=False, na=False))]
        
        if not match.empty:
            row = match.iloc[0]
            comparacion.append({
                "municipio": row['municipio'],
                "departamento": row['departamento'],
                "cluster": int(row['cluster']),
                "tasa_matriculacion": float(row['tasa_matriculaci_n_5_16']) if pd.notna(row['tasa_matriculaci_n_5_16']) else None,
                "cobertura_neta": float(row['cobertura_neta']) if pd.notna(row['cobertura_neta']) else None
            })
    
    return {
        "total_municipios": len(comparacion),
        "municipios": comparacion
    }

# Importar pandas para pd.notna
import pandas as pd

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
