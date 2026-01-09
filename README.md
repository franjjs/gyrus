# 🧠 Gyrus: Semantic Collective Memory

Gyrus is a brain-inspired, collective intelligence infrastructure for your clipboard. It builds a semantic memory graph using Hexagonal Architecture and asynchronous workflows.


## 🚀 The Vision: Hebbian Intelligence

Gyrus follows the **Hebb's Law principle**: *"Nodes that fire together, wire together."* Our architecture evolves through stages of increasing connectivity and collective consciousness.

| Stage | Name | Focus | Status |
| :--- | :--- | :--- | :--- |
| **Stage 1** | **Synapse** | Local semantic capture, vector embeddings, and SQLite persistence. | **Active** |
| **Stage 2** | **Cortex** | Visual recall interface (Rofi/Fzf), fuzzy search, and temporal decay. | Planned |
| **Stage 3** | **Neural Circle** | E2EE Trust Circles, NATS-based P2P sync, and collective memory. | Research |

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

- **`storage/sqlite_adapter.py`**: SQLite + NumPy to store vectors as BLOBs.
- **`ai/fastembed_adapter.py`**: Local BGE-small embeddings.
- **`system/linux_adapter.py`**: `pynput` for hotkeys and `wl-clipboard/xclip` for text.

---

## 🛠️ Tooling & Commands

We use **`uv`** for management and **`taskipy`** for automation.

| Command | Action |
| :--- | :--- |
| `uv sync` | Install all dependencies into `.venv` |
| `uv run task check` | **Linter (Ruff)** + **Tests (Pytest)**. Run this before every commit! |
| `uv run task format` | Automatically fix PEP8 issues with Ruff |
| `uv run task start` | Launch the Gyrus background daemon |

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
2. **Integration (Infra)**: Tests `sqlite_adapter.py` using `:memory:` databases.
3. **End-to-End**: Tests the `CaptureClipboard` use case with mocked adapters.

---

## ⌨️ Controls (Linux Default)
- **Capture Hotkey**: `Ctrl + Super + C`
- **Output**: Logs to terminal and persists to `gyrus.db`.

## 📄 License
MIT License.
