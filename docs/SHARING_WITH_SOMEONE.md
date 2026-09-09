# Sharing ProducerOS with a friend

Send **https://prodos.tech/**. It includes an interactive sample, the current
Windows preview download and setup instructions. The same reviewed package is
available on the [GitHub preview release](https://github.com/AgentMindCloud/ProdOS/releases/tag/preview-0.2.0).
Neither download requires a GitHub account.

## What your friend should do

1. Download `ProducerOS-0.2.0-Windows.zip`.
2. Choose **Extract All** and keep the whole extracted `ProducerOS` folder,
   including `_internal`.
3. Run `ProducerOS.exe`, create a local login and start with a test project.

Send [START-HERE.txt](../START-HERE.txt) if they want a short walkthrough.
The download includes Python. It is a portable preview, so it does not create
shortcuts or run an installer wizard. It is unsigned and has not been verified
on a clean recipient computer or with a very large library.

**Code → Download ZIP** on GitHub downloads source code and the legacy
`installer/ProducerOS-Setup-0.1.0.exe`; that installer has the previous UI.
Use the explicit 0.2.0 preview link for the current app.

## Why an email attachment can fail

Email services may reject executable programs, including programs inside ZIPs.
The current ZIP is about 28.2 MB. Sending the website or release link avoids
attachment restrictions and lets your friend share one stable address.
Changing the extension or putting the executable in another ZIP is not a
reliable distribution method.

## Existing installations and backups

Ask your friend to back up the app database and music separately before an
update. Quit the older app from Settings first; closing its browser tab does
not stop the local server. Do not overwrite music folders with the app files.
This preview has not been certified for clean-machine upgrades.

## Keep the connection simple

The website provides downloads, release notes, guidance and a feedback link.
The desktop app has no required background connection to it. Music files and
the local database stay on the producer's computer; website hosting does not
need space for each visitor's library. App backups do not contain the music.

New downloads and updates remain the user's choice. Submitting a GitHub issue
requires a GitHub account; ProducerOS never sends that feedback automatically.
