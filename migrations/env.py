from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from pecuaria_dados.config import configuracao
from pecuaria_dados.db import metadata

if context.config.config_file_name is not None:
    # Sem isso o fileConfig desliga os loggers já criados pela aplicação
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)

url = context.config.attributes.get("database_url") or configuracao().database_url


def rodar_migrations() -> None:
    conectavel = create_engine(url)
    try:
        with conectavel.connect() as conexao:
            context.configure(connection=conexao, target_metadata=metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        conectavel.dispose()  # fecha o pool; sem isso a conexão fica aberta até o coletor de lixo


rodar_migrations()
