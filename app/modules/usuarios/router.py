"""Rutas de autenticación y usuarios.

En el ejercicio 3, incluye el contrato estricto de registro (POST /auth/registro)
para verificar el rechazo de campos no declarados (como 'rol') con 422.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.modules.usuarios.schemas import RegistroIn

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registro(payload: RegistroIn) -> JSONResponse:
    # En ej3 validamos el contrato estricto de entrada (extra="forbid" rechaza 'rol')
    return JSONResponse(
        {"mensaje": "Usuario y cliente registrados exitosamente", "email": payload.email},
        status_code=status.HTTP_201_CREATED,
    )
