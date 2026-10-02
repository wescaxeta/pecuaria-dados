"""Esquema inicial: municípios e efetivo dos rebanhos.

Revision ID: 0001
Revises:
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Busca de município sem acento ("goiania" encontra "Goiânia"). O wrapper IMMUTABLE permite
    # usar a função em índices, o que unaccent() sozinha não permite.
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("""
        CREATE OR REPLACE FUNCTION unaccent_lower(texto text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT lower(public.unaccent('public.unaccent'::regdictionary, texto)) $$
    """)

    op.create_table(
        "municipio",
        sa.Column(
            "codigo", sa.Integer(), autoincrement=False, nullable=False, comment="Código IBGE de 7 dígitos"
        ),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.PrimaryKeyConstraint("codigo"),
    )
    op.create_index("ix_municipio_uf", "municipio", ["uf"])
    op.execute("CREATE INDEX ix_municipio_nome_sem_acento ON municipio (unaccent_lower(nome))")

    op.create_table(
        "efetivo_rebanho",
        sa.Column("municipio_codigo", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("especie", sa.String(length=20), nullable=False),
        sa.Column(
            "efetivo",
            sa.BigInteger(),
            nullable=True,
            comment="Cabeças; nulo quando não disponível ou sigiloso",
        ),
        sa.Column("situacao", sa.String(length=20), nullable=False),
        sa.CheckConstraint("efetivo IS NULL OR efetivo >= 0", name="ck_efetivo_nao_negativo"),
        sa.CheckConstraint(
            "(situacao = 'informado') = (efetivo IS NOT NULL)", name="ck_efetivo_coerente_com_situacao"
        ),
        sa.ForeignKeyConstraint(["municipio_codigo"], ["municipio.codigo"]),
        sa.PrimaryKeyConstraint("municipio_codigo", "ano", "especie"),
    )
    op.create_index("ix_efetivo_especie_ano", "efetivo_rebanho", ["especie", "ano"])


def downgrade() -> None:
    op.drop_table("efetivo_rebanho")
    op.drop_table("municipio")
    op.execute("DROP FUNCTION IF EXISTS unaccent_lower(text)")
