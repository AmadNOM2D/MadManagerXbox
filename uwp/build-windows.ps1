<#
.SYNOPSIS
  Build the UWP agent shell (.appx) on a Windows VM for dev-mode Xbox sideload.

.REQUIREMENTS
  Visual Studio 2022 + "Universal Windows Platform" workload
  (this installs the Windows 10 SDK 10.0.19041 reference + UAP targets).
  If missing: VS Installer -> Workloads -> "Universal Windows Platform".

.USAGE
  Open an "x86 Developer Command Prompt for VS", cd to THIS repo root, then:
    .\uwp\build-windows.ps1            # uses default Mac brain 192.168.12.242
    .\uwp\build-windows.ps1 -MacLanIp 10.0.0.55   # if your Mac IP differs
  Produces:  uwp\AppPackages\MadManagerXbox_1.0.0.0_Test\*.appx
#>
param([string]$MacLanIp = "192.168.12.242")

# Stage the WebView UI + brain endpoint into the UWP project
Copy-Item -Force web\index.html          uwp\index.html
"{" + '"' + "apiBase" + '"' + ":" + '"' +"ws://$MacLanIp:8765" + '"' +"}" |
  Set-Content -NoNewline -Encoding utf8 uwp\config.json
Write-Host "config.json -> $(Get-Content uwp\config.json)"

# One-shot unsigned SideloadOnly appx (dev-mode Xbox accepts it)
msbuild "uwp\XboxAgent.csproj" `
  /p:Configuration=Release `
  /p:Platform=x86 `
  /p:GenerateAppxPackageOnBuild=true `
  /p:UapAppxPackageBuildMode=SideloadOnly `
  /p:AppxBundle=Never `
  /p:AppxPackageSigningEnabled=false
if ($LASTEXITCODE -ne 0) { throw "msbuild failed (exit $LASTEXITCODE)" }

Write-Host "`n=== BUILD OK. Package(s): ==="
Get-ChildItem -Path uwp\AppPackages -Recurse -Filter *.appx | Select-Object -ExpandProperty FullName
