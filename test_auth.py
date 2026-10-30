from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from sqlalchemy.ext.asyncio import async_sessionmaker


@pytest_asyncio.fixture
async def auth_client():
    """Cada prueba usa savepoints; los commits del servicio no persisten sus datos."""
    async with app.router.lifespan_context(app):
        original_factory = app.state.session_factory
        async with app.state.engine.connect() as connection:
            transaction = await connection.begin()
            app.state.session_factory = async_sessionmaker(
                connection, expire_on_commit=False, autoflush=False,
                join_transaction_mode="create_savepoint",
            )
            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test",
                ) as client:
                    yield client
            finally:
                await transaction.rollback()
                app.state.session_factory = original_factory


@pytest.fixture
def registro_data():
    # Correo corto y único: no colisiona con datos de otra ejecución.
    return {
        "email": f"{uuid4().hex[:8]}@test.com",
        "nombre": "Test User",
        "password": "Password123",
    }


@pytest.mark.asyncio
async def test_password_bcryt_72_bytes():
    from app.core.tipos import PasswordBcrypt
    from pydantic import TypeAdapter, ValidationError

    ta = TypeAdapter(PasswordBcrypt)
    assert ta.validate_python("contraseña123") == "contraseña123"
    pass_larga = "ñ" * 37
    with pytest.raises(ValidationError):
        ta.validate_python(pass_larga)


@pytest.mark.asyncio
async def test_registro_y_login(auth_client, registro_data):
    response = await auth_client.post("/auth/registro", json=registro_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == registro_data["email"]
    assert "CLIENTE" in data["roles"]

    response_login = await auth_client.post(
        "/auth/login",
        json={"email": registro_data["email"], "password": registro_data["password"]},
    )
    assert response_login.status_code == 200
    assert "access_token" in response_login.cookies

    response_yo = await auth_client.get("/auth/yo")
    assert response_yo.status_code == 200
    assert response_yo.json()["email"] == registro_data["email"]

    response_logout = await auth_client.post("/auth/logout")
    assert response_logout.status_code == 200


@pytest.mark.asyncio
async def test_login_password_incorrecta(auth_client, registro_data):
    registro = await auth_client.post("/auth/registro", json=registro_data)
    assert registro.status_code == 201

    response = await auth_client.post(
        "/auth/login",
        json={"email": registro_data["email"], "password": "Incorrecta123"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Correo o contraseña incorrectos"}
    assert "access_token" not in response.cookies
