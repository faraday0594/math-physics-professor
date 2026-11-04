import base64
import io
import os
import sys
import traceback
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp


def execute_math_physics_code(code: str) -> Dict[str, Any]:
    """
    Executes Python code in a scientific environment with SymPy, NumPy, SciPy, and Matplotlib.
    Captures stdout, any returned `result` variable, and any generated Matplotlib figures as base64 PNGs.
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    plots_base64: List[str] = []

    # Prepare clean figure style for dark/modern UI
    plt.close("all")
    plt.rcParams.update({
        "figure.figsize": (8, 5),
        "figure.dpi": 130,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.edgecolor": "#475569",
        "axes.linewidth": 0.8,
        "font.size": 11,
    })

    # Pre-populated scientific namespace
    local_env: Dict[str, Any] = {
        "sp": sp,
        "sympy": sp,
        "np": np,
        "numpy": np,
        "plt": plt,
        "matplotlib": matplotlib,
    }
    try:
        import scipy
        local_env["scipy"] = scipy
    except ImportError:
        pass

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    success = True
    error_msg = None

    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # Avoid blocking calls to plt.show()
        plt.show = lambda *args, **kwargs: None

        exec(code, local_env, local_env)

        # Capture all open matplotlib figures
        fig_nums = plt.get_fignums()
        for num in fig_nums:
            fig = plt.figure(num)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
            buf.seek(0)
            b64_img = base64.b64encode(buf.read()).decode("utf-8")
            plots_base64.append(f"data:image/png;base64,{b64_img}")
            buf.close()
        plt.close("all")

    except Exception:
        success = False
        error_msg = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        plt.close("all")

    output_text = stdout_capture.getvalue().strip()
    err_text = stderr_capture.getvalue().strip()

    # If the script assigned a variable named `result` or `final_answer`, include it if stdout is empty
    if not output_text and "result" in local_env:
        output_text = f"result = {local_env['result']}"

    return {
        "success": success,
        "stdout": output_text,
        "stderr": err_text,
        "error": error_msg,
        "plots": plots_base64,
        "code": code,
    }
