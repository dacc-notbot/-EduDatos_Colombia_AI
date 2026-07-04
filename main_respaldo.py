from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="EducaDatos API",
    description="Backend ciudadano para consultar datos educativos abiertos de Colombia",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En desarrollo se permite todo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DATOS_GOV_BASE = "https://www.datos.gov.co/resource"

DATASETS = {
    "establecimientos": "cfw5-qzt5",
    "estadisticas_municipales": "nudc-7mev",
    "saber_pro": "u37r-hjmu",
    "programas_superior": "cfw5-qzt5"
}
from config import DATASETS, DATASET_BASE, PUBLIC_BASE_URL
from services.socrata_service import (
    consultar_dataset,
    explorar_columnas_dataset,
    buscar_en_dataset
)
from services.consulta_service import resolver_consulta_ciudadana
from services.clustering_service import (
    obtener_metadata_clustering_service,
    consultar_clusters_municipios_service,
    consultar_cluster_municipio_service,
    buscar_municipios_similares_service,
    generar_recomendaciones_municipio_service
)
from services.cruce_service import analizar_transito_educativo_service
from services.diagnostico_service import diagnostico_territorial_educativo_service
from config import DATASETS, DATASET_BASE, PUBLIC_BASE_URL

import requests
import pandas as pd
import numpy as np
import re
import unicodedata


@app.get("/", operation_id="inicioApi")

@app.get("/health", operation_id="verificarEstadoApi")
def health():
    return {
        "status": "ok",
        "message": "API EducaDatos funcionando correctamente",
        "proyecto": "Asistente ciudadano para datos abiertos educativos"
    }


@app.get("/datasets", operation_id="listarDatasetsEducativos")
def listar_datasets():
    return {
        "total_datasets": len(DATASETS),
        "dataset_base": DATASET_BASE,
        "datasets": DATASETS
    }
def limpiar_numero(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    if texto == "" or texto.lower() in ["nan", "none", "null"]:
        return None

    texto = texto.replace("%", "").strip()

    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return None


def serie_numerica(df, columna):
    if not columna or columna not in df.columns:
        return None

    return df[columna].apply(limpiar_numero)

@app.get("/datasets/{dataset_key}", operation_id="obtenerDetalleDataset")
def obtener_detalle_dataset(dataset_key: str):
    if dataset_key not in DATASETS:
        raise HTTPException(
            status_code=404,
            detail=f"No existe un dataset configurado con la clave: {dataset_key}"
        )

    return {
        "dataset_key": dataset_key,
        "detalle": DATASETS[dataset_key]
    }


@app.get("/datasets/{dataset_key}/preview", operation_id="previsualizarDatasetEducativo")
def previsualizar_dataset_educativo(
    dataset_key: str,
    limit: int = Query(5, ge=1, le=50, description="Número de registros de muestra.")
):
    try:
        registros = consultar_dataset(dataset_key=dataset_key, limit=limit)
        return {
            "dataset_key": dataset_key,
            "total_registros_devuelto": len(registros),
            "registros": registros
        }
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.get("/datasets/{dataset_key}/columnas", operation_id="explorarColumnasDatasetEducativo")
def explorar_columnas_dataset_educativo(
    dataset_key: str,
    limit: int = Query(10, ge=1, le=50, description="Número de registros usados para detectar columnas.")
):
    try:
        return explorar_columnas_dataset(dataset_key=dataset_key, limit=limit)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))

class PreguntaRequest(BaseModel):
    pregunta: str
@app.get("/consulta", operation_id="consultaCiudadanaEducativa")


class MunicipioRequest(BaseModel):
    departamento: str
    municipio: str

import re
import unicodedata


def normalizar_texto(texto: str) -> str:
    texto = texto.lower().strip()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto


