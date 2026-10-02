"""Esquema do banco (SQLAlchemy Core). As migrations do Alembic são geradas a partir daqui."""

from functools import lru_cache

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Engine,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    create_engine,
)

from pecuaria_dados.config import configuracao

metadata = MetaData()

municipio = Table(
    "municipio",
    metadata,
    Column("codigo", Integer, primary_key=True, autoincrement=False, comment="Código IBGE de 7 dígitos"),
    Column("nome", String(100), nullable=False),
    Column("uf", String(2), nullable=False),
    Index("ix_municipio_uf", "uf"),
)

efetivo_rebanho = Table(
    "efetivo_rebanho",
    metadata,
    Column("municipio_codigo", Integer, ForeignKey("municipio.codigo"), primary_key=True),
    Column("ano", SmallInteger, primary_key=True),
    Column("especie", String(20), primary_key=True),
    Column("efetivo", BigInteger, nullable=True, comment="Cabeças; nulo quando não disponível ou sigiloso"),
    Column("situacao", String(20), nullable=False),
    CheckConstraint("efetivo IS NULL OR efetivo >= 0", name="ck_efetivo_nao_negativo"),
    CheckConstraint(
        "(situacao = 'informado') = (efetivo IS NOT NULL)", name="ck_efetivo_coerente_com_situacao"
    ),
    # Consultas analíticas filtram por espécie e ano (ranking, evolução)
    Index("ix_efetivo_especie_ano", "especie", "ano"),
)


@lru_cache
def engine(url: str | None = None) -> Engine:
    return create_engine(url or configuracao().database_url, pool_pre_ping=True)
