[Setup]
AppName=DIY Particle Detector
AppVersion=0.1.1
DefaultDirName={autopf}\DIY Particle Detector
OutputDir=..\dist
OutputBaseFilename=DIY-Particle-Detector-Setup
UninstallDisplayName=DIY Particle Detector

[Files]
Source: "..\dist\DIY-Particle-Detector\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\DIY Particle Detector"; Filename: "{app}\DIY-Particle-Detector.exe"
