; HomerView_setup.iss
; Compile with Inno Setup 6.
; Source root and installation destination: C:\HomerView

#define AppName "HomerView"
; THE VERSION COMES FROM ONE PLACE, and it is not this file.
;
; It used to be written here AND in the add-on manifest, and the two were kept
; level by hand. They stopped being level: the manifest said 1.48.3 while the
; documentation described 1.48.5, and tagRelease refused to publish because the
; installer it found on disk carried a version already released. Nothing was
; broken; the release simply did not happen, and the reason was two numbers that
; had to agree and no mechanism making them.
;
; manifest.ini is the source. buildHomerView reads it and writes version.txt
; beside this script, and this reads that. A build must therefore precede a
; compile, which was already true and is now enforced rather than remembered.
#if FileExists(SourcePath + "\version.txt")
#define FileHandle FileOpen(SourcePath + "\version.txt")
#define AppVersion Trim(FileRead(FileHandle))
#expr FileClose(FileHandle)
#else
#error version.txt is missing. Run buildHomerView before compiling this script.
#endif
#define AppPublisher "Jamal Mazrui"
; A stable name on purpose. The version lives in the add-on's manifest and
; reaches this script through version.txt. Putting it in the file name as well
; meant this line had to be edited for every release, and forgetting would break
; the compile for a reason unrelated to the change.
#define AddonFile "HomerView.nvda-addon"

