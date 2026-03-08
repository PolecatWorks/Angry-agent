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


# ------------- CLI commands above here -------------

if __name__ == "__main__":
    cli()
