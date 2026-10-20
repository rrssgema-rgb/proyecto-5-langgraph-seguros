
import os

from typing import Annotated
from typing_extensions import TypedDict

from dotenv import load_dotenv

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from enmascaramiento import mask_otel_spans

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage
)

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from herramientas import consultar_siniestro


# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

load_dotenv()

NOMBRE_PROMPT = "asistente-seguros-auto"
VERSION_PROMPT = int(os.getenv("PROMPT_VERSION", "1"))

NOMBRE_MODELO = "openai/gpt-6-luna"


# --------------------------------------------------
# LANGFUSE Y ENMASCARAMIENTO
# --------------------------------------------------

langfuse = Langfuse(
    mask_otel_spans=mask_otel_spans
)

langfuse_handler = CallbackHandler()


# --------------------------------------------------
# RECUPERACIÓN DEL PROMPT
# --------------------------------------------------

try:
    prompt_obj = langfuse.get_prompt(
        NOMBRE_PROMPT,
        version=VERSION_PROMPT,
        type="text"
    )

    SYSTEM_PROMPT = prompt_obj.prompt

    print(
        f"Prompt cargado: {NOMBRE_PROMPT}, "
        f"versión {VERSION_PROMPT}"
    )

except Exception as error:
    raise RuntimeError(
        f"No se ha podido recuperar el prompt "
        f"{NOMBRE_PROMPT}, versión {VERSION_PROMPT}. "
        "Comprueba que existe en Langfuse y que "
        "las credenciales están configuradas."
    ) from error


# --------------------------------------------------
# ESTADO DEL GRAFO
# --------------------------------------------------

