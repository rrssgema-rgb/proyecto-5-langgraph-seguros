import os

from typing import Annotated
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage
)

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from herramientas import consultar_siniestro


load_dotenv()


# --------------------------------------------------
# ESTADO
# --------------------------------------------------

class Estado(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    llamadas_herramienta: int
    consulta_valida: bool


# --------------------------------------------------
# MODELO
# --------------------------------------------------

modelo = ChatOpenAI(
    model="openai/gpt-6-luna",
    temperature=0.2,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


# --------------------------------------------------
# MODELO + HERRAMIENTA
# --------------------------------------------------

modelo_con_herramientas = modelo.bind_tools(
    [consultar_siniestro]
)


# --------------------------------------------------
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
    "prima",
    "franquicia",
    "reparación",
    "reparacion"
]

    es_valida = any(
        palabra in mensaje
        for palabra in palabras_validas
    )

    if not es_valida:
        return {
            "consulta_valida": False,
            "messages": [
                AIMessage(
                    content=(
                        "La consulta no está relacionada "
                        "con seguros de automóvil."
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

    respuesta = modelo_con_herramientas.invoke(
        state["messages"]
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

    # Si la consulta no es válida,
    # mostramos directamente el mensaje de validación.
    if not state["consulta_valida"]:
        return {}

    ultimo_mensaje = state["messages"][-1]

    # Si la última respuesta procede de una herramienta,
    # utilizamos directamente la información obtenida.
    if isinstance(ultimo_mensaje, ToolMessage):

        return {
            "messages": [
                AIMessage(
                    content=ultimo_mensaje.content
                )
            ]
        }

    # Si no se ha utilizado ninguna herramienta,
    # dejamos que el modelo responda normalmente.
    respuesta = modelo.invoke(
        [
            (
                "system",
                "Eres un asistente especializado "
                "en seguros de automóvil. "
                "Responde de forma clara, breve y profesional. "
                "No inventes información. "
                "Responde únicamente a la pregunta planteada."
            ),
            *state["messages"]
        ]
    )

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

    # Si ya hemos realizado 2 llamadas,
    # pasamos al nodo de finalización.
    if state["llamadas_herramienta"] >= 2:
        return "finalizar"

    ultima_respuesta = state["messages"][-1]

    # Si el modelo solicita una herramienta
    if getattr(ultima_respuesta, "tool_calls", None):
        return "tools"

    # Si no necesita herramientas
    return "finalizar"


# --------------------------------------------------
# CONSTRUCCIÓN DEL GRAFO
# --------------------------------------------------

builder = StateGraph(Estado)


builder.add_node(
    "validar",
    validar
)

builder.add_node(
    "reiniciar",
    reiniciar
)


builder.add_node(
    "chatbot",
    chatbot
)

builder.add_node(
    "tools",
    ejecutar_herramientas
)

builder.add_node(
    "finalizar",
    finalizar
)


# Inicio → validación

builder.add_edge(
    START,
    "validar"
)


# Validación → chatbot o finalizar

builder.add_conditional_edges(
    "validar",
    decidir_validacion,
    {
        "chatbot": "chatbot",
        "reiniciar": "reiniciar"
    }
)

builder.add_edge(
    "reiniciar",
    END
)


# Chatbot → tools o finalizar

builder.add_conditional_edges(
    "chatbot",
    decidir_siguiente_paso,
    {
        "tools": "tools",
        "finalizar": "finalizar"
    }
)


# Tools → chatbot

builder.add_edge(
    "tools",
    "chatbot"
)


# Finalizar → END

builder.add_edge(
    "finalizar",
    END
)


# --------------------------------------------------
# MEMORIA SQLITE
# --------------------------------------------------

with SqliteSaver.from_conn_string("memoria.db") as checkpointer:

    app = builder.compile(
        checkpointer=checkpointer
    )


    # --------------------------------------------------
    # EJECUCIÓN DEL CHAT
    # --------------------------------------------------

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
                        HumanMessage(
                            content=consulta
                        )
                    ],
                    "llamadas_herramienta": 0,
                    "consulta_valida": False
                },
                config={
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
            )

            print("\nAsistente:")
            print(
                resultado["messages"][-1].content
            )

            print(
                f"\nLlamadas a herramientas: "
                f"{resultado['llamadas_herramienta']}"
            )