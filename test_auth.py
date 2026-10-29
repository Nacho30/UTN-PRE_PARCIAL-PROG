import pytest
from httpx import AsyncClient, ASGITransport
from main import app


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
async def test_registro_y_login():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/auth/registro",
                json={
                    "email": "test@taller.com",
                    "nombre": "Test User",
                    "password": "Password123",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "test@taller.com"
            assert "CLIENTE" in data["roles"]

            response_login = await ac.post(
                "/auth/login",
                json={
                    "email": "test@taller.com",
                    "password": "Password123",
                },
            )
            assert response_login.status_code == 200
            assert "access_token" in response_login.cookies

            response_yo = await ac.get("/auth/yo")
            assert response_yo.status_code == 200
            assert response_yo.json()["email"] == "test@taller.com"

            response_logout = await ac.post("/auth/logout")
            assert response_logout.status_code == 200
