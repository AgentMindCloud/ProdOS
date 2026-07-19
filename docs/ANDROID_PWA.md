# Android / PWA Access

ProducerOS's dashboard is a responsive web app: usable from any browser on
your Android phone or tablet over your home network, and installable as a
standalone PWA (Progressive Web App) so it behaves like a native app icon
with no browser chrome. This is entirely local -- your phone talks
directly to the ProducerOS instance running on your Windows machine over
your own Wi-Fi, never through the internet.

## 1. Start LAN mode on Windows

```powershell
.\scripts\run_lan.ps1
```

This binds ProducerOS to your machine's private LAN address (e.g.
`192.168.1.42`) instead of `127.0.0.1`, so other devices on the same
network can reach it. The console prints the address it bound to. **Never
forward this port through your router** -- it's for your home network
only (see `docs/SECURITY_MODEL.md`).

## 2. Pair your phone

1. On the Windows dashboard, connected as the admin, go to **Settings ->
   LAN mode & devices**.
2. Click **Generate pairing code**. You'll see a QR code and an 8-character
   code (letters/digits only, no ambiguous `0`/`O`/`1`/`I`), valid for 10
   minutes and single-use.
3. On your phone, make sure it's on the **same Wi-Fi network** as the
   Windows machine.
4. Either scan the QR code with your phone's camera, or open a browser on
   the phone and go to `http://<the-LAN-address>:8420/lan/pair/<device-id>`
   and type in the code manually.
5. Submit the code. Your phone is now paired -- it gets its own signed
   session cookie tied specifically to that device (not your admin
   password), which you can revoke at any time from the same Settings
   page without affecting your desktop session.

If you enter the code wrong repeatedly, pairing is rate-limited (5
attempts/minute by default) -- wait a minute and try again.

## 3. Install as a PWA (optional but recommended)

Once paired and viewing the dashboard in your phone's browser:

- **Chrome/Edge on Android**: tap the browser menu -> **Add to Home
  screen** (or you may see an automatic "Install app" prompt/banner).
- The app installs with the ProducerOS icon, name, and dark theme
  (`manifest.webmanifest`), opens in standalone mode (no address bar),
  and works in either orientation.

## 4. What works offline vs. online

ProducerOS is **not** a fully offline-capable app -- it needs to reach
your Windows machine over the LAN for every real action (creating a
project, registering an asset, etc.). The installed PWA's service worker
only caches the static "offline app shell" (`templates/offline.html`) so
that if your phone briefly loses the LAN connection, you see a clear
"you're offline" page with your last-cached dashboard summary instead of
a browser error page -- it does not let you keep working disconnected.

## 5. Layout on mobile

Below a 768px viewport width, the desktop sidebar is replaced by a bottom
tab bar (Home / Projects / Releases / Calendar / More), touch targets are
44px+, tables become stacked cards, and filters move into a slide-out
drawer. A phone in **landscape** whose width crosses 768px (common on
modern phones, e.g. a Pixel 7 at 915px landscape) intentionally gets the
roomier desktop sidebar layout instead -- the breakpoint is width-based,
not orientation-based. This is exercised for real (not just assumed) in
`tests/e2e/test_mobile_viewport.py`, which drives an actual Chromium
browser at phone-sized viewports in both portrait and landscape.

## 6. Revoking a device

Settings -> LAN mode & devices -> **Revoke** next to the device. Effective
immediately on that device's very next request (no need to wait for a
token to expire) -- see `docs/SECURITY_MODEL.md` for why.

## Troubleshooting

- **Phone can't reach the address**: confirm both devices are on the same
  Wi-Fi network (not phone data, not a guest network isolated from the
  main LAN), and that Windows Firewall isn't blocking the port -- you may
  need to allow `ProducerOS.exe` through the firewall on first LAN-mode
  launch.
- **Pairing code expired**: codes are single-use and time-limited; just
  generate a new one.
- **Lost your phone / it was paired by mistake**: revoke it from
  Settings -- see above.
