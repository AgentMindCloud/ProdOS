# PyInstaller spec for ProducerOS.
#
# Build with:  pyinstaller packaging/pyinstaller/produceros.spec --noconfirm
# (see scripts/build_windows.ps1 for the Windows-side wrapper, and
# scripts/build_installer.ps1 for the full installer .exe build).
#
# Bundles the application package, its Jinja templates and static assets,
# the Alembic migration scripts, and alembic.ini, so the frozen build can
# migrate and serve itself with no external Python or `alembic` CLI on
# PATH -- see produceros.cli._alembic_config(), which falls back to
# looking for alembic.ini next to the executable when running frozen.
#
# Built windowed (console=False): double-clicking the desktop icon should
# feel like launching a normal app, not a terminal program. Startup
# failures still surface via a Windows message box (launcher.py), and
# _fix_windowed_stdio() in launcher.py prevents the classic
# "sys.stdout is None in a windowed build" crash. Everything that would
# have gone to a console is still captured in the on-disk log file
# regardless (see logging_config.py).

import os

block_cipher = None

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
REPO_ROOT = os.path.abspath(os.path.join(SPEC_DIR, "..", ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
ICON_PATH = os.path.join(SPEC_DIR, "app-icon.ico")

datas = [
    (os.path.join(SRC_DIR, "produceros", "web", "templates"), os.path.join("produceros", "web", "templates")),
    (os.path.join(SRC_DIR, "produceros", "web", "static"), os.path.join("produceros", "web", "static")),
    (os.path.join(REPO_ROOT, "migrations"), "migrations"),
    (os.path.join(REPO_ROOT, "alembic.ini"), "."),
]

hiddenimports = [
    "produceros.web.routes.analytics",
    "produceros.web.routes.auth",
    "produceros.web.routes.backup",
    "produceros.web.routes.calendar",
    "produceros.web.routes.catalog",
    "produceros.web.routes.dashboard",
    "produceros.web.routes.delivery",
    "produceros.web.routes.lan",
    "produceros.web.routes.marketing",
    "produceros.web.routes.pwa",
    "produceros.web.routes.releases",
    "produceros.web.routes.scanner",
    "produceros.web.routes.search",
    "produceros.web.routes.settings",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "alembic",
    "mcp.server.fastmcp",
]

a = Analysis(
    [os.path.join(SPEC_DIR, "launcher.py")],
    pathex=[SRC_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ProducerOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=ICON_PATH,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ProducerOS",
)
