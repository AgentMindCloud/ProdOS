# Sending ProducerOS to someone else

This is the "I want my friend to just use it" guide. It's for **you**
(the person who owns the repo), not for them -- they get
[`START-HERE.txt`](../START-HERE.txt), which is written in plain language
with no jargon.

## The important thing to know first

**The built installer is committed into this repo, in `installer/`.**

That is deliberate and slightly unusual. Normally
`ProducerOS-Setup-X.Y.Z.exe` would live only on the Releases page, and a
repo ZIP would contain source code with nothing runnable in it. Here the
current installer is committed so that "Code -> Download ZIP" gives you a
package you can hand straight to a non-technical person:

```
ProdOS-main.zip
  START-HERE.txt                          <- plain-language instructions
  installer/ProducerOS-Setup-0.1.0.exe    <- the thing he double-clicks
  ...everything else is source code he can ignore
```

The cost of doing it this way, for the record: ~23 MB per release stays in
git history forever. Keep only the newest installer in `installer/`
(replace, don't accumulate) and that stays manageable for a project this
size. See [`../installer/README.md`](../installer/README.md).

The installer is *also* still published on the
[Releases page](https://github.com/AgentMindCloud/ProdOS/releases), which
is the smaller, faster download if he's willing to click a link.

## Option 0: send him the repo ZIP (what you asked for)

1. Go to <https://github.com/AgentMindCloud/ProdOS>
2. Green **Code** button -> **Download ZIP**
3. Send him that ZIP however you like (WhatsApp, Drive, WeTransfer, USB).

Tell him: *unzip it, open the `installer` folder, double-click the .exe,
and read `START-HERE.txt` if anything is confusing.*

This is the heaviest option (the ZIP carries the source tree as well as
the installer, so ~30 MB instead of ~23 MB) but it needs no explaining and
no GitHub visit at all.

## Option 1: send him a link (smallest download)

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

1. Take `installer/ProducerOS-Setup-X.Y.Z.exe` from your own clone (or
   download it from <https://github.com/AgentMindCloud/ProdOS/releases>).
2. Put that file and `START-HERE.txt` together in one folder.
3. Zip the folder and send it however you like.

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

One extra step if you want the repo-ZIP route to keep working: after the
release finishes, swap the new `.exe` into `installer/`. Full steps are in
[`BUILDING.md`](BUILDING.md) under "Refreshing the committed installer".

If you'd rather build one locally on your own Windows PC, that's also in
[`BUILDING.md`](BUILDING.md) -- it needs Python and Inno Setup installed.

## First-time setup on his machine

Covered in `START-HERE.txt`, but the two things most likely to worry him:

- **The SmartScreen warning** ("Windows protected your PC") is expected.
  It appears because the installer isn't signed with a paid code-signing
  certificate, not because anything is wrong. "More info" -> "Run anyway".
- **It opens in a browser.** That's just how ProducerOS draws its screen.
  It's still running entirely on his own PC and still works with no
  internet.
