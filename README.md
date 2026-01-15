# 🧠 Gyrus: Semantic Collective Memory

Gyrus is a brain-inspired, collective intelligence infrastructure for your clipboard. It builds a semantic memory graph using Hexagonal Architecture and asynchronous workflows.


## 🚀 The Vision: Hebbian Intelligence

Gyrus follows the **Hebb's Law principle**: *"Nodes that fire together, wire together."* Our architecture evolves through stages of increasing connectivity and collective consciousness.

| Stage | Name | Focus | Status |
| :---- | :---- | :---- | :---- |
| **S1** | **Synapse** | Local semantic capture, vector embeddings, and SQLite persistence. | **Active** |
| **S2** | **Cortex** | Visual recall interface (Rofi/Tkinter), semantic and fuzzy search, and temporal decay. | **Active** |
| **S3** | **Neural Circle** | E2EE Trust Circles, NATS-based P2P sync, and collective memory. | Research |

---

## 📂 Implementation Blueprint (The "Everything" Guide)

### 1. Domain Layer (`src/gyrus/domain/`)
The core logic. No external dependencies allowed.

- **`models.py`**: Contains the `Node` dataclass (content, vector, metadata, timestamp).
- **`repository.py`**: Abstract Base Class (ABC) defining how to `save` and `find_similar` nodes.

### 2. Application Layer (`src/gyrus/application/`)
The orchestrator. Defines interfaces for the outside world.

- **`services.py`**: ABCs for `EmbeddingService` (AI) and `ClipboardService` (System).
- **`use_cases.py`**: The `CaptureClipboard` class. It fetches text, calls the AI to get a vector, and tells the repository to save the Node.

### 3. Infrastructure Layer (`src/gyrus/infrastructure/adapters/`)
The "doing" layer. Real implementations.

- **`storage/sqlite_storage.py`**: SQLite + NumPy to store vectors as BLOBs.
- **`ai/fastembed_adapter.py`**: Local BGE-small embeddings.
- **`system/linux_adapter.py`**: `pynput` for hotkeys and `wl-clipboard/xclip` for text.
- **`ui/` adapters** (Recall UI):
  - **`tkinter_adapter.py`** *(Default)*: Tkinter picker with **hybrid semantic + fuzzy search** (leverages vector embeddings for semantic ranking + difflib for fuzzy matching). Includes live preview tooltip.
  - **`rofi_adapter.py`**: External dmenu-like UI with **traditional text search** (no vector embeddings).

---

## 🛠️ Tooling & Commands

We use **`uv`** for management and **`taskipy`** for automation.

| Command | Action |
| :--- | :--- |
| `uv sync` | Install all dependencies into `.venv` |
| `uv pip install -e .` | **Install package in editable mode** (required for systemd service and scripts) |
| `uv run task check` | **Linter (Ruff)** + **Tests (Pytest)**. Run this before every commit! |
| `uv run task format` | Automatically fix PEP8 issues with Ruff |
| `uv run task start` | Launch the Gyrus background daemon |
| `PYTHONPATH=src uv run python scripts/show_gyrus_memory.py` | Display all stored memory nodes from the database |

---

## 📜 Utility Scripts

Located in `scripts/`:

- **`show_gyrus_memory.py`**: Display all nodes stored in the database with their circle_id, content, embeddings, and expiration time
- **`install_gyrus_linux.sh`**: Install Gyrus as a systemd user service on Linux
- **`uninstall_gyrus_linux.sh`**: Remove the Gyrus systemd user service

---

## ⚙️ Configuration (`pyproject.toml`)

Your project is pre-configured with:
- **Python**: >= 3.12
- **Linter**: Ruff (Strict PEP8 + Isort)
- **Database**: `gyrus.db` (Git-ignored to protect your privacy)
- **Linter Rules**: `select = ["E", "F", "I", "B"]` (Errors, Flakes, Imports, Bugbear)

---

## 🧪 Testing Hierarchy

1. **Unit (Domain)**: Tests logic in `domain/models.py`.
2. **Integration (Infra)**: Tests `sqlite_storage.py` using `:memory:` databases.
3. **End-to-End**: Tests the `CaptureClipboard` use case with mocked adapters.

---

## ⌨️ Controls (Linux Default)
- **Capture Hotkey**: `Ctrl + Super + C`
- **Output**: Logs to terminal and persists to `gyrus.db`.

---

## 🐧 Linux Installation & Systemd User Service

### 1. Install System Dependencies
```sh
sudo apt-get update
sudo apt-get install python3.12 python3.12-venv python3-pip x11-utils xclip rofi

# Optional: For GNOME system tray support (AppIndicator in top panel)
sudo apt-get install python3-gi gir1.2-appindicator3-0.1
```

### 2. Clone & Setup Project
```sh
git clone https://github.com/franjjs/gyrus
cd gyrus
python3.12 -m venv .venv
source .venv/bin/activate
uv sync
```

### 2b. Optional: Enable GNOME AppIndicator (System Tray)

#### For Ubuntu 20.04:
```sh
# Install system dependencies
sudo apt-get install python3-gi gir1.2-appindicator3-0.1

# Install Python AppIndicator support
uv sync --group gnome-ubuntu-2004

# If you get girepository-2.0 build errors, fix pkgconfig:
sudo ln -sf /usr/lib/x86_64-linux-gnu/pkgconfig/gobject-introspection-1.0.pc \
  /usr/lib/x86_64-linux-gnu/pkgconfig/girepository-2.0.pc
```

#### For Ubuntu 22.04+:
```sh
# Install system dependencies
sudo apt-get install python3-gi gir1.2-appindicator3-0.1

# Install Python AppIndicator support
uv sync --group gnome-ubuntu-2204
```

After this, `uv run task start` will display the 🧠 icon in GNOME's top panel with circle selection menu.

### 3. Launch as User Systemd Service
```sh
bash scripts/install_gyrus_linux.sh
```
This will create and start a user-level systemd service for Gyrus, with X11 clipboard access.

#### Useful systemd user commands:
- `systemctl --user status gyrus` — Check service status
- `journalctl --user -u gyrus -f` — View logs
- `systemctl --user stop gyrus` — Stop service
- `systemctl --user restart gyrus` — Restart service
- `systemctl --user disable gyrus` — Disable autostart
- `systemctl --user is-enabled gyrus` — Check if enabled

### 4. Uninstall User Service
```sh
bash scripts/uninstall_gyrus_linux.sh
```
This will stop, disable, and remove the user systemd service for Gyrus.

---

## 📄 License
MIT License.
