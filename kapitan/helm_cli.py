import logging
import os
import subprocess
from subprocess import DEVNULL, PIPE

logger = logging.getLogger(__name__)


def helm_cli(helm_path, args, stdout=None, verbose=False):
    # if helm is not specified, try to get it from env var, and defaults to looking up helm in the path.
    if not helm_path:
        helm_path = os.getenv("KAPITAN_HELM_PATH", "helm")
    try:
        logger.debug("launching helm with arguments: %s", args)
        res = subprocess.run(
            args=[helm_path] + args, stderr=PIPE, stdout=stdout or (PIPE if verbose else DEVNULL)
        )
        if verbose and not stdout:
            for line in res.stdout.splitlines():
                if line:
                    logger.debug("[helm] %s", line.decode())
        return res.stderr.decode() if res.returncode != 0 else ""
    except FileNotFoundError:
        return "helm binary not found. helm must be present in the PATH to use kapitan helm functionalities"
