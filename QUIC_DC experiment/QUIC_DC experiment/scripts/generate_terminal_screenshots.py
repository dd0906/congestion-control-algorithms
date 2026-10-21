"""
generate_terminal_screenshots.py
==================================
Runs the experiment, captures actual stdout/stderr, saves the raw text log
to ../raw_outputs/terminal_execution.txt, and renders faithful terminal
screenshot PNG images to ../terminal_screenshots/.
"""

import os
import sys
import subprocess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPERIMENT_DIR = os.path.join(SCRIPT_DIR, "..")
RAW_OUTPUTS_DIR = os.path.join(EXPERIMENT_DIR, "raw_outputs")
SCREENSHOTS_DIR = os.path.join(EXPERIMENT_DIR, "terminal_screenshots")

os.makedirs(RAW_OUTPUTS_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def render_terminal_image(lines: list[str], output_png: str, title: str = "Command Prompt - QUIC-DC"):
    """Renders text lines onto a dark terminal-styled image."""
    fig_height = max(6.0, len(lines) * 0.28 + 1.2)
    fig_width = 13.0

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor="#1e1e1e")
    ax.set_facecolor("#1e1e1e")
    ax.axis("off")

    # Title bar
    fig.text(0.02, 0.98, title, color="#cccccc", fontsize=11, family="monospace", va="top")
    fig.text(0.96, 0.98, "[ - + x ]", color="#888888", fontsize=11, family="monospace", va="top", ha="right")

    # Line separator under title bar
    ax.plot([0, 1], [0.96, 0.96], color="#333333", transform=ax.transAxes, clip_on=False)

    y_pos = 0.93
    line_step = 0.91 / max(1, len(lines))

    for line in lines:
        color = "#f1f1f1"
        if "=" in line or "-" * 5 in line:
            color = "#569cd6"
        elif "QUIC-DC" in line:
            color = "#4ec9b0"
        elif "[OK]" in line:
            color = "#b5cea8"
        elif "Saved:" in line:
            color = "#dcdcaa"
        elif "Error" in line or "WARN" in line:
            color = "#f44747"

        ax.text(
            0.02, y_pos, line,
            color=color,
            fontsize=9.5,
            family="monospace",
            va="top",
            transform=ax.transAxes
        )
        y_pos -= line_step

    plt.tight_layout()
    fig.savefig(output_png, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Terminal screenshot rendered: {output_png}")


def main():
    runner_script = os.path.join(SCRIPT_DIR, "run_experiment.py")
    print(f"Executing {runner_script} and capturing actual output...")

    proc = subprocess.run(
        [sys.executable, "-X", "utf8", runner_script],
        cwd=SCRIPT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    full_output = proc.stdout + ("\nSTDERR:\n" + proc.stderr if proc.stderr else "")

    # Save raw terminal output file
    log_file = os.path.join(RAW_OUTPUTS_DIR, "terminal_execution.txt")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(full_output)
    print(f"Raw terminal log saved: {log_file}")

    all_lines = [line.rstrip() for line in full_output.splitlines() if line.strip() != ""]

    # Image 1: Full run overview
    screenshot1 = os.path.join(SCREENSHOTS_DIR, "terminal_run_summary.png")
    render_terminal_image(all_lines[:50], screenshot1, title="Windows Terminal (PowerShell) - python scripts/run_experiment.py")

    # Image 2: Final results summary table
    table_lines = []
    capture = False
    for line in all_lines:
        if "Summary (Buffer = 4x BDP" in line:
            capture = True
        if capture:
            table_lines.append(line)

    if not table_lines:
        table_lines = all_lines[-30:]

    screenshot2 = os.path.join(SCREENSHOTS_DIR, "terminal_summary_table.png")
    render_terminal_image(table_lines, screenshot2, title="Windows Terminal - QUIC-DC Results Table (4x BDP)")

    print("Terminal screenshots generated successfully.")

if __name__ == "__main__":
    main()