class Estado(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    llamadas_herramienta: int
    consulta_valida: bool


# --------------------------------------------------
# MODELO
# --------------------------------------------------

modelo = ChatOpenAI(
    model=NOMBRE_MODELO,
    temperature=0.2,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


# --------------------------------------------------
# MODELO CON HERRAMIENTAS
# --------------------------------------------------

modelo_con_herramientas = modelo.bind_tools(
    [consultar_siniestro]
)



# NODO DE VALIDACIÓN
# --------------------------------------------------

def validar(state: Estado):

    mensaje = state["messages"][-1].content.lower()

    palabras_validas = [
        "siniestro",
        "seguro",
        "póliza",
        "poliza",
        "accidente",
        "coche",
        "auto",
        "automóvil",
        "automovil",
        "parte",
        "documentación",
        "documentacion",
        "cobertura",
        "coberturas",
        "prima",
        "franquicia",
        "reparación",
        "reparacion",
        "estado",
        "expediente",
        "indemnización",
        "indemnizacion",
        "recibo",
        "renovación",
        "renovacion",
        "asistencia",
        "robo",
        "incendio",
        "lunas",
        "defensa jurídica",
        "defensa juridica",
        "responsabilidad civil",
        "daños propios",
        "danos propios",
        "terceros"
    ]

    # También aceptamos identificadores como SIN-1002.
    contiene_id_siniestro = "sin-" in mensaje

    es_valida = (
        contiene_id_siniestro
        or any(palabra in mensaje for palabra in palabras_validas)
    )

    if not es_valida:
        return {
            "consulta_valida": False,
            "messages": [
                AIMessage(
                    content=(
                        "La consulta no está relacionada "
                        "con seguros de automóvil. "
                        "¿Necesitas ayuda con alguna consulta sobre seguros?"
                    )
                )
            ]
        }

    return {
        "consulta_valida": True
    }


# --------------------------------------------------
# NODO DE REINICIO
# --------------------------------------------------

def reiniciar(state: Estado):

    return {
        "messages": [
            AIMessage(
                content=(
                    "No he podido identificar una consulta "
                    "relacionada con seguros de automóvil. "
                    "Por favor, formula de nuevo tu consulta."
                )
            )
        ]
    }


# --------------------------------------------------
# NODO CHATBOT
# --------------------------------------------------

def chatbot(state: Estado):

    mensajes = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"]
    ]

    respuesta = modelo_con_herramientas.invoke(
        mensajes
    )

    return {
        "messages": [respuesta]
    }


# --------------------------------------------------
# NODO DE HERRAMIENTAS
# --------------------------------------------------

tool_node = ToolNode(
    [consultar_siniestro]
)


def ejecutar_herramientas(state: Estado):

    try:
        resultado = tool_node.invoke(state)

        numero_llamadas = len(
            state["messages"][-1].tool_calls
        )

        return {
            "messages": resultado["messages"],
            "llamadas_herramienta": (
                state["llamadas_herramienta"]
                + numero_llamadas
            )
        }

    except Exception as error:

        print(
            f"\nError al ejecutar la herramienta: {error}"
        )

        return {
            "messages": [
                AIMessage(
                    content=(
                        "Lo siento, ha ocurrido un error al "
                        "consultar la información del siniestro. "
                        "Por favor, inténtalo de nuevo."
                    )
                )
            ]
        }





# --------------------------------------------------
# NODO FINALIZAR
# --------------------------------------------------

def finalizar(state: Estado):

    if not state["consulta_valida"]:
        return {}

    mensajes = state["messages"]

    # Localizar el último mensaje del usuario.
    ultimo_usuario = None

    for i in range(len(mensajes) - 1, -1, -1):
        if isinstance(mensajes[i], HumanMessage):
            ultimo_usuario = i
            break

    # Buscar una respuesta de herramienta SOLO en la consulta actual.
    if ultimo_usuario is not None:
        for mensaje in reversed(mensajes[ultimo_usuario + 1:]):
            if isinstance(mensaje, ToolMessage):
                return {
                    "messages": [
                        AIMessage(content=mensaje.content)
                    ]
                }

    # Si la consulta actual no ha utilizado herramientas,
    # generar una respuesta normal del modelo.
    mensajes_modelo = [
        SystemMessage(content=SYSTEM_PROMPT),
        *mensajes
    ]

    respuesta = modelo.invoke(mensajes_modelo)

    return {
        "messages": [respuesta]
    }


# --------------------------------------------------
# DECISIÓN DESPUÉS DE VALIDAR
# --------------------------------------------------

def decidir_validacion(state: Estado):

    if state["consulta_valida"]:
        return "chatbot"

    return "reiniciar"


# --------------------------------------------------
# DECISIÓN DEL SIGUIENTE PASO
# --------------------------------------------------

def decidir_siguiente_paso(state: Estado):

    if state["llamadas_herramienta"] >= 2:
        return "finalizar"

    ultima_respuesta = state["messages"][-1]

    if getattr(ultima_respuesta, "tool_calls", None):
        return "tools"

    return "finalizar"


# --------------------------------------------------
# CONSTRUCCIÓN DEL GRAFO
# --------------------------------------------------

builder = StateGraph(Estado)

builder.add_node("validar", validar)
builder.add_node("reiniciar", reiniciar)
builder.add_node("chatbot", chatbot)
builder.add_node("tools", ejecutar_herramientas)
builder.add_node("finalizar", finalizar)

builder.add_edge(START, "validar")

builder.add_conditional_edges(
    "validar",
    decidir_validacion,
    {
        "chatbot": "chatbot",
        "reiniciar": "reiniciar"
    }
)

builder.add_edge("reiniciar", END)

builder.add_conditional_edges(
    "chatbot",
    decidir_siguiente_paso,
    {
        "tools": "tools",
        "finalizar": "finalizar"
    }
)

builder.add_edge("tools", "chatbot")
builder.add_edge("finalizar", END)


# --------------------------------------------------
# MEMORIA Y EJECUCIÓN
# --------------------------------------------------

with SqliteSaver.from_conn_string("memoria.db") as checkpointer:

    app = builder.compile(
        checkpointer=checkpointer
    )

    if __name__ == "__main__":

        thread_id = input(
            "Introduce el identificador de la conversación: "
        )

        while True:

            consulta = input("\nTú: ")

            if consulta.lower() in [
                "salir",
                "exit",
                "quit"
            ]:
                break

            resultado = app.invoke(
                {
                    "messages": [
                        HumanMessage(content=consulta)
                    ],
                    "llamadas_herramienta": 0,
                    "consulta_valida": False
                },
                config={
                    "configurable": {
                        "thread_id": thread_id
                    },
                    "callbacks": [langfuse_handler],
                    "run_name": "chatbot-seguros-langgraph",
                    "metadata": {
                        "prompt_name": NOMBRE_PROMPT,
                        "prompt_version": VERSION_PROMPT,
                        "model_name": NOMBRE_MODELO,
                        "conversation_id": thread_id
                    }
                }
            )

            print("\nAsistente:")
            print(resultado["messages"][-1].content)

            print(
                "\nLlamadas a herramientas: "
                f"{resultado['llamadas_herramienta']}"
            )
