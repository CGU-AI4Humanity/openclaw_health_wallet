#!/usr/bin/env python3
"""OpenClaw Health Assistant — macOS setup wizard."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "setup-wizard"))
sys.path.insert(0, str(ROOT / "apple-health-bridge"))

import state  # noqa: E402
from db_utils import ensure_database, ensure_local_user, expand_path, resolve_db_path  # noqa: E402
from env_utils import load_env, write_env  # noqa: E402

ENV_PATH = ROOT / "config" / ".env"
EXAMPLE_ENV = ROOT / "config" / ".env.example"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
DEFAULT_DB_STR = str(Path.home() / ".openclaw-health-assistant" / "openclaw_health.db")


class WizardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OpenClaw Health Assistant — Setup")
        self.geometry("780x680")
        self.pairing_server = None
        self.qr_photo = None
        self.logs: dict[str, scrolledtext.ScrolledText] = {}

        if not ENV_PATH.is_file() and EXAMPLE_ENV.is_file():
            shutil.copy(EXAMPLE_ENV, ENV_PATH)
            ENV_PATH.chmod(0o600)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.frames = {
            "prerequisites": self._build_prereq(),
            "sqlite_and_mcp_venv": self._build_sqlite(),
            "fhir_config": self._build_fhir(),
            "mcp_wired": self._build_mcp(),
            "apple_health_paired": self._build_apple(),
            "ollama_medgemma": self._build_ollama(),
            "ready": self._build_ready(),
        }
        for name in state.STEPS:
            self.notebook.add(self.frames[name], text=name.replace("_", " ").title()[:18])

        jump = state.first_incomplete()
        idx = state.STEPS.index(jump)
        self.notebook.select(idx)

    def _run(self, cmd: list[str], cwd: Path | None = None, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        p = subprocess.run(
            cmd,
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out

    def _log(self, step: str, text: str, *, clear: bool = False) -> None:
        widget = self.logs.get(step)
        if widget is None:
            return
        if clear:
            widget.delete("1.0", tk.END)
        widget.insert(tk.END, text.rstrip() + "\n")
        widget.see(tk.END)

    def _log_run(self, step: str, title: str, cmd: list[str], **run_kw) -> tuple[int, str]:
        self._log(step, f"▶ {title}\n  $ {' '.join(cmd)}")
        code, out = self._run(cmd, **run_kw)
        status = "OK" if code == 0 else f"FAILED (exit {code})"
        self._log(step, f"── {status} ──\n{out.strip() or '(no output)'}\n")
        return code, out

    def _output_panel(self, parent: ttk.Frame, step: str, height: int = 10) -> None:
        ttk.Label(parent, text="Action log", font=("", 10, "bold")).pack(anchor=tk.W, pady=(8, 0))
        box = scrolledtext.ScrolledText(parent, height=height, width=88, wrap=tk.WORD)
        box.pack(fill=tk.BOTH, expand=True, pady=4)
        self.logs[step] = box

    def _prepare_db(self, step: str) -> Path | None:
        env = load_env(ENV_PATH)
        db = resolve_db_path(env)
        ok, msg = ensure_database(db, SCHEMA_PATH)
        self._log(step, msg)
        if not ok:
            messagebox.showerror("Database", msg)
            return None
        canonical = str(db)
        if env.get("OPENCLAW_HEALTH_DB_PATH") != canonical:
            write_env(ENV_PATH, {"OPENCLAW_HEALTH_DB_PATH": canonical})
            self._log(step, f"Updated config/.env OPENCLAW_HEALTH_DB_PATH to:\n  {canonical}")
        return db

    def _build_prereq(self) -> ttk.Frame:
        step = "prerequisites"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 1 — Check installations", font=("", 14, "bold")).pack(anchor=tk.W)
        self._output_panel(f, step, height=12)

        def check() -> None:
            self._log(step, "Running prerequisite checks…", clear=True)
            ok = True
            for label, cmd in [
                ("Node 24+", ["bash", "-lc", "source ~/.nvm/nvm.sh 2>/dev/null; nvm use 24; node -v"]),
                ("Ollama", ["ollama", "--version"]),
                ("OpenClaw", ["bash", "-lc", "source ~/.nvm/nvm.sh 2>/dev/null; nvm use 24; openclaw --version"]),
                ("Python 3", [sys.executable, "--version"]),
                ("sqlite3", ["sqlite3", "--version"]),
            ]:
                code, out = self._run(cmd)
                status = "OK" if code == 0 else "MISSING"
                if code != 0:
                    ok = False
                self._log(step, f"[{status}] {label}: {out.strip()[:120]}")
            if ok:
                state.mark_done(step)
                self._log(step, "All prerequisites passed.")
                messagebox.showinfo("Done", "Prerequisites look good. Continue to SQLite step.")
            else:
                self._log(step, "Fix missing tools above, then run checks again.")

        ttk.Button(f, text="Run checks", command=check).pack(anchor=tk.W)
        return f

    def _build_sqlite(self) -> ttk.Frame:
        step = "sqlite_and_mcp_venv"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 2 — SQLite + MCP venv", font=("", 14, "bold")).pack(anchor=tk.W)
        self._output_panel(f, step, height=14)

        def run() -> None:
            self._log(step, "Starting database and MCP venv setup…", clear=True)
            db = self._prepare_db(step)
            if db is None:
                return
            code1, _ = self._log_run(
                step,
                "init_db.sh",
                ["./scripts/init_db.sh"],
                extra_env={"OPENCLAW_HEALTH_DB_PATH": str(db)},
            )
            code2, _ = self._log_run(step, "setup_sqlite_mcp_venv.sh", ["./scripts/setup_sqlite_mcp_venv.sh"])
            if code1 == 0 and code2 == 0:
                state.mark_done(step)
                self._log(step, "Step 2 complete.")
                messagebox.showinfo("Done", "Database and SQLite MCP venv ready.")
            else:
                messagebox.showerror("Error", "See action log for details.")

        ttk.Button(f, text="Initialize DB + venv", command=run).pack(anchor=tk.W, pady=8)
        return f

    def _build_fhir(self) -> ttk.Frame:
        step = "fhir_config"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 3 — FHIR MCP (admin API key + identity)", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Request X-API-Key from your FHIR MCP administrator. Stored only in config/.env (never Git).",
            wraplength=650,
        ).pack(anchor=tk.W, pady=4)

        env = load_env(ENV_PATH)
        self.fhir_key = tk.StringVar(value=env.get("FHIR_MCP_API_KEY", ""))
        self.fhir_fn = tk.StringVar(value=env.get("FHIR_PATIENT_FIRST_NAME", ""))
        self.fhir_ln = tk.StringVar(value=env.get("FHIR_PATIENT_LAST_NAME", ""))
        self.fhir_dob = tk.StringVar(value=env.get("FHIR_PATIENT_DOB", ""))

        for label, var in [
            ("API Key", self.fhir_key),
            ("First name", self.fhir_fn),
            ("Last name", self.fhir_ln),
            ("DOB (YYYY-MM-DD)", self.fhir_dob),
        ]:
            row = ttk.Frame(f)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, show="*" if "Key" in label else "").pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )

        self._output_panel(f, step, height=8)

        def save() -> None:
            db_path = expand_path(
                load_env(ENV_PATH).get("OPENCLAW_HEALTH_DB_PATH") or DEFAULT_DB_STR
            )
            write_env(
                ENV_PATH,
                {
                    "FHIR_MCP_BASE_URL": "https://mcp-fhir-server.com",
                    "FHIR_MCP_API_KEY": self.fhir_key.get().strip(),
                    "FHIR_PATIENT_FIRST_NAME": self.fhir_fn.get().strip(),
                    "FHIR_PATIENT_LAST_NAME": self.fhir_ln.get().strip(),
                    "FHIR_PATIENT_DOB": self.fhir_dob.get().strip(),
                    "OPENCLAW_HEALTH_DB_PATH": str(db_path),
                },
            )
            state.mark_done(step)
            key = self.fhir_key.get().strip()
            masked = "(empty)" if not key else f"{key[:4]}…{key[-4:]}" if len(key) > 8 else "****"
            self._log(step, "Saved config/.env:", clear=True)
            self._log(step, f"  FHIR_MCP_API_KEY: {masked}")
            self._log(step, f"  FHIR_PATIENT_FIRST_NAME: {self.fhir_fn.get().strip()}")
            self._log(step, f"  FHIR_PATIENT_LAST_NAME: {self.fhir_ln.get().strip()}")
            self._log(step, f"  FHIR_PATIENT_DOB: {self.fhir_dob.get().strip()}")
            self._log(step, f"  OPENCLAW_HEALTH_DB_PATH: {db_path}")
            messagebox.showinfo("Saved", f"Wrote {ENV_PATH}")

        ttk.Button(f, text="Save to config/.env", command=save).pack(anchor=tk.W, pady=8)
        return f

    def _build_mcp(self) -> ttk.Frame:
        step = "mcp_wired"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 4 — Wire MCP in OpenClaw", font=("", 14, "bold")).pack(anchor=tk.W)
        self._output_panel(f, step, height=16)

        def wire() -> None:
            self._log(step, "Registering MCP servers in OpenClaw…", clear=True)
            code, _ = self._log_run(
                step,
                "cleanup_mcp_servers.sh",
                [
                    "bash",
                    "-lc",
                    "source ~/.nvm/nvm.sh && nvm use 24 && set -a && source config/.env && set +a && ./scripts/cleanup_mcp_servers.sh",
                ],
            )
            if code == 0:
                state.mark_done(step)
                self._log(step, "Step 4 complete.")
                messagebox.showinfo("Done", "MCP servers registered. See action log for probe output.")
            else:
                messagebox.showerror("Error", "MCP wiring failed. See action log.")

        ttk.Button(f, text="Register SQLite + FHIR MCP", command=wire).pack(anchor=tk.W, pady=8)
        return f

    def _build_apple(self) -> ttk.Frame:
        step = "apple_health_paired"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 5 — Apple Health (QR + local API)", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Start pairing server, scan QR with iPhone Health Link app (see docs/SETUP_WIZARD_AND_APPLE_HEALTH.md).",
            wraplength=650,
        ).pack(anchor=tk.W, pady=4)
        self.qr_label = ttk.Label(f)
        self.qr_label.pack(pady=8)
        self.pair_status = tk.StringVar(value="Not started")
        ttk.Label(f, textvariable=self.pair_status).pack(anchor=tk.W)
        self._output_panel(f, step, height=10)

        def start_pairing() -> None:
            self._log(step, "Preparing Apple Health pairing…", clear=True)
            try:
                from pairing_server import PairingServer
            except ImportError as e:
                self._log(step, f"Import error: {e}")
                messagebox.showerror("Import error", str(e))
                return

            db = self._prepare_db(step)
            if db is None:
                return

            try:
                user_id, user_msg = ensure_local_user(db)
                self._log(step, user_msg)
            except Exception as e:
                self._log(step, f"ERROR opening database: {e}")
                messagebox.showerror("Database", str(e))
                return

            host = subprocess.getoutput("ipconfig getifaddr en0").strip() or "127.0.0.1"
            port = 8765

            def on_ok() -> None:
                state.mark_done(step)
                self.pair_status.set("Paired — health data received")
                self._log(step, "SUCCESS: iPhone POST /v1/health/sync completed.")

            if self.pairing_server:
                self.pairing_server.stop()
                self._log(step, "Stopped previous pairing server.")

            self.pairing_server = PairingServer(db, user_id, host="0.0.0.0", port=port, on_success=on_ok)
            self.pairing_server.start()
            url = self.pairing_server.pair_url.replace("127.0.0.1", host)

            write_env(
                ENV_PATH,
                {
                    "APPLE_HEALTH_API_BASE_URL": f"http://{host}:{port}",
                    "APPLE_HEALTH_DEVICE_TOKEN": self.pairing_server.token,
                },
            )
            self._log(step, f"Pairing server listening on 0.0.0.0:{port}")
            self._log(step, f"LAN host for iPhone: {host}")
            self._log(step, f"Pair URL:\n  {url}")
            self._log(step, f"Saved APPLE_HEALTH_* to {ENV_PATH}")

            try:
                import qrcode
                from PIL import Image, ImageTk

                qr = qrcode.make(url)
                buf = io.BytesIO()
                qr.save(buf, format="PNG")
                buf.seek(0)
                img = Image.open(buf)
                img = img.resize((280, 280))
                self.qr_photo = ImageTk.PhotoImage(img)
                self.qr_label.configure(image=self.qr_photo, text="")
                self._log(step, "QR code displayed (qrcode[pil] OK).")
            except ImportError:
                self.qr_label.configure(image="", text=f"Install: pip install qrcode[pil]\n\n{url}")
                self._log(step, "QR libs missing — URL shown on screen. pip install qrcode[pil]")

            self.pair_status.set(f"Waiting for iPhone… POST /v1/health/sync\n{url}")

        ttk.Button(f, text="Start pairing + show QR", command=start_pairing).pack(anchor=tk.W, pady=8)
        return f

    def _build_ollama(self) -> ttk.Frame:
        step = "ollama_medgemma"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 6 — Ollama + Qwen3 (MCP tools)", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Default agent uses qwen3:4b (Ollama tools). Optional: ollama pull medgemma:4b for plain chat only.",
            wraplength=650,
        ).pack(anchor=tk.W, pady=4)
        self._output_panel(f, step, height=14)

        def run() -> None:
            self._log(step, "Pulling Qwen3 and configuring OpenClaw for MCP…", clear=True)
            code1, _ = self._log_run(step, "ollama pull qwen3:4b", ["bash", "-lc", "ollama pull qwen3:4b"])
            code2, _ = self._log_run(
                step,
                "configure_qwen_tools.sh",
                ["bash", "-lc", "source ~/.nvm/nvm.sh && nvm use 24 && ./scripts/configure_qwen_tools.sh"],
            )
            if code2 == 0:
                state.mark_done(step)
                self._log(step, "Step 6 complete. Use: nvm use 24 && openclaw chat")
                messagebox.showinfo("Done", "Qwen3 configured for MCP tool calling.")
            else:
                messagebox.showerror("Error", "See action log for details.")
            if code1 != 0:
                self._log(step, "Note: ollama pull failed — model may already exist or Ollama may be offline.")

        ttk.Button(f, text="Pull qwen3:4b + configure OpenClaw", command=run).pack(anchor=tk.W, pady=8)
        return f

    def _build_ready(self) -> ttk.Frame:
        step = "ready"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Ready for OpenClaw", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Run: nvm use 24 && openclaw chat\nThen use docs/FIRST_RUN_PROMPTS.md for FHIR sync + Q&A.",
            wraplength=650,
        ).pack(anchor=tk.W, pady=8)
        self._output_panel(f, step, height=6)

        def finish() -> None:
            state.mark_done(step)
            self._log(step, "Setup marked complete.", clear=True)
            self._log(step, "Next: nvm use 24 && openclaw chat")
            self._log(step, "Prompts: docs/FIRST_RUN_PROMPTS.md")
            messagebox.showinfo("Complete", "Setup marked complete. See README Step 10–11.")

        ttk.Button(f, text="Mark setup complete", command=finish).pack(anchor=tk.W)
        return f


def main() -> None:
    app = WizardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