def detectar_municipio_departamento(pregunta: str):
    texto = normalizar_texto(pregunta)

    departamento = "META"
    municipio = None

    alias_municipios_meta = {
        "VILLAVICENCIO": ["villavicencio", "villa vicencio", "villavo", "ciudad de villavicencio"],
        "ACACIAS": ["acacias", "acacías"],
        "GRANADA": ["granada"],
        "PUERTO LOPEZ": ["puerto lopez", "puerto lópez"],
        "PUERTO GAITAN": ["puerto gaitan", "puerto gaitán"],
        "SAN MARTIN": ["san martin", "san martín"],
        "CUMARAL": ["cumaral"],
        "RESTREPO": ["restrepo"],
        "CASTILLA LA NUEVA": ["castilla la nueva"],
        "GUAMAL": ["guamal"],
        "MESETAS": ["mesetas"],
        "LA MACARENA": ["la macarena"],
        "URIBE": ["uribe"],
        "LEJANIAS": ["lejanias", "lejanías"],
        "EL CASTILLO": ["el castillo"],
        "EL DORADO": ["el dorado"],
        "FUENTE DE ORO": ["fuente de oro"],
        "PUERTO CONCORDIA": ["puerto concordia"],
        "PUERTO LLERAS": ["puerto lleras"],
        "PUERTO RICO": ["puerto rico"],
        "SAN JUAN DE ARAMA": ["san juan de arama"],
        "SAN CARLOS DE GUAROA": ["san carlos de guaroa"],
        "BARRANCA DE UPIA": ["barranca de upia", "barranca de upía"],
        "CABUYARO": ["cabuyaro"],
        "MAPIRIPAN": ["mapiripan", "mapiripán"],
        "VISTAHERMOSA": ["vistahermosa", "vista hermosa"]
    }

    for nombre_municipio, alias in alias_municipios_meta.items():
        for forma in alias:
            if normalizar_texto(forma) in texto:
                municipio = nombre_municipio
                break
        if municipio:
            break

    if "meta" in texto:
        departamento = "META"

    return departamento, municipio

def construir_respuesta_no_encontrada(pregunta: str):
    return {
        "pregunta": pregunta,
        "respuesta": (
            "Entendí la pregunta, pero todavía no tengo conectada una consulta específica "
            "para responderla con datos reales. Esta solicitud debe ser atendida por el "
            "orquestador ciudadano del backend."
        ),
        "datos": {},
        "fuentes": [],
        "advertencias": [
            "La conexión entre la app y el backend funciona.",
            "Falta conectar esta intención con una consulta real a los datos abiertos."
        ]
    }
def normalizar_texto(texto: str) -> str:
    texto = str(texto).lower().strip()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto


def obtener_columnas_dataset(resource_id: str):
    """
    Consulta los metadatos del dataset en Socrata/datos.gov.co
    y devuelve las columnas disponibles.
    """
    url = f"https://www.datos.gov.co/api/views/{resource_id}"
    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudieron obtener los metadatos del dataset {resource_id}"
        )

    metadata = response.json()
    columnas = []

    for col in metadata.get("columns", []):
        field_name = col.get("fieldName")
        name = col.get("name")

        if field_name:
            columnas.append({
                "field_name": field_name,
                "name": name
            })

    return columnas


def elegir_columna(columnas, posibles_nombres):
    """
    Busca una columna del dataset comparando nombres técnicos y nombres visibles.
    Esto hace que el código sea más resistente si datos.gov.co usa nombres como:
    municipio, nombre_municipio, c_digo_municipio, etc.
    """
    posibles_normalizados = [normalizar_texto(x) for x in posibles_nombres]

    for col in columnas:
        field_name = col.get("field_name", "")
        name = col.get("name", "")

        field_norm = normalizar_texto(field_name)
        name_norm = normalizar_texto(name)

        for posible in posibles_normalizados:
            if posible == field_norm or posible == name_norm:
                return field_name

    for col in columnas:
        field_name = col.get("field_name", "")
        name = col.get("name", "")

        field_norm = normalizar_texto(field_name)
        name_norm = normalizar_texto(name)

        for posible in posibles_normalizados:
            if posible in field_norm or posible in name_norm:
                return field_name

    return None


def consultar_datos_socrata(resource_id: str, params: dict):
    """
    Consulta un recurso JSON de datos.gov.co.
    """
    url = f"{DATOS_GOV_BASE}/{resource_id}.json"
    response = requests.get(url, params=params, timeout=30)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={
                "mensaje": "Error consultando datos.gov.co",
                "dataset": resource_id,
                "status_code": response.status_code,
                "respuesta": response.text[:500]
            }
        )

    return response.json()
