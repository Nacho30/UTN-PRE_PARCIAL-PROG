"""Jerarquía de errores de dominio y traducción de IntegrityError.

Los servicios lanzan errores de dominio sin conocer HTTP ni SQL (D-12).
FastAPI traduce estos errores a respuestas JSON {"detail": "..."} con su código HTTP.
"""

from typing import Any
from sqlalchemy.exc import IntegrityError


class ErrorDominio(Exception):
    """Base para errores del modelo de negocio."""

    status_code: int = 400

    def __init__(
        self,
        detail: str,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        self.headers = headers

    def __str__(self) -> str:
        return self.detail


class ErrorNoEncontrado(ErrorDominio):
    status_code = 404

    def __init__(self, detail: str = "Recurso no encontrado") -> None:
        super().__init__(detail, status_code=404)


class ErrorConflicto(ErrorDominio):
    status_code = 409

    def __init__(self, detail: str = "Conflicto con el estado actual") -> None:
        super().__init__(detail, status_code=409)


class ErrorValidacion(ErrorDominio):
    status_code = 422

    def __init__(self, detail: str = "Error de validación") -> None:
        super().__init__(detail, status_code=422)


class ErrorPaginacion(ErrorValidacion):
    pass


class ErrorNoAutenticado(ErrorDominio):
    status_code = 401

    def __init__(self, detail: str = "No autenticado") -> None:
        super().__init__(detail, status_code=401)


class ErrorPermiso(ErrorDominio):
    status_code = 403

    def __init__(self, detail: str = "Permiso denegado") -> None:
        super().__init__(detail, status_code=403)


class ErrorDemasiadosIntentos(ErrorDominio):
    status_code = 429

    def __init__(
        self,
        retry_after: int,
        detail: str = "Demasiados intentos fallidos. Intente más tarde.",
    ) -> None:
        super().__init__(
            detail,
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )
        self.retry_after = retry_after


# --- Traducción de IntegrityError (RN-18 y design.md) ------------------------

RESTRICCIONES_A_MENSAJES: dict[str, str] = {
    "uq_usuario_email": "El correo ya está registrado",
    "usuario.email": "El correo ya está registrado",
    "uq_cliente_documento": "Ya existe un cliente con ese documento",
    "cliente.documento": "Ya existe un cliente con ese documento",
    "uq_cliente_usuario_id": "El usuario ya tiene una ficha de cliente",
    "cliente.usuario_id": "El usuario ya tiene una ficha de cliente",
    "ux_vehiculo_patente_vigente": "Ya existe un vehículo vigente con esa patente",
    "ux_repuesto_codigo_vigente": "Ya existe un repuesto vigente con ese código",
    "ux_asignacion_rol_abierta": "El usuario ya tiene ese rol asignado",
    "uq_item_orden_orden_id_repuesto_id": "La orden tiene repuestos repetidos",
    "fk_orden_trabajo_estado_estado_orden": "El catálogo de estados de orden no está cargado",
    "fk_orden_trabajo_vehiculo_id_vehiculo": "El vehículo especificado no existe",
    "fk_item_orden_repuesto_id_repuesto": "El repuesto especificado no existe",
    "fk_vehiculo_cliente_id_cliente": "El cliente especificado no existe",
    "precio_positivo": "El precio debe ser mayor a cero",
    "ck_repuesto_precio_positivo": "El precio debe ser mayor a cero",
    "stock_no_negativo": "El stock no puede ser negativo",
    "ck_repuesto_stock_no_negativo": "El stock no puede ser negativo",
    "cantidad_positiva": "La cantidad debe ser mayor a cero",
    "ck_item_orden_cantidad_positiva": "La cantidad debe ser mayor a cero",
    "precio_unitario_positivo": "El precio unitario debe ser mayor a cero",
    "ck_item_orden_precio_unitario_positivo": "El precio unitario debe ser mayor a cero",
    "total_no_negativo": "El total no puede ser negativo",
    "ck_orden_trabajo_total_no_negativo": "El total no puede ser negativo",
    "anio_valido": "El año debe estar entre 1950 y 2100",
    "ck_vehiculo_anio_valido": "El año debe estar entre 1950 y 2100",
    "precio_nuevo_positivo": "El precio nuevo debe ser mayor a cero",
    "ck_historial_precio_repuesto_precio_nuevo_positivo": "El precio nuevo debe ser mayor a cero",
    "precio_cambia": "El precio nuevo debe ser distinto al anterior",
    "ck_historial_precio_repuesto_precio_cambia": "El precio nuevo debe ser distinto al anterior",
    "cantidad_distinta_de_cero": "La cantidad debe ser distinta de cero",
    "ck_movimiento_stock_cantidad_distinta_de_cero": "La cantidad debe ser distinta de cero",
}


def extraer_nombre_restriccion(exc: IntegrityError) -> str | None:
    """Extrae el nombre de la restricción desde el objeto de diagnóstico o mensaje."""
    orig: Any = getattr(exc, "orig", None)
    if orig is not None:
        # asyncpg
        diag = getattr(orig, "diag", None)
        if diag is not None:
            c_name = getattr(diag, "constraint_name", None)
            if c_name:
                return str(c_name)
        # psycopg
        c_name = getattr(orig, "constraint_name", None)
        if c_name:
            return str(c_name)

    # Búsqueda por coincidencia de subcadena en el mensaje del error
    mensaje_str = str(exc)
    for constraint_name in RESTRICCIONES_A_MENSAJES:
        if constraint_name in mensaje_str:
            return constraint_name

    return None


def traducir_integrity_error(exc: IntegrityError) -> str:
    """Traduce un IntegrityError a un mensaje amigable en castellano (409).

    Nunca devuelve SQL ni texto interno de la base de datos (RN-18).
    """
    nombre = extraer_nombre_restriccion(exc)
    if nombre and nombre in RESTRICCIONES_A_MENSAJES:
        return RESTRICCIONES_A_MENSAJES[nombre]

    return "Violación de restricción de integridad en los datos"
