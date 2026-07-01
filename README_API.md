# EduDatos Colombia API

## 📊 Descripción

API REST para análisis de educación en Colombia usando Machine Learning (K-Means Clustering). Proporciona análisis automático de datos educativos por municipio desde `datos.gov.co`.

## 🚀 Características

- ✅ Clustering automático de municipios basado en indicadores educativos
- ✅ Recomendaciones personalizadas por municipio
- ✅ Comparación entre múltiples municipios
- ✅ Integración directa con ChatGPT via GPT Actions
- ✅ Documentación interactiva (Swagger UI)
- ✅ CORS habilitado para integración con GPT

## 📋 Variables Analizadas

- Tasa de matriculación
- Cobertura neta
- Tasas de reprobación (primaria, secundaria, media)
- Repitencia
- Tamaño promedio de grupos
- Conectividad a internet

## 🏗️ Arquitectura

```
┌─────────────────────┐
│   Datos.gov.co      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ EducacionClustering │  (app/clustering.py)
│  - K-Means (5)      │
│  - StandardScaler   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   FastAPI (main.py) │  Endpoints REST
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ChatGPT Actions    │  Integración GPT
└─────────────────────┘
```

## 🔧 Instalación

### Requisitos
- Python 3.9+
- pip

### Local
```bash
# Clonar repositorio
git clone https://github.com/dacc-notbot/-EduDatos_Colombia_AI.git
cd -EduDatos_Colombia_AI

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
uvicorn app.main:app --reload
```

### Docker
```bash
docker-compose up
```

## 📚 Endpoints

### Health
```bash
GET /health
```

### Información
```bash
GET /metadata
```

### Municipios
```bash
# Listar todos
GET /municipios

# Filtrar por departamento
GET /municipios?departamento=Antioquia

# Filtrar por cluster
GET /municipios?cluster=2
```

### Cluster de Municipio
```bash
GET /municipio/cluster?municipio=Bogotá&departamento=Cundinamarca
```

### Perfil de Cluster
```bash
GET /cluster/0/perfil
GET /cluster/1/perfil
# ... 0-4
```

### Municipios por Cluster
```bash
GET /cluster/2/municipios?limit=50
```

### Recomendaciones
```bash
GET /recomendaciones?municipio=Medellín&departamento=Antioquia
```

### Comparar
```bash
GET /comparar?municipios=Bogotá,Medellín&departamentos=Cundinamarca,Antioquia
```

## 📖 Documentación Interactiva

Una vez ejecutando la API:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤖 Integración con ChatGPT

Ver [`GPT_INTEGRATION_GUIDE.md`](./GPT_INTEGRATION_GUIDE.md) para instrucciones completas.

### Resumen rápido:
1. Desplega la API (local o en servidor)
2. Crea un GPT en https://chat.openai.com
3. Configura Actions con el schema: `{URL_API}/openapi.json`
4. ¡Listo! El GPT puede consultar la API automáticamente

## 📊 Clusters

- **Cluster 0**: Desafíos en retención escolar
- **Cluster 1**: Necesidad de infraestructura tecnológica
- **Cluster 2**: Énfasis en educación inicial
- **Cluster 3**: Buena transición a educación superior
- **Cluster 4**: Optimización de recursos docentes

## 🔐 Seguridad

La API actual:
- ✅ Permite CORS desde cualquier origen (para GPT)
- ⚠️ Sin autenticación (agregar en producción)
- ✅ Valida inputs
- ✅ Manejo de errores robusto

## 📈 Despliegue en Producción

### Render (Recomendado)
```bash
# Push a GitHub y conecta Render
# Build: pip install -r requirements.txt
# Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Railway
```bash
# Conecta tu repo de GitHub
# Railway detecta automáticamente Python
```

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| Port 8000 en uso | Usa otro puerto: `--port 8001` |
| ModuleNotFoundError | Instala dependencias: `pip install -r requirements.txt` |
| CORS error | Ya está configurado en main.py |
| Datos no cargan | Verifica conexión a internet (requiere datos.gov.co) |

## 📝 Ejemplos de Uso

### Curl
```bash
# Health check
curl http://localhost:8000/health

# Obtener cluster
curl "http://localhost:8000/municipio/cluster?municipio=Bogotá&departamento=Cundinamarca"

# Recomendaciones
curl "http://localhost:8000/recomendaciones?municipio=Bogotá&departamento=Cundinamarca"
```

### Python
```python
import requests

url = "http://localhost:8000"

# Obtener metadata
meta = requests.get(f"{url}/metadata").json()
print(meta)

# Obtener cluster
cluster = requests.get(
    f"{url}/municipio/cluster",
    params={"municipio": "Bogotá", "departamento": "Cundinamarca"}
).json()
print(cluster)
```

## 📄 Licencia

MIT

## 👤 Autor

DACC - dacc-notbot

## 🔗 Enlaces

- [Datos.gov.co](https://www.datos.gov.co)
- [FastAPI](https://fastapi.tiangolo.com/)
- [ChatGPT](https://chat.openai.com)