def consultar_colegios_municipio(departamento: str, municipio: str):
    resource_id = DATASETS.get("establecimientos", "cfw5-qzt5")

    columnas = obtener_columnas_dataset(resource_id)

    col_departamento = elegir_columna(columnas, [
        "departamento",
        "nombre departamento",
        "nombre_departamento",
        "departamento_nombre"
    ])

    col_municipio = elegir_columna(columnas, [
        "municipio",
        "nombre municipio",
        "nombre_municipio",
        "municipio_nombre"
    ])

    col_establecimiento_codigo = elegir_columna(columnas, [
        "codigo dane establecimiento",
        "código dane establecimiento",
        "codigo_dane_establecimiento",
        "codigo dane del establecimiento",
        "código dane del establecimiento",
        "cod_dane_establecimiento",
        "codigo_dane"
    ])

    col_establecimiento_nombre = elegir_columna(columnas, [
        "nombre establecimiento",
        "nombre del establecimiento",
        "establecimiento",
        "institucion educativa",
        "institución educativa",
        "nombre_establecimiento"
    ])

    col_sede_codigo = elegir_columna(columnas, [
        "codigo dane sede",
        "código dane sede",
        "codigo_dane_sede",
        "codigo dane de la sede",
        "código dane de la sede",
        "cod_dane_sede"
    ])

    col_sector = elegir_columna(columnas, [
        "sector",
        "sector educativo"
    ])

    col_zona = elegir_columna(columnas, [
        "zona",
        "zona educativa",
        "area",
        "área"
    ])

    if not col_departamento or not col_municipio:
        return {
            "respuesta": (
                "No pude identificar las columnas de departamento y municipio en el dataset "
                "de establecimientos educativos. Es necesario revisar los metadatos del conjunto."
            ),
            "datos": {
                "columnas_detectadas": columnas[:20]
            },
            "advertencias": [
                "El backend sí consultó datos.gov.co, pero no encontró columnas territoriales esperadas."
            ]
        }

    params = {
        "$limit": 50000,
        "$where": (
            f"upper({col_departamento}) = '{departamento.upper()}' "
            f"AND upper({col_municipio}) = '{municipio.upper()}'"
        )
    }

    registros = consultar_datos_socrata(resource_id, params)

    if not registros:
        return {
            "respuesta": (
                f"No encontré registros de establecimientos educativos para "
                f"{municipio.title()}, {departamento.title()} en el conjunto consultado."
            ),
            "datos": {
                "departamento": departamento,
                "municipio": municipio,
                "total_registros": 0
            },
            "advertencias": [
                "Puede deberse a diferencias en la escritura del municipio o a filtros del dataset."
            ]
        }

    df = pd.DataFrame(registros)

    total_registros = len(df)

    if col_establecimiento_codigo and col_establecimiento_codigo in df.columns:
        total_establecimientos = df[col_establecimiento_codigo].nunique()
        criterio_conteo = f"establecimientos únicos por {col_establecimiento_codigo}"
    elif col_establecimiento_nombre and col_establecimiento_nombre in df.columns:
        total_establecimientos = df[col_establecimiento_nombre].nunique()
        criterio_conteo = f"establecimientos únicos por {col_establecimiento_nombre}"
    else:
        total_establecimientos = total_registros
        criterio_conteo = "registros disponibles, sin columna única de establecimiento"

    if col_sede_codigo and col_sede_codigo in df.columns:
        total_sedes = df[col_sede_codigo].nunique()
    else:
        total_sedes = total_registros

    distribucion_sector = {}
    if col_sector and col_sector in df.columns:
        distribucion_sector = (
            df[col_sector]
            .fillna("SIN DATO")
            .value_counts()
            .to_dict()
        )

    distribucion_zona = {}
    if col_zona and col_zona in df.columns:
        distribucion_zona = (
            df[col_zona]
            .fillna("SIN DATO")
            .value_counts()
            .to_dict()
        )

    ejemplos = []
    if col_establecimiento_nombre and col_establecimiento_nombre in df.columns:
        ejemplos = (
            df[col_establecimiento_nombre]
            .dropna()
            .drop_duplicates()
            .head(10)
            .tolist()
        )

    respuesta = (
        f"En {municipio.title()}, {departamento.title()}, encontré "
        f"{total_establecimientos} establecimientos educativos registrados en el conjunto "
        f"de datos abiertos del MEN. Además, se identificaron aproximadamente "
        f"{total_sedes} sedes o registros asociados, según las columnas disponibles del dataset. "
        f"El conteo se realizó usando el criterio: {criterio_conteo}."
    )

    return {
        "respuesta": respuesta,
        "datos": {
            "departamento": departamento,
            "municipio": municipio,
            "total_establecimientos": int(total_establecimientos),
            "total_sedes_o_registros": int(total_sedes),
            "total_registros_descargados": int(total_registros),
            "criterio_conteo": criterio_conteo,
            "distribucion_sector": distribucion_sector,
            "distribucion_zona": distribucion_zona,
            "ejemplos_establecimientos": ejemplos
        },
        "fuentes": [
            "https://www.datos.gov.co/resource/cfw5-qzt5.json",
            "MEN - Establecimientos educativos preescolar, básica y media"
        ],
        "advertencias": [
            "El resultado depende de los registros disponibles en datos.gov.co.",
            "Si el conjunto contiene historia de varios años, puede ser necesario filtrar por vigencia para evitar duplicados históricos."
        ]
    }
