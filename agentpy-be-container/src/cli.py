#!/usr/bin/env python

# chatbot Copyright (C) 2024 Ben Greene
"""CLI initiated python app"""

import click
import sys
import logging
import logging.config
from ruamel.yaml import YAML
import io

from src.config import ServiceConfig


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
    from src import app_start

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
    from src.database import init_db_pool, close_db_pool
    from src.agent.agent_store import save_agent_definition

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)
    logging.config.dictConfig(configObj.logging)

    logger = logging.getLogger(__name__)

    async def _load():
        try:
            logger.info(f"Loading agent definition from {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Initialize DB pool
            await init_db_pool(configObj.persistence.db)

            await save_agent_definition(agent_name, content, configObj)

        except Exception as e:
            logger.error(f"Failed to load agent: {e}", exc_info=True)
        finally:
            await close_db_pool()

    asyncio.run(_load())


@cli.command()
@shared_options
def list_threads(ctx, config, secrets):
    """List recent threads"""
    import asyncio
    from psycopg_pool import AsyncConnectionPool
    from psycopg.rows import dict_row

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)
    logging.config.dictConfig(configObj.logging)

    async def _list():
        dsn = configObj.persistence.db.connection.dsn
        async with AsyncConnectionPool(conninfo=dsn, row_factory=dict_row) as pool:
            async with pool.acquire() as conn:
                rows = await conn.fetch_all("SELECT thread_id, title, user_id FROM threads ORDER BY created_at DESC LIMIT 5")
                click.echo("--- Recent threads ---")
                for r in rows:
                    click.echo(f"{r['thread_id']} | {r['user_id']} | {r['title']}")

    asyncio.run(_list())


@cli.command()
@shared_options
def test_pool(ctx, config, secrets):
    """Test database connection pooling"""
    import asyncio
    from psycopg_pool import AsyncConnectionPool
    from psycopg.rows import dict_row

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)
    logging.config.dictConfig(configObj.logging)

    async def _test():
        dsn = configObj.persistence.db.connection.dsn
        pool_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        }

        pool = AsyncConnectionPool(
            conninfo=dsn,
            kwargs=pool_kwargs,
            check=AsyncConnectionPool.check_connection
        )
        import pprint
        pprint.pprint(dir(pool))

    asyncio.run(_test())


@cli.command()
@click.option("--thread-id", required=True, type=str, help="The ID of the thread to inspect")
@shared_options
def inspect_state(ctx, config, secrets, thread_id):
    """Inspect the state of a thread"""
    import asyncio
    from src.database import init_db_pool, close_db_pool
    from src.agent.handler import LLMHandler

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)
    logging.config.dictConfig(configObj.logging)

    async def _inspect():
        try:
            await init_db_pool(configObj.persistence.db)
            handler = LLMHandler(db_dsn=configObj.persistence.db.connection.dsn)
            await handler.initialize()

            state = await handler.get_thread_state(thread_id)

            click.echo("\n--- Agent State Values ---")
            if state:
                click.echo(state.values)
                click.echo("\n--- Agent State Next Node ---")
                click.echo(state.next)
            else:
                click.echo(f"No state found for thread {thread_id}")

            await handler.close()
        except Exception as e:
            click.echo(f"Error: {e}")
        finally:
            await close_db_pool()

    asyncio.run(_inspect())


@cli.command()
@click.option("--thread-id", required=True, type=str, help="The ID of the thread to inspect fully")
@shared_options
def inspect_full_state(ctx, config, secrets, thread_id):
    """Inspect the full state of a thread including detailed message contents"""
    import asyncio
    from src.database import init_db_pool, close_db_pool
    from src.agent.handler import LLMHandler

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)
    logging.config.dictConfig(configObj.logging)

    async def _inspect_full():
        try:
            await init_db_pool(configObj.persistence.db)
            handler = LLMHandler(db_dsn=configObj.persistence.db.connection.dsn)
            await handler.initialize()

            state = await handler.get_thread_state(thread_id)

            click.echo("\n--- Agent State Values ---")
            if state and state.values:
                messages = state.values.get("messages", [])
                click.echo(f"Messages count: {len(messages)}")
                for i, m in enumerate(messages):
                    click.echo(f"{i}: {type(m).__name__}")
                    click.echo(f"  Content: {repr(m.content)}")
                    if hasattr(m, 'additional_kwargs') and m.additional_kwargs:
                        click.echo(f"  Kwargs: {m.additional_kwargs.keys()}")
                    if hasattr(m, 'tool_calls') and m.tool_calls:
                        click.echo(f"  ToolCalls: {len(m.tool_calls)}")
            else:
                click.echo("No state values found.")

            click.echo("\n--- Agent State Next Node ---")
            click.echo(state.next if state else "None")

            await handler.close()
        except Exception as e:
            click.echo(f"Error: {e}")
        finally:
            await close_db_pool()

    asyncio.run(_inspect_full())


@cli.command()
@click.option("--thread-id", required=True, type=str, help="The ID of the thread to inspect checkpoints for")
@shared_options
def inspect_checkpoint(ctx, config, secrets, thread_id):
    """Inspect the checkpoint of a thread directly from AsyncPostgresSaver"""
    import asyncio
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool
    from psycopg.rows import dict_row

    configObj: ServiceConfig = ServiceConfig.from_yaml_and_secrets_dir(config.name, secrets)
    logging.config.dictConfig(configObj.logging)

    async def _inspect_cp():
        dsn = configObj.persistence.db.connection.dsn
        pool_kwargs = {
            "prepare_threshold": 0,
            "row_factory": dict_row,
        }

        async with AsyncConnectionPool(
            conninfo=dsn,
            max_size=5,
            kwargs=pool_kwargs,
            check=AsyncConnectionPool.check_connection
        ) as pool:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()

            config = {"configurable": {"thread_id": thread_id}}

            state = await checkpointer.aget(config)

            if not state:
                click.echo(f"No state found for thread {thread_id}")
                return

            click.echo("\n--- Checkpoint Found ---")

            values = state.get('values', {})
            messages = values.get('messages', [])

            click.echo(f"\n--- Messages ({len(messages)}) ---")
            for i, m in enumerate(messages):
                m_type = type(m).__name__
                content = getattr(m, 'content', str(m))
                click.echo(f"{i}: {m_type} - {content[:100]}...")
                if hasattr(m, 'additional_kwargs') and m.additional_kwargs:
                    click.echo(f"   kwargs: {m.additional_kwargs}")

    asyncio.run(_inspect_cp())


# ------------- CLI commands above here -------------

if __name__ == "__main__":
    cli()
