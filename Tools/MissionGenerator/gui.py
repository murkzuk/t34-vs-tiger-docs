#!/usr/bin/env python3
"""
GUI for the Quick Mission Generator.

Thin wrapper around generate_mission.py - runs it as a subprocess with the
chosen faction/seed and shows the result. Does not duplicate or reimplement
any generation logic; the CLI script remains the single source of truth.
"""

import json
import os
import random
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GENERATOR = SCRIPT_DIR / "generate_mission.py"
ROSTER = SCRIPT_DIR / "roster.json"


def load_default_faction() -> str:
    try:
        with open(ROSTER, "r", encoding="utf-8") as f:
            config = json.load(f)
        faction = config.get("player_faction", "SOVIET")
        return faction if faction in ("SOVIET", "AXIS") else "SOVIET"
    except Exception:
        return "SOVIET"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TvT Quick Mission Generator")
        self.resizable(False, False)

        pad = {"padx": 10, "pady": 6}

        tk.Label(self, text="Play as:", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", **pad
        )
        self.faction_var = tk.StringVar(value=load_default_faction())
        faction_frame = tk.Frame(self)
        faction_frame.grid(row=0, column=1, sticky="w", **pad)
        tk.Radiobutton(faction_frame, text="Soviet", variable=self.faction_var, value="SOVIET").pack(side="left")
        tk.Radiobutton(faction_frame, text="Axis", variable=self.faction_var, value="AXIS").pack(side="left")

        tk.Label(self, text="Seed (optional):").grid(row=1, column=0, sticky="w", **pad)
        seed_frame = tk.Frame(self)
        seed_frame.grid(row=1, column=1, sticky="w", **pad)
        self.seed_var = tk.StringVar(value="")
        tk.Entry(seed_frame, textvariable=self.seed_var, width=12).pack(side="left")
        tk.Button(seed_frame, text="Random", command=self.randomize_seed).pack(side="left", padx=5)

        tk.Label(
            self,
            text="Leave blank for a fresh layout each time.\nSet a seed to replay the same layout later.",
            fg="gray", justify="left",
        ).grid(row=2, column=1, sticky="w", padx=10)

        self.generate_btn = tk.Button(
            self, text="Generate Mission", font=("Segoe UI", 11, "bold"),
            bg="#4a7a4a", fg="white", activebackground="#5b8f5b",
            command=self.generate,
        )
        self.generate_btn.grid(row=3, column=0, columnspan=2, pady=15, ipadx=20, ipady=6)

        tk.Label(self, text="Result:").grid(row=4, column=0, sticky="nw", padx=10)
        self.output = tk.Text(self, height=12, width=64, state="disabled", bg="#f4f4f4", wrap="word")
        self.output.grid(row=5, column=0, columnspan=2, padx=10, pady=5)

        bottom = tk.Frame(self)
        bottom.grid(row=6, column=0, columnspan=2, pady=10)
        tk.Button(bottom, text="Edit Roster (roster.json)", command=self.open_roster).pack(side="left", padx=5)
        tk.Button(bottom, text="Quit", command=self.destroy).pack(side="left", padx=5)

    def randomize_seed(self):
        self.seed_var.set(str(random.randint(1, 999999)))

    def set_output(self, text: str):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def generate(self):
        seed = self.seed_var.get().strip()
        if seed and not seed.isdigit():
            messagebox.showerror("Invalid seed", "Seed must be a whole number, or left blank.")
            return

        self.generate_btn.configure(state="disabled", text="Generating...")
        self.update_idletasks()

        cmd = [sys.executable, str(GENERATOR), "--faction", self.faction_var.get()]
        if seed:
            cmd += ["--seed", seed]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SCRIPT_DIR))
        except Exception as e:
            self.set_output(f"Failed to run generate_mission.py:\n{e}")
            self.generate_btn.configure(state="normal", text="Generate Mission")
            return

        output_text = ((result.stdout or "") + (result.stderr or "")).strip()
        self.set_output(output_text or "(no output)")
        self.generate_btn.configure(state="normal", text="Generate Mission")

        if result.returncode == 0:
            messagebox.showinfo(
                "Done",
                'Mission generated.\n\nLoad "Quick Mission (Generated)" in the Level Editor to play it.',
            )
        else:
            messagebox.showerror("Generation failed", "See the Result box for details.")

    def open_roster(self):
        try:
            os.startfile(str(ROSTER))
        except Exception as e:
            messagebox.showerror("Could not open roster.json", str(e))


if __name__ == "__main__":
    App().mainloop()
