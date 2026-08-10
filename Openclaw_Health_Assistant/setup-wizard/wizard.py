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
from db_utils import ensure_apple_health_tables, ensure_database, ensure_local_user, expand_path, resolve_db_path  # noqa: E402
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
        self.step_badges: dict[str, ttk.Label] = {}

        if not ENV_PATH.is_file() and EXAMPLE_ENV.is_file():
            shutil.copy(EXAMPLE_ENV, ENV_PATH)
            ENV_PATH.chmod(0o600)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 4))

        self.frames = {
            "prerequisites": self._build_prereq(),
            "demo_db_and_health_mcp": self._build_demo_db(),
            "demo_patient": self._build_demo_patient(),
            "mcp_wired": self._build_mcp(),
            "apple_health_paired": self._build_apple(),
            "ollama_qwen": self._build_ollama(),
            "ready": self._build_ready(),
        }
        for name in state.STEPS:
            self.notebook.add(self.frames[name], text=state.tab_label(name))

        self._restore_saved_logs()
        self._refresh_tab_titles()
        self._update_all_badges()

        if state.all_done():
            self.notebook.select(0)
        else:
            jump = state.first_incomplete()
            self.notebook.select(state.STEPS.index(jump))

        footer = ttk.Frame(self, padding=(12, 8))
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(footer, text="Exit setup wizard", command=self._exit_wizard).pack(side=tk.RIGHT)

        self.protocol("WM_DELETE_WINDOW", self._exit_wizard)

    def _exit_wizard(self) -> None:
        for step in state.STEPS:
            self._persist_log(step)
        if self.pairing_server:
            try:
                self.pairing_server.stop()
            except Exception:
                pass
            self.pairing_server = None
        self.destroy()

    def _finish_step(self, step: str, **meta) -> None:
        self._persist_log(step)
        state.mark_done(step, log_text=state.get_log(step), **meta)
        self._refresh_tab_titles()
        self._update_badge(step)

    def _persist_log(self, step: str) -> None:
        widget = self.logs.get(step)
        if widget is None:
            return
        text = widget.get("1.0", tk.END).strip()
        if text:
            state.set_log(step, text)

    def _restore_saved_logs(self) -> None:
        for step in state.STEPS:
            text = state.get_log(step)
            if not text:
                continue
            widget = self.logs.get(step)
            if widget is None:
                continue
            widget.delete("1.0", tk.END)
            widget.insert(tk.END, text + "\n")

    def _refresh_tab_titles(self) -> None:
        for i, name in enumerate(state.STEPS):
            self.notebook.tab(i, text=state.tab_label(name))

    def _step_banner(self, parent: ttk.Frame, step: str) -> ttk.Label:
        badge = ttk.Label(parent, text="", font=("", 11, "bold"))
        badge.pack(anchor=tk.W, pady=(0, 4))
        self.step_badges[step] = badge
        return badge

    def _update_badge(self, step: str) -> None:
        badge = self.step_badges.get(step)
        if badge is None:
            return
        if state.is_done(step):
            at = state.load().get("completed_at", {}).get(step, "")
            badge.configure(text=f"✓ Complete{f' — {at}' if at else ''}")
        else:
            badge.configure(text="Pending — run the action below")

    def _update_all_badges(self) -> None:
        for step in state.STEPS:
            self._update_badge(step)

    def _bash_openclaw(self, script: str) -> list[str]:
        return [
            "bash",
            "-lc",
            f"source ~/.nvm/nvm.sh && nvm use 24 && set -a && source config/.env && set +a && {script}",
        ]

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
        self._persist_log(step)

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
        ensure_apple_health_tables(db)
        canonical = str(db)
        env_updates = {"HEALTH_DB_PATH": canonical, "OPENCLAW_HEALTH_DB_PATH": canonical}
        if load_env(ENV_PATH).get("HEALTH_DB_PATH") != canonical or load_env(ENV_PATH).get(
            "OPENCLAW_HEALTH_DB_PATH"
        ) != canonical:
            write_env(ENV_PATH, env_updates)
            self._log(step, f"Synced HEALTH_DB_PATH + OPENCLAW_HEALTH_DB_PATH:\n  {canonical}")
        return db

    def _build_prereq(self) -> ttk.Frame:
        step = "prerequisites"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 1 — Check installations", font=("", 14, "bold")).pack(anchor=tk.W)
        self._step_banner(f, step)
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
                self._finish_step(step)
                self._log(step, "All prerequisites passed.")
                messagebox.showinfo("Done", "Prerequisites look good.")
            else:
                self._log(step, "Fix missing tools above, then run checks again.")

        def run_all() -> None:
            self._run_complete_setup()

        ttk.Button(f, text="Run checks", command=check).pack(anchor=tk.W, pady=4)
        ttk.Button(f, text="Run complete setup (all steps)", command=run_all).pack(anchor=tk.W, pady=4)
        return f

    def _build_demo_db(self) -> ttk.Frame:
        step = "demo_db_and_health_mcp"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 2 — Demo database + health MCP venv", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Seeds synthetic CSV data (Brandon Medina sqlite_plus_custom_mcp) and installs the typed health MCP server.",
            wraplength=650,
        ).pack(anchor=tk.W, pady=4)
        self._step_banner(f, step)
        self._output_panel(f, step, height=14)

        def run() -> None:
            self._log(step, "Seeding demo DB and health MCP venv…", clear=True)
            code1, _ = self._log_run(step, "setup_health_mcp_venv.sh", ["./scripts/setup_health_mcp_venv.sh"])
            code2, _ = self._log_run(step, "seed_demo_database.sh", ["./scripts/seed_demo_database.sh"])
            if code1 == 0 and code2 == 0:
                self._finish_step(step)
                self._log(step, "Step 2 complete.")
                messagebox.showinfo("Done", "Demo DB and health MCP venv ready.")
            else:
                messagebox.showerror("Error", "See action log for details.")

        ttk.Button(f, text="Seed demo DB + venv", command=run).pack(anchor=tk.W, pady=8)
        return f

    def _build_demo_patient(self) -> ttk.Frame:
        step = "demo_patient"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 3 — Active demo patient", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Demo patient PT0001 + FHIR identity (local DB matches provider demo patient).",
            wraplength=650,
        ).pack(anchor=tk.W, pady=4)
        self._step_banner(f, step)

        env = load_env(ENV_PATH)
        self.health_db = tk.StringVar(
            value=env.get("HEALTH_DB_PATH", str(Path.home() / ".openclaw-health-assistant" / "final_project.db"))
        )
        self.health_user = tk.StringVar(value=env.get("HEALTH_ACTIVE_USER_ID", "PT0001"))
        self.fhir_fn = tk.StringVar(value=env.get("FHIR_PATIENT_FIRST_NAME", "Ruben688"))
        self.fhir_ln = tk.StringVar(value=env.get("FHIR_PATIENT_LAST_NAME", "Waters156"))
        self.fhir_dob = tk.StringVar(value=env.get("FHIR_PATIENT_DOB", "1972-08-02"))
        self.fhir_key = tk.StringVar(value=env.get("FHIR_MCP_API_KEY", ""))

        for label, var, secret in [
            ("HEALTH_DB_PATH", self.health_db, False),
            ("HEALTH_ACTIVE_USER_ID", self.health_user, False),
            ("FHIR_PATIENT_FIRST_NAME", self.fhir_fn, False),
            ("FHIR_PATIENT_LAST_NAME", self.fhir_ln, False),
            ("FHIR_PATIENT_DOB", self.fhir_dob, False),
            ("FHIR_MCP_API_KEY", self.fhir_key, True),
        ]:
            row = ttk.Frame(f)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, show="*" if secret else "").pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._output_panel(f, step, height=8)

        def save() -> None:
            db_path = expand_path(self.health_db.get().strip())
            active = self.health_user.get().strip() or "PT0001"
            write_env(
                ENV_PATH,
                {
                    "HEALTH_DB_PATH": str(db_path),
                    "OPENCLAW_HEALTH_DB_PATH": str(db_path),
                    "HEALTH_ACTIVE_USER_ID": active,
                    "FHIR_PATIENT_FIRST_NAME": self.fhir_fn.get().strip(),
                    "FHIR_PATIENT_LAST_NAME": self.fhir_ln.get().strip(),
                    "FHIR_PATIENT_DOB": self.fhir_dob.get().strip(),
                    "FHIR_MCP_API_KEY": self.fhir_key.get().strip(),
                    "FHIR_MCP_BASE_URL": env.get("FHIR_MCP_BASE_URL", "https://mcp-fhir-server.com"),
                },
            )
            self._log(step, "Saved config/.env:", clear=True)
            self._log(step, f"  HEALTH_DB_PATH: {db_path}")
            self._log(step, f"  HEALTH_ACTIVE_USER_ID: {active}")
            self._log(step, f"  FHIR patient: {self.fhir_fn.get().strip()} {self.fhir_ln.get().strip()} ({self.fhir_dob.get().strip()})")
            code, out = self._run(["python3", str(ROOT / "scripts/sync_demo_patient_from_env.py")])
            self._log(step, out.strip() or "(sync skipped)")
            if code == 0:
                self._finish_step(step)
                messagebox.showinfo("Saved", f"Wrote {ENV_PATH}")
            else:
                messagebox.showerror("Error", out.strip() or "Sync failed")

        ttk.Button(f, text="Save patient + sync SQLite", command=save).pack(anchor=tk.W, pady=8)
        return f

    def _build_mcp(self) -> ttk.Frame:
        step = "mcp_wired"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 4 — Wire MCP in OpenClaw", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Registers health MCP (+ fhir-remote when API key set). Chat uses health__* tools only.",
            wraplength=650,
        ).pack(anchor=tk.W, pady=4)
        self._step_banner(f, step)
        self._output_panel(f, step, height=16)

        def wire() -> None:
            self._log(step, "Registering MCP servers in OpenClaw…", clear=True)
            code, _ = self._log_run(step, "cleanup_mcp_servers.sh", self._bash_openclaw("./scripts/cleanup_mcp_servers.sh"))
            if code == 0:
                self._finish_step(step)
                self._log(step, "Step 4 complete.")
                messagebox.showinfo("Done", "MCP registered. See action log.")
            else:
                messagebox.showerror("Error", "MCP wiring failed. See action log.")

        ttk.Button(f, text="Register MCP (health + FHIR)", command=wire).pack(anchor=tk.W, pady=8)
        return f

    def _build_apple(self) -> ttk.Frame:
        step = "apple_health_paired"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 5 — Apple Health (optional)", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Optional: QR pairing for live Apple Health sync during your presentation.\n"
            "Tonight you may Skip; tomorrow use Start pairing + show QR (keep this window open while the iPhone syncs).",
            wraplength=650,
        ).pack(anchor=tk.W, pady=4)
        self._step_banner(f, step)
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
                user_id, user_msg = ensure_local_user(db, env=load_env(ENV_PATH))
                self._log(step, user_msg)
            except Exception as e:
                self._log(step, f"ERROR opening database: {e}")
                messagebox.showerror("Database", str(e))
                return

            host = subprocess.getoutput("ipconfig getifaddr en0").strip()
            if not host:
                host = subprocess.getoutput("ipconfig getifaddr en1").strip()
            if not host:
                host = "127.0.0.1"
            port = 8765

            def on_ok() -> None:
                self.pair_status.set("Paired — health data received")
                self._log(step, "SUCCESS: iPhone POST /v1/health/sync completed.")
                self._finish_step(step, apple_health="paired")

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

        ttk.Button(f, text="Start pairing + show QR", command=start_pairing).pack(anchor=tk.W, pady=4)

        def skip() -> None:
            self._log(step, "Apple Health: optional for demo.", clear=True)
            self._log(step, "Using synthetic demo vitals/labs for PT0001. Health Link can pair live during demo.")
            self._finish_step(step, apple_health="skipped")
            messagebox.showinfo("Skipped", "Step marked complete for demo walkthrough.")

        ttk.Button(f, text="Skip (demo data only)", command=skip).pack(anchor=tk.W, pady=4)
        return f

    def _build_ollama(self) -> ttk.Frame:
        step = "ollama_qwen"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 6 — Ollama + Qwen 2.5 (health MCP)", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Pull qwen2.5:7b and configure OpenClaw (tool allowlist + docs/AGENTS.md workspace).",
            wraplength=650,
        ).pack(anchor=tk.W, pady=4)
        self._step_banner(f, step)
        self._output_panel(f, step, height=14)

        def run() -> None:
            self._log(step, "Pulling Qwen 2.5 and configuring OpenClaw…", clear=True)
            code1, _ = self._log_run(step, "ollama pull qwen2.5:7b", ["bash", "-lc", "ollama pull qwen2.5:7b"])
            code2, _ = self._log_run(
                step,
                "configure_health_assistant.sh",
                self._bash_openclaw("./scripts/configure_health_assistant.sh"),
            )
            if code2 == 0:
                self._finish_step(step)
                self._log(step, "Step 6 complete. Use: nvm use 24 && openclaw chat")
                messagebox.showinfo("Done", "Qwen 2.5 configured for health MCP.")
            else:
                messagebox.showerror("Error", "See action log for details.")
            if code1 != 0:
                self._log(step, "Note: ollama pull failed — model may already exist or Ollama may be offline.")

        ttk.Button(f, text="Pull qwen2.5:7b + configure OpenClaw", command=run).pack(anchor=tk.W, pady=8)
        return f

    def _build_ready(self) -> ttk.Frame:
        step = "ready"
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Ready for OpenClaw", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="All steps complete — open each tab to review saved action logs.\n"
            "Then: nvm use 24 && openclaw chat",
            wraplength=650,
        ).pack(anchor=tk.W, pady=8)
        self._step_banner(f, step)
        self._output_panel(f, step, height=8)

        def finish() -> None:
            self._log(step, "Setup marked complete.", clear=True)
            self._log(step, "Next: nvm use 24 && openclaw chat")
            self._log(step, "Docs: docs/FIRST_RUN_PROMPTS.md")
            self._finish_step(step)
            messagebox.showinfo("Complete", "Setup complete.")

        def verify_demo() -> None:
            self._log(step, "Re-verifying OpenClaw stack…", clear=True)
            for title, cmd in [
                ("model", self._bash_openclaw("openclaw config get agents.defaults.model.primary")),
                ("mcp", self._bash_openclaw("openclaw mcp status --verbose")),
                ("patient", ["python3", str(ROOT / "scripts/sync_demo_patient_from_env.py")]),
            ]:
                code, out = self._run(cmd)
                self._log(step, f"[{'OK' if code == 0 else 'WARN'}] {title}:\n{out.strip()[:2000]}\n")
            self._persist_log(step)

        ttk.Button(f, text="Mark setup complete", command=finish).pack(anchor=tk.W, pady=4)
        ttk.Button(f, text="Re-verify setup", command=verify_demo).pack(anchor=tk.W, pady=4)
        return f

    def _run_complete_setup(self) -> None:
        if not messagebox.askyesno(
            "Run complete setup",
            "Run all wizard steps now? (Re-seeds demo DB, wires MCP, configures Qwen 2.5.)",
        ):
            return
        steps = [
            ("prerequisites", self._setup_step_prereq),
            ("demo_db_and_health_mcp", self._setup_step_demo_db),
            ("demo_patient", self._setup_step_patient),
            ("mcp_wired", self._setup_step_mcp),
            ("apple_health_paired", self._setup_step_apple_skip),
            ("ollama_qwen", self._setup_step_ollama),
            ("ready", self._setup_step_ready),
        ]
        for _name, fn in steps:
            if not fn():
                messagebox.showerror("Setup stopped", "See the action log on the failed tab.")
                return
        messagebox.showinfo("Complete", "All steps done. Review each tab — logs are saved for tomorrow's demo.")

    def _setup_step_prereq(self) -> bool:
        step = "prerequisites"
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
            ok = ok and code == 0
            self._log(step, f"[{status}] {label}: {out.strip()[:120]}")
        if ok:
            self._finish_step(step)
        return ok

    def _setup_step_demo_db(self) -> bool:
        step = "demo_db_and_health_mcp"
        self._log(step, "Seeding demo DB and health MCP venv…", clear=True)
        c1, _ = self._log_run(step, "setup_health_mcp_venv.sh", ["./scripts/setup_health_mcp_venv.sh"])
        c2, _ = self._log_run(step, "seed_demo_database.sh", ["./scripts/seed_demo_database.sh"])
        if c1 == 0 and c2 == 0:
            self._finish_step(step)
            return True
        return False

    def _setup_step_patient(self) -> bool:
        step = "demo_patient"
        env = load_env(ENV_PATH)
        db = str(
            expand_path(
                self.health_db.get()
                or env.get("HEALTH_DB_PATH")
                or str(Path.home() / ".openclaw-health-assistant/final_project.db")
            )
        )
        write_env(
            ENV_PATH,
            {
                "HEALTH_DB_PATH": db,
                "OPENCLAW_HEALTH_DB_PATH": db,
                "HEALTH_ACTIVE_USER_ID": self.health_user.get().strip() or env.get("HEALTH_ACTIVE_USER_ID", "PT0001"),
                "FHIR_PATIENT_FIRST_NAME": self.fhir_fn.get().strip() or env.get("FHIR_PATIENT_FIRST_NAME", ""),
                "FHIR_PATIENT_LAST_NAME": self.fhir_ln.get().strip() or env.get("FHIR_PATIENT_LAST_NAME", ""),
                "FHIR_PATIENT_DOB": self.fhir_dob.get().strip() or env.get("FHIR_PATIENT_DOB", ""),
                "FHIR_MCP_API_KEY": self.fhir_key.get().strip() or env.get("FHIR_MCP_API_KEY", ""),
                "FHIR_MCP_BASE_URL": env.get("FHIR_MCP_BASE_URL", "https://mcp-fhir-server.com"),
            },
        )
        self._log(step, "Saved patient + FHIR identity to config/.env", clear=True)
        code, out = self._run(["python3", str(ROOT / "scripts/sync_demo_patient_from_env.py")])
        self._log(step, out.strip())
        if code != 0:
            return False
        self._finish_step(step)
        return True

    def _setup_step_mcp(self) -> bool:
        step = "mcp_wired"
        self._log(step, "Registering MCP…", clear=True)
        code, _ = self._log_run(step, "cleanup_mcp_servers.sh", self._bash_openclaw("./scripts/cleanup_mcp_servers.sh"))
        if code == 0:
            self._finish_step(step)
            return True
        return False

    def _setup_step_apple_skip(self) -> bool:
        step = "apple_health_paired"
        self._log(step, "Apple Health optional — marked complete for demo.", clear=True)
        self._log(step, "Use 'Start pairing + QR' before a live Health Link demo, or skip with synthetic data.")
        self._finish_step(step, apple_health="skipped")
        return True

    def _setup_step_ollama(self) -> bool:
        step = "ollama_qwen"
        self._log(step, "Configuring Qwen 2.5…", clear=True)
        self._log_run(step, "configure_health_assistant.sh", self._bash_openclaw("./scripts/configure_health_assistant.sh"))
        code, out = self._run(self._bash_openclaw("openclaw config get agents.defaults.model"))
        self._log(step, out.strip())
        if code == 0 and "qwen2.5" in out.lower():
            self._finish_step(step)
            return True
        return False

    def _setup_step_ready(self) -> bool:
        step = "ready"
        self._log(step, "Setup complete.", clear=True)
        self._finish_step(step)
        return True


def main() -> None:
    app = WizardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
