; HomerView_setup.iss
; Compile with Inno Setup 6.
; Source root and installation destination: C:\HomerView

#define AppName "HomerView"
#define AppVersion "1.26.4"
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

; No Tasks section. The one optional step, installing the add-on into NVDA, is
; offered as a checkbox on the Finish page through the Run section below, which
; is one fewer wizard page than a task would need.

[Files]
; The add-on package, which is what the Run section hands to NVDA.
Source: "C:\HomerView\build\{#AddonFile}"; DestDir: "{app}\build"; Flags: ignoreversion

; Documentation, as Markdown and as a web page. The web page is what the
; Alternate Menu and the start page open, in the HomerView window.
Source: "C:\HomerView\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\README.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\HomerView.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\HomerView.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\History.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\History.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Developer.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Developer.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\LICENSE.md"; DestDir: "{app}"; DestName: "License.txt"; Flags: ignoreversion

; Source, so the installed copy can be read and rebuilt.
Source: "C:\HomerView\addon\*"; DestDir: "{app}\addon"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\HomerView\HomerView_setup.iss"; DestDir: "{app}"; Flags: ignoreversion

; Build and repository scripts.
Source: "C:\HomerView\buildAddon.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\buildAddon.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\buildAll.cmd"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\buildAll.ps1"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\clean.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\createHomerViewRepo.cmd"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\createHomerViewRepo.ps1"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\.gitignore"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\.gitattributes"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; The development plan, kept for its historical value.
Source: "C:\HomerView\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; The converters, if they are sitting beside this script when it is compiled.
; The installation folder is the first place HomerView looks for either.
Source: "C:\HomerView\2htm.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\pandoc.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; A Start Menu group is created only if the user asks for one, since
; DisableProgramGroupPage and AllowNoIcons are both yes.
Name: "{group}\HomerView quick start"; Filename: "{app}\README.htm"
Name: "{group}\HomerView user guide"; Filename: "{app}\HomerView.htm"
Name: "{group}\HomerView history of changes"; Filename: "{app}\History.htm"
Name: "{group}\HomerView developer notes"; Filename: "{app}\Developer.htm"
; A shortcut runs as whoever double-clicks it, so this one can point at the
; add-on file directly and let the file association do its work.
Name: "{group}\Install the HomerView add-on in NVDA"; Filename: "{app}\build\{#AddonFile}"; WorkingDir: "{app}\build"
Name: "{group}\Uninstall HomerView"; Filename: "{uninstallexe}"

[Run]
; Back to the shell, which is what worked, plus the one flag that was missing.
;
; The history is worth recording, because the second change here was a mistake
; and the first was incomplete.
;
; Originally this used shellexec on the add-on file, which asks Windows to open
; it with whatever is registered for the type. NVDA registers itself, so NVDA
; received it. That worked.
;
; A user then reported ShellExecuteEx failing with an access violation, and it
; was replaced with a direct call to nvda.exe. That was a speculative fix for a
; fault that could not be reproduced, and it broke the path that worked: an
; installer running as administrator starts a child process as administrator,
; and an elevated NVDA cannot join the ordinary one already running.
;
; The likely explanation of both reports is the same missing flag. Opening a
; file through the shell often reaches the running program in the user's own
; context, which is why it worked here, but it is not guaranteed to, which
; would explain a failure elsewhere. runasoriginaluser makes it certain by
; running as the account that started Setup rather than the elevated one.
;
; So this is the original mechanism with the flag it always needed. If it fails
; again, the answer is not another mechanism: it is installing from the file,
; which the finish page now explains in every case.
Filename: "{app}\build\{#AddonFile}"; Description: "Install the HomerView add-on in NVDA (recommended)"; Flags: postinstall shellexec skipifsilent runasoriginaluser nowait

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

{ ---------------------------------------------------------------------------
  Finding NVDA.

  This no longer launches anything. It answers one question: is NVDA installed
  on this machine at all. When it is not, the add-on cannot be handed to it by
  any means, and the finish page says so and gives the manual route rather than
  letting the attempt fail with a number.

  Four places are looked at, in the order most likely to be right.
  --------------------------------------------------------------------------- }

var
  gsNvdaPath: String;
  gbNvdaChecked: Boolean;

function FindNvda(): String;
var
  sPath: String;
begin
  Result := '';

  { Where NVDA's own uninstaller records the installation. }
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\NVDA',
      'UninstallString', sPath) then
  begin
    sPath := RemoveQuotes(sPath);
    sPath := ExtractFilePath(sPath) + 'nvda.exe';
    if FileExists(sPath) then
    begin
      Result := sPath;
      Exit;
    end;
  end;

  { The App Paths entry, which Windows keeps for programs that register one. }
  if RegQueryStringValue(HKLM,
      'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\nvda.exe', '', sPath) then
  begin
    sPath := RemoveQuotes(sPath);
    if FileExists(sPath) then
    begin
      Result := sPath;
      Exit;
    end;
  end;

  { The usual folders, for an installation that recorded neither. }
  sPath := ExpandConstant('{autopf}\NVDA\nvda.exe');
  if FileExists(sPath) then
  begin
    Result := sPath;
    Exit;
  end;
  sPath := ExpandConstant('{commonpf32}\NVDA\nvda.exe');
  if FileExists(sPath) then
    Result := sPath;
end;

{ Kept as the cache for HaveNvda below, which is now its only caller. }
function GetNvdaPath(Param: String): String;
begin
  if not gbNvdaChecked then
  begin
    gsNvdaPath := FindNvda();
    gbNvdaChecked := True;
    Log('HomerView: NVDA was ' + gsNvdaPath);
  end;
  Result := gsNvdaPath;
end;

function HaveNvda(): Boolean;
begin
  Result := GetNvdaPath('') <> '';
end;

{ If NVDA cannot be found, the checkbox on the last page will hand the file to
  the shell, which is what failed for one user. Saying so before that happens
  costs nothing and turns an access violation into an instruction. }
procedure CurPageChanged(iCurPageID: Integer);
var
  sBreak, sMessage: String;
begin
  if (iCurPageID = wpFinished) and (not HaveNvda()) then
  begin
    { Held in a variable rather than written inline. Two rules govern every
      line in this file, and both are enforced before Pascal is ever compiled.
      A line must not begin with a hash, which the preprocessor reads as one of
      its own directives; and a line must not begin with an opening bracket,
      which the section parser reads as a section header. Neither rule cares
      that the line sits inside a Pascal comment. Chr(13) and Chr(10) avoid the
      first, and starting every comment line with a word avoids the second. }
    sBreak := Chr(13) + Chr(10) + Chr(13) + Chr(10);
    sMessage := 'NVDA was not found on this computer.' + sBreak +
      'The HomerView files are installed, but the add-on still has to be given ' +
      'to NVDA before any of its commands will work.' + sBreak +
      'Install it from the file instead: open NVDA, choose Tools, then ' +
      'Add-on Store, then Install from external source, and pick this file:' +
      sBreak + ExpandConstant('{app}\build\{#AddonFile}') + sBreak +
      'If NVDA is not installed at all, it is free from www.nvaccess.org.';
    MsgBox(sMessage, mbInformation, MB_OK);
  end;
end;

{ The browser profile lives under the user's local application data folder,     }
{ never under the installation folder, because this installer requires          }
{ administrator rights and a standard user could not then write to the profile. }

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
