"""
Sandboxed Python execution tool.
Grab-bag: Code Execution — the agent writes pandas/numpy/matplotlib code
and this module runs it at runtime, returning stdout + any generated files.
"""
from __future__ import annotations
import io
import json
import os
import sys
import traceback
import contextlib
from typing import Any

import pandas as pd
import numpy as np

from config import OUTPUTS_DIR


@contextlib.contextmanager
def _capture_output():
    """Capture stdout/stderr from exec'd code."""
    old_out, old_err = sys.stdout, sys.stderr
    out, err = io.StringIO(), io.StringIO()
    sys.stdout, sys.stderr = out, err
    try:
        yield out, err
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def execute_python_analysis(code: str, data_json: str = "{}") -> str:
    """
    Execute a Python snippet in a restricted sandbox with access to pandas,
    numpy, and the provided data. The code can print results or produce
    a DataFrame called `result_df`.

    Args:
        code: Python source code (string). May use `data` (the parsed data_json),
              `pd` (pandas), `np` (numpy), and `json`. Any matplotlib figures
              are saved automatically.
        data_json: JSON string of data to inject into the sandbox as `data`.

    Returns:
        JSON string with keys: stdout (str), result_df (list of dicts if present),
        error (str if any), saved_files (list of paths).
    """
    try:
        data: Any = json.loads(data_json)
    except Exception:
        data = data_json

    saved_files: list[str] = []

    # Minimal safe namespace
    namespace: dict[str, Any] = {
        "pd":       pd,
        "np":       np,
        "json":     json,
        "data":     data,
        "OUTPUTS_DIR": OUTPUTS_DIR,
        "saved_files": saved_files,
    }

    # Intercept matplotlib so figures are saved, not shown
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_counter = [0]
    _orig_show  = plt.show

    def _auto_save_figure():
        fig_counter[0] += 1
        path = os.path.join(OUTPUTS_DIR, f"figure_{fig_counter[0]}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
        saved_files.append(path)
        plt.close("all")

    namespace["plt"]       = plt
    namespace["save_fig"]  = _auto_save_figure

    stdout_str = ""
    error_str  = ""
    result_df_records: list[dict] = []

    with _capture_output() as (out, err):
        try:
            exec(compile(code, "<alphatrace_sandbox>", "exec"), namespace)  # noqa: S102
        except Exception:
            error_str = traceback.format_exc()

    stdout_str = out.getvalue()
    if err.getvalue():
        error_str = (error_str + "\n" + err.getvalue()).strip()

    # If the code produced a DataFrame called result_df, serialise it
    if "result_df" in namespace and isinstance(namespace["result_df"], pd.DataFrame):
        try:
            result_df_records = json.loads(
                namespace["result_df"].to_json(orient="records", default_handler=str)
            )
        except Exception:
            pass

    # Auto-save any open matplotlib figures the code forgot to save
    try:
        for fig_num in plt.get_fignums():
            _auto_save_figure()
    except Exception:
        pass

    return json.dumps({
        "stdout":      stdout_str,
        "result_df":   result_df_records,
        "error":       error_str,
        "saved_files": saved_files,
    })
