# Stage 01: Setup & Installation

## Goal

Install NautilusTrader and verify it works. Two paths: install from PyPI (quickest) or build from source (needed for development).

## Prerequisites

- Python 3.12–3.14 (vanilla CPython recommended; Conda not officially supported)
- Git
- A terminal you're comfortable with

## Concepts

NautilusTrader is a **Rust core + Python API** platform. The Python package wraps high-performance Rust code via PyO3/Cython bindings. Pre-built wheels are available on PyPI for most platforms, but building from source requires a Rust toolchain.

The project recommends **`uv`** (not pip) as its package manager.

### Supported Platforms

| Operating System | Versions | CPU Architecture |
|-----------------|----------|------------------|
| Linux (Ubuntu) | 22.04+ | x86_64, ARM64 |
| macOS | 15.0+ | ARM64 |
| Windows Server | 2022+ | x86_64 |

## Path A: Install from PyPI (Quickest)

### 1. Install uv

**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

### 2. Install NautilusTrader

```bash
uv pip install nautilus_trader
```

With optional extras (e.g., Interactive Brokers adapter, visualization):
```bash
uv pip install "nautilus_trader[ib,visualization]"
```

### 3. Verify

```bash
python -c "import nautilus_trader; print(nautilus_trader.__version__)"
```

---

## Path B: Build from Source (For Development)

### 1. Install Rust Toolchain

**Linux / macOS:**
```bash
curl https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env
```

**Windows:**
- Download and install [`rustup-init.exe`](https://win.rustup.rs/x86_64)
- Install "Desktop development with C++" via [Build Tools for Visual Studio 2022](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Start a new PowerShell session

Verify: `rustc --version`

### 2. Install Clang

**Linux:**
```bash
sudo apt-get install clang
```

**macOS:**
```bash
xcode-select --install
```
(This provides clang via Xcode Command Line Tools)

**Windows:**
1. Open Visual Studio Installer → Modify → check "C++ Clang tools for Windows" → Modify
2. Add clang to PATH:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('path', "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\Llvm\x64\bin\;" + $env:Path,"User")
   ```

Verify: `clang --version`

### 3. Install uv

(Same as Path A — see above)

### 4. Clone and Build

```bash
git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
cd nautilus_trader
uv sync --all-extras
```

Or use `make` targets for development builds:

```bash
# Full debug install (unoptimized but fast compile)
make install-debug

# Full release install (slow compile, fast runtime)
make install
```

### 5. Set Environment Variables (Linux/macOS only)

```bash
# Linux only: Set library path for the Python interpreter
export LD_LIBRARY_PATH="$(python -c 'import sys; print(sys.base_prefix)')/lib:$LD_LIBRARY_PATH"

# Set Python executable path for PyO3
export PYO3_PYTHON=$(pwd)/.venv/bin/python

# Required for Rust tests when using uv-installed Python
export PYTHONHOME=$(python -c "import sys; print(sys.base_prefix)")
```

(On macOS, skip the `LD_LIBRARY_PATH` line — it's Linux-specific.)

### 6. Verify

```bash
# Activate the venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Smoke test
python -c "import nautilus_trader; print(nautilus_trader.__version__)"

# Run tests
make pytest       # Python test suite
make cargo-test   # Rust test suite
```

## Key `make` Targets

| Target | Purpose |
|--------|---------|
| `make install-debug` | Full install, debug mode (fastest compile) |
| `make install` | Full install, release mode (fastest runtime) |
| `make build-debug` | Build Rust only, debug mode |
| `make build` | Build Rust only, release mode |
| `make pytest` | Run Python tests |
| `make cargo-test` | Run Rust tests |
| `make clean` | Clean build artifacts |

## Optional: Redis

Redis is optional — only needed if you configure it as a cache database or message bus backend. For a quick setup:

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

## Checkpoint

You're ready for Stage 02 when:
- [ ] `python -c "import nautilus_trader"` succeeds
- [ ] You understand that NT is Rust core + Python API
- [ ] (If building from source) `make pytest` runs without import errors

## Common Issues

**"clang not found"**: Install via your system package manager (see step 2).

**"rustup not found"**: Ensure `~/.cargo/bin` is in your `PATH`. Restart your terminal after installing rustup.

**Windows build errors**: Make sure both "Desktop development with C++" and "C++ Clang tools for Windows" are installed via Visual Studio Build Tools.

**Slow first build**: The initial Rust compilation takes several minutes. Subsequent incremental rebuilds are much faster.

**Precision mode**: By default, Linux/macOS wheels use 128-bit high-precision. Windows uses 64-bit standard-precision (MSVC doesn't support `__int128`). For source builds, control via `HIGH_PRECISION=true|false` environment variable.