[Setup]
AppId={{E728BC1D-448B-4D56-A549-4C5603A3A9B5}

; THE UNINSTALLER IS STATED, NOT ASSUMED.
;
; NVDA can remove an add-on from its own Add-on Store. JAWS has nothing of the
; kind: scripts compiled into a settings folder and keys written into a user's
; default.jkm stay there until something takes them out. So the uninstaller is
; the only way back, and it must be somewhere a person can find it.
;
; Inno does all four of these by default. They are written down anyway, because
; a default that nobody has stated is a default that a later edit can turn off
; without anyone noticing.
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallFilesDir={app}
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\HomerView.exe
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
; Hidden when a previous install of the same AppId is found, which is what the
; other Homer Tools do: a reinstall then asks nothing at all and goes where the
; last one went. A first install still chooses the folder. This used to be no,
; on the reasoning that the page was worth seeing because it says where the
; program is going. It says that on the finished page too, and a page that only
; ever needs Enter is a page that has stopped being read.
DisableDirPage=auto
DisableReadyPage=yes
DisableFinishedPage=no
AllowNoIcons=yes
; Remember where it went last time, and pre-fill the directory page with that
; rather than proposing the default again. Someone reinstalling presses Enter
; and it goes back where it was; someone who wants it elsewhere can still say
; so, because the page is shown either way.
;
; This was briefly set to no, to force upgrades off the old C:\HomerView path
; that early versions used. That path is behind us and the setting is back to
; matching the other Homer installers.
UsePreviousAppDir=yes
UsePreviousGroup=yes
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
Source: "C:\HomerView\ReadMe.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\ReadMe.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\HomerView.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\HomerView.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\History.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\History.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Announce.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Announce.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Hotkeys.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Hotkeys.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Developer.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Developer.htm"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\Hotkeys.inix"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\LICENSE.md"; DestDir: "{app}"; DestName: "License.txt"; Flags: ignoreversion

; Source, so the installed copy can be read and rebuilt.
Source: "C:\HomerView\addon\*"; DestDir: "{app}\addon"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\HomerView\HomerView_setup.iss"; DestDir: "{app}"; Flags: ignoreversion

; Build scripts only. The repository scripts, the clean script and the two Git
; configuration files belong to the development directory and have no meaning
; in an installation: nobody installs HomerView in order to create its GitHub
; repository, and a .gitignore beside the program is at best confusing.
Source: "C:\HomerView\buildHomerView.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\buildHomerView.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\cleanDir.cmd"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\cleanDir.ps1"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; The development plan, kept for its historical value.
Source: "C:\HomerView\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; The converters, if they are sitting beside this script when it is compiled.
; The installation folder is the first place HomerView looks for either.
Source: "C:\HomerView\2htm.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; pandoc is NOT packaged. It is about 220 megabytes, which GitHub refuses and
; which is a long download to impose on someone who may already have it or may
; never open an ebook. The Run section below offers to fetch it instead.
; The JAWS side. The bridge is the one piece JAWS scripting cannot supply for
; itself, and the scripts are copied into every JAWS version by the script
; below rather than by this section, because they must be compiled in place.
Source: "C:\HomerView\HomerView.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\HomerView.cs"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\jaws\*"; DestDir: "{app}\jaws"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\installJawsScripts.ps1"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "C:\HomerView\installJawsScripts.cmd"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Run by installJawsScripts.ps1, not by hand. It writes the MyExtensions file
; that makes JAWS load our scripts at all, and puts the keys into the user's own
; copy of default.jkm.
Source: "C:\HomerView\chainJawsScripts.ps1"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; One line, the version. Written by buildHomerView so the installed scripts and
; their log can say which build they came from without being told.
Source: "C:\HomerView\version.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

Source: "C:\HomerView\installPandoc.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\HomerView\installPandoc.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; A Start Menu group is created only if the user asks for one, since
; DisableProgramGroupPage and AllowNoIcons are both yes.
Name: "{group}\HomerView read me"; Filename: "{app}\ReadMe.htm"
Name: "{group}\HomerView app guide"; Filename: "{app}\HomerView.htm"
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

; Pandoc, fetched rather than packaged, for the same reason HomerScribe fetches
; Ollama: it is far too large to ship and not everybody needs it.
;
; Checked by default because the reader who needs it is the reader who cannot
; tell in advance that they do: they find out when an ebook will not open. The
; script notices a copy already on the machine and copies that instead of
; downloading, so ticking it when pandoc is present costs a second.
;
; runascurrentuser matters. winget installs per user, into the profile of
; whoever is signed in, and this installer is running elevated.
; The JAWS scripts, checked by default when JAWS is installed and absent
; entirely when it is not. A checkbox offering to install scripts for a screen
; reader the user does not have is a question with only one sensible answer,
; which is not worth asking.
;
; runasoriginaluser matters more here than anywhere. JAWS keeps its settings
; under the user's own roaming application data, and this installer runs
; elevated; without the flag the scripts would go into the administrator's
; profile and the user would see nothing at all.
; Run through the wrapper rather than PowerShell directly, so a refusal to run
; the script at all is still recorded. The log is one timestamped file in
; %LOCALAPPDATA%\HomerView\logs, and the window stays open until a key is
; pressed so nothing scrolls away unread.
;
; The version is handed over rather than looked up. Nothing that reaches the
; installation folder carries it, and a log that does not say which build wrote
; it has to be dated by guesswork.
; NO CONSOLE WINDOW, AND NO KEY TO PRESS.
;
; This used to leave a console open on "Press any key to close this window",
; on the reasoning that nothing should scroll away unread. But the person
; installing cannot read it either way: it is a wall of console output at the
; end of an installation, and it stops the installer dead until a key is
; pressed. Everything it said is in the log, and what MATTERS is now summarised
; in one message box at the end, which a screen reader reads properly.
;
; -bQuiet was already there for the silent case; runhidden keeps the window
; from appearing at all. waituntilterminated stays, so the summary can report
; what happened rather than guess.
Filename: "{app}\installJawsScripts.cmd"; \
  Parameters: "-sVersion {#AppVersion} -bQuiet"; \
  WorkingDir: "{app}"; \
  Description: "Install the HomerView scripts for JAWS (recommended)"; \
  Flags: postinstall skipifsilent runasoriginaluser waituntilterminated runhidden; \
  Check: HaveJaws

; THE SAME STEP AGAIN, FOR A SILENT INSTALLATION.
;
; Every postinstall entry carries skipifsilent, which is right for the two that
; need a person -- the add-on opens NVDA's own dialog, and pandoc is a 220 MB
; download nobody should be given without being asked. But it meant that
; /SILENT copied the files, reported success, and installed NO JAWS SCRIPTS AT
; ALL. An installer that succeeds without doing the thing is the same fault as
; a check that passes without checking.
;
; So this entry runs the JAWS step when, and only when, the wizard is silent.
; runhidden because there is no window worth showing, and -bQuiet so the
; wrapper does not stop at "press any key" that nobody is there to press.
Filename: "{app}\installJawsScripts.cmd"; \
  Parameters: "-sVersion {#AppVersion} -bQuiet"; \
  WorkingDir: "{app}"; \
  Flags: runhidden runasoriginaluser waituntilterminated; \
  Check: JawsAndSilent

Filename: "{cmd}"; \
  Parameters: "/c """"{app}\installPandoc.cmd"""""; \
  WorkingDir: "{app}"; \
  Description: "Install pandoc, for reading ebooks, Markdown and OpenDocument text (about 220 MB)"; \
  Flags: postinstall skipifsilent runascurrentuser; \
  Check: NeedPandoc

[UninstallRun]
; Take the JAWS scripts back out. Ours to remove, since we put them there, and
; leaving compiled scripts behind for a program that is gone would be untidy at
; best and confusing at worst.
;
; No runasoriginaluser here: that is a [Run] flag and [UninstallRun] does not
; accept it, which is what stopped this script compiling the first time. The
; uninstaller usually runs as the user who is removing the program, so the
; settings folder it finds is theirs.
; THE LOG GOES SOMEWHERE THAT SURVIVES THE UNINSTALL.
;
; HomerView normally logs into its own data folder, and [UninstallDelete] below
; deletes that folder a moment later -- so a removal that went wrong would erase
; the only record of how. The removal log goes to the temporary folder instead,
; where it outlives the program and can still be sent.
Filename: "{app}\installJawsScripts.cmd"; \
  Parameters: "-bUninstall -pathLogFile ""{%TEMP}\HomerViewUninstall.log"""; \
  WorkingDir: "{app}"; \
  Flags: runhidden waituntilterminated skipifdoesntexist; \
  RunOnceId: "RemoveJawsScripts"

; NO runasoriginaluser below. It is a [Run] flag and [UninstallRun] rejects it;
; the comment above records that this exact mistake stopped the script compiling
; once already, and I made it again while writing this entry.
;
; And the NVDA add-on, through NVDA's own mechanism rather than by deleting
; folders under it. NVDA keeps its own record of what is installed, and a
; directory removed behind its back leaves that record claiming an add-on that
; is not there. --remove-addon is how NVDA is told.
Filename: "{code:GetNvdaPath}"; \
  Parameters: "--remove-addon ""HomerView"""; \
  Flags: runhidden waituntilterminated skipifdoesntexist; \
  RunOnceId: "RemoveNvdaAddon"; \
  Check: HaveNvda

[UninstallDelete]
; EVERYTHING HOMERVIEW MADE, not only what it installed.
;
; The program folder is Inno's to clear. These are the places HomerView wrote to
; while it ran: its own data folder holds the log, the cached engines, the
; extracted pages and the whole Edge profile, and none of it means anything once
; the program is gone. Downloads are deliberately NOT touched -- reports and
; fetched files are the user's, and an uninstaller that deletes a person's
; Downloads folder has badly overstepped.
Type: filesandordirs; Name: "{localappdata}\HomerView"
Type: files; Name: "{app}\HomerView.log"
Type: files; Name: "{app}\installJawsScripts.result"
Type: files; Name: "{app}\HomerView.previous.log"
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

{ Whether JAWS is installed for this user.
  Its settings live under the user's roaming application data, one folder per
  version, and that folder is what JAWS actually loads scripts from. If it is
  not there, JAWS is not here, and the checkbox is not offered. }
{ ---------------------------------------------------------------------------
  Whether pandoc still needs fetching.

  The task that offers it was shown on every reinstall, whether or not pandoc
  was already sitting in the installation folder. The script it runs does check,
  and exits saying so, but by then a person has already been offered a two
  hundred megabyte download, ticked a box, watched a window open and closed it
  again. An offer that is always declined by the program is an offer that should
  not have been made.
  --------------------------------------------------------------------------- }

function NeedPandoc(): Boolean;
begin
  Result := not FileExists(ExpandConstant('{app}\pandoc.exe'));
end;

function HaveJaws(): Boolean;
var
  sPath: String;
  findRec: TFindRec;
begin
  Result := False;

  // A MACHINE-WIDE CHECK FIRST, AND THIS IS NOT BELT AND BRACES.
  //
  // The user application data constant resolves to the profile of whoever the
  // installer is RUNNING AS. When a standard user starts it and types an
  // administrator's password, that is a DIFFERENT ACCOUNT, whose profile has
  // no JAWS settings -- so JAWS went undetected, the checkbox was never
  // offered, no scripts were installed, and the key did nothing afterwards.
  // A tester lost an evening to exactly this. The program folder belongs to
  // the machine and cannot be fooled by elevation.
  //
  // WRITTEN WITH // RATHER THAN BRACES ON PURPOSE. A brace comment ends at the
  // FIRST closing brace, so naming a constant like the one above inside one
  // terminates the comment early and the rest of the sentence is compiled as
  // code. That is exactly what happened here: "Unknown identifier 'resolves'".
  if DirExists(ExpandConstant('{commonpf}\Freedom Scientific\JAWS'))
     or DirExists(ExpandConstant('{commonpf32}\Freedom Scientific\JAWS')) then
  begin
    Result := True;
    Log('HomerView: JAWS found in the program folder');
    Exit;
  end;

  sPath := ExpandConstant('{userappdata}\Freedom Scientific\JAWS');
  if not DirExists(sPath) then
    Exit;
  { A year folder, rather than merely the parent, because an uninstalled JAWS
    can leave the parent behind empty. }
  if FindFirst(sPath + '\*', findRec) then
  begin
    try
      repeat
        if (findRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
        begin
          if (findRec.Name <> '.') and (findRec.Name <> '..') then
          begin
            if DirExists(sPath + '\' + findRec.Name + '\Settings') then
            begin
              Result := True;
              Log('HomerView: JAWS ' + findRec.Name + ' found');
              Exit;
            end;
          end;
        end;
      until not FindNext(findRec);
    finally
      FindClose(findRec);
    end;
  end;
end;

// Both conditions in one identifier, because a Check clause names a function
// of ours rather than taking an expression. WizardSilent is built in and is
// true for /SILENT and /VERYSILENT alike.
function JawsAndSilent(): Boolean;
begin
  Result := HaveJaws and WizardSilent;
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

{ ---------------------------------------------------------------------------
  WHAT THE INSTALLER ACTUALLY DID.

  The JAWS step used to end at a console prompt: a wall of output and a key to
  press before Setup could finish. A sighted reader skims that; a screen reader
  user has to hunt through it, and it stops the installer dead either way.

  So the window is gone and this takes its place -- ONE message box, read
  properly by a screen reader, saying where things went, which optional steps
  ran, and how they turned out.

  EVERY LINE IS AN OBSERVED FACT, not a checkbox that was ticked. A ticked box
  says what was ASKED FOR; the folder on disk and the result file say what
  HAPPENED, and those differ often enough to matter -- most of all for the NVDA
  add-on, which silently does nothing when NVDA is not running.
  --------------------------------------------------------------------------- }

var
  bInstalled: Boolean;

procedure CurStepChanged(iCurStep: TSetupStep);
begin
  { DeinitializeSetup runs whenever Setup exits, INCLUDING WHEN THE USER
    CANCELS. Announcing "HomerView is installed" to somebody who has just
    backed out would be a plain lie, so the summary is shown only if the files
    were actually copied. }
  if iCurStep = ssPostInstall then
    bInstalled := True;
end;

function NvdaIsRunning(): Boolean;
var
  iResult: Integer;
begin
  Result := False;
  if Exec(ExpandConstant('{cmd}'),
          '/c tasklist /fi "imagename eq nvda.exe" | find /i "nvda.exe"',
          '', SW_HIDE, ewWaitUntilTerminated, iResult) then
    Result := (iResult = 0);
end;

function AddonIsInstalled(): Boolean;
var
  sAddons: String;
begin
  { NVDA copies an add-on in as <name>.pendingInstall until it restarts, so
    both spellings count as installed. }
  sAddons := ExpandConstant('{userappdata}\nvda\addons\');
  Result := DirExists(sAddons + 'homerView')
         or DirExists(sAddons + 'homerView.pendingInstall');
end;

function JawsResult(): Integer;
var
  sText: AnsiString;
  sValue: String;
begin
  { -1 means the step did not run at all. }
  Result := -1;
  if LoadStringFromFile(ExpandConstant('{app}\installJawsScripts.result'), sText) then
  begin
    { ASSIGNED, NOT CAST. LoadStringFromFile wants an AnsiString, and Pascal
      Script converts one to a String on assignment; writing String(sText) as a
      cast is not something it accepts. }
    sValue := Trim(sText);
    Result := StrToIntDef(sValue, 0);
  end;
end;

procedure DeinitializeSetup();
var
  sMessage: String;
  iJaws: Integer;
begin
  { Nothing to report if nothing was installed, and nobody to read it in a
    silent installation -- where a message box would sit there forever
    waiting for a click that a script cannot give. }
  if (not bInstalled) or WizardSilent then
    Exit;
  sMessage := 'HomerView is installed.' + #13#10 + #13#10
    + 'Program files:' + #13#10 + '  ' + ExpandConstant('{app}') + #13#10 + #13#10
    + 'Results' + #13#10;

  iJaws := JawsResult();
  if iJaws = 0 then
    sMessage := sMessage + '  JAWS scripts: installed.' + #13#10
  else if iJaws > 0 then
    sMessage := sMessage + '  JAWS scripts: FAILED. Send the logs named below.' + #13#10
  else
    { REPORTED EVEN WHEN JAWS WAS NEVER DETECTED, which is the case that cost a
      tester an evening: no result file AND no checkbox means the step was never
      offered, and a summary that stays silent about it looks like success. }
    sMessage := sMessage + '  JAWS scripts: NOT installed (the step did not run).' + #13#10;

  if AddonIsInstalled() then
    sMessage := sMessage + '  NVDA add-on: installed. Restart NVDA to use it.' + #13#10
  else if not NvdaIsRunning() then
    sMessage := sMessage + '  NVDA add-on: NOT installed, because NVDA was not running.' + #13#10
      + '    Start NVDA, then open:' + #13#10
      + '    ' + ExpandConstant('{app}\build\{#AddonFile}') + #13#10
  else
    sMessage := sMessage + '  NVDA add-on: not installed. Open the file in the program folder''s build folder.' + #13#10;

  if FileExists(ExpandConstant('{app}\pandoc.exe')) then
    sMessage := sMessage + '  pandoc: present. Ebooks and Markdown will open.' + #13#10
  else
    sMessage := sMessage + '  pandoc: not present. Ebooks and Markdown will not open until it is.' + #13#10;

  { THE LOGS, NAMED IN THE BOX SO THEY CAN BE ASKED FOR OVER THE PHONE.
    Copied to one fixed path each: Inno's own log otherwise sits in the
    temporary folder under a dated name nobody can dictate, and the JAWS log
    under a timestamped one among several. }
  ForceDirectories('C:\temp');
  // CopyFile, not FileCopy. The documented name is CopyFile(Existing, New,
  // FailIfExists) -- there is no FileCopy in Pascal Script at all, and the
  // compile aborted before it reached this line, so the wrong name would have
  // failed the NEXT build rather than this one.
  if CopyFile(ExpandConstant('{log}'), 'C:\temp\HomerView_setup.log', False) then
    sMessage := sMessage + #13#10 + 'If anything above went wrong, send:' + #13#10
      + '  C:\temp\HomerView_setup.log' + #13#10
  else
    sMessage := sMessage + #13#10 + 'If anything above went wrong, send:' + #13#10;
  if FileExists('C:\temp\HomerView_jaws.log') then
    sMessage := sMessage + '  C:\temp\HomerView_jaws.log' + #13#10;

  { LAST, BECAUSE IT IS THE ONE THING THEY NEED NEXT. }
  sMessage := sMessage + #13#10
    + 'To start HomerView, press Alt+Insert+H in JAWS, or Alt+NVDA+H in NVDA.';

  MsgBox(sMessage, mbInformation, MB_OK);
end;
