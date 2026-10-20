# Build the UWP shell (.appx) on Windows — dev-mode Xbox deployment

The MSIX/appx is Windows-only (UAP toolchain). Build it on a Windows box with
Visual Studio 2022 + the **Universal Windows Platform** workload (this installs
the Windows 10 SDK 10.0.19041 reference and the UAP targets). Then deploy the
resulting `.appx` to the Xbox over Device Portal (`/api/app/install`, auth `M:M`).

## Prerequisites (VS Installer → Workloads)
- [x] **Universal Windows Platform** (includes Windows 10 SDK 10.0.19041)
- [x] .NET desktop development
- [x] (optional) Visual Studio C++ Build Tools (for native toolchain / .NET Native)

## Build steps (run from an x86 "Developer Command Prompt for VS")

```bat
git clone https://github.com/AmadNOM2D/MadManagerXbox.git
cd MadManagerXbox

:: Stage the WebView UI + brain endpoint into the UWP project
copy /Y web\index.html        uwp\index.html
echo {"apiBase":"ws://__MAC_LAN_IP__:8765"} > uwp\config.json

:: One-shot build -> unsigned SideloadOnly appx (dev-mode Xbox accepts this)
msbuild "uwp\XboxAgent.csproj" ^
  /p:Configuration=Release ^
  /p:Platform=x86 ^
  /p:GenerateAppxPackageOnBuild=true ^
  /p:UapAppxPackageBuildMode=SideloadOnly ^
  /p:AppxBundle=Never ^
  /p:AppxPackageSigningEnabled=false

:: Package lands here:
::   uwp\AppPackages\MadManagerXbox_1.0.0.0_Test\MadManagerXbox_1.0.0.0_x86_Test.appx
```

`__MAC_LAN_IP__` = the Mac that hosts the agent brain. In this project: `192.168.12.242`
(verified via `ipconfig getifaddr en1` on the Mac; the Xbox at `192.168.12.131`
reaches it on the same LAN, and `/health` returns `{"status":"ok",...}`).

## Deploy (Mac side) — already prepared
`~/xbox-agent/deploy_to_xbox.sh /path/to/MadManagerXbox_1.0.0.0_x86_Test.appx`
Posts the package to the Xbox Device Portal at `https://192.168.12.131:11443/api/app/install`
(auth `M:M`, verified live), polls install status, and reports. Hand me the `.appx`
(via UTM shared folder → `~/Desktop`, or share the VM's IP) and I'll run it + confirm.
