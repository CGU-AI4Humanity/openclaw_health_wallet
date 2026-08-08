#!/usr/bin/env python3
"""OpenClaw Health Assistant — macOS setup wizard."""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "setup-wizard"))
sys.path.insert(0, str(ROOT / "apple-health-bridge"))

import state  # noqa: E402
from env_utils import load_env, write_env  # noqa: E402

ENV_PATH = ROOT / "config" / ".env"
EXAMPLE_ENV = ROOT / "config" / ".env.example"


class WizardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OpenClaw Health Assistant — Setup")
        self.geometry("720x560")
        self.pairing_server = None
        self.qr_photo = None

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

    def _run(self, cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
        p = subprocess.run(
            cmd,
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out

    def _build_prereq(self) -> ttk.Frame:
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 1 — Check installations", font=("", 14, "bold")).pack(anchor=tk.W)
        self.prereq_text = tk.Text(f, height=14, width=80)
        self.prereq_text.pack(fill=tk.BOTH, expand=True, pady=8)

        def check() -> None:
            lines = []
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
                lines.append(f"[{status}] {label}: {out.strip()[:80]}")
            self.prereq_text.delete("1.0", tk.END)
            self.prereq_text.insert(tk.END, "\n".join(lines))
            if ok:
                state.mark_done("prerequisites")
                messagebox.showinfo("Done", "Prerequisites look good. Continue to SQLite step.")

        ttk.Button(f, text="Run checks", command=check).pack(anchor=tk.W)
        return f

    def _build_sqlite(self) -> ttk.Frame:
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 2 — SQLite + MCP venv", font=("", 14, "bold")).pack(anchor=tk.W)

        def run() -> None:
            code1, o1 = self._run(["./scripts/init_db.sh"])
            code2, o2 = self._run(["./scripts/setup_sqlite_mcp_venv.sh"])
            if code1 == 0 and code2 == 0:
                state.mark_done("sqlite_and_mcp_venv")
                messagebox.showinfo("Done", "Database and SQLite MCP venv ready.")
            else:
                messagebox.showerror("Error", o1 + "\n" + o2)

        ttk.Button(f, text="Initialize DB + venv", command=run).pack(anchor=tk.W, pady=8)
        return f

    def _build_fhir(self) -> ttk.Frame:
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

        def save() -> None:
            write_env(
                ENV_PATH,
                {
                    "FHIR_MCP_BASE_URL": "https://mcp-fhir-server.com",
                    "FHIR_MCP_API_KEY": self.fhir_key.get().strip(),
                    "FHIR_PATIENT_FIRST_NAME": self.fhir_fn.get().strip(),
                    "FHIR_PATIENT_LAST_NAME": self.fhir_ln.get().strip(),
                    "FHIR_PATIENT_DOB": self.fhir_dob.get().strip(),
                    "OPENCLAW_HEALTH_DB_PATH": str(
                        Path.home() / ".openclaw-health-assistant" / "openclaw_health.db"
                    ),
                },
            )
            state.mark_done("fhir_config")
            messagebox.showinfo("Saved", f"Wrote {ENV_PATH}")

        ttk.Button(f, text="Save to config/.env", command=save).pack(anchor=tk.W, pady=12)
        return f

    def _build_mcp(self) -> ttk.Frame:
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 4 — Wire MCP in OpenClaw", font=("", 14, "bold")).pack(anchor=tk.W)

        def wire() -> None:
            code, out = self._run(
                ["bash", "-lc", "source ~/.nvm/nvm.sh && nvm use 24 && set -a && source config/.env && set +a && ./scripts/wire_mcp_servers.sh"]
            )
            if code == 0:
                state.mark_done("mcp_wired")
                messagebox.showinfo("Done", "MCP servers registered.\n" + out[-500:])
            else:
                messagebox.showerror("Error", out[-800:])

        ttk.Button(f, text="Register SQLite + FHIR MCP", command=wire).pack(anchor=tk.W, pady=8)
        return f

    def _build_apple(self) -> ttk.Frame:
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

        def start_pairing() -> None:
            try:
                from pairing_server import PairingServer
            except ImportError as e:
                messagebox.showerror("Import error", str(e))
                return

            env = load_env(ENV_PATH)
            db = Path(
                env.get(
                    "OPENCLAW_HEALTH_DB_PATH",
                    env.get(
                        "MYWELLWALLET_DB_PATH",
                        str(Path.home() / ".openclaw-health-assistant" / "openclaw_health.db"),
                    ),
                )
            )

            import sqlite3

            conn = sqlite3.connect(str(db))
            row = conn.execute("SELECT id FROM users ORDER BY created_at DESC LIMIT 1").fetchone()
            conn.close()
            user_id = row[0] if row else "local_user_1"
            if not row:
                conn = sqlite3.connect(str(db))
                conn.execute(
                    "INSERT OR IGNORE INTO users (id, name, email, created_at, updated_at) VALUES (?,?,?,?,?)",
                    (user_id, "Local User", "local@openclaw.health", "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
                )
                conn.commit()
                conn.close()

            host = subprocess.getoutput("ipconfig getifaddr en0").strip() or "127.0.0.1"
            port = 8765

            def on_ok() -> None:
                state.mark_done("apple_health_paired")
                self.pair_status.set("Paired — health data received")

            if self.pairing_server:
                self.pairing_server.stop()
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

            try:
                import qrcode
                from PIL import ImageTk

                qr = qrcode.make(url)
                buf = io.BytesIO()
                qr.save(buf, format="PNG")
                buf.seek(0)
                from PIL import Image

                img = Image.open(buf)
                img = img.resize((280, 280))
                self.qr_photo = ImageTk.PhotoImage(img)
                self.qr_label.configure(image=self.qr_photo)
            except ImportError:
                self.qr_label.configure(text=f"Install: pip install qrcode[pil]\n\n{url}")

            self.pair_status.set(f"Waiting for iPhone… POST /v1/health/sync\n{url}")

        ttk.Button(f, text="Start pairing + show QR", command=start_pairing).pack(anchor=tk.W, pady=8)
        return f

    def _build_ollama(self) -> ttk.Frame:
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Step 6 — Ollama + MedGemma", font=("", 14, "bold")).pack(anchor=tk.W)

        def run() -> None:
            code1, o1 = self._run(["bash", "-lc", "ollama pull medgemma:4b"])
            code2, o2 = self._run(["bash", "-lc", "source ~/.nvm/nvm.sh && nvm use 24 && ./scripts/configure_medgemma.sh"])
            if code2 == 0:
                state.mark_done("ollama_medgemma")
                messagebox.showinfo("Done", "MedGemma configured for OpenClaw.")
            else:
                messagebox.showerror("Error", o1 + o2)

        ttk.Button(f, text="Pull medgemma:4b + configure OpenClaw", command=run).pack(anchor=tk.W, pady=8)
        return f

    def _build_ready(self) -> ttk.Frame:
        f = ttk.Frame(self.notebook, padding=10)
        ttk.Label(f, text="Ready for OpenClaw", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="Run: nvm use 24 && openclaw tui\nThen use docs/FIRST_RUN_PROMPTS.md for FHIR sync + Q&A.",
            wraplength=650,
        ).pack(anchor=tk.W, pady=8)

        def finish() -> None:
            state.mark_done("ready")
            messagebox.showinfo("Complete", "Setup marked complete. See README Step 10–11.")

        ttk.Button(f, text="Mark setup complete", command=finish).pack(anchor=tk.W)
        return f


def main() -> None:
    app = WizardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
