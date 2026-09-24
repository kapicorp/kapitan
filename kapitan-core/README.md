# kapitan-core

The Rust core for [Kapitan](https://github.com/kapicorp/kapitan), exposed to
Python as a [PyO3](https://pyo3.rs) extension module and built into a wheel with
[maturin](https://www.maturin.rs).

This package is where performance-sensitive functionality is migrated out of the
pure-Python `kapitan` package over time. It is **abi3** — a single wheel per
platform works on every CPython >= 3.10.

## Layout

```
kapitan-core/
├── Cargo.toml        # Rust crate (cdylib, pyo3 with abi3-py310)
├── pyproject.toml    # maturin build backend; version is dynamic (from Cargo.toml)
├── src/
│   └── lib.rs        # #[pymodule] kapitan_core
└── README.md
```

## Local development

`kapitan-core` is wired into the kapitan repo as an opt-in `uv` dependency
group named `rust` (a path source pointing at this crate). All commands below
run from the **repo root**.

### Build and install into the project venv

```sh
uv sync --group rust --reinstall-package kapitan-core
```

When executing Kapitan, `kapitan-core` will be available:
```
uv run kapitan --help
```

### Build a redistributable wheel (does not install it)

```sh
cd kapitan-core
uvx maturin build --release    # abi3 wheel lands in target/wheels/
```
Without the `rust` group (a plain `uv sync` or a normal `pip install kapitan`),
the extension is simply absent and kapitan behaves exactly as before.
