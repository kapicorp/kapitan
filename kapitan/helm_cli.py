import subprocess
from subprocess import PIPE


def helm_cli(args):
    try:
        res = subprocess.run(args=["helm"] + args, stderr=PIPE)
        return res.stderr.decode() if res.returncode != 0 else ""
    except FileNotFoundError:
        return "helm binary not found. helm must be present in the PATH to use kapitan helm functionalities"