def consultar_diagnostico_municipal(departamento: str, municipio: str):
    resource_id = DATASETS.get("estadisticas_municipales", "nudc-7mev")

    columnas = obtener_columnas_dataset(resource_id)

    col_departamento = elegir_columna(columnas, [
        "departamento",
        "nombre departamento",
        "nombre_departamento",
        "departamento_nombre"
    ])

    col_municipio = elegir_columna(columnas, [
        "municipio",
        "nombre municipio",
        "nombre_municipio",
        "municipio_nombre"
    ])

    col_anio = elegir_columna(columnas, [
        "año",
        "ano",
        "anio",
        "vigencia",
        "periodo",
        "periodo_anual"
    ])

    col_matricula = elegir_columna(columnas, [
        "matricula",
        "matrícula",
        "matricula total",
        "matrícula total",
        "total matricula",
        "total matrícula"
    ])

    col_aprobados = elegir_columna(columnas, [
        "aprobados",
        "total aprobados",
        "aprobacion",
        "aprobación"
    ])

    col_reprobados = elegir_columna(columnas, [
        "reprobados",
        "total reprobados",
        "reprobacion",
        "reprobación"
    ])

    col_desertores = elegir_columna(columnas, [
        "desertores",
        "desercion",
        "deserción",
        "total desertores"
    ])

    col_tasa_desercion = elegir_columna(columnas, [
        "tasa desercion",
        "tasa deserción",
        "porcentaje desercion",
        "porcentaje deserción"
    ])

    if not col_departamento or not col_municipio:
        return {
            "respuesta": (
                "No pude identificar las columnas de departamento y municipio en el dataset "
                "de estadísticas municipales. Es necesario revisar los metadatos del conjunto."
            ),
            "datos": {
                "columnas_detectadas": columnas[:30]
            },
            "fuentes": [
                "https://www.datos.gov.co/resource/nudc-7mev.json"
            ],
            "advertencias": [
                "El backend consultó datos.gov.co, pero no encontró columnas territoriales esperadas."
            ]
        }

    params = {
        "$limit": 50000,
        "$where": f"upper({col_departamento}) = '{departamento.upper()}'"
    }

    try:
        registros = consultar_datos_socrata(resource_id, params)
    except Exception:
        registros = consultar_datos_socrata(resource_id, {"$limit": 50000})

    if not registros:
        return {
            "respuesta": (
                f"No encontré registros estadísticos para {departamento.title()} "
                "en el conjunto consultado."
            ),
            "datos": {
                "departamento": departamento,
                "municipio": municipio,
                "total_registros": 0
            },
            "fuentes": [
                "https://www.datos.gov.co/resource/nudc-7mev.json"
            ],
            "advertencias": [
                "Puede deberse a cambios en la estructura del dataset o en los nombres territoriales."
            ]
        }

    df = pd.DataFrame(registros)

    df["_departamento_norm"] = df[col_departamento].apply(normalizar_texto)
    df["_municipio_norm"] = df[col_municipio].apply(normalizar_texto)

    departamento_norm = normalizar_texto(departamento)
    municipio_norm = normalizar_texto(municipio)

    df = df[
        (df["_departamento_norm"] == departamento_norm) &
        (df["_municipio_norm"] == municipio_norm)
    ].copy()

    if df.empty:
        return {
            "respuesta": (
                f"No encontré registros estadísticos para {municipio.title()}, "
                f"{departamento.title()} en el conjunto consultado."
            ),
            "datos": {
                "departamento": departamento,
                "municipio": municipio,
                "total_registros": 0
            },
            "fuentes": [
                "https://www.datos.gov.co/resource/nudc-7mev.json"
            ],
            "advertencias": [
                "Puede haber diferencias en la escritura del municipio dentro del dataset."
            ]
        }

    ultimo_anio = None
    df_base = df.copy()

    if col_anio and col_anio in df.columns:
        df["_anio_num"] = df[col_anio].apply(limpiar_numero)
        if df["_anio_num"].notna().any():
            ultimo_anio = int(df["_anio_num"].max())
            df_base = df[df["_anio_num"] == ultimo_anio].copy()

    def sumar_columna(columna):
        serie = serie_numerica(df_base, columna)
        if serie is None or serie.dropna().empty:
            return None
        return float(serie.sum())

    def promedio_columna(columna):
        serie = serie_numerica(df_base, columna)
        if serie is None or serie.dropna().empty:
            return None
        return float(serie.mean())

    matricula = sumar_columna(col_matricula)
    aprobados = sumar_columna(col_aprobados)
    reprobados = sumar_columna(col_reprobados)
    desertores = sumar_columna(col_desertores)
    tasa_desercion = promedio_columna(col_tasa_desercion)

    tasa_aprobacion_calculada = None
    tasa_reprobacion_calculada = None
    tasa_desercion_calculada = None

    if matricula and matricula > 0:
        if aprobados is not None:
            tasa_aprobacion_calculada = round((aprobados / matricula) * 100, 2)
        if reprobados is not None:
            tasa_reprobacion_calculada = round((reprobados / matricula) * 100, 2)
        if desertores is not None:
            tasa_desercion_calculada = round((desertores / matricula) * 100, 2)

    datos = {
        "departamento": departamento,
        "municipio": municipio,
        "anio_usado": ultimo_anio,
        "registros_analizados": int(len(df_base)),
        "columnas_detectadas": {
            "departamento": col_departamento,
            "municipio": col_municipio,
            "anio": col_anio,
            "matricula": col_matricula,
            "aprobados": col_aprobados,
            "reprobados": col_reprobados,
            "desertores": col_desertores,
            "tasa_desercion": col_tasa_desercion
        },
        "indicadores": {
            "matricula": int(matricula) if matricula is not None else None,
            "aprobados": int(aprobados) if aprobados is not None else None,
            "reprobados": int(reprobados) if reprobados is not None else None,
            "desertores": int(desertores) if desertores is not None else None,
            "tasa_desercion_promedio_dataset": round(tasa_desercion, 2) if tasa_desercion is not None else None,
            "tasa_aprobacion_calculada": tasa_aprobacion_calculada,
            "tasa_reprobacion_calculada": tasa_reprobacion_calculada,
            "tasa_desercion_calculada": tasa_desercion_calculada
        }
    }

    partes = []

    partes.append(
        f"Para {municipio.title()}, {departamento.title()}, encontré información estadística "
        f"en el conjunto de datos municipales de educación preescolar, básica y media."
    )

    if ultimo_anio:
        partes.append(
            f"El análisis usa el año más reciente disponible detectado en el dataset: {ultimo_anio}."
        )

    if matricula is not None:
        partes.append(f"La matrícula registrada es de aproximadamente {int(matricula):,} estudiantes.")

    if aprobados is not None:
        partes.append(f"El número de estudiantes aprobados es de aproximadamente {int(aprobados):,}.")

    if reprobados is not None:
        partes.append(f"El número de estudiantes reprobados es de aproximadamente {int(reprobados):,}.")

    if desertores is not None:
        partes.append(f"El número de estudiantes desertores es de aproximadamente {int(desertores):,}.")

    lectura = []

    if tasa_aprobacion_calculada is not None:
        lectura.append(f"aprobación cercana al {tasa_aprobacion_calculada}%")

    if tasa_reprobacion_calculada is not None:
        lectura.append(f"reprobación cercana al {tasa_reprobacion_calculada}%")

    if tasa_desercion_calculada is not None:
        lectura.append(f"deserción cercana al {tasa_desercion_calculada}%")

    if lectura:
        partes.append(
            "Como lectura ciudadana, el municipio presenta una " + ", ".join(lectura) + "."
        )

    partes.append(
        "Esta lectura es descriptiva: permite observar el comportamiento educativo del municipio, "
        "pero no prueba por sí sola las causas de los resultados."
    )

    respuesta = " ".join(partes)

    return {
        "respuesta": respuesta,
        "datos": datos,
        "fuentes": [
            "https://www.datos.gov.co/resource/nudc-7mev.json",
            "MEN - Estadísticas municipales de educación preescolar, básica y media"
        ],
        "advertencias": [
            "El diagnóstico depende de las columnas disponibles en el dataset.",
            "La interpretación es descriptiva y no causal.",
            "Si algún indicador aparece como null, significa que no se detectó una columna equivalente en el conjunto consultado."
        ]
    }
    
