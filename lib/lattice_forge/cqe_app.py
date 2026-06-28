"""
CQE Rule 30 Solver — Operable Desktop App
============================================
Author: Nicholas Barker

GUI for the unified CQE TarPit Ecology Rule 30 solver.

Usage:
    python -m lattice_forge.cqe_app
    or
    python src/lattice_forge/cqe_app.py

Workflow:
  1. Enter target depth N in the input field
  2. Click "Solve" — the CQE solver computes every bit from 1..N
     using the full TarPit Ecology (P03/P04 operators, Lucas decomposition,
     Gluon update, MORSR phase cycle, Dust/Triad formation, MirrorOperator
     for emergent terms).
  3. NO CA RUNS. Every bit displayed is computed by the solver.
  4. The step map renders the Rule 30 triangle, animated at a variable
     speed controlled by the speed slider (1 = slow, 100 = fast).
  5. Live readouts show: solver accuracy, Gluon state, phase cycle,
     wall statistics, Dust/Triad formation, K-window governance.

Architecture:
  CQERule30Solver  (cqe_rule30_solver.py)
    -> SolverResult per depth
        -> bit, Gluon, walls, dusts, phase
    -> step_map: full triangle from known bits

  CQEApp (this file)
    -> Tkinter GUI
    -> Background solver thread (non-blocking)
    -> Variable-speed canvas animation
    -> Live statistics panel
"""

from __future__ import annotations

