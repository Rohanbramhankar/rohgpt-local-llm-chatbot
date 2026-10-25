#define AppName "RohGPT"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{8E8F6E6B-E5A4-4D29-A2D6-7476A7231881}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Rohan Bramhankar
DefaultDirName={localappdata}\Programs\RohGPT
DefaultGroupName=RohGPT
OutputDir=dist
OutputBaseFilename=RohGPT-Setup-Windows-x64
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\RohGPT.exe
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\RohGPT.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; DestName: "RohGPT-README.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\RohGPT"; Filename: "{app}\RohGPT.exe"
Name: "{autodesktop}\RohGPT"; Filename: "{app}\RohGPT.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RohGPT.exe"; Description: "Launch RohGPT"; Flags: postinstall nowait skipifsilent
