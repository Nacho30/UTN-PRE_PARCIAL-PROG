# Diseño · Autenticación

## Orden del login

```
POST /auth/login
  │
  ├─ 1. AccesoUnitOfWork (sesión propia): contar fallos de (email, ip) en 60 s,
  │     posteriores al último éxito. ≥ 5 → 429 + Retry-After. No se calcula ningún hash.
  │
  ├─ 2. UoW de la petición: leer el usuario por email (lectura corta, se confirma).
  │
  ├─ 3. bcrypt.checkpw en to_thread + semáforo, SIN transacción abierta:
  │     contra el hash del usuario, o contra app.state.hash_ficticio si no existe.
  │
  ├─ 4. AccesoUnitOfWork: anotar el intento (exito true/false). Se confirma siempre.
  │
  ├─ 5. Falla → 401 «Correo o contraseña incorrectos» (mismo cuerpo exista o no el correo).
  │
  └─ 6. Roles vigentes → JWT {sub, iat, exp, roles} → Set-Cookie access_token.
```

El intento bloqueado (429) no se anota: no llegó a verificarse, y anotarlo correría la
ventana y haría que `Retry-After` mintiera.

## Retry-After
Se traen los fallos que cuentan, del más nuevo al más viejo, con `LIMIT 5`. El quinto es el
que tiene que salir de la ventana para que vuelva a haber lugar:
`Retry-After = ceil(quinto.cuando + 60 s − ahora)`, mínimo 1.

## Hash ficticio
Se calcula una vez en el lifespan con el mismo costo que los reales, así verificar contra él
tarda lo mismo que verificar contra uno verdadero (RN-09).

## Límite de 72 bytes
`PasswordBcrypt = Annotated[str, AfterValidator(max_72_bytes)]`. Se mide
`len(valor.encode("utf-8"))`: una «ñ» ocupa dos bytes.
