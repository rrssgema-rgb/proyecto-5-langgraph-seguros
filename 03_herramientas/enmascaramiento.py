

import re
from typing import Optional

from langfuse.types import (
    MaskOtelSpansParams,
    MaskOtelSpansResult,
    OtelSpanPatch,
)


def enmascarar_datos(texto: str) -> str:
    """Oculta emails, DNI, teléfonos y matrículas españolas."""

    # 1. Correos electrónicos
    texto = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL OCULTO]",
        texto,
    )

    # 2. DNI español: 8 números y una letra
    texto = re.sub(
        r"\b\d{8}[A-Za-z]\b",
        "[DNI OCULTO]",
        texto,
        flags=re.IGNORECASE,
    )

    # 3. Teléfonos españoles, con o sin prefijo +34
    texto = re.sub(
        r"(?<!\d)(?:\+34[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?!\d)",
        "[TELÉFONO OCULTO]",
        texto,
    )

    # 4. Matrículas españolas modernas
    texto = re.sub(
        r"\b\d{4}\s?[BCDFGHJKLMNPRSTVWXYZ]{3}\b",
        "[MATRÍCULA OCULTA]",
        texto,
        flags=re.IGNORECASE,
    )

    return texto


def mask_otel_spans(
    *,
    params: MaskOtelSpansParams,
) -> Optional[MaskOtelSpansResult]:
    """
    Enmascara datos personales en los atributos de los spans
    antes de que Langfuse los registre.
    """

    cambios = {}

    for identificador, span in params.spans.items():
        atributos_modificados = {}

        for nombre, valor in span.attributes.items():
            if isinstance(valor, str):
                valor_enmascarado = enmascarar_datos(valor)

                if valor_enmascarado != valor:
                    atributos_modificados[nombre] = valor_enmascarado

        if atributos_modificados:
            cambios[identificador] = OtelSpanPatch(
                set_attributes=atributos_modificados
            )

    if not cambios:
        return None

    return MaskOtelSpansResult(span_patches=cambios)


if __name__ == "__main__":
    ejemplo = (
        "Cliente: Ana Pérez. "
        "Email: ana.prueba@example.com. "
        "DNI: 12345678Z. "
        "Teléfono: 612345678. "
        "Móvil internacional: +34 612 345 678. "
        "Matrícula: 1234 BCD."
    )

    print("Texto original:")
    print(ejemplo)

    print("\nTexto enmascarado:")
    print(enmascarar_datos(ejemplo))
