# Installing ProducerOS on Windows

## The easy way (this is what most people want)

1. Go to the repository's [Releases](../../releases) page.
2. Download **`ProducerOS-Setup-X.Y.Z.exe`** (the top file under the
   newest release -- not the "portable" zip).
3. Double-click it.
   - Windows may show a SmartScreen notice ("Windows protected your PC")
     the first time, since the installer isn't yet signed with a paid
     code-signing certificate. Click **More info -> Run anyway**. This is
     normal for a small open-source tool and only appears once.
   - No admin password or "allow this app to make changes?" prompt --
     ProducerOS installs just for your account, the same way apps like
     VS Code or Discord do.
4. Click through the installer (the defaults are fine). Leave
   **"Create a desktop icon"** checked.
5. When it finishes, click **Launch ProducerOS now** (or just double-click
   the new **ProducerOS** icon on your desktop).
6. Your browser opens automatically to the setup page. Create your admin
   account (a display name, a username, and a password) and you're in.

That desktop icon (also in your Start Menu) is what you use to open
ProducerOS from now on -- there's no separate "server" to start, no
terminal, no browser bookmark to remember. Double-click the icon, wait a
few seconds, your browser opens to the dashboard.

Your data (database, projects, logs, backups, generated secret key) lives
at `%LOCALAPPDATA%\ProducerOS\` -- a completely separate location from
where the app itself is installed, so it's never touched by installing,
updating, or uninstalling.

## Updating to a new version

When a new version comes out:

1. Download the new `ProducerOS-Setup-X.Y.Z.exe` from Releases, same as
   before.
2. Close ProducerOS if it's running (close the browser tab is enough for
   the page; if you want to be thorough, right-click the ProducerOS
   window in your taskbar and close it, or just restart your PC first).
3. Double-click the new installer and click through it, same as the first
   time.

That's it -- it upgrades your existing install in place. Same desktop
icon, same Start Menu entry, same data. You do not need to uninstall the
old version first, and nothing you've entered into ProducerOS is
affected.

Database migrations (if any) run automatically the next time you open the
app -- see `docs/BACKUP_RESTORE.md` for making a backup first if you want
extra peace of mind before a big update.

## Uninstalling

Windows Settings -> **Apps** -> find **ProducerOS** -> **Uninstall**. (Or
the classic Control Panel -> Programs and Features.) This removes the
installed app only -- when it finishes, a message tells you your data at
`%LOCALAPPDATA%\ProducerOS\` was kept. Delete that folder yourself if you
also want to remove your data (back it up first via
`docs/BACKUP_RESTORE.md` if there's any chance you'll want it again).

## Running modes

- **Desktop mode** (default): binds to `127.0.0.1` only, nothing else on
  your network can reach it. This is what the desktop icon uses.
- **LAN mode**: binds to your machine's private network address so a
  paired Android phone can connect. See `docs/ANDROID_PWA.md` for the
  walkthrough -- it's a command-line option (`ProducerOS.exe run --mode lan`),
  a bit more involved than the default desktop icon, aimed at whoever set
  the app up rather than day-to-day use.

## Troubleshooting

See `docs/TROUBLESHOOTING.md`. Short version: a startup failure shows a
Windows message box with the error, and a full log is always at
`%LOCALAPPDATA%\ProducerOS\logs\produceros.log` even though the app
itself no longer shows a console window while running.

---

## For developers: building from source

Requires [Python 3.12](https://python.org) and [git](https://git-scm.com/)
on PATH.

```powershell
git clone https://github.com/AgentMindCloud/ProdOS.git
cd ProdOS
.\scripts\setup_windows.ps1      # creates .venv, installs ProducerOS + dev deps
.\scripts\run_tests.ps1          # optional: confirm everything passes on your machine
.\scripts\run_desktop.ps1        # run it directly from source, no installer needed
```

To build the same installer described above (needs
[Inno Setup](https://jrsoftware.org/isdl.php) in addition to the Python
setup -- `windows-latest` GitHub Actions runners already have it, so CI
needs no extra step):

```powershell
.\scripts\build_installer.ps1
```

This produces `installer-output\ProducerOS-Setup-<version>.exe` -- the
exact file described above, built locally. `scripts\build_windows.ps1`
alone (no Inno Setup needed) produces just the raw
`dist\ProducerOS\ProducerOS.exe` + `_internal\` bundle as a portable,
installer-free alternative -- see `packaging/README.md` for what's
bundled and [ADR 0006](adr/0006-inno-setup-installer.md) for why both
exist and how they differ.
