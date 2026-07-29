"""Interface Tkinter do MaineMed."""

from __future__ import annotations

import logging
import queue
import re
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from mainemed import (
    __version__,
    audio,
    config,
    exporters,
    prontuario,
    provenancia,
    transcription,
)

log = logging.getLogger(config.APP_NAME)

POLL_MS = 100
WHISPER_CHOICES = [
    "mlx-community/whisper-large-v3-turbo",
    "mlx-community/whisper-large-v3-mlx",
]
MODEL_CHOICES = ["claude-opus-5", "claude-sonnet-5"]


def _sanitize(nome: str) -> str:
    nome = re.sub(r"[^\w\sÀ-ÿ-]", "", nome, flags=re.UNICODE).strip()
    return nome or "Paciente"


class MaineMedApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.cfg = config.load()
        self.recorder: audio.Recorder | None = None
        self.consulta_dir: Path | None = None
        self.busy = False
        self._events: queue.Queue = queue.Queue()

        root.title(f"MaineMed {__version__} — documentação de consultas")
        root.geometry("980x740")
        root.minsize(760, 560)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._tick()
        self.root.after(POLL_MS, self._poll)
        if not self.cfg.get("api_key"):
            self.root.after(400, lambda: self._settings_dialog(first_run=True))

    # ------------------------------------------------------------- layout
    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=(12, 10, 12, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Paciente:").pack(side="left")
        self.nome_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.nome_var, width=34).pack(side="left", padx=(6, 12))
        self.data_label = ttk.Label(top, text=datetime.now().strftime("%d/%m/%Y"))
        self.data_label.pack(side="left")
        ttk.Button(top, text="⚙ Configurações", command=self._settings_dialog).pack(side="right")
        ttk.Button(top, text="Nova consulta", command=self._nova_consulta).pack(
            side="right", padx=(0, 8)
        )

        rec = ttk.Frame(self.root, padding=(12, 6))
        rec.pack(fill="x")
        self.rec_btn = tk.Button(
            rec,
            text="●  Gravar consulta",
            font=("Helvetica", 16, "bold"),
            fg="#b3261e",
            height=2,
            width=24,
            command=self._toggle_record,
        )
        self.rec_btn.pack(side="left")
        meter_frame = ttk.Frame(rec)
        meter_frame.pack(side="left", padx=14, fill="x", expand=True)
        self.timer_label = ttk.Label(meter_frame, text="00:00", font=("Helvetica", 14))
        self.timer_label.pack(anchor="w")
        self.level_bar = ttk.Progressbar(meter_frame, maximum=100, length=240)
        self.level_bar.pack(anchor="w", pady=(4, 0))
        ttk.Label(meter_frame, text="nível do microfone").pack(anchor="w")

        self.status_var = tk.StringVar(value="Pronto. Escreva o nome do paciente e grave a consulta.")
        ttk.Label(self.root, textvariable=self.status_var, padding=(12, 2)).pack(fill="x")

        paned = ttk.PanedWindow(self.root, orient="vertical")
        paned.pack(fill="both", expand=True, padx=12, pady=(4, 6))

        transc_frame = ttk.Labelframe(paned, text="Transcrição (editável)")
        self.transc_text = scrolledtext.ScrolledText(transc_frame, wrap="word", height=8)
        self.transc_text.pack(fill="both", expand=True, padx=6, pady=6)
        paned.add(transc_frame, weight=1)

        pront_frame = ttk.Labelframe(paned, text="Prontuário (editável)")
        self.pront_text = scrolledtext.ScrolledText(pront_frame, wrap="word", height=12)
        self.pront_text.pack(fill="both", expand=True, padx=6, pady=6)
        paned.add(pront_frame, weight=2)

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        actions.pack(fill="x")
        self.gerar_btn = ttk.Button(actions, text="Gerar prontuário", command=self._gerar)
        self.gerar_btn.pack(side="left")
        ttk.Button(actions, text="Copiar", command=self._copiar).pack(side="left", padx=8)
        ttk.Button(actions, text="Exportar Word", command=lambda: self._exportar("docx")).pack(
            side="left"
        )
        ttk.Button(actions, text="Exportar PDF", command=lambda: self._exportar("pdf")).pack(
            side="left", padx=8
        )
        ttk.Button(actions, text="Abrir pasta de consultas", command=self._abrir_pasta).pack(
            side="right"
        )

    # ------------------------------------------------------------ helpers
    def _status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.rec_btn.configure(state=state)
        self.gerar_btn.configure(state=state)

    def _tick(self) -> None:
        if self.recorder and self.recorder.recording:
            secs = int(self.recorder.elapsed)
            self.timer_label.configure(text=f"{secs // 60:02d}:{secs % 60:02d}")
            self.level_bar["value"] = min(100, int(self.recorder.level * 300))
        self.root.after(200, self._tick)

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind == "status":
                    self._status(payload)
                elif kind == "transcript":
                    self.transc_text.delete("1.0", "end")
                    self.transc_text.insert("1.0", payload)
                    self._set_busy(False)
                    self._status(
                        "Transcrição pronta. Revise o texto e clique em Gerar prontuário."
                    )
                elif kind == "prontuario":
                    self.pront_text.delete("1.0", "end")
                    self.pront_text.insert("1.0", payload)
                    self._set_busy(False)
                    self._status("Prontuário gerado. Revise, copie ou exporte.")
                elif kind == "error":
                    self._set_busy(False)
                    self._status("Ocorreu um erro.")
                    messagebox.showerror("MaineMed", payload)
        except queue.Empty:
            pass
        self.root.after(POLL_MS, self._poll)

    # ---------------------------------------------------------- recording
    def _toggle_record(self) -> None:
        if self.busy:
            return
        if self.recorder and self.recorder.recording:
            self._stop_and_transcribe()
            return
        try:
            self.recorder = audio.Recorder()
            self.recorder.start()
        except audio.AudioError as exc:
            self.recorder = None
            messagebox.showerror("MaineMed", str(exc))
            return
        stamp = datetime.now()
        self.consulta_dir = (
            config.CONSULTAS_DIR
            / f"{stamp:%Y-%m-%d %H%M} - {_sanitize(self.nome_var.get())}"
        )
        self.rec_btn.configure(text="■  Parar gravação", fg="#1b5e20")
        self._status("Gravando… fale normalmente. Clique em Parar ao terminar.")

    def _stop_and_transcribe(self) -> None:
        recorder, self.recorder = self.recorder, None
        self.rec_btn.configure(text="●  Gravar consulta", fg="#b3261e")
        data = recorder.stop()
        self.timer_label.configure(text="00:00")
        self.level_bar["value"] = 0
        self._set_busy(True)

        repo = self.cfg.get("whisper_model") or transcription.DEFAULT_REPO
        if transcription.model_cached(repo):
            self._status("Transcrevendo localmente…")
        else:
            self._status(
                "Primeira utilização: baixando o modelo de transcrição (≈1,6 GB). "
                "Isso leva alguns minutos e precisa de internet…"
            )

        consulta_dir = self.consulta_dir
        language = self.cfg.get("language") or "pt"

        def worker() -> None:
            try:
                if consulta_dir is not None:
                    consulta_dir.mkdir(parents=True, exist_ok=True)
                    audio.Recorder.save_wav(consulta_dir / "audio.wav", data)
                    provenancia.registrar(
                        consulta_dir, "gravacao", duracao_s=round(len(data) / audio.SAMPLE_RATE, 1)
                    )
                texto = transcription.transcrever(data, repo=repo, language=language)
                if consulta_dir is not None:
                    provenancia.salvar_texto(consulta_dir, "transcricao-original.txt", texto)
                    provenancia.registrar(consulta_dir, "transcricao", modelo=repo, origem="maquina")
                self._events.put(("transcript", texto))
            except transcription.TranscriptionError as exc:
                self._events.put(("error", str(exc)))
            except Exception as exc:  # inesperado: registrar e avisar
                log.exception("falha na transcrição")
                self._events.put(("error", f"Erro inesperado na transcrição: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    # --------------------------------------------------------- prontuário
    def _gerar(self) -> None:
        if self.busy:
            return
        transcricao = self.transc_text.get("1.0", "end").strip()
        if not transcricao:
            messagebox.showinfo("MaineMed", "Grave uma consulta primeiro (ou cole a transcrição).")
            return
        if not self.cfg.get("api_key"):
            self._settings_dialog(first_run=True)
            return
        self._set_busy(True)
        self._status("Gerando prontuário…")
        cabecalho = (
            f"PACIENTE: {_sanitize(self.nome_var.get())}\n"
            f"DATA: {datetime.now():%d/%m/%Y %H:%M}\n\n"
        )
        api_key = self.cfg["api_key"]
        modelo = self.cfg.get("model") or prontuario.DEFAULT_MODEL
        consulta_dir = self.consulta_dir

        def worker() -> None:
            try:
                if consulta_dir is not None:
                    original = provenancia.texto_salvo(consulta_dir, "transcricao-original.txt")
                    editada = transcricao != original.strip()
                    if editada:
                        provenancia.salvar_texto(
                            consulta_dir, "transcricao-revisada.txt", transcricao
                        )
                corpo = prontuario.gerar(api_key, transcricao, modelo=modelo)
                texto = cabecalho + corpo
                if consulta_dir is not None:
                    provenancia.salvar_texto(consulta_dir, "prontuario-gerado.txt", texto)
                    provenancia.registrar(
                        consulta_dir,
                        "prontuario_gerado",
                        modelo=modelo,
                        transcricao_editada=editada,
                        origem="maquina",
                    )
                self._events.put(("prontuario", texto))
            except prontuario.ProntuarioError as exc:
                self._events.put(("error", str(exc)))
            except Exception as exc:
                log.exception("falha ao gerar prontuário")
                self._events.put(("error", f"Erro inesperado ao gerar o prontuário: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------ actions
    def _copiar(self) -> None:
        texto = self.pront_text.get("1.0", "end").strip()
        if not texto:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self._salvar_final(texto, acao="copiar")
        self._status("Prontuário copiado para a área de transferência.")

    def _exportar(self, formato: str) -> None:
        texto = self.pront_text.get("1.0", "end").strip()
        if not texto:
            messagebox.showinfo("MaineMed", "Gere o prontuário antes de exportar.")
            return
        nome = _sanitize(self.nome_var.get())
        sugestao = f"Prontuario {nome} {datetime.now():%Y-%m-%d}.{formato}"
        path = filedialog.asksaveasfilename(
            defaultextension=f".{formato}",
            initialfile=sugestao,
            filetypes=[("Word", "*.docx")] if formato == "docx" else [("PDF", "*.pdf")],
        )
        if not path:
            return
        try:
            if formato == "docx":
                exporters.export_docx(Path(path), texto)
            else:
                exporters.export_pdf(Path(path), texto)
        except Exception as exc:
            log.exception("falha na exportação")
            messagebox.showerror("MaineMed", f"Não foi possível exportar: {exc}")
            return
        self._salvar_final(texto, acao=f"exportar-{formato}")
        self._status(f"Exportado: {path}")

    def _salvar_final(self, texto: str, acao: str) -> None:
        # A versão final aprovada pela médica — a que vale — fica separada
        # das saídas brutas de máquina.
        if self.consulta_dir is None or not texto:
            return
        try:
            provenancia.salvar_texto(self.consulta_dir, "prontuario-final.txt", texto)
            provenancia.registrar(self.consulta_dir, "prontuario_final", acao=acao, origem="humano")
        except OSError:
            log.exception("falha ao salvar prontuário final")

    def _abrir_pasta(self) -> None:
        import subprocess
        import sys

        config.ensure_dirs()
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(config.CONSULTAS_DIR)])
        else:
            self._status(str(config.CONSULTAS_DIR))

    def _nova_consulta(self) -> None:
        if self.recorder and self.recorder.recording:
            messagebox.showinfo("MaineMed", "Pare a gravação antes de iniciar outra consulta.")
            return
        if self.busy:
            return
        self.nome_var.set("")
        self.transc_text.delete("1.0", "end")
        self.pront_text.delete("1.0", "end")
        self.consulta_dir = None
        self.data_label.configure(text=datetime.now().strftime("%d/%m/%Y"))
        self._status("Pronto. Escreva o nome do paciente e grave a consulta.")

    def _on_close(self) -> None:
        if self.recorder and self.recorder.recording:
            if not messagebox.askyesno(
                "MaineMed", "Há uma gravação em andamento. Sair mesmo assim?"
            ):
                return
            try:
                self.recorder.stop()
            except Exception:
                pass
        self.root.destroy()

    # ----------------------------------------------------------- settings
    def _settings_dialog(self, first_run: bool = False) -> None:
        win = tk.Toplevel(self.root)
        win.title("Configurações")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)

        if first_run:
            ttk.Label(
                frame,
                text=(
                    "Bem-vindo ao MaineMed!\n\n"
                    "Para gerar prontuários, cole abaixo a chave que você recebeu.\n"
                    "A transcrição do áudio acontece só neste Mac; a chave é usada\n"
                    "apenas na etapa de redação do prontuário."
                ),
                justify="left",
            ).grid(column=0, row=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="Chave:").grid(column=0, row=1, sticky="w")
        key_var = tk.StringVar(value=self.cfg.get("api_key", ""))
        key_entry = ttk.Entry(frame, textvariable=key_var, width=46, show="•")
        key_entry.grid(column=1, row=1, sticky="we", padx=6, pady=2)
        show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="mostrar",
            variable=show_var,
            command=lambda: key_entry.configure(show="" if show_var.get() else "•"),
        ).grid(column=2, row=1)

        ttk.Label(frame, text="Modelo do prontuário:").grid(column=0, row=2, sticky="w")
        model_var = tk.StringVar(value=self.cfg.get("model", prontuario.DEFAULT_MODEL))
        ttk.Combobox(
            frame, textvariable=model_var, values=MODEL_CHOICES, state="readonly", width=28
        ).grid(column=1, row=2, sticky="w", padx=6, pady=2)

        ttk.Label(frame, text="Modelo de transcrição:").grid(column=0, row=3, sticky="w")
        whisper_var = tk.StringVar(value=self.cfg.get("whisper_model", transcription.DEFAULT_REPO))
        ttk.Combobox(
            frame, textvariable=whisper_var, values=WHISPER_CHOICES, width=42
        ).grid(column=1, row=3, sticky="w", padx=6, pady=2)

        def salvar() -> None:
            self.cfg["api_key"] = key_var.get().strip()
            self.cfg["model"] = model_var.get().strip() or prontuario.DEFAULT_MODEL
            self.cfg["whisper_model"] = whisper_var.get().strip() or transcription.DEFAULT_REPO
            config.save(self.cfg)
            win.destroy()
            self._status("Configurações salvas.")

        btns = ttk.Frame(frame)
        btns.grid(column=0, row=4, columnspan=3, pady=(14, 0), sticky="e")
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Salvar e começar" if first_run else "Salvar", command=salvar).pack(
            side="right"
        )
        key_entry.focus_set()


def run() -> None:
    root = tk.Tk()
    MaineMedApp(root)
    root.mainloop()
