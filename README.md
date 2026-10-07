# Proyecto 5 — LangGraph: Asistente de Seguros de Automóvil

## Descripción

Este proyecto desarrolla un asistente conversacional especializado en **seguros de automóvil** utilizando **LangGraph** y **LangChain**.

El objetivo es comprender cómo construir un agente mediante un grafo de estados, y para ello se incorpora:

* Estados y mensajes.
* Nodos de procesamiento.
* Conexiones y decisiones condicionales.
* Uso de herramientas.
* Validación de consultas.
* Control del número de llamadas a herramientas.
* Memoria persistente mediante SQLite.
* Conversaciones independientes mediante `thread_id`.

El proyecto utiliza datos ficticios de siniestros de automóvil y no realiza operaciones reales.

---

## Arquitectura

El flujo principal del agente es:

```text
                    ┌──────────────┐
                    │    START     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Validar    │
                    │   consulta   │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        Consulta válida           Consulta no válida
              │                         │
              ▼                         ▼
       ┌──────────────┐          ┌──────────────┐
       │   Chatbot    │          │  Reiniciar   │
       └──────┬───────┘          └──────┬───────┘
              │                         │
       ¿Necesita tool?                  ▼
         │        │                    END
        Sí       No
         │        │
         ▼        ▼
   ┌──────────┐ ┌──────────────┐
   │  Tools   │ │  Finalizar   │
   └────┬─────┘ └──────┬───────┘
        │               │
        └───────► Chatbot
                        │
                        ▼
                       END
```

El agente puede utilizar la herramienta de consulta de siniestros cuando la pregunta lo requiere. El flujo limita las llamadas a herramientas a un máximo de 2 por turno.

---

## Estructura del proyecto

```text
proyecto-5-langgraph-seguros/
│
├── .gitignore
├── README.md
│
├── 01_grafo/
│   └── grafo.py
│
├── 02_chatbot/
│   └── chatbot.py
│
└── 03_herramientas/
    ├── herramientas.py
    ├── agente_tools.py
    └── memoria.db
```

> `memoria.db` se genera automáticamente durante la ejecución y está excluidpero está excluidao del repositorio mediante `.gitignore`.

---

# 1. Grafo básico

Archivo:

```text
01_grafo/grafo.py
```

Esta primera parte muestra la estructura básica de un grafo utilizando LangGraph.

Se define un estado y un nodo que procesa la información recibida.

Conceptos principales:

* `StateGraph`
* `START`
* `END`
* Estado
* Nodo
* Compilación del grafo

El flujo básico es:

```text
START → nodo → END
```

---

# 2. Chatbot con LangGraph

Archivo:

```text
02_chatbot/chatbot.py
```

En esta segunda parte se construye un chatbot especializado en seguros de automóvil.

El usuario introduce una consulta y el estado del grafo contiene:

```text
mensaje
respuesta
```

El flujo es:

```text
START → chatbot → END
```

El modelo utilizado es accesible mediante OpenRouter.

---

# 3. Agente con herramientas y memoria

Archivos:

```text
03_herramientas/herramientas.py
03_herramientas/agente_tools.py
```

Se construye un agente capaz de decidir cuándo necesita utilizar una herramienta para consultar información sobre un siniestro.


### Herramienta

La herramienta:

```text
consultar_siniestro()
```

permite consultar el estado de siniestros ficticios.

Ejemplos disponibles:

| Siniestro | Estado         | Descripción             |
| --------- | -------------- | ----------------------- |
| SIN-1001  | Abierto        | Pendiente de peritación |
| SIN-1002  | En tramitación | Documentación recibida  |
| SIN-1003  | Cerrado        | Indemnización pagada    |

También se contempla el caso de un número de siniestro inexistente , por ejemplo SIN-9990.

---

## Validación de consultas

Antes de ejecutar el agente se comprueba si la consulta está relacionada con el ámbito de los seguros de automóvil.

Por ejemplo:

```text
¿Cuál es el estado del siniestro SIN-1001?
```

es una consulta válida.

En cambio:

```text
¿Cuál es la capital de Francia?
```

se considera fuera del ámbito del asistente.

En ese caso el flujo se dirige al nodo de reinicio y no se utilizan herramientas.

---

## Control de herramientas

El agente controla el número de llamadas realizadas a las herramientas.

Se establece un máximo de:

```text
2 llamadas por turno
```

Esto evita que el agente pueda entrar en un ciclo indefinido de llamadas.

El estado mantiene este contador mediante:

```python
llamadas_herramienta
```

---

## Memoria con SQLite

El agente utiliza `SqliteSaver` para mantener el estado de las conversaciones.

La memoria se almacena localmente en:

```text
memoria.db
```

Cada conversación utiliza un identificador:

```text
thread_id
```

Esto permite cerrar el programa y continuar posteriormente una conversación utilizando el mismo identificador.

