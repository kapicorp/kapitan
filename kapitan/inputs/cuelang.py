
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import yaml

from kapitan.errors import KustomizeTemplateError
from kapitan.inputs.base import InputType
from kapitan.inventory.model.input_types import KapitanInputTypeCuelangConfig

logger = logging.getLogger(__name__)


class Cuelang(InputType):
    """CUE-Lang implementation."""

    def __init__(self, compile_path: str, search_paths: list, ref_controller, target_name: str, args):
        """Initialize the Kustomize implementation.

        Args:
            compile_path: Base path for compiled output
            search_paths: List of paths to search for input files
            ref_controller: Reference controller for handling refs
            target_name: Name of the target being compiled
            args: Additional arguments passed to the tool
        """
        super().__init__(compile_path, search_paths, ref_controller, target_name, args)
        self.cue_path = args.cue_path if hasattr(
            args, "cue_path") else "cue"

    def compile_file(
        self, config: KapitanInputTypeCuelangConfig, input_path: str, compile_path: str
    ) -> None:
        temp_dir = tempfile.mkdtemp()
        abs_input_path = os.path.abspath(input_path)

        # Copy the input directory to the temporary directory
        input_dir_name = os.path.basename(abs_input_path)
        temp_input_dir = os.path.join(temp_dir, input_dir_name)
        shutil.copytree(abs_input_path, temp_input_dir)

        cwd = os.getcwd()

        # os.chdir(temp_input_dir)

        input_file_path = os.path.join(temp_input_dir, "input.yaml")
        with open(input_file_path, "w") as f:
            yaml.dump(config.input, f)

        cmd = [
            self.cue_path,
            "export",
            ".", # can't get it to work compiling from an absolute path
            # temp_input_dir,
            "-l",
            "input:",
            "input.yaml",
            "--out",
            "yaml",
        ]

        with open("output.yaml", "w") as f:
            result = subprocess.run(
                cmd, stdout=f, stderr=subprocess.PIPE, text=True, cwd=temp_input_dir)
            if result.returncode != 0:
                err = f"Failed to run CUE export: {result.stderr}"
                raise KustomizeTemplateError(err)

        # os.chdir(cwd)
        output_file = os.path.join(compile_path, "output.yaml")

        with open(output_file, "w") as out_f:
            with open("output.yaml", "r") as in_f:
                out_f.write(in_f.read())
