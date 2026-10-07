from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# Estado de la aplicación
class Estado(TypedDict):
    mensaje: str


# Nodo del asistente
def asistente_seguro(estado: Estado):
    return {
        "mensaje": (
            "Hola. Soy el asistente de seguros de automóvil. "
            f"Has indicado: {estado['mensaje']}"
        )
    }


# Crear el grafo
grafo = StateGraph(Estado)

# Añadir el nodo
grafo.add_node("asistente_seguro", asistente_seguro)

# Definir el recorrido
grafo.add_edge(START, "asistente_seguro")
grafo.add_edge("asistente_seguro", END)

# Compilar
app = grafo.compile()


# Ejecutar
if __name__ == "__main__":
    consulta = input("¿En qué puedo ayudarte con tu seguro de automóvil? ")

    resultado = app.invoke({
        "mensaje": consulta
    })

    print("\nRespuesta:")
    print(resultado["mensaje"])