import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lattice_forge.cqe_rule30_solver import CQERule30Solver


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class CQEApp:
    """Tkinter app for the CQE Rule 30 solver."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CQE Rule 30 Solver — TarPit Ecology Unified")
        self.root.geometry("1100x780")
        self.root.configure(bg="#0a0a14")

        self.solver_result: dict | None = None
        self.animation_running = False
        self.animation_thread: threading.Thread | None = None
        self.current_display_depth = 0

        self._build_ui()

    # ----- UI construction -----

    def _build_ui(self):
        # Top control panel
        top = tk.Frame(self.root, bg="#0a0a14", pady=8)
        top.pack(fill=tk.X, padx=10, pady=(10, 4))

        tk.Label(
            top, text="Target Depth N:",
            fg="#aaccff", bg="#0a0a14", font=("Consolas", 11, "bold")
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.n_var = tk.StringVar(value="64")
        n_entry = tk.Entry(
            top, textvariable=self.n_var, width=8,
            font=("Consolas", 11), bg="#1a1a2a", fg="#ffffff",
            insertbackground="#ffffff"
        )
        n_entry.pack(side=tk.LEFT, padx=(0, 14))

        self.solve_btn = tk.Button(
            top, text="SOLVE  (no CA runs)",
            command=self.on_solve,
            font=("Consolas", 10, "bold"),
            bg="#2266dd", fg="white", padx=14, pady=4,
            activebackground="#3377ee", relief=tk.FLAT
        )
        self.solve_btn.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(
            top, text="Animation speed:",
            fg="#aaccff", bg="#0a0a14", font=("Consolas", 10)
        ).pack(side=tk.LEFT, padx=(20, 4))

        self.speed_var = tk.IntVar(value=30)
        speed = tk.Scale(
            top, from_=1, to=100, orient=tk.HORIZONTAL,
            variable=self.speed_var, length=180,
            bg="#0a0a14", fg="#aaccff", troughcolor="#1a1a2a",
            highlightthickness=0, font=("Consolas", 8)
        )
        speed.pack(side=tk.LEFT)

        self.animate_btn = tk.Button(
            top, text="Play Step Map",
            command=self.on_animate,
            font=("Consolas", 10),
            bg="#229944", fg="white", padx=10, pady=4,
            activebackground="#33aa55", relief=tk.FLAT
        )
        self.animate_btn.pack(side=tk.LEFT, padx=(14, 4))

        self.stop_btn = tk.Button(
            top, text="Stop",
            command=self.on_stop,
            font=("Consolas", 10),
            bg="#993322", fg="white", padx=10, pady=4,
            activebackground="#aa4433", relief=tk.FLAT
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Status line
        self.status_var = tk.StringVar(value="Ready. Enter N and click SOLVE.")
        status = tk.Label(
            self.root, textvariable=self.status_var,
            fg="#ffaa33", bg="#0a0a14", font=("Consolas", 10, "bold"),
            anchor="w"
        )
        status.pack(fill=tk.X, padx=10, pady=(0, 6))

        # Main split: canvas (left) + stats panel (right)
        main = tk.Frame(self.root, bg="#0a0a14")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Left: triangle canvas
        canvas_frame = tk.Frame(main, bg="#000000", relief=tk.SUNKEN, bd=1)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        self.canvas = tk.Canvas(
            canvas_frame, bg="#000000",
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Right: stats panel
        stats_frame = tk.Frame(main, bg="#0a0a14", width=380)
        stats_frame.pack(side=tk.RIGHT, fill=tk.Y)
        stats_frame.pack_propagate(False)

        tk.Label(
            stats_frame, text="TarPit Ecology State",
            fg="#aaccff", bg="#0a0a14", font=("Consolas", 11, "bold")
        ).pack(anchor="w", pady=(0, 4))

        self.stats_text = scrolledtext.ScrolledText(
            stats_frame, width=44, height=42,
            font=("Consolas", 9),
            bg="#0d0d1a", fg="#cceeff",
            insertbackground="#ffffff",
            wrap=tk.WORD
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        # Bottom: bit sequence display
        bottom = tk.Frame(self.root, bg="#0a0a14")
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(
            bottom, text="Computed bit sequence:",
            fg="#aaccff", bg="#0a0a14", font=("Consolas", 10, "bold")
        ).pack(anchor="w")

        self.bit_seq_var = tk.StringVar(value="(press SOLVE)")
        bit_label = tk.Label(
            bottom, textvariable=self.bit_seq_var,
            fg="#ccffcc", bg="#0d0d1a", font=("Consolas", 10),
            anchor="w", padx=8, pady=6, relief=tk.SUNKEN, bd=1
        )
        bit_label.pack(fill=tk.X, pady=(2, 0))

    # ----- Event handlers -----

    def on_solve(self):
        """Solve the Rule 30 bit sequence using the CQE TarPit Ecology."""
        try:
            N = int(self.n_var.get())
        except ValueError:
            self.status_var.set("ERROR: N must be an integer.")
            return

        if N < 1 or N > 500:
            self.status_var.set("ERROR: N must be between 1 and 500.")
            return

        self.solve_btn.config(state=tk.DISABLED, text="Solving...")
        self.status_var.set(
            f"Running CQE solver for N=1..{N} (TarPit Ecology, NO CA runs)..."
        )
        self.root.update_idletasks()

        # Run in background thread
        def solve_task():
            t0 = time.time()
            solver = CQERule30Solver()
            try:
                result = solver.solve_sequence(N)
                elapsed = time.time() - t0
                result["_elapsed_seconds"] = elapsed
                self.root.after(0, lambda: self._on_solve_complete(result))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda: self._on_solve_error(msg))

        threading.Thread(target=solve_task, daemon=True).start()

    def _on_solve_complete(self, result: dict):
        self.solver_result = result
        N = result["N"]
        defects = result["defects"]
        elapsed = result.get("_elapsed_seconds", 0)

        self.status_var.set(
            f"DONE: N={N}, defects={defects}/{N} "
            f"(accuracy {result['accuracy']:.4f}), elapsed {elapsed:.2f}s. "
            f"Press 'Play Step Map' to visualize."
        )
        self.solve_btn.config(state=tk.NORMAL, text="SOLVE  (no CA runs)")

        # Display bit sequence
        bits = result["bits"]
        bit_str = "".join(str(b) for b in bits)
        if len(bit_str) > 120:
            bit_str = bit_str[:60] + " ... " + bit_str[-60:]
        self.bit_seq_var.set(bit_str)

        # Update stats panel
        self._update_stats_panel(result)

        # Draw the complete triangle immediately (static)
        self._draw_step_map(len(result["step_map"]) - 1)

    def _on_solve_error(self, msg: str):
        self.status_var.set(f"ERROR: {msg}")
        self.solve_btn.config(state=tk.NORMAL, text="SOLVE  (no CA runs)")

    def on_animate(self):
        if not self.solver_result:
            self.status_var.set("Solve first, then animate.")
            return
        if self.animation_running:
            return

        self.animation_running = True
        self.current_display_depth = 0
        self.animate_btn.config(text="Playing...")

        def animate_task():
            step_map = self.solver_result["step_map"]
            total = len(step_map)
            while self.animation_running and self.current_display_depth < total:
                d = self.current_display_depth
                self.root.after(0, lambda dd=d: self._draw_step_map(dd))
                # Variable speed: 1=slow (250ms), 100=fast (5ms)
                speed = self.speed_var.get()
                delay = max(0.005, 0.255 - (speed / 100.0) * 0.25)
                time.sleep(delay)
                self.current_display_depth += 1
            self.root.after(0, self._on_animate_complete)

        self.animation_thread = threading.Thread(target=animate_task, daemon=True)
        self.animation_thread.start()

    def on_stop(self):
        self.animation_running = False
        self.animate_btn.config(text="Play Step Map")

    def _on_animate_complete(self):
        self.animation_running = False
        self.animate_btn.config(text="Play Step Map")
        self.status_var.set(
            self.status_var.get() + "  [animation complete]"
        )

    # ----- Stats panel -----

    def _update_stats_panel(self, result: dict):
        N = result["N"]
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)

        lines = []
        lines.append(f"DEPTH N = {N}")
        lines.append(f"ACCURACY: {result['accuracy']:.4f}")
        lines.append(f"DEFECTS:  {result['defects']}/{N}")
        lines.append(f"ELAPSED:  {result.get('_elapsed_seconds', 0):.3f}s")
        lines.append("")

        lines.append("--- WALL STATISTICS ---")
        lines.append(f"Output walls (real):  {result['total_output_walls']}")
        lines.append(f"Error walls (skip):   {result['total_skip_pads']}")
        lines.append(f"Mirror resolved:      {result['total_mirror_resolved']}")
        lines.append(f"Mean skip fraction:   {result['mean_skip_fraction']:.3f}")
        lines.append("")

        lines.append("--- BOND CHEMISTRY ---")
        lines.append(f"Dust formations:      {result['total_dusts']}")
        lines.append(f"Triad closures:       {result['total_triads']}")
        lines.append(f"(N|-N bonded pairs, Lie conjugate contacts)")
        lines.append("")

        lines.append("--- GLUON STATE ---")
        sectors = result["gluon_sector"]
        vac_count = sectors.count("Vacuum")
        exc_count = sectors.count("Excited")
        lines.append(f"Vacuum phases:        {vac_count}")
        lines.append(f"Excited phases:       {exc_count}")
        lines.append(f"Final C_accumulated:  {result['gluon_accumulated'][-1]}")
        lines.append("")

        lines.append("--- MORSR PHASE CYCLE (Z4) ---")
        phases = result["phases"]
        phase_counts = {}
        for p in phases:
            phase_counts[p] = phase_counts.get(p, 0) + 1
        for ph in ["observe", "reflect", "synthesize", "recurse"]:
            lines.append(f"  {ph:12s}: {phase_counts.get(ph, 0)}")
        lines.append("")

        lines.append("--- ARCH HEIGHT (digit residuals) ---")
        arch = result["arch_history"][:30]
        lines.append("  " + " ".join(str(d) for d in arch))
        if len(result["arch_history"]) > 30:
            lines.append(f"  ... ({len(result['arch_history'])} total)")
        lines.append("")

        lines.append("--- K-WINDOW GOVERNANCE (P01) ---")
        lines.append(f"K_max: {result['K_max']}")
        lines.append(result["K_window_note"])
        lines.append("")

        lines.append("--- THEOREMS ACTIVE ---")
        for t in result["theorems"]:
            wrapped = self._wrap_text(t, 42)
            for line in wrapped:
                lines.append(f"  {line}")

        self.stats_text.insert(tk.END, "\n".join(lines))
        self.stats_text.config(state=tk.DISABLED)

    def _wrap_text(self, text: str, width: int) -> list[str]:
        words = text.split()
        lines = []
        current = ""
        for w in words:
            if len(current) + len(w) + 1 <= width:
                current = (current + " " + w).strip()
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines

    # ----- Canvas rendering -----

    def _draw_step_map(self, up_to_depth: int):
        """Render the Rule 30 triangle up to depth `up_to_depth`."""
        if not self.solver_result:
            return

        self.canvas.delete("all")
        step_map = self.solver_result["step_map"]
        bits = self.solver_result["bits"]
        N = self.solver_result["N"]

        # Canvas dimensions
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 400)

        # Cell size: fit triangle width 2N+1 cells
        max_width = 2 * N + 1
        cell_size = max(2, min(int(w / max_width), int(h / (N + 1))))
        if cell_size < 1:
            cell_size = 1

        # Triangle center
        cx = w // 2

        max_d = min(up_to_depth, len(step_map) - 1)
        for d in range(max_d + 1):
            row = step_map[d]
            row_width = len(row)
            row_center = row_width // 2
            y = d * cell_size + 4

            if y + cell_size > h:
                break

            for i, bit in enumerate(row):
                x = cx + (i - row_center) * cell_size
                if x < 0 or x + cell_size > w:
                    continue
                # Highlight the center column (the solved bit)
                is_center = (i == row_center)
                if bit == 1:
                    fill = "#ffcc33" if is_center else "#99ddff"
                else:
                    fill = "#664422" if is_center else "#0a1a2a"
                self.canvas.create_rectangle(
                    x, y, x + cell_size, y + cell_size,
                    fill=fill, outline=""
                )

        # Display current depth indicator
        self.canvas.create_text(
            8, 4, anchor="nw",
            text=f"Displayed depth: {max_d+1} / {N+1}    "
                 f"(yellow = solver-computed center column)",
            fill="#aaccff", font=("Consolas", 9)
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass
    app = CQEApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
