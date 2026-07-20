; Inno Setup script for ProducerOS.
;
; Produces a single ProducerOS-Setup-<version>.exe that a non-technical
; user downloads from GitHub Releases and double-clicks: it installs
; per-user (no admin/UAC prompt, like VS Code or Discord), creates a
; Start Menu entry and an optional desktop icon, both pointing at
; ProducerOS.exe, and registers a normal uninstaller in
; "Apps & features". Re-running a newer version's installer upgrades an
; existing install in place -- same shortcuts, same AppId, and (because
; the install directory only ever holds the bundled app, never user
; data) nothing the user created is touched.
;
; Build with:  scripts\build_installer.ps1  (wraps PyInstaller + this)
; or directly: ISCC packaging\inno\producer-os.iss /DMyAppVersion=1.2.3
;
; See docs/adr/0006-inno-setup-installer.md for why Inno Setup (over
; WiX/MSI or a plain zip) and why a per-user, no-admin install.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#define MyAppName "ProducerOS"
#define MyAppPublisher "ProducerOS Contributors"
#define MyAppURL "https://github.com/AgentMindCloud/ProdOS"
#define MyAppExeName "ProducerOS.exe"
#define RepoRoot "..\.."
#define DistDir RepoRoot + "\dist\ProducerOS"
#define IconFile "..\pyinstaller\app-icon.ico"

[Setup]
; This GUID is ProducerOS's permanent identity for Windows' installer
; system -- it is what makes "run a newer Setup.exe" register as an
; in-place upgrade instead of a second, separate install. Never change
; it, ever, across any future version.
AppId={{30410FF3-33D3-4734-86A5-23F7A36CB46E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user install: no admin rights required, no UAC prompt. This is the
; single most important thing for a non-technical friend to be able to
; install ProducerOS themselves without needing to be a Windows admin or
; click through a scary "allow this app to make changes?" dialog.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#RepoRoot}\installer-output
OutputBaseFilename=ProducerOS-Setup-{#MyAppVersion}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
LicenseFile={#RepoRoot}\LICENSE
; ProducerOS's own data (database, logs, backups, secret key) lives at
; %LOCALAPPDATA%\ProducerOS -- a different path from the install
; directory above (%LOCALAPPDATA%\Programs\ProducerOS) -- so upgrading
; or uninstalling the app here never touches it. See [Code] below for a
; post-uninstall reminder of that.
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: checkedonce

[InstallDelete]
; Wipe the previous version's bundled runtime/dependencies before copying
; the new ones in, so an upgrade never leaves orphaned files from a build
; whose dependency set changed. Safe: {app} only ever holds the bundled
; app itself, never user data.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // A friendly, explicit reassurance -- non-technical users uninstalling
  // an app often worry their data went with it. It didn't: the data
  // directory is a separate folder from the install directory and was
  // never touched by this uninstaller.
  if CurUninstallStep = usPostUninstall then
    MsgBox(
      'ProducerOS has been removed.' + #13#10 + #13#10 +
      'Your projects, releases, and settings were kept and were not deleted. ' +
      'They are stored separately at:' + #13#10 +
      ExpandConstant('{localappdata}') + '\ProducerOS' + #13#10 + #13#10 +
      'If you want to remove that data too, delete that folder yourself.',
      mbInformation, MB_OK
    );
end;