@app.post("/chat")
def chat_ciudadano(request: PreguntaRequest):
    pregunta = request.pregunta.strip()
    texto = normalizar_texto(pregunta)

    departamento, municipio = detectar_municipio_departamento(pregunta)

    if not pregunta:
        return {
            "pregunta": pregunta,
            "respuesta": "Por favor escribe una pregunta sobre educación en Colombia.",
            "datos": {},
            "fuentes": [],
            "advertencias": []
        }

    if texto in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"]:
        return {
            "pregunta": pregunta,
            "respuesta": (
                "Hola, soy EducaDatos, un asistente ciudadano para consultar datos abiertos "
                "del sector educativo colombiano. Puedes preguntarme por colegios, matrícula, "
                "deserción, bachilleres, educación superior, ICETEX o clústeres educativos municipales."
            ),
            "datos": {},
            "fuentes": [],
            "advertencias": []
        }

    if "colegio" in texto or "colegios" in texto or "institucion educativa" in texto or "establecimiento" in texto:
        if not municipio:
            return {
                "pregunta": pregunta,
                "respuesta": (
                "Puedo ayudarte a consultar colegios, pero necesito que indiques el municipio. "
                "Por ejemplo: ¿Cuántos colegios hay en Villavicencio?"
            ),
            "datos": {
                "intencion": "establecimientos_educativos",
                "departamento_detectado": departamento,
                "municipio_detectado": municipio
            },
            "fuentes": [],
            "advertencias": [
                "No se detectó municipio en la pregunta."
            ]
        }
        resultado = consultar_colegios_municipio(departamento, municipio)

        return {
            "pregunta": pregunta,
            "respuesta": resultado.get("respuesta"),
            "datos": resultado.get("datos", {}),
            "fuentes": resultado.get("fuentes", []),
            "advertencias": resultado.get("advertencias", [])
    }

    if "diagnostico" in texto:
        if not municipio:
            return {
                "pregunta": pregunta,
                "respuesta": (
                "Puedo hacer un diagnóstico educativo municipal, pero necesito que indiques el municipio. "
                "Por ejemplo: Haz un diagnóstico educativo de Villavicencio."
            ),
            "datos": {
                "intencion": "diagnostico_municipal",
                "departamento_detectado": departamento,
                "municipio_detectado": municipio
            },
            "fuentes": [],
            "advertencias": [
                "No se detectó municipio en la pregunta."
            ]
        }

        resultado = consultar_diagnostico_municipal(departamento, municipio)

        return {
        "pregunta": pregunta,
        "respuesta": resultado.get("respuesta"),
        "datos": resultado.get("datos", {}),
        "fuentes": resultado.get("fuentes", []),
        "advertencias": resultado.get("advertencias", [])
    }

    if "cluster" in texto or "clúster" in texto or "similares" in texto or "parecidos" in texto:
        return {
            "pregunta": pregunta,
            "respuesta": (
                f"Identifiqué una solicitud de análisis por clúster"
                f"{' para ' + municipio.title() if municipio else ''}. "
                "Esta pregunta debe responderse con el modelo de clustering educativo municipal "
                "del backend."
            ),
            "datos": {
                "intencion": "cluster_municipal",
                "departamento_detectado": departamento,
                "municipio_detectado": municipio
            },
            "cluster": {},
            "fuentes": [
                "Modelo de clustering educativo municipal del backend EducaDatos"
            ],
            "advertencias": [
                "Falta conectar esta intención con la función real del modelo de clustering."
            ]
        }

    if "bachiller" in texto or "bachilleres" in texto or "icetex" in texto or "educacion superior" in texto:
        return {
            "pregunta": pregunta,
            "respuesta": (
                "Identifiqué una pregunta de relación entre bachilleres, educación superior e ICETEX. "
                "Esta consulta debe cruzar información de egresados de educación media, oferta de "
                "educación superior y apoyos financieros."
            ),
            "datos": {
                "intencion": "relacion_bachilleres_superior_icetex",
                "departamento_detectado": departamento,
                "municipio_detectado": municipio
            },
            "fuentes": [
                "Datos abiertos de bachilleres",
                "Datos abiertos de educación superior",
                "Datos abiertos relacionados con ICETEX"
            ],
            "advertencias": [
                "La respuesta debe ser descriptiva y no causal, salvo que se implemente un análisis estadístico específico."
            ]
        }

    return construir_respuesta_no_encontrada(pregunta)
    
