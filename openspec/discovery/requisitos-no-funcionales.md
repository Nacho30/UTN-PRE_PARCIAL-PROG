# Requisitos no funcionales

| Requisito | Detalle | Cómo se verifica | Estado |
|---|---|---|---|
| Asincronía | Todos los handlers con `async def`; bcrypt siempre fuera del bucle | Revisión de código; `to_thread` + semáforo en `security.py` | 🟡 bcrypt listo |
| Credenciales | Ninguna contraseña ni clave de firma en el código (tampoco como default), en `alembic.ini` ni en el repo | `Settings` sin defaults para `POSTGRES_PASSWORD` y `JWT_SECRET`; `.env` en `.gitignore` | ✅ |
| Token | Sólo en la cookie `HttpOnly`; nunca en el cuerpo ni leído de `Authorization` | C-03 | ⏳ |
| Esquema | Sólo con Alembic; nunca `create_all` | `alembic upgrade head` sobre base vacía | ✅ |
| Transacciones | Ningún repositorio confirma; ningún servicio construye su UoW; el UoW no cierra la sesión | Revisión de código; C-02, C-10, C-11 | ⏳ |
| Carga perezosa | Prohibida: toda relación que se lee se precarga en el repositorio | `lazy="raise_on_sql"` en todas las relaciones; C-15 | 🟡 relaciones listas |
| SQL | Nunca armado por concatenación con datos del usuario | C-16 (`' OR '1'='1`) | ⏳ |
| Errores | Mensajes propios; nunca texto de la base ni traza; ninguna entrada inválida en 500 | C-01, C-02, C-16 | 🟡 manejador final listo |
| Unicidad | Garantizada por la base; no se verifica con una consulta previa | C-02, C-19 | 🟡 restricciones listas |
| Diagnóstico | Las consultas se ven en la consola (`SQL_ECHO=true`) | C-15 | ✅ |

## Evidencias que pide la entrega

- **C-15:** captura o fragmento de la consola con las consultas del detalle de una orden con 2
  ítems y de otra con 4.
- **C-14:** captura de `psql` con los seis rechazos del disparador y el de la clave foránea.
