#!/usr/bin/env python3
"""
Script to help refactor test files to use pytest fixtures and best practices.
This analyzes test files and provides refactoring suggestions.
"""

import ast
import os
from pathlib import Path
from typing import List, Set, Tuple


class TestAnalyzer(ast.NodeVisitor):
    """Analyze test files for refactoring opportunities."""

    def __init__(self):
        self.uses_unittest = False
        self.uses_setup_teardown = False
        self.uses_os_chdir = False
        self.uses_shutil_rmtree = False
        self.uses_tempfile = False
        self.hardcoded_paths = []
        self.test_classes = []
        self.setup_methods = []
        self.teardown_methods = []
        self.chdir_calls = []

    def visit_ImportFrom(self, node):
        if node.module == "unittest":
            self.uses_unittest = True
        elif node.module == "tempfile":
            self.uses_tempfile = True
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == "unittest":
                self.uses_unittest = True
            elif alias.name == "tempfile":
                self.uses_tempfile = True
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        # Check if it's a test class
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                if base.attr == "TestCase":
                    self.test_classes.append(node.name)
            elif isinstance(base, ast.Name):
                if base.id == "TestCase":
                    self.test_classes.append(node.name)

        # Check for setUp/tearDown methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name in ("setUp", "setUpClass"):
                    self.setup_methods.append((node.name, item.name))
                    self.uses_setup_teardown = True
                elif item.name in ("tearDown", "tearDownClass"):
                    self.teardown_methods.append((node.name, item.name))
                    self.uses_setup_teardown = True

        self.generic_visit(node)

    def visit_Call(self, node):
        # Check for os.chdir calls
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == "os" and node.func.attr == "chdir":
                    self.uses_os_chdir = True
                    self.chdir_calls.append(self._get_line_number(node))
                elif node.func.value.id == "shutil" and node.func.attr == "rmtree":
                    self.uses_shutil_rmtree = True

        # Check for hardcoded paths
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if "test_resources" in arg.value or "examples/" in arg.value:
                    self.hardcoded_paths.append(arg.value)

        self.generic_visit(node)

    def _get_line_number(self, node):
        return getattr(node, "lineno", 0)


def analyze_test_file(filepath: Path) -> dict:
    """Analyze a test file and return refactoring suggestions."""
    with open(filepath, "r") as f:
        content = f.read()

    try:
        tree = ast.parse(content)
        analyzer = TestAnalyzer()
        analyzer.visit(tree)

        return {
            "file": filepath.name,
            "uses_unittest": analyzer.uses_unittest,
            "uses_setup_teardown": analyzer.uses_setup_teardown,
            "uses_os_chdir": analyzer.uses_os_chdir,
            "uses_shutil_rmtree": analyzer.uses_shutil_rmtree,
            "uses_tempfile": analyzer.uses_tempfile,
            "test_classes": analyzer.test_classes,
            "setup_methods": analyzer.setup_methods,
            "teardown_methods": analyzer.teardown_methods,
            "hardcoded_paths": analyzer.hardcoded_paths,
            "needs_refactoring": (
                analyzer.uses_unittest
                or analyzer.uses_setup_teardown
                or analyzer.uses_os_chdir
                or len(analyzer.hardcoded_paths) > 0
            ),
        }
    except SyntaxError:
        return {"file": filepath.name, "error": "syntax_error"}


def generate_refactoring_report():
    """Generate a report of all test files that need refactoring."""
    test_dir = Path(__file__).parent
    test_files = sorted(test_dir.glob("test_*.py"))

    # Exclude already refactored files
    exclude_files = {"test_compile_refactored.py", "test_helpers.py", "refactor_tests.py"}
    test_files = [f for f in test_files if f.name not in exclude_files]

    report = []
    for test_file in test_files:
        analysis = analyze_test_file(test_file)
        if analysis.get("needs_refactoring"):
            report.append(analysis)

    return report


def print_refactoring_report():
    """Print a formatted refactoring report."""
    report = generate_refactoring_report()

    print("=" * 80)
    print("TEST REFACTORING REPORT")
    print("=" * 80)
    print(f"\nFiles needing refactoring: {len(report)}")
    print("-" * 80)

    for item in report:
        print(f"\n{item['file']}:")
        if item["uses_unittest"]:
            print("  ✗ Uses unittest.TestCase - convert to pytest classes")
        if item["uses_setup_teardown"]:
            print(f"  ✗ Has setUp/tearDown methods: {item['setup_methods']} - convert to fixtures")
        if item["uses_os_chdir"]:
            print("  ✗ Uses os.chdir() - use isolated fixtures instead")
        if item["uses_shutil_rmtree"]:
            print("  ✗ Uses shutil.rmtree() - use temp_dir fixture instead")
        if item["hardcoded_paths"]:
            print(f"  ✗ Has hardcoded paths: {len(item['hardcoded_paths'])} occurrences")
            for path in item["hardcoded_paths"][:3]:
                print(f"    - {path}")
        if item["test_classes"]:
            print(f"  Classes to convert: {', '.join(item['test_classes'])}")

    print("\n" + "=" * 80)
    print("REFACTORING PRIORITIES:")
    print("=" * 80)

    # Prioritize by impact
    high_priority = [f for f in report if f["uses_os_chdir"] or f["uses_setup_teardown"]]
    medium_priority = [f for f in report if f["uses_unittest"] and f not in high_priority]

    print(f"\nHigh Priority ({len(high_priority)} files):")
    for item in high_priority[:5]:
        print(f"  - {item['file']}")

    print(f"\nMedium Priority ({len(medium_priority)} files):")
    for item in medium_priority[:5]:
        print(f"  - {item['file']}")


if __name__ == "__main__":
    print_refactoring_report()
