# Guía de Integración con ChatGPT

## Paso 1: Desplegar la API

### Opción A: Local (desarrollo)
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

La API estará disponible en: `http://localhost:8000`

### Opción B: Docker
```bash
docker-compose up
```

### Opción C: Servidor Production (Render, Railway, Heroku)
1. Hacer push del código a GitHub
2. Conectar el repositorio a la plataforma
3. Configurar comando de inicio: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Opción D: ngrok (para pruebas públicas)
```bash
# En Google Colab o local
from pyngrok import ngrok
ngrok.set_auth_token("TU_TOKEN")
public_url = ngrok.connect(8000)
print(f"URL pública: {public_url}")
```

---

## Paso 2: Configurar GPT Actions en ChatGPT

### 2.1 Acceder a GPT Builder
1. Ve a https://chat.openai.com
2. Haz clic en **"Explore"** → **"Create a GPT"**
3. Dale un nombre: **"EduDatos Colombia Analista"**

### 2.2 Configurar Instructions (Instrucciones)
En la sección **"Instructions"**, pega esto:

```
Eres un experto en análisis de educación en Colombia. 
Tienes acceso a una API que contiene datos de municipios 
y su clasificación en clusters educativos.

Tu rol es:
1. Analizar indicadores educativos por municipio
2. Proporcionar recomendaciones basadas en clusters
3. Comparar datos entre municipios
4. Sugerir políticas educativas basadas en datos

Usa siempre la API para obtener datos actuales.
```

### 2.3 Configurar el Schema de Acciones
En la sección **"Actions"**:

1. Haz clic en **"Create new action"**
2. Selecciona **"Import from URL"**
3. Pega la URL de tu API + `/openapi.json`
   - **Local**: `http://localhost:8000/openapi.json`
   - **Remota**: `https://tu-api-publica.com/openapi.json`
4. Haz clic en **"Import"**

Esto importará automáticamente todos los endpoints disponibles.

### 2.4 Configurar Autenticación (si es necesario)
En **"Authentication"**:
- Selecciona **"API Key"** si requieres autenticación
- O déjalo en **"None"** para acceso público

### 2.5 Guardar el GPT
1. Haz clic en **"Save"**
2. Selecciona **"Only me"** o **"Anyone with the link"**
3. ¡Listo! Tu GPT está configurado

---

## Paso 3: Pruebas Iniciales

### Desde ChatGPT:
```
Cuál es el cluster del municipio Bogotá en Cundinamarca?
```

### Respuesta esperada:
El GPT llamará a `/municipio/cluster` y recibirá datos del municipio.

---

## Endpoints Disponibles

### Health Check
```
GET /health
```
Verifica que la API esté funcionando.

### Metadata
```
GET /metadata
```
Obtiene información sobre el modelo y variables.

### Buscar Municipio
```
GET /municipio/cluster?municipio=Bogotá&departamento=Cundinamarca
```

### Listar Municipios por Cluster
```
GET /cluster/{cluster_id}/municipios?limit=50
```

### Obtener Perfil de Cluster
```
GET /cluster/{cluster_id}/perfil
```

### Recomendaciones
```
GET /recomendaciones?municipio=Bogotá&departamento=Cundinamarca
```

### Comparar Municipios
```
GET /comparar?municipios=Bogotá,Medellín&departamentos=Cundinamarca,Antioquia
```

---

## Solución de Problemas

### Error: "Connection refused"
- Verifica que la API esté corriendo: `http://localhost:8000/health`
- Comprueba el puerto (por defecto 8000)

### Error: "Invalid schema"
- Abre `http://tu-api/openapi.json` en el navegador
- Verifica que el JSON sea válido

### El GPT no encuentra los endpoints
- Recarga la página del GPT Builder
- Vuelve a importar el schema desde el URL

### Timeout en llamadas
- Aumenta el tiempo de espera en el GPT
- Verifica que el servidor responda rápidamente

---

## Prompts Sugeridos para Probar

1. **Análisis rápido**
   > "Analiza la situación educativa de Medellín en Antioquia"

2. **Comparación**
   > "Compara los indicadores educativos entre Bogotá y Cali"

3. **Recomendaciones**
   > "¿Qué acciones debería tomar el municipio de Cúcuta para mejorar su educación?"

4. **Clustering**
   > "Muéstrame todos los municipios en el mismo cluster que Ibagué"

5. **Análisis por departamento**
   > "Lista los municipios de Boyacá y su clasificación educativa"

---

## Publicación en Producción

### Opción 1: Render (Recomendado - Gratuito)
1. Ve a https://render.com
2. New → Web Service
3. Conecta tu repo de GitHub
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. ¡Listo! URL pública generada automáticamente

### Opción 2: Railway
1. Ve a https://railway.app
2. New Project → GitHub repo
3. Selecciona Python
4. Configura las variables de entorno

### Opción 3: Heroku (Requiere tarjeta)
```bash
heroku login
heroku create mi-api-educacion
git push heroku main
```

---

## Monitoreo y Logs

### Ver logs locales:
```bash
# Si usas docker-compose
docker-compose logs -f api

# Si usas Render/Railway, ver en el dashboard
```

### Health check automático:
La API incluye `/health` para monitoring.

---

## Seguridad

- [ ] Habilitar CORS solo en dominios de confianza
- [ ] Agregar rate limiting
- [ ] Usar HTTPS en producción
- [ ] Validar inputs en todos los endpoints
- [ ] Agregar autenticación si es necesario

---

## Soporte

Para problemas o preguntas:
- Revisa los logs de la API
- Verifica `/docs` para ver la documentación interactiva
- Prueba los endpoints directamente con curl:
  ```bash
  curl http://localhost:8000/health
  ```
