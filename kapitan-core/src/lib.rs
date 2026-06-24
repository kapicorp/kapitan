// Copyright 2026 The Kapitan Authors
// SPDX-License-Identifier: Apache-2.0

//! kapitan-core: the Rust core for Kapitan, exposed to Python via PyO3.
//!
//! For now this crate exists purely to prove the Python <-> Rust piping.
//! Functionality will be migrated here from the `kapitan` Python package
//! incrementally.

use pyo3::prelude::*;

/// Print a greeting from Rust and return it to the caller.
///
/// This is a placeholder used to verify the build/import pipeline end to end.
#[pyfunction]
fn hello_from_kapitan_core() -> PyResult<String> {
    let message = "Hello from kapitan-core (Rust)!".to_string();
    println!("{message}");
    Ok(message)
}

/// The `kapitan_core` Python module.
///
/// The function name must match the `[lib] name` in Cargo.toml and the
/// `module-name` in pyproject.toml.
#[pymodule]
fn kapitan_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello_from_kapitan_core, m)?)?;
    m.add("__doc__", "Rust core extension for Kapitan.")?;
    Ok(())
}
