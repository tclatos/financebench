# Justfile for financebench
# Run `just` to see available recipes.

# Default recipe — show help
default:
    @just --list

# ── Development ─────────────────────────────────────────────────────────────

# Install / sync dependencies
sync:
    uv sync

# Format code with ruff
fmt:
    uv run ruff format .

# Lint code with ruff
lint:
    uv run ruff check .
    uv run cli skills validate --all || true

# Format + lint
check: fmt lint

# Run tests
test:
    uv run pytest tests/ -v

# Run unit tests only
test-unit:
    uv run pytest tests/unit_tests/ -v

# ── Skills ───────────────────────────────────────────────────────────────────

# List all available skills
skills:
    uv run cli skills list

# Add a skill by name (bundled)
add-skill name:
    uv run cli skills add {{name}}

# Validate all skills
lint-skills:
    uv run cli skills validate --all

# ── Web Interface ────────────────────────────────────────────────────────────

# Launch Streamlit webapp (entry point discovered from genai-tk package)
webapp:
    entry=$(uv run python -c 'import pathlib, genai_tk; print(pathlib.Path(genai_tk.__file__).parent / "webapp/main/streamlit.py")') && uv run python -m streamlit run "$entry"

# ── Project-specific ─────────────────────────────────────────────────────────

# Launch agent chat
run:
    uv run cli agent chat

# ── FinanceBench bench harness ─────────────────────────────────────────────────

# Install deps incl. the harnessing extra (DeepAgents SDK) needed for the deep agent
bench-setup:
    uv sync --extra harnessing

# Full Phase-1 bench: dataset → PDF → OCR/graph → run questions → grade
bench:
    uv run python -m financebench.bench.load_dataset
    uv run python -m financebench.bench.fetch_pdf
    uv run python -m financebench.bench.build_graph
    uv run python -m financebench.bench.run_questions
    uv run python -m financebench.bench.grade

bench-load:
    uv run python -m financebench.bench.load_dataset

bench-fetch:
    uv run python -m financebench.bench.fetch_pdf

bench-build:
    uv run python -m financebench.bench.build_graph

bench-run:
    uv run python -m financebench.bench.run_questions

bench-grade:
    uv run python -m financebench.bench.grade

