"""Windows entry point for the frozen ProducerOS executable.

PyInstaller's built .exe calls this module directly (see produceros.spec).
Startup is wrapped in a broad try/except so a failure surfaces as a visible
message box instead of the process silently vanishing -- the classic
"double-clicked the .exe and nothing happened" support dead end for a
non-technical producer with no terminal open.
"""

from __future__ import annotations

import sys
import traceback


def _show_startup_error(details: str) -> None:
    message = (
        "ProducerOS failed to start.\n\n"
        f"{details}\n\n"
        "A full log is written to %LOCALAPPDATA%\\ProducerOS\\logs\\produceros.log"
    )
    if sys.platform == "win32":
        try:
            import ctypes

            MB_ICONERROR = 0x10
            ctypes.windll.user32.MessageBoxW(0, message, "ProducerOS - Startup Error", MB_ICONERROR)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


def main() -> None:
    try:
        from produceros.cli import main as cli_main

        # Forward real argv (e.g. --mode lan, --port, --no-browser) so the
        # scripts that shell out to this exe with flags actually take
        # effect; default to a plain "run" only when none were given, since
        # double-clicking the .exe passes no arguments at all.
        cli_main(sys.argv[1:] or ["run"])
    except SystemExit:
        raise
    except Exception:
        _show_startup_error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
