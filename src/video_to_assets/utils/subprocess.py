from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Sequence


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    """Centralized subprocess wrapper for all external commands."""

    def __init__(self, logger=None):
        self.logger = logger

    def which(self, binary: str) -> str | None:
        return shutil.which(binary)

    def run(
        self,
        command: Sequence[str],
        timeout: int | None = None,
        check: bool = True,
        cwd: str | None = None,
    ) -> CommandResult:
        cmd = [str(x) for x in command]
        if self.logger:
            self.logger.info("Run command: %s", " ".join(cmd))
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        result = CommandResult(
            command=cmd,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
        if proc.returncode != 0 and check:
            msg = (
                f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
                f"stdout: {proc.stdout[-1000:]}\n"
                f"stderr: {proc.stderr[-1000:]}"
            )
            raise RuntimeError(msg)
        return result
