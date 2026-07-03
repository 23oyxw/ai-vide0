#!/usr/bin/env python3
"""C4D MCP Server — thin wrapper around Cinema 4D Commandline.exe."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastmcp import FastMCP

C4D_ROOT = Path(os.environ.get("C4D_ROOT", r"C:\BKC4D"))
COMMANDLINE = C4D_ROOT / "Commandline.exe"

mcp = FastMCP("c4d-mcp")


def _render(project_path: str, output_path: str | None, width: int, height: int) -> dict:
    if not COMMANDLINE.exists():
        return {"ok": False, "error": f"Commandline.exe not found at {COMMANDLINE}"}

    project = Path(project_path)
    if not project.exists():
        return {"ok": False, "error": f"Project not found: {project_path}"}

    out = Path(output_path) if output_path else project.with_suffix(".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(COMMANDLINE),
        "-load", str(project.resolve()),
        "-oimage", str(out.resolve()),
        "-ow", str(width),
        "-oh", str(height),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=str(C4D_ROOT))
        if proc.returncode == 0:
            return {"ok": True, "output": str(out), "stdout": proc.stdout[-500:]}
        return {"ok": False, "error": proc.stderr[-1000] or f"exit {proc.returncode}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "render timed out (1800s)"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def c4d_render_project(
    project_path: str,
    output_path: str = "",
    width: int = 1920,
    height: int = 1080,
) -> dict:
    """Render a Cinema 4D project file using Commandline.exe (headless).

    Args:
        project_path: Absolute path to .c4d project file.
        output_path: Optional output image/video path. Defaults to same name as project.
        width: Output width in pixels.
        height: Output height in pixels.
    """
    out = output_path if output_path else None
    return _render(project_path, out, width, height)


@mcp.tool()
def c4d_check_installation() -> dict:
    """Verify C4D Commandline.exe and c4dpy are available."""
    c4dpy = C4D_ROOT / "c4dpy.exe"
    return {
        "c4d_root": str(C4D_ROOT),
        "commandline": str(COMMANDLINE),
        "commandline_exists": COMMANDLINE.exists(),
        "c4dpy": str(c4dpy),
        "c4dpy_exists": c4dpy.exists(),
    }


@mcp.tool()
def c4d_list_resources(resource_dir: str = "") -> dict:
    """List .c4d files in a directory (project browser stub)."""
    base = Path(resource_dir) if resource_dir else C4D_ROOT
    if not base.exists():
        return {"ok": False, "error": f"Directory not found: {base}"}
    projects = [str(p) for p in base.rglob("*.c4d")][:50]
    return {"ok": True, "count": len(projects), "projects": projects}


if __name__ == "__main__":
    mcp.run()
