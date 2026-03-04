"""Shell command execution tool.

Improvements over CoPaw:
- Both sync (``run_shell``) and async (``execute_shell_command``) entry points
- Graceful terminate → force kill on timeout (like CoPaw)
- Output truncation for large stdout/stderr
- WORKING_DIR as default cwd
"""

from __future__ import annotations

import asyncio
import locale
import logging
import subprocess
from pathlib import Path
from typing import Optional

from ...constant import WORKING_DIR

logger = logging.getLogger(__name__)


def run_shell(
    command: str,
    timeout: int = 120,
    cwd: Optional[str] = None,
) -> dict[str, str | int]:
    """Execute a shell command synchronously and return the output.

    Parameters
    ----------
    command:
        Shell command to execute.
    timeout:
        Maximum execution time in seconds (default 120).
    cwd:
        Working directory for the command. Defaults to WORKING_DIR.

    Returns
    -------
    dict
        Result with ``stdout``, ``stderr``, ``returncode``.
    """
    working_dir = cwd or WORKING_DIR
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(working_dir),
        )

        stdout = result.stdout
        stderr = result.stderr

        # Truncate long output
        if len(stdout) > 100_000:
            stdout = stdout[:100_000] + "\n... [output truncated]"
        if len(stderr) > 50_000:
            stderr = stderr[:50_000] + "\n... [stderr truncated]"

        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": (
                f"⚠️ TimeoutError: The command execution exceeded "
                f"the timeout of {timeout} seconds. "
                f"Please consider increasing the timeout value if this "
                f"command requires more time to complete."
            ),
            "returncode": -1,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Command execution failed: {e}",
            "returncode": -1,
        }


async def execute_shell_command(
    command: str,
    timeout: int = 60,
    cwd: Optional[str] = None,
) -> str:
    """Execute a shell command asynchronously with graceful termination.

    If the command exceeds ``timeout`` seconds, it is first terminated
    gracefully (SIGTERM), then force-killed (SIGKILL) after 1 second.

    Parameters
    ----------
    command:
        The shell command to execute.
    timeout:
        Maximum time in seconds. Default is 60.
    cwd:
        Working directory. Defaults to WORKING_DIR.

    Returns
    -------
    str
        Formatted result text.
    """
    cmd = (command or "").strip()
    working_dir = cwd or WORKING_DIR

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            bufsize=0,
            cwd=str(working_dir),
        )

        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
            stdout_bytes, stderr_bytes = await proc.communicate()
            encoding = locale.getpreferredencoding(False) or "utf-8"
            stdout_str = stdout_bytes.decode(encoding, errors="replace").strip(
                "\n",
            )
            stderr_str = stderr_bytes.decode(encoding, errors="replace").strip(
                "\n",
            )
            returncode = proc.returncode

        except asyncio.TimeoutError:
            timeout_msg = (
                f"⚠️ TimeoutError: The command execution exceeded "
                f"the timeout of {timeout} seconds. "
                f"Please consider increasing the timeout value if this "
                f"command requires more time to complete."
            )
            returncode = -1
            try:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=1)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()

                stdout_bytes, stderr_bytes = await proc.communicate()
                encoding = locale.getpreferredencoding(False) or "utf-8"
                stdout_str = stdout_bytes.decode(
                    encoding,
                    errors="replace",
                ).strip("\n")
                stderr_str = stderr_bytes.decode(
                    encoding,
                    errors="replace",
                ).strip("\n")
                if stderr_str:
                    stderr_str += f"\n{timeout_msg}"
                else:
                    stderr_str = timeout_msg
            except ProcessLookupError:
                stdout_str = ""
                stderr_str = timeout_msg

        # Truncate long output
        if len(stdout_str) > 100_000:
            stdout_str = stdout_str[:100_000] + "\n... [output truncated]"
        if len(stderr_str) > 50_000:
            stderr_str = stderr_str[:50_000] + "\n... [stderr truncated]"

        # Format response
        if returncode == 0:
            if stdout_str:
                return stdout_str
            return "Command executed successfully (no output)."
        else:
            parts = [f"Command failed with exit code {returncode}."]
            if stdout_str:
                parts.append(f"\n[stdout]\n{stdout_str}")
            if stderr_str:
                parts.append(f"\n[stderr]\n{stderr_str}")
            return "".join(parts)

    except Exception as e:
        return f"Error: Shell command execution failed due to \n{e}"
