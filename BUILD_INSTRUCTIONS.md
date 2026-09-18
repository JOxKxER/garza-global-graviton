# Global Graviton Gauntlet (#GGG) — Desktop Build Instructions

Compile the production `index.html` into a native standalone binary
(`.exe` on Windows, `.app` / `.dmg` on macOS) via the Tauri v2 shell in
`src-tauri/`. The finished app is 100% offline-first: it pings the local
Ollama daemon on loopback before the window appears and shows a tactical-red
banner with the exact recovery commands if the daemon is down.

---

## 1. Prerequisites (one-time)

### Windows
```powershell
# 1. Rust toolchain (https://rustup.rs) — pick the MSVC stable toolchain when prompted
winget install Rustlang.Rustup

# 2. Microsoft C++ Build Tools — "Desktop development with C++" workload
winget install Microsoft.VisualStudio.2022.BuildTools

# 3. WebView2 Runtime — preinstalled on Windows 11 / most Windows 10; otherwise:
winget install Microsoft.EdgeWebView2Runtime

# 4. Tauri CLI
cargo install tauri-cli --version "^2.0" --locked
```

### macOS
```bash
# 1. Xcode Command Line Tools
xcode-select --install

# 2. Rust toolchain (https://rustup.rs)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 3. Tauri CLI
cargo install tauri-cli --version "^2.0" --locked
```

## 2. Prepare the runtime (both platforms)

The shell expects the Ollama daemon on `http://localhost:11434`:

```bash
ollama pull qwen2.5-coder:latest
ollama serve
```

Set `OLLAMA_ORIGINS="*"` (or add `http://tauri.localhost` on Windows /
`tauri://localhost` on macOS) so the webview origin is allowed:

```powershell
# Windows (new terminals / services pick it up after restart)
[Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "User")
```
```bash
# macOS / Linux
export OLLAMA_ORIGINS="*"
```

## 3. Optional: brand icons

The config ships with an empty `icon` array so it compiles out of the box.
To stamp the GGG mark onto the binaries, convert `logo.jpg` to a square
`logo.png` (1024×1024 recommended), then from `03_Source_Code/`:

```bash
cargo tauri icon ./logo.png
```

This fills `src-tauri/icons/` and updates `tauri.conf.json` automatically.

## 4. Run in development mode

```bash
cd 03_Source_Code
python -m http.server 8080   # serves index.html at the configured devUrl
cargo tauri dev
```

## 5. Compile native release binaries

```bash
cd 03_Source_Code
cargo tauri build
```

Artifacts land under `src-tauri/target/release/bundle/`:

| Platform | Output |
|----------|--------|
| Windows  | `nsis/Global Graviton Gauntlet_1.4.5_x64-setup.exe`, `msi/Global Graviton Gauntlet_1.4.5_x64_en-US.msi`, standalone `release/ggg-gauntlet.exe` |
| macOS    | `macos/Global Graviton Gauntlet.app`, `dmg/Global Graviton Gauntlet_1.4.5_aarch64.dmg` |

> macOS Gatekeeper: unsigned builds require right-click → Open on first
> launch, or an Apple Developer ID + `TAURI_SIGNING_PRIVATE_KEY` for
> notarized distribution.

## 6. Bundle-size optimization (recommended)

`build.frontendDist` is `../` per the directive, which embeds **everything**
in `03_Source_Code/` (including Python sources and `build_output/`) into the
installer. For a lean production bundle, stage only the web assets:

```powershell
# Windows — from 03_Source_Code/
robocopy . dist-app index.html logo.jpg
```
```bash
# macOS / Linux — from 03_Source_Code/
mkdir -p dist-app && cp index.html logo.jpg dist-app/ 2>/dev/null || cp index.html dist-app/
```

Then point `src-tauri/tauri.conf.json` → `build.frontendDist` to
`"../dist-app"` before running `cargo tauri build`.

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Red "LOCAL OLLAMA NOT DETECTED" banner in the app | Run `ollama serve`, then use the tray menu → **Recheck Ollama** |
| Chat errors inside the app but works in the browser | `OLLAMA_ORIGINS` doesn't include the Tauri origin — set it to `*` and restart Ollama |
| Window closes but process stays alive | By design: the shell closes to the system tray; use tray → **Quit** |
| `cargo tauri build` fails on Windows linker errors | Install the MSVC "Desktop development with C++" workload (step 1) |
