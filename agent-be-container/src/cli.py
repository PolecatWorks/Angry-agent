#!/usr/bin/env python

# chatbot Copyright (C) 2024 Ben Greene
"""CLI initiated python app"""

import click
import sys
import logging
import logging.config
from ruamel.yaml import YAML
import io

from .config import ServiceConfig


# https://stackoverflow.com/questions/242485/starting-python-debugger-automatically-on-error
def interactivedebugger(type, value, tb):
    if hasattr(sys, "ps1") or not sys.stderr.isatty():
        # we are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import traceback
        import pdb

        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(type, value, tb)
        print
        # ...then start the debugger in post-mortem mode.
        # pdb.pm() # deprecated
        pdb.post_mortem(tb)  # more "modern"


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, debug):
    """
    Service and tools for basic service
    """
    ctx.ensure_object(dict)

    ctx.obj["DEBUG"] = debug

    if debug:
        click.echo(f"Debug mode is {'on' if debug else 'off'}", err=True)
        sys.excepthook = interactivedebugger


# ------------- CLI commands go below here -------------



def shared_options(function):
    function = click.option("--config", required=True, type=click.File("rb"))(function)
    function = click.option("--secrets", required=True, type=click.Path(exists=True))(function)
    function = click.pass_context(function)
    return function


@cli.command()
@shared_options
def parse(ctx, config, secrets):
    """Parse a config"""
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)

    # Print to stdout
    stream = io.StringIO()
    yaml.dump(configObj.model_dump(mode='json'), stream)
    click.echo(stream.getvalue())


@cli.command()
@shared_options
def start(ctx, config, secrets):
    """Start the service"""
    from . import app_start

    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)

    # Load logging configuration from YAML file
    logging.config.dictConfig(configObj.logging)

    # Print config
    stream = io.StringIO()
    yaml.dump(configObj.model_dump(mode='json'), stream)
    print(stream.getvalue())

    app_start(configObj)


@cli.command()
@click.option("--action", type=click.Choice(["apply", "rollback", "list"]), default="apply", help="Migration action to perform.")
@shared_options
def migrate(ctx, config, secrets, action):
    """Run database schema migrations"""
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)

    # Load logging configuration from YAML file
    logging.config.dictConfig(configObj.logging)

    from yoyo import read_migrations, get_backend
    import os

    backend = get_backend(configObj.persistence.db.connection.dsn)

    # Check migrations directory
    migrations_dir = os.path.join(os.getcwd(), "migrations")
    if not os.path.exists(migrations_dir):
        migrations_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")

    migrations = read_migrations(migrations_dir)
    with backend.lock():
        if action == "list":
            applied = backend.to_rollback(migrations)
            pending = backend.to_apply(migrations)
            click.echo("--- Applied Migrations ---")
            for m in applied:
                click.echo(f"  {m.id}")
            if not applied:
                click.echo("  (None)")
            click.echo("\n--- Pending Migrations ---")
            for m in pending:
                click.echo(f"  {m.id}")
            if not pending:
                click.echo("  (None)")
        elif action == "rollback":
            applied = backend.to_rollback(migrations)
            if applied:
                m = applied[-1] # Rollback the latest applied migration
                logging.getLogger(__name__).info(f"Rolling back migration: {m.id}")
                backend.rollback_migrations([m])
                logging.getLogger(__name__).info("Database migration rolled back successfully.")
            else:
                click.echo("No applied migrations to rollback.")
        else: # apply
            pending = backend.to_apply(migrations)
            if pending:
                logging.getLogger(__name__).info(f"Applying {len(pending)} database migrations...")
                backend.apply_migrations(pending)
                logging.getLogger(__name__).info("Database migrations applied successfully.")
            else:
                click.echo("Database is up to date. No pending migrations to apply.")


@cli.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.argument("agent_name", type=str)
@shared_options
def load_agent(ctx, config, secrets, filepath, agent_name):
    """Load an agent definition from a Markdown file into the database"""
    import asyncio
    import uuid
    import os
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from src.agent.embeddings import get_embeddings_model
    from src.database import init_db_pool, close_db_pool, get_db_pool

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)
    logging.config.dictConfig(configObj.logging)

    logger = logging.getLogger(__name__)

    async def _load():
        try:
            logger.info(f"Loading agent definition from {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            logger.info(f"Splitting content into chunks")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )
            chunks = text_splitter.split_text(content)
            logger.info(f"Created {len(chunks)} chunks")

            # Get embedding model
            embedding_model = get_embeddings_model(configObj.embedding_client)

            logger.info("Generating embeddings for chunks...")
            embeddings = embedding_model.embed_documents(chunks)

            # Initialize DB pool
            await init_db_pool(configObj.persistence.db)
            pool = await get_db_pool()

            agent_id = str(uuid.uuid4())

            logger.info("Saving to database...")
            async with pool.acquire() as conn:
                async with conn.transaction():
                    # Insert parent record
                    await conn.execute(
                        "INSERT INTO agent_definitions (id, name, content) VALUES ($1::uuid, $2, $3)",
                        agent_id, agent_name, content
                    )

                    # Insert chunks
                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        chunk_id = str(uuid.uuid4())
                        # Format list as postgres vector string: "[1.0, 2.0, ...]"
                        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

                        await conn.execute(
                            """
                            INSERT INTO agent_definition_chunks (id, agent_id, chunk_index, content, embedding)
                            VALUES ($1::uuid, $2::uuid, $3, $4, $5::vector)
                            """,
                            chunk_id, agent_id, i, chunk, embedding_str
                        )

            logger.info(f"Successfully loaded agent '{agent_name}' with ID: {agent_id}")

        except Exception as e:
            logger.error(f"Failed to load agent: {e}", exc_info=True)
        finally:
            await close_db_pool()

    asyncio.run(_load())


# ------------- CLI commands above here -------------

if __name__ == "__main__":
    cli()
