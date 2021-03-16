import logging
import subprocess
from subprocess import PIPE, DEVNULL

logger = logging.getLogger(__name__)


def helm_cli(args, verbose=False):
    try:
        logger.debug("launching helm with arguments: %s", args)
        res = subprocess.run(args=["helm"] + args, stderr=PIPE, stdout=PIPE if verbose else DEVNULL)
        if verbose:
            for line in res.stdout.splitlines():
                if line:
                    logger.debug("[helm] %s", line.decode())
        return res.stderr.decode() if res.returncode != 0 else ""
    except FileNotFoundError:
        return "helm binary not found. helm must be present in the PATH to use kapitan helm functionalities"
