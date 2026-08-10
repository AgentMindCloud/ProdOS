# Sending ProducerOS to someone else

This is the "I want my friend to just use it" guide. It's for **you**
(the person who owns the repo), not for them -- they get
[`START-HERE.txt`](../START-HERE.txt), which is written in plain language
with no jargon.

## The important thing to know first

**The installer is not in the repository, and it can't be.**

`ProducerOS-Setup-X.Y.Z.exe` is *built* from the source code, on Windows,
by GitHub Actions. It isn't a file that lives in the repo. So:

- Downloading the repo as a ZIP ("Code -> Download ZIP") gives you the
  **source code** -- about 200 Python files, no installer. Sending that
  to a non-technical person is not useful: there's nothing in it they can
  double-click.
- The built installer lives on the **Releases** page instead, which is
  exactly what that page is for.

Good news: the Releases route is *simpler* than the ZIP route for both of
you. It's one file instead of a whole source tree.

> Why not commit the .exe into the repo anyway? It's ~40 MB per release,
> and git keeps every version forever -- ten releases would add ~400 MB
> that everyone re-downloads on every clone, permanently. Releases exist
> precisely so binaries don't have to live in git history.

## Option 1: send him a link (easiest)

Send him this URL:

    https://github.com/AgentMindCloud/ProdOS/releases

The repository is **public**, so he does **not** need a GitHub account,
does not need to log in, and does not need to be added to anything. He
clicks the `ProducerOS-Setup-....exe` file under the newest release and
it downloads.

Then send him `START-HERE.txt` (or just paste its contents into a
message) so he knows what to do with it.

## Option 2: send him the file directly (WhatsApp, email, USB, Drive)

If he shouldn't have to visit GitHub at all:

1. Go to <https://github.com/AgentMindCloud/ProdOS/releases>
2. Download `ProducerOS-Setup-X.Y.Z.exe` yourself (~40 MB).
3. Put that file and `START-HERE.txt` together in one folder.
4. Zip the folder and send it however you like.

That gives him a two-file package: the thing to double-click, and the
instructions. Nothing else.

Note that email providers usually block `.exe` attachments -- use
WhatsApp/Drive/Dropbox/WeTransfer/USB, or zip it first.

## Telling him about updates

When you release a new version, he does the same thing again: download
the new `ProducerOS-Setup-....exe`, double-click, click through. It
upgrades in place -- same desktop icon, same data, no uninstall needed.

One thing worth telling him: **have him close ProducerOS first** via
Settings -> Close ProducerOS. Closing the browser tab doesn't stop it, and
the installer has to replace files the running app is holding. (If he
forgets, the installer closes it for him -- this just avoids a confusing
prompt.)

## How a new release actually gets made

You don't build anything by hand. Pushing a version tag does it all:

```bash
git tag v0.1.1
git push origin v0.1.1
```

That triggers `.github/workflows/release.yml`, which runs the full test
suite, builds the Windows installer on a real Windows machine, and
publishes it to the Releases page with a checksum and an SBOM. It takes
roughly 10-15 minutes, after which the new `.exe` is on the Releases page
ready to share.

If you'd rather build one locally on your own Windows PC, see
`docs/INSTALL_WINDOWS.md` ("For developers: building from source") --
that needs Python and Inno Setup installed.

## First-time setup on his machine

Covered in `START-HERE.txt`, but the two things most likely to worry him:

- **The SmartScreen warning** ("Windows protected your PC") is expected.
  It appears because the installer isn't signed with a paid code-signing
  certificate, not because anything is wrong. "More info" -> "Run anyway".
- **It opens in a browser.** That's just how ProducerOS draws its screen.
  It's still running entirely on his own PC and still works with no
  internet.