@app.get("/datasets/{dataset_key}/buscar", operation_id="buscarEnDatasetEducativo")
def buscar_en_dataset_educativo(
    dataset_key: str,
    texto: str | None = Query(None, description="Texto libre para buscar. Ejemplo: Villavicencio, Normal Superior, ingeniería."),
    departamento: str | None = Query(None, description="Departamento. Ejemplo: Meta."),
    municipio: str | None = Query(None, description="Municipio. Ejemplo: Villavicencio."),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a consultar.")
):
    try:
        return buscar_en_dataset(
            dataset_key=dataset_key,
            texto=texto,
            departamento=departamento,
            municipio=municipio,
            limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))

from pydantic import BaseModel

class PreguntaRequest(BaseModel):
    pregunta: str
@app.get("/consulta", operation_id="consultaCiudadanaEducativa")
def consulta_ciudadana_educativa(
    pregunta: str = Query(
        ...,
        min_length=3,
        description="Pregunta natural del ciudadano. Ejemplo: ¿Qué colegios hay en Villavicencio?"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Número máximo de registros a consultar."
    )
):
    try:
        return resolver_consulta_ciudadana(
            pregunta=pregunta,
            limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))
@app.get("/cruce/transito-educativo", operation_id="analizarTransitoEducativo")
def analizar_transito_educativo(
    departamento: str | None = Query(None, description="Departamento a analizar. Ejemplo: Meta."),
    municipio: str | None = Query(None, description="Municipio a analizar. Ejemplo: Villavicencio."),
    limit: int = Query(1000, ge=10, le=5000, description="Cantidad máxima de registros por dataset.")
):
    try:
        return analizar_transito_educativo_service(
            departamento=departamento,
            municipio=municipio,
            limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))    
