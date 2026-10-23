import functools
import logging
import os
import subprocess
from subprocess import DEVNULL, PIPE


logger = logging.getLogger(__name__)


@functools.cache
def helm_version(helm_path: str | None = None) -> str:
    """Return ``helm version --short`` output for cache-key purposes.

    Resolves the binary the same way :func:`helm_cli` does (explicit
    ``helm_path``, then ``KAPITAN_HELM_PATH`` env var, then ``"helm"`` via
    PATH). Memoized per resolved binary so we incur at most one
    ``helm version`` subprocess per distinct binary per worker process.

    On failure (binary missing, timeout, non-zero exit), returns a sentinel
    string derived from the path so callers that include it in a cache key
    still differentiate user-supplied paths. The render itself will fail
    loudly downstream if the binary is truly broken.
    """
    binary = helm_path or os.getenv("KAPITAN_HELM_PATH", "helm")
    try:
        res = subprocess.run(
            [binary, "version", "--short"],
            stdout=PIPE,
            stderr=DEVNULL,
            check=False,
            timeout=10,
        )
        if res.returncode == 0:
            return res.stdout.decode().strip()
        logger.debug("helm version probe for %s returned %d", binary, res.returncode)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug("helm version probe failed for %s: %s", binary, e)
    return f"unresolved:{binary}"


def helm_cli(helm_path, args, stdout=None, verbose=False, timeout=None):
    # if helm is not specified, try to get it from env var, and defaults to looking up helm in the path.
    if not helm_path:
        helm_path = os.getenv("KAPITAN_HELM_PATH", "helm")
    # Allow timeout to be configured via environment variable, default to 30 seconds
    if timeout is None:
        timeout = int(os.getenv("KAPITAN_HELM_TIMEOUT", "30"))
    try:
        logger.debug("launching helm with arguments: %s", args)
        res = subprocess.run(
            args=[helm_path] + args,
            stderr=PIPE,
            stdout=stdout or (PIPE if verbose else DEVNULL),
            check=False,
            timeout=timeout,
        )
        if verbose and not stdout:
            for line in res.stdout.splitlines():
                if line:
                    logger.debug("[helm] %s", line.decode())
        return res.stderr.decode() if res.returncode != 0 else ""
    except FileNotFoundError:
        return "helm binary not found. helm must be present in the PATH to use kapitan helm functionalities"
    except subprocess.TimeoutExpired:
        helm_command = " ".join([helm_path] + args)
        return (
            f"Helm command timed out after {timeout} seconds. "
            f"This may be due to network connectivity issues or slow chart repositories. "
            f"Command: '{helm_command}'. "
            f"You can increase the timeout by setting the KAPITAN_HELM_TIMEOUT environment variable."
        )
