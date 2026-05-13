[Setup]
AppName=Focus Pet Pro
AppVersion=1.0
DefaultDirName={autopf}\Focus Pet Pro
DefaultGroupName=Focus Pet Pro
UninstallDisplayIcon={app}\FocusPetPro.exe
Compression=lzma2
SolidCompression=yes
OutputDir=Output
OutputBaseFilename=FocusPetPro_Setup
SetupIconFile=assets\icon.ico

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\FocusPetPro\FocusPetPro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\FocusPetPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Focus Pet Pro"; Filename: "{app}\FocusPetPro.exe"
Name: "{autodesktop}\Focus Pet Pro"; Filename: "{app}\FocusPetPro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FocusPetPro.exe"; Description: "Khởi động Focus Pet Pro ngay bây giờ"; Flags: nowait postinstall skipifsilent
