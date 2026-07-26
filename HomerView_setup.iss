; HomerView_setup.iss
; Compile with Inno Setup 6.
; Source root and installation destination: C:\HomerView

#define AppName "HomerView"
#define AppVersion "1.0.4"
#define AppPublisher "Jamal Mazrui"
#define AddonFile "HomerView-1.0.4.nvda-addon"

[Setup]
AppId={{E728BC1D-448B-4D56-A549-4C5603A3A9B5}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/JamalMazrui/HomerView
DefaultDirName={autopf}\HomerView
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=C:\HomerView\dist
OutputBaseFilename=HomerView_setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=C:\HomerView\installer\license.txt
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=HomerView installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
ChangesAssociations=no
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "installaddon"; Description: "Open the HomerView add-on package in NVDA after installation"; GroupDescription: "NVDA integration:"; Flags: checkedonce

[Dirs]
; Grant the Users group modify rights on the installation folder so that the
; add-on can write HomerView.log there. Without this, a standard user cannot
; write to a folder created by an administrator, and the log falls back to the
; local application data folder. Remove this line if a program folder writable
; by ordinary users is not acceptable in your environment.
Name: "{app}"; Permissions: users-modify

[Files]
; Optional bundled converters. Place 2htm.exe and pandoc.exe beside this
; script before compiling to include them; the "skipifsourcedoesntexist" flag
; means the installer still builds when they are absent.
;
; Program Files is the right home for a binary and the add-on folder is not.
; An add-on folder is replaced wholesale on every update, is included in every
; add-on backup, and lives under the roaming profile, which a growing number of
; managed environments refuse to execute anything from. None of that applies
; here, so bundling in the installation folder is sound where bundling in the
; add-on would not be.
Source: "C:\HomerView\2htm.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\pandoc.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Build the add-on with buildAddon.cmd before compiling this installer.
Source: "C:\HomerView\build\{#AddonFile}"; DestDir: "{app}\build"; Flags: ignoreversion
Source: "C:\HomerView\addon\*"; DestDir: "{app}\addon"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\HomerView\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\HomerView\installer\*"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "C:\HomerView\buildAddon.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\buildAddon.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\clean.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\createHomerViewRepo.cmd"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\createHomerViewRepo.ps1"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\.gitignore"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\.gitattributes"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\HomerView_setup.iss"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\LICENSE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Install the HomerView NVDA add-on"; Filename: "{app}\build\{#AddonFile}"; WorkingDir: "{app}\build"; Comment: "Open the HomerView add-on package in NVDA"
Name: "{group}\HomerView user guide"; Filename: "{app}\docs\HomerView_User_Guide.md"; WorkingDir: "{app}\docs"
Name: "{group}\HomerView design notes"; Filename: "{app}\docs\HomerView_Design_Notes.md"; WorkingDir: "{app}\docs"
Name: "{group}\Uninstall HomerView"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\build\{#AddonFile}"; Description: "Open the HomerView NVDA add-on package"; Flags: postinstall shellexec skipifsilent; Tasks: installaddon

[UninstallDelete]
Type: files; Name: "{app}\HomerView.log"
Type: files; Name: "{app}\HomerView.previous.log"
Type: files; Name: "{app}\buildAddon.log"
Type: files; Name: "{app}\Axe.json"
Type: files; Name: "{app}\Ace.json"
Type: files; Name: "{app}\HomerView.db"
Type: files; Name: "{app}\HomerView.jsonl"
Type: files; Name: "{app}\Start.html"
Type: filesandordirs; Name: "{app}\build"
Type: filesandordirs; Name: "{app}\dist"

[Code]
{ The browser profile lives under the user's local application data folder,     }
{ never under the installation folder, because this installer requires          }
{ administrator rights and a standard user could not then write to the profile. }

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
