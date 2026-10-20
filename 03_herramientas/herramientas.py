import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool


# Cargar las variables del archivo .env
load_dotenv()


# Datos ficticios de siniestros
siniestros = {
    "SIN-1001": {
        "estado": "Abierto",
        "descripcion": "Pendiente de peritación"
    },
    "SIN-1002": {
        "estado": "En tramitación",
        "descripcion": "Documentación recibida"
    },
    "SIN-1003": {
        "estado": "Cerrado",
        "descripcion": "Indemnización pagada"
    }
}



# Definir la función como herramienta
@tool
def consultar_siniestro(numero_siniestro: str):
    """
    Consulta el estado de un siniestro de automóvil.
    Si el número no existe, informa de que no se ha encontrado.
    """

    numero_siniestro = numero_siniestro.strip().upper()

    if numero_siniestro in siniestros:
        siniestro = siniestros[numero_siniestro]

        return (
            f"El siniestro {numero_siniestro} está "
            f"{siniestro['estado']}. "
            f"{siniestro['descripcion']}."
        )

    return (
        f"No se ha encontrado el siniestro {numero_siniestro}. "
        "No existe ningún siniestro con ese número en los datos de prueba."
    )



# Crear el modelo
modelo = ChatOpenAI(
    model="openai/gpt-6-luna",
    temperature=0.2,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


# Conectar la herramienta con el modelo
modelo_con_herramientas = modelo.bind_tools(
    [consultar_siniestro]
)


# Probar el modelo
if __name__ == "__main__":

    consulta = input("¿En qué puedo ayudarte? ")

    respuesta = modelo_con_herramientas.invoke(consulta)

    print("\nRespuesta del modelo:")
    print(respuesta)

    print("\nHerramientas solicitadas:")
    print(respuesta.tool_calls)