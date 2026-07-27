; HomerView_setup.iss
; Compile with Inno Setup 6.
; Source root and installation destination: C:\HomerView

#define AppName "HomerView"
#define AppVersion "1.24.0"
#define AppPublisher "Jamal Mazrui"
; A stable name on purpose. The version lives in the add-on's manifest, which is
; what NVDA reads, and in AppVersion above. Putting it in the file name as well
; meant this line had to be edited for every release, and forgetting would break
; the compile for a reason unrelated to the change.
#define AddonFile "HomerView.nvda-addon"

[Setup]
AppId={{E728BC1D-448B-4D56-A549-4C5603A3A9B5}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/JamalMazrui/HomerView
DefaultDirName={autopf}\HomerView
DefaultGroupName={#AppName}
; Prompts kept to the minimum, matching the pattern in the other Homer
; installers. The directory page stays, because a user who installs to a
; different drive should be able to say so. Everything else is suppressed:
; there is no Start Menu folder to choose, no separate licence page, no
; component or task selection, and no readme afterwards.
DisableProgramGroupPage=yes
DisableDirPage=no
DisableReadyPage=yes
DisableFinishedPage=no
AllowNoIcons=yes
; Deliberately no. Earlier versions installed to C:\HomerView, and with
; UsePreviousAppDir set to yes the installer keeps proposing that recorded path
; instead of the default below, so an upgrade never moves to Program Files. The
; directory page is still shown, so anyone who chose a different drive can
; choose it again; they just have to say so once more.
UsePreviousAppDir=no
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; tagRelease reads the version from this file's version resource and expects
; to find it in the repository root, so that is where it is written.
OutputDir=C:\HomerView
OutputBaseFilename=HomerView_setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; The licence is summarised on the welcome page rather than given a page of its
; own, which is one page fewer to pass through. The full text installs as
; License.txt beside the program.
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

[Messages]
WelcomeLabel2=This will install [name/ver], an NVDA add-on that drives Microsoft Edge through the Chrome DevTools Protocol.%n%nHomerView is free software under the GNU General Public License version 2. The full text installs as License.txt.%n%nAccepting the defaults throughout will install the add-on into NVDA as well as copying the program files. NVDA will ask you to confirm, and will need to restart afterwards.
FinishedLabel=Setup has installed [name/ver] on your computer.%n%nThe checked box below hands the add-on to NVDA, which will ask you to confirm it and then restart. Until that happens, HomerView is only a folder of files and none of its commands will work.%n%nAfter NVDA restarts, press NVDA+Alt+H to begin, or NVDA+Alt+F10 for a list of every command.

; No [Tasks] section. The one optional step, installing the add-on into NVDA,
; is offered as a checkbox on the Finish page through [Run] below, which is one
; fewer wizard page than a task would need.

; No [Dirs] section, and no loosened permissions.
;
; Earlier versions granted the Users group modify rights on the installation
; folder so that HomerView could write its log there. That was solving the
; wrong problem: a program folder should be written by the installer and read
; afterwards, and making it writable by every user is a privilege escalation
; surface offered in exchange for a convenience. The log and the history
; database now live in the user's local application data, where they belong,
; and the installation folder needs no special rights at all.

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
; The development plan is kept for its historical value.
Source: "C:\HomerView\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "C:\HomerView\installer\license.txt"; DestDir: "{app}"; DestName: "License.txt"; Flags: ignoreversion
Source: "C:\HomerView\buildAddon.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\buildAddon.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\clean.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\buildAll.cmd"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\buildAll.ps1"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\createHomerViewRepo.cmd"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\createHomerViewRepo.ps1"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\.gitignore"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\.gitattributes"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\HomerView_setup.iss"; DestDir: "{app}"; Flags: ignoreversion
; Every document ships as Markdown and as a web page. The web page is what the
; Alternate Menu and the start page open, in the HomerView window.
Source: "C:\HomerView\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\README.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\HomerView.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\HomerView.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\History.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\History.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Developer.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Developer.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\LICENSE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Install the HomerView NVDA add-on"; Filename: "{app}\build\{#AddonFile}"; WorkingDir: "{app}\build"; Comment: "Open the HomerView add-on package in NVDA"
Name: "{group}\HomerView quick start"; Filename: "{app}\README.htm"
Name: "{group}\HomerView user guide"; Filename: "{app}\HomerView.htm"
Name: "{group}\HomerView history of changes"; Filename: "{app}\History.htm"
Name: "{group}\HomerView developer notes"; Filename: "{app}\Developer.htm"
Name: "{group}\Uninstall HomerView"; Filename: "{uninstallexe}"

[Run]
; shellexec is required: a .nvda-addon file is not executable, so Windows has to
; hand it to whatever is registered for that extension, which is NVDA. Without
; the flag Inno Setup would try to run it as a program and fail.
; This is the step that matters, and it is checked by default on purpose. The
; program files alone do nothing: HomerView is an NVDA add-on, and until this
; runs, NVDA has not been given it. A user who presses Enter through the wizard
; to accept the defaults, which is the sensible way to install anything, must
; end up with a working installation rather than a folder of files.
;
; Version 1.5.1 had this unchecked, and a tester who accepted every default
; went on running an older add-on for a whole session without knowing it. That
; is the failure this comment exists to prevent recurring.
Filename: "{app}\build\{#AddonFile}"; Description: "Install the HomerView add-on in NVDA (recommended)"; Flags: postinstall shellexec skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\HomerView.log"
Type: files; Name: "{app}\HomerView.previous.log"
Type: files; Name: "{app}\buildAddon.log"
Type: files; Name: "{app}\Axe.json"
Type: files; Name: "{app}\Ace.json"
Type: files; Name: "{app}\HomerView.db"
Type: files; Name: "{app}\HomerView.jsonl"
Type: files; Name: "{app}\Start.htm"
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
