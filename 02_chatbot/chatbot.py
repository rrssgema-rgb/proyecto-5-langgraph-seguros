import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END


# Cargar las variables del archivo .env
load_dotenv()


# Estado del grafo
class Estado(TypedDict):
    mensaje: str
    respuesta: str


# Modelo de lenguaje
modelo = ChatOpenAI(
    model="openai/gpt-6-luna",
    temperature=0.2,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


# Nodo del chatbot
def chatbot(estado: Estado):
    respuesta = modelo.invoke([
        (
            "system",
            "Eres un asistente especializado en seguros de automóvil. "
            "Responde de forma clara, sencilla y profesional."
        ),
        (
            "human",
            estado["mensaje"]
        )
    ])

    return {
        "respuesta": respuesta.content
    }


# Crear el grafo
grafo = StateGraph(Estado)

# Añadir el nodo
grafo.add_node("chatbot", chatbot)

# Definir el recorrido
grafo.add_edge(START, "chatbot")
grafo.add_edge("chatbot", END)

# Compilar el grafo
app = grafo.compile()


# Ejecutar el chatbot
if __name__ == "__main__":

    consulta = input(
        "¿En qué puedo ayudarte con tu seguro de automóvil? "
    )

    resultado = app.invoke({
        "mensaje": consulta,
        "respuesta": ""
    })

    print("\nRespuesta:")
    print(resultado["respuesta"])