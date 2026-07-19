"""Command-line entrypoint: ``produceros <command>``.

This is what scripts/run_desktop.ps1, scripts/run_lan.ps1, and the
PyInstaller-packaged executable all call. Database migrations are run
through Alembic's Python API (not the ``alembic`` CLI) so a frozen,
Python-less Windows package can still migrate its own database.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser
from pathlib import Path

from produceros.config import get_settings
from produceros.logging_config import configure_logging, get_logger

logger = get_logger("cli")


def _alembic_config():
    from alembic.config import Config

    if getattr(sys, "frozen", False):
        # Running as a PyInstaller build: bundled datas (alembic.ini,
        # migrations/) are extracted under sys._MEIPASS, which is a
        # `_internal/` folder next to the exe for a onedir build or a
        # temp dir for onefile -- never simply "next to the executable"
        # as of PyInstaller 6's layout, so use the real extraction root.
        ini_path = Path(sys._MEIPASS) / "alembic.ini"  # type: ignore[attr-defined]
    else:
        ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(ini_path.parent / "migrations"))
    return cfg


def cmd_db_upgrade(_args: argparse.Namespace) -> None:
    from alembic import command

    settings = get_settings()
    settings.ensure_directories()
    command.upgrade(_alembic_config(), "head")
    print(f"Database at {settings.database_path} is up to date.")


def cmd_db_current(_args: argparse.Namespace) -> None:
    from alembic import command

    command.current(_alembic_config(), verbose=True)


def _detect_bind_host(bind_mode: str) -> str:
    if bind_mode == "lan":
        from produceros.services.network import detect_private_ipv4

        host = detect_private_ipv4()
        if host is None:
            print("Could not detect a private LAN address. Falling back to 127.0.0.1 (desktop-only).")
            return "127.0.0.1"
        return host
    return "127.0.0.1"


def cmd_run(args: argparse.Namespace) -> None:
    import uvicorn
    from alembic import command

    settings = get_settings()
    settings.ensure_directories()
    configure_logging(settings.logs_dir, settings.log_level)

    bind_mode = args.mode or settings.bind_mode
    host = _detect_bind_host(bind_mode)
    port = args.port or settings.port

    logger.info("Running Alembic migrations before startup.")
    command.upgrade(_alembic_config(), "head")

    from produceros.web.app import create_app

    app = create_app()

    if bind_mode == "lan":
        print(f"LAN mode: binding to {host}:{port}. Do not forward this port through your router.")
        from produceros.services.network import (
            qr_code_data_uri,  # noqa: F401  (import validated here; used in-app)
        )
    else:
        print(f"Desktop mode: binding to {host}:{port} (localhost only).")

    if not args.no_browser and settings.open_browser:
        def _open_browser() -> None:
            time.sleep(1.0)
            webbrowser.open(f"http://{host}:{port}/")

        threading.Thread(target=_open_browser, daemon=True).start()

    if settings.mcp_enabled:
        from produceros.mcp_server.server import run_mcp_server_blocking

        print(f"MCP server enabled: http://{settings.mcp_bind}:{settings.mcp_port}")
        # run_mcp_server_blocking() calls FastMCP's server.run(), which
        # starts its own asyncio event loop -- it needs its own thread
        # since uvicorn.run() below does the same on the main thread.
        threading.Thread(target=run_mcp_server_blocking, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level=settings.log_level.lower())


def cmd_demo_load(_args: argparse.Namespace) -> None:
    from produceros.db.session import session_scope
    from produceros.demo.generator import load_demo_data

    with session_scope() as session:
        summary = load_demo_data(session)
    print(f"Demo data loaded: {summary}")


def cmd_demo_clean(_args: argparse.Namespace) -> None:
    from produceros.db.session import session_scope
    from produceros.demo.generator import clean_demo_data

    with session_scope() as session:
        removed = clean_demo_data(session)
    print(f"Removed {removed} demo-tagged rows.")


def cmd_backup_create(_args: argparse.Namespace) -> None:
    from produceros.db.session import session_scope
    from produceros.services.backup import create_backup

    settings = get_settings()
    with session_scope() as session:
        record = create_backup(session, settings)
    print(f"Backup created: {record.file_path}")


def cmd_restore_dry_run(args: argparse.Namespace) -> None:
    from produceros.services.backup import restore_dry_run

    result = restore_dry_run(args.backup_path)
    print(f"OK: {result.ok}")
    print(f"Integrity check: {result.integrity_check}")
    if result.table_counts:
        print("Table counts:")
        for table, count in sorted(result.table_counts.items()):
            print(f"  {table}: {count} rows")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    if not result.ok:
        raise SystemExit(1)


def cmd_restore(args: argparse.Namespace) -> None:
    from produceros.services.backup import restore_backup

    if not args.yes:
        print("Refusing to restore without --yes -- this replaces your live database.")
        print(f"Run 'produceros restore-dry-run \"{args.backup_path}\"' first to preview it.")
        raise SystemExit(1)

    settings = get_settings()
    restored_path = restore_backup(settings, args.backup_path, confirmed=True)
    print(f"Restored from '{args.backup_path}'. Live database is now: {restored_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="produceros", description="ProducerOS command-line interface.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the ProducerOS web application.")
    run_parser.add_argument("--mode", choices=["desktop", "lan"], default=None)
    run_parser.add_argument("--port", type=int, default=None)
    run_parser.add_argument("--no-browser", action="store_true")
    run_parser.set_defaults(func=cmd_run)

    db_upgrade = subparsers.add_parser("db-upgrade", help="Apply database migrations.")
    db_upgrade.set_defaults(func=cmd_db_upgrade)

    db_current = subparsers.add_parser("db-current", help="Show current migration revision.")
    db_current.set_defaults(func=cmd_db_current)

    demo_load = subparsers.add_parser("demo-load", help="Load the synthetic demo catalog.")
    demo_load.set_defaults(func=cmd_demo_load)

    demo_clean = subparsers.add_parser("demo-clean", help="Remove demo-tagged data.")
    demo_clean.set_defaults(func=cmd_demo_clean)

    backup_create = subparsers.add_parser("backup-create", help="Create a database backup now.")
    backup_create.set_defaults(func=cmd_backup_create)

    restore_dry_run = subparsers.add_parser(
        "restore-dry-run", help="Preview a backup file (integrity check, table counts) before restoring it."
    )
    restore_dry_run.add_argument("backup_path")
    restore_dry_run.set_defaults(func=cmd_restore_dry_run)

    restore = subparsers.add_parser(
        "restore", help="Restore the live database from a backup file. Destructive; requires --yes."
    )
    restore.add_argument("backup_path")
    restore.add_argument("--yes", action="store_true", help="Confirm the destructive restore.")
    restore.set_defaults(func=cmd_restore)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
