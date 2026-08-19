#!/usr/bin/env python3
"""La fuente de tiempo de los sellos: el reloj del sistema, nunca la cabeza de quien redacta.

POR QUE EXISTE
--------------
El 19-ago-2026 se descubrio que 14 artefactos del archivo declaraban en su ID una fecha
POSTERIOR a su propio commit — imposible: el sello no puede ocurrir despues de publicarse.
Siete eran de dos dias de trabajo intenso, y la causa era siempre la misma: el timestamp
se escribia a mano en el sellador, tomado del contexto del que redactaba y no del reloj.

El caso peor de ese lote: `RQ-PREREG-AIRBUS-001` declara 20260820T1900Z y su borrador
fuente se publico el 2026-08-19T14:47Z — leido literal, el pre-registro «ocurrio» despues
de su propia fuente. Git y OTS dicen lo contrario, pero es exactamente la inversion que un
auditor buscaria, y nuestra afirmacion central es que el pre-registro precede a todo.

El notario ya ABORTA ante fechas futuras no declaradas (paso 1 ter de notarize.py). Esto es
la capa que previene en vez de atrapar: mismo principio que leer los sha del disco en vez
de tipearlos.

USO
---
    from reloj_sello import ahora_stamp, ahora_iso
    STAMP = ahora_stamp()                  # "20260819T1532Z"  -> para el ID del archivo
    rs.seal(doc, ..., sealed_at=ahora_iso())

Para re-sellar un artefacto ya emitido y conservar su hash, se pasa el instante explicito
con `congelado=` — y eso queda visible en el codigo, que es la diferencia con tipearlo.
"""
from datetime import datetime, timezone

FORMATO_ID = "%Y%m%dT%H%MZ"


def _ahora(congelado=None):
    if congelado is not None:
        if congelado.tzinfo is None:
            raise ValueError("un instante congelado va con zona horaria explicita")
        return congelado
    return datetime.now(timezone.utc)


def ahora_stamp(congelado=None):
    """El sello de tiempo del ID: 20260819T1532Z, del reloj."""
    return _ahora(congelado).strftime(FORMATO_ID)


def ahora_iso(congelado=None):
    """ISO-8601 UTC para `sealed_at`, del mismo instante."""
    return _ahora(congelado).replace(microsecond=0).isoformat()


def coherentes(stamp, iso):
    """¿El ID y el sealed_at hablan del mismo minuto? Un sellador que los toma de aqui
    no puede desincronizarlos; esto atrapa al que mezcle una fuente con la otra."""
    return stamp == datetime.fromisoformat(iso).astimezone(timezone.utc).strftime(FORMATO_ID)