@app.get("/diagnostico/territorial", operation_id="generarDiagnosticoTerritorialEducativo")
def generar_diagnostico_territorial_educativo(
    departamento: str | None = Query(None, description="Departamento a analizar. Ejemplo: Meta."),
    municipio: str | None = Query(None, description="Municipio a analizar. Ejemplo: Villavicencio."),
    limit: int = Query(1000, ge=100, le=5000, description="Cantidad máxima de registros por consulta.")
):
    try:
        return diagnostico_territorial_educativo_service(
            departamento=departamento,
            municipio=municipio,
            limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))

@app.get("/metadata", operation_id="obtenerMetadataClustering")
def obtener_metadata_clustering(
    limit: int = Query(100000, ge=100, le=1000000)
):
    try:
        return obtener_metadata_clustering_service(limit=limit)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.get("/cluster/municipios", operation_id="consultarClustersMunicipios")
def consultar_clusters_municipios(
    departamento: str | None = Query(None, description="Departamento a filtrar. Ejemplo: Meta."),
    anio: int | None = Query(None, description="Año o vigencia. Si no se envía, se usa la más reciente detectada."),
    n_clusters: int | None = Query(None, ge=2, le=8, description="Número de clústeres."),
    max_resultados: int = Query(100, ge=1, le=500),
    limit: int = Query(100000, ge=100, le=1000000)
):
    try:
        return consultar_clusters_municipios_service(
            departamento=departamento,
            anio=anio,
            n_clusters=n_clusters,
            max_resultados=max_resultados,
            limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.get("/cluster/municipio", operation_id="consultarClusterMunicipio")
def consultar_cluster_municipio(
    departamento: str = Query(..., description="Departamento del municipio. Ejemplo: Meta."),
    municipio: str = Query(..., description="Municipio a consultar. Ejemplo: Villavicencio."),
    anio: int | None = Query(None, description="Año o vigencia."),
    n_clusters: int | None = Query(None, ge=2, le=8),
    limit: int = Query(100000, ge=100, le=1000000)
):
    try:
        return consultar_cluster_municipio_service(
            departamento=departamento,
            municipio=municipio,
            anio=anio,
            n_clusters=n_clusters,
            limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.get("/similar/municipios", operation_id="buscarMunicipiosSimilares")
def buscar_municipios_similares(
    departamento: str = Query(..., description="Departamento del municipio base. Ejemplo: Meta."),
    municipio: str = Query(..., description="Municipio base. Ejemplo: Villavicencio."),
    top_n: int = Query(5, ge=1, le=20),
    anio: int | None = Query(None),
    n_clusters: int | None = Query(None, ge=2, le=8),
    solo_mismo_departamento: bool = Query(False),
    limit: int = Query(100000, ge=100, le=1000000)
):
    try:
        return buscar_municipios_similares_service(
            departamento=departamento,
            municipio=municipio,
            top_n=top_n,
            anio=anio,
            n_clusters=n_clusters,
            solo_mismo_departamento=solo_mismo_departamento,
            limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.get("/recomendaciones", operation_id="generarRecomendacionesMunicipio")
def generar_recomendaciones_municipio(
    departamento: str = Query(..., description="Departamento del municipio. Ejemplo: Meta."),
    municipio: str = Query(..., description="Municipio a consultar. Ejemplo: Villavicencio."),
    anio: int | None = Query(None),
    n_clusters: int | None = Query(None, ge=2, le=8),
    limit: int = Query(100000, ge=100, le=1000000)
):
    try:
        return generar_recomendaciones_municipio_service(
            departamento=departamento,
            municipio=municipio,
            anio=anio,
            n_clusters=n_clusters,
            limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))

@app.get("/colegios")
def colegios_por_municipio(
    departamento: str = Query("META", description="Departamento"),
    municipio: str = Query("VILLAVICENCIO", description="Municipio")
):
    resultado = consultar_colegios_municipio(departamento, municipio)

    return {
        "departamento": departamento,
        "municipio": municipio,
        "respuesta": resultado.get("respuesta"),
        "datos": resultado.get("datos", {}),
        "fuentes": resultado.get("fuentes", []),
        "advertencias": resultado.get("advertencias", [])
    }
    
@app.get("/openapi-gpt.json", include_in_schema=False)
def generar_openapi_para_gpt():
    """
    Genera una versión limpia del OpenAPI para cargar en un GPT personalizado.
    Solo expone las acciones más útiles para el asistente ciudadano.
    """

    acciones_permitidas = {
        "verificarEstadoApi",
        "consultaCiudadanaEducativa",
        "generarDiagnosticoTerritorialEducativo",
        "analizarTransitoEducativo",
        "consultarClusterMunicipio",
        "buscarMunicipiosSimilares",
        "generarRecomendacionesMunicipio",
        "listarDatasetsEducativos",
        "buscarEnDatasetEducativo",
        "explorarColumnasDatasetEducativo",
    }

    esquema_original = app.openapi()

    paths_filtrados = {}

    for ruta, metodos in esquema_original.get("paths", {}).items():
        metodos_filtrados = {}

        for metodo_http, definicion in metodos.items():
            operation_id = definicion.get("operationId")

            if operation_id in acciones_permitidas:
                metodos_filtrados[metodo_http] = definicion

        if metodos_filtrados:
            paths_filtrados[ruta] = metodos_filtrados

    esquema_gpt = {
        **esquema_original,
        "info": {
            "title": "EducaDatos - Acciones para GPT Ciudadano",
            "description": (
                "API ciudadana para consultar datos abiertos educativos de Colombia, "
                "realizar diagnóstico territorial, analizar tránsito educativo y aplicar clustering municipal."
            ),
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": PUBLIC_BASE_URL,
                "description": "Servidor público de EducaDatos"
            }
        ],
        "paths": paths_filtrados
    }

    return esquema_gpt