Por ejemplo:

```text
cliente_019
```

---

## Estado del agente

El estado principal utilizado por el agente contiene:

```text
messages
llamadas_herramienta
consulta_valida
```

### `messages`

Contiene el historial de mensajes de la conversación.

### `llamadas_herramienta`

Controla cuántas veces se han utilizado las herramientas durante el turno.

### `consulta_valida`

Indica si la consulta pertenece al ámbito de los seguros de automóvil.

---

## Flujo del agente

El flujo completo puede resumirse como:

```text
START
  │
  ▼
Validar consulta
  │
  ├── No válida ──► Reiniciar ──► END
  │
  └── Válida
         │
         ▼
      Chatbot
         │
         ├── No necesita herramienta ──► Finalizar ──► END
         │
         └── Necesita herramienta
                    │
                    ▼
                  Tools
                    │
                    ▼
                 Chatbot
                    │
                    ▼
                 Finalizar
                    │
                    ▼
                   END
```

## Ejemplos de rutas del grafo

El agente puede seguir diferentes rutas dependiendo de la consulta del usuario.

**Ruta 1** — Consulta válida sin herramienta

Cuando la consulta está relacionada con seguros, pero no necesita consultar un siniestro concreto:

Flujo:

START → Validar → Chatbot → Finalizar → END

Ejemplo:

Tú: ¿Qué documentación necesito para dar un parte?

Llamadas a herramientas: 0

**Ruta 2** — Consulta válida con herramienta

Cuando el usuario pregunta por un siniestro concreto, el agente utiliza la herramienta correspondiente:

Flujo:

START → Validar → Chatbot → Tools → Chatbot → Finalizar → END

Ejemplo:

Tú: ¿Cuál es el estado del siniestro SIN-1001?

Llamadas a herramientas: 1

La herramienta devuelve la información del siniestro y el agente continúa el flujo hasta la finalización.

**Ruta 3** — Consulta no válida

Cuando la consulta no está relacionada con seguros de automóvil, el agente no utiliza herramientas y termina mediante el nodo de reinicio:

Flujo:

START → Validar → Reiniciar → END

Ejemplo:

Tú: ¿Cuál es la capital de Francia?

El sistema identifica que la consulta está fuera del ámbito del asistente y solicita una nueva consulta relacionada con seguros de automóvil.

**Control de terminación**

Para evitar bucles de llamadas a herramientas, el agente establece un máximo de 2 llamadas por turno.

Si se alcanza este límite, el flujo pasa al nodo finalizar:

Flujo:

Chatbot → Tools → Chatbot → Tools → Finalizar → END

---


# Instalación

Entorno virtual de Python.

Crear el entorno:

```bash
python -m venv .venv
```

Activarlo en PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Instalar las dependencias:

```bash
pip install langgraph langchain langchain-openai python-dotenv langgraph-checkpoint-sqlite
```

---

# Configuración

El proyecto utiliza una variable de entorno para la API.

Crear un archivo:

```text
.env
```

con:

```text
OPENROUTER_API_KEY=tu_clave_de_openrouter
```

La clave no debe incluirse en GitHub.

Por este motivo `.env` está incluido en `.gitignore`.

---

# Ejecución

## Grafo básico

Desde la raíz del proyecto:

```bash
python 01_grafo/grafo.py
```

## Chatbot

```bash
python 02_chatbot/chatbot.py
```

## Agente con herramientas y memoria

```bash
python 03_herramientas/agente_tools.py
```

Al iniciar el agente se solicita un identificador para la conversación:

```text
Introduce el identificador de la conversación:
```

Después se pueden realizar diferentes consultas.

Para finalizar:

```text
salir
```

---

# Ejemplos de funcionamiento

### Consulta de un siniestro

```text
Tú: ¿Cuál es el estado del siniestro SIN-1001?
```

Respuesta:

```text
El siniestro SIN-1001 está abierto y pendiente de peritación.
```

La herramienta se utiliza:

```text
Llamadas a herramientas: 1
```

### Consulta sin necesidad de herramienta

```text
Tú: ¿Qué documentación necesito para dar un parte?
```

El modelo responde directamente sin consultar un siniestro concreto.

```text
Llamadas a herramientas: 0
```

### Consulta fuera del ámbito

```text
Tú: ¿Cuál es la capital de Francia?
```

El sistema detecta que la consulta no está relacionada con seguros de automóvil y evita ejecutar herramientas.

### Siniestro inexistente

```text
Tú: ¿Cuál es el estado del siniestro SIN-9999?
```

El sistema consulta la herramienta y devuelve que no existe ningún siniestro con ese número.

---

# Tecnologías utilizadas

* **Python**
* **LangGraph**
* **LangChain**
* **LangChain OpenAI**
* **OpenRouter**
* **SQLite**
* **python-dotenv**

---
