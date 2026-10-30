"""Aviso al cliente cuando su orden se termina (ejercicio 8, sección 3.9).

El router lo agenda con `BackgroundTasks`, así que corre DESPUÉS de enviar la respuesta: el
mecánico no espera el aviso. Y lo agenda sólo cuando el servicio volvió sin excepción, es
decir, cuando el Unit of Work ya confirmó: si la terminación falla (403, 409 o un commit que
no entra), no hay nada que avisar.

Recibe valores sueltos y no objetos del ORM: cuando corre, la sesión de la petición ya se
cerró, y con `raise_on_sql` tocar una relación de un objeto suelto sería un error.

Límites aceptados (consigna, «Qué queda afuera»): corre en el mismo proceso, así que si el
proceso se reinicia el aviso se pierde y no hay reintento. Se acepta porque es simulado y
perderlo no rompe nada; una cola de tareas (capítulo 8) lo resuelve.
"""

import asyncio
import logging

logger = logging.getLogger("taller.avisos")


async def avisar_cliente(*, orden_id: int, cliente: str, patente: str) -> None:
    # Simula el envío (un correo, un mensaje) sin bloquear el bucle de eventos:
    # `asyncio.sleep` cede el control; `time.sleep` frenaría a todas las peticiones.
    await asyncio.sleep(0.5)
    logger.info(
        "Aviso enviado a %s: la orden %s del vehículo %s está terminada",
        cliente,
        orden_id,
        patente,
    )
