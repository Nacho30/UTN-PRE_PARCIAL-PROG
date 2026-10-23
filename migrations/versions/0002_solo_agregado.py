"""solo agregado

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-23 11:45:00

MIGRACIÓN ESCRITA A MANO, LEÍDA Y PROBADA ANTES DE APLICARLA.

`--autogenerate` compara tablas, columnas, índices y restricciones, pero no ve funciones ni
disparadores: esto no saldría nunca de la comparación automática.

Instala el disparador de sólo agregado (RN-15, sección 6.9) sobre las tres tablas que no se
corrigen: historial_estado_orden, movimiento_stock e historial_precio_repuesto. Rechaza
cualquier UPDATE o DELETE, venga de donde venga (la API, psql u otro programa). Los INSERT
siguen permitidos.

TRUNCATE no dispara triggers de fila: seed.py lo usa para dejar la base en su estado inicial.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLAS_SOLO_AGREGADO = ("historial_estado_orden", "movimiento_stock", "historial_precio_repuesto")


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION rechazar_modificacion() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% es de sólo agregado: no se permite %', TG_TABLE_NAME, TG_OP
                USING ERRCODE = 'restrict_violation',
                      HINT = 'Las correcciones se registran como una fila nueva.';
        END;
        $$;
        """
    )
    for tabla in TABLAS_SOLO_AGREGADO:
        op.execute(
            f"""
            CREATE TRIGGER trg_{tabla}_solo_agregado
            BEFORE UPDATE OR DELETE ON {tabla}
            FOR EACH ROW EXECUTE FUNCTION rechazar_modificacion();
            """
        )


def downgrade() -> None:
    for tabla in TABLAS_SOLO_AGREGADO:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_solo_agregado ON {tabla};")
    op.execute("DROP FUNCTION IF EXISTS rechazar_modificacion();")
