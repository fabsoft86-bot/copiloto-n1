"""Aplicação desktop nativa para o N1 Flow.

Esta é a versão oficial do app: desktop-only, sem Streamlit e sem threads
complexas para o fluxo principal.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import queue
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np

from copiloto_n1 import audio as audio_mod
from copiloto_n1 import pipeline as pipeline_mod
from copiloto_n1 import transcricao as transcricao_mod

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSizePolicy,
        QStatusBar,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover - depende do runtime do usuário.
    QApplication = None
    QFileDialog = None
    QFrame = None
    QGridLayout = None
    QLabel = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QTextEdit = None
    QVBoxLayout = None
    QWidget = object
    Qt = None
    _PYSIDE6_DISPONIVEL = False
else:
    _PYSIDE6_DISPONIVEL = True

from copiloto_n1.extrator import ExtratorRegras
from copiloto_n1.painel import sugestoes_do_assistente
from copiloto_n1.perfil import carregar_perfil
from copiloto_n1.schemas import Chamado, gerar_relatorio_ticket
from copiloto_n1.validador import validar

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("copiloto_n1.desktop_app")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler(_LOG_DIR / "app.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)


def salvar_atendimento_historico(chamado: Chamado, transcricao: str, relatorio: str, base_dir: str | Path | None = None) -> Path:
    pasta = Path(base_dir) if base_dir is not None else _PROJECT_ROOT / "data" / "atendimentos"
    pasta.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = pasta / f"atendimento_{timestamp}.json"
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "transcricao": transcricao,
        "relatorio": relatorio,
        "chamado": chamado.model_dump(),
    }
    caminho.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


class N1FlowMainWindow(QMainWindow):
    def __init__(self) -> None:
        if not _PYSIDE6_DISPONIVEL:
            raise RuntimeError(
                f"PySide6 não está instalado para o interpretador {sys.executable}. "
                f"Comando exato: \"{sys.executable}\" -m pip install PySide6"
            )
        if sys.platform == "win32":
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:  # pragma: no cover - depende do SO do usuário.
                pass

        super().__init__()
        self.setWindowTitle("N1 Flow")
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)
        self.setBaseSize(1100, 720)

        if QApplication.instance() is not None:
            QApplication.instance().setStyle("Fusion")

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#090f1a"))
        palette.setColor(QPalette.WindowText, QColor("#e5edf8"))
        palette.setColor(QPalette.Base, QColor("#0b1220"))
        palette.setColor(QPalette.AlternateBase, QColor("#111827"))
        palette.setColor(QPalette.ToolTipBase, QColor("#0f172a"))
        palette.setColor(QPalette.ToolTipText, QColor("#e5edf8"))
        palette.setColor(QPalette.Text, QColor("#e5edf8"))
        palette.setColor(QPalette.Button, QColor("#111827"))
        palette.setColor(QPalette.ButtonText, QColor("#e5edf8"))
        palette.setColor(QPalette.Light, QColor("#1f2937"))
        palette.setColor(QPalette.Midlight, QColor("#111827"))
        palette.setColor(QPalette.Dark, QColor("#020817"))
        palette.setColor(QPalette.Mid, QColor("#0f172a"))
        palette.setColor(QPalette.Shadow, QColor("#020817"))
        palette.setColor(QPalette.Highlight, QColor("#2563eb"))
        palette.setColor(QPalette.HighlightedText, QColor("#f8fafc"))
        self.setPalette(palette)

        self.setStyleSheet(
            "QMainWindow { background: #eef2f7; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }"
            "QWidget { background-color: #f7f9fc; color: #0f172a; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }"
            "QLabel { color: #0f172a; background: transparent; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }"
            "QLabel.section-title { font-size: 12pt; font-weight: 700; color: #0f172a; padding: 0 0 4px 0; }"
            "QTextEdit { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 9px; color: #111827; font-size: 10pt; }"
            "QTextEdit:focus { border: 1px solid #3b82f6; }"
            "QComboBox, QCheckBox { font-size: 10pt; }"
            "QAbstractButton { min-height: 34px; padding: 8px 12px; font-size: 10pt; font-weight: 600; border-radius: 9px; }"
            "QPushButton { background: #f3f4f6; color: #111827; border: 1px solid #cbd5e1; min-width: 110px; min-height: 34px; padding: 8px 12px; margin: 2px 0; }"
            "QPushButton:hover { background: #e5e7eb; border: 1px solid #94a3b8; }"
            "QPushButton:pressed { background: #dfe7f2; }"
            "QPushButton#recordButton { background: #166534; color: #f0fdf4; border: 1px solid #22c55e; min-width: 150px; min-height: 44px; padding: 10px 16px; font-size: 11pt; font-weight: 700; }"
            "QPushButton#recordButton:hover { background: #14532d; }"
            "QPushButton#recordButton:pressed { background: #114b2d; }"
            "QPushButton#recordButton[active=true] { background: #7f1d1d; border: 1px solid #ef4444; }"
            "QPushButton#recordButton[active=true]:hover { background: #991b1b; }"
            "QPushButton.secondary { background: #0f172a; color: #e2e8f0; border: 1px solid #334155; min-height: 32px; }"
            "QPushButton.secondary:hover { background: #1e293b; }"
            "QPushButton.primary { background: #1d4ed8; color: #eff6ff; border: 1px solid #3b82f6; min-height: 32px; }"
            "QPushButton.primary:hover { background: #1e40af; }"
            "QFrame.card { background: #ffffff; border: 1px solid #dfe7f2; border-radius: 12px; }"
            "QFrame.card QLabel { color: #475569; }"
            "QFrame#header { background: #f8fafc; border: 1px solid #dbe3ef; border-radius: 12px; }"
            "QFrame#sidebar { background: #f3f6fb; border: 1px solid #dfe7f2; border-radius: 12px; }"
            "QFrame.side-panel { background: #ffffff; border: 1px solid #dfe7f2; border-radius: 12px; }"
            "QFrame.side-panel QLabel { font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.05em; }"
            "QScrollBar:vertical { background: #edf2f7; width: 9px; border-radius: 5px; }"
            "QScrollBar::handle:vertical { background: #94a3b8; border-radius: 5px; min-height: 20px; }"
            "QTabWidget::pane { border: 1px solid #d8e1ee; border-radius: 12px; background: #ffffff; }"
            "QTabBar::tab { background: #f3f6fb; color: #334155; border: 1px solid #d8e1ee; border-top-left-radius: 8px; border-top-right-radius: 8px; padding: 8px 14px; margin-right: 4px; font-size: 10pt; }"
            "QTabBar::tab:selected { background: #ffffff; color: #0f172a; font-weight: 700; border: 1px solid #bfdbfe; }"
            "QStatusBar { background: #0b1220; color: #e2e8f0; border-top: 1px solid #1e293b; font-size: 10pt; }"
            "QStatusBar::item { border: 0; }"
        )
        self._chamado = Chamado()
        self._perfil = carregar_perfil("software_house")
        self._gravador_ativo = False
        self._estado_gravacao = "pronto"
        self._gravacao_inicio: float | None = None
        self._microfone_stop_event = threading.Event()
        self._microfone_thread = None
        self._microfone_listener = None
        self._microfone_source = None
        self._microfone_recognizer = None
        self._gravador_instancia = None
        self._transcricao_queue: queue.Queue[dict[str, object]] = queue.Queue()
        self._volume_timer = QTimer(self)
        self._volume_timer.timeout.connect(self._atualizar_medidor_volume)
        self._poller_transcricao = QTimer(self)
        self._poller_transcricao.timeout.connect(self._processar_queue_transcricao)
        self._poller_transcricao.start(200)

        central = QWidget(self)
        central.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(central)
        self.statusBar().setFixedHeight(32)
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().setStyleSheet(
            "QStatusBar { background: #0b1220; color: #e2e8f0; border-top: 1px solid #1e293b; padding: 0 12px; font-size: 10pt; }"
            "QStatusBar::item { border: 0; }"
        )

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(16)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(0)
        sidebar.setVisible(False)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(sidebar)

        self.nav_buttons = {}

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        title_block = QVBoxLayout()
        title = QLabel("Atendimento N1")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #f8fafc; letter-spacing: -0.03em;")
        subtitle = QLabel("Fluxo operacional para apoio ao atendimento")
        subtitle.setStyleSheet("font-size: 11px; color: #94a3b8; margin-top: 0px;")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header_layout.addLayout(title_block)
        header_layout.addStretch()

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.setContentsMargins(0, 0, 0, 0)

        self.config_button = QPushButton("⚙ Config")
        self.config_button.clicked.connect(self._abrir_configuracoes)
        self.config_button.setToolTip("Configurações do microfone")
        self.config_button.setStyleSheet(
            "QPushButton { background: #111827; color: #e5edf8; border: 1px solid #2a3b57; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #182338; }"
        )
        action_row.addWidget(self.config_button)

        self.novo_atendimento_button = QPushButton("Novo")
        self.novo_atendimento_button.clicked.connect(self._novo_atendimento)
        self.novo_atendimento_button.setStyleSheet(
            "QPushButton { background: #131d2f; color: #e5edf8; border: 1px solid #2a3b57; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #182338; }"
        )
        action_row.addWidget(self.novo_atendimento_button)

        self.microfone_button = QPushButton("🎙 Gravar")
        self.microfone_button.setObjectName("recordButton")
        self.microfone_button.clicked.connect(self._transcrever_microfone)
        self.microfone_button.setToolTip("Iniciar ou encerrar gravação")
        self.microfone_button.setStyleSheet(
            "QPushButton#recordButton { background: #166534; color: #f0fdf4; border: 1px solid #22c55e; border-radius: 10px; min-width: 150px; min-height: 42px; padding: 10px 16px; font-size: 11pt; font-weight: 700; }"
            "QPushButton#recordButton:hover { background: #14532d; }"
            "QPushButton#recordButton:pressed { background: #114b2d; }"
            "QPushButton#recordButton[active=true] { background: #7f1d1d; border: 1px solid #ef4444; }"
            "QPushButton#recordButton[active=true]:hover { background: #991b1b; }"
        )
        action_row.addWidget(self.microfone_button)

        self.gerar_relatorio_button = QPushButton("Gerar relatório")
        self.gerar_relatorio_button.clicked.connect(self._gerar_relatorio)
        self.gerar_relatorio_button.setStyleSheet(
            "QPushButton { background: #102b1d; color: #dcfce7; border: 1px solid #22c55e; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #123425; }"
        )
        action_row.addWidget(self.gerar_relatorio_button)

        self.manualmente_button = QPushButton("Digitar")
        self.manualmente_button.clicked.connect(self._inserir_transcricao_manual)
        self.manualmente_button.setStyleSheet(
            "QPushButton { background: #131d2f; color: #e5edf8; border: 1px solid #2a3b57; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #182338; }"
        )
        action_row.addWidget(self.manualmente_button)

        self.assistente_button = QPushButton("Assistente")
        self.assistente_button.clicked.connect(self._assistente_automatico)
        self.assistente_button.setStyleSheet(
            "QPushButton { background: #22162f; color: #e9d5ff; border: 1px solid #8b5cf6; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #2b1b3d; }"
        )
        action_row.addWidget(self.assistente_button)

        self.validar_button = QPushButton("Validar")
        self.validar_button.clicked.connect(self._validar_chamado)
        self.validar_button.setStyleSheet(
            "QPushButton { background: #102b1d; color: #dcfce7; border: 1px solid #22c55e; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #123425; }"
        )
        action_row.addWidget(self.validar_button)

        self.microfone_status = QLabel("Microfone: desligado")
        self.microfone_status.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 700; margin-left: 4px;")
        action_row.addWidget(self.microfone_status)

        self.limpar_transcricao_button = QPushButton("Limpar")
        self.limpar_transcricao_button.clicked.connect(self._limpar_transcricao)
        self.limpar_transcricao_button.setToolTip("Limpar a transcrição atual")
        self.limpar_transcricao_button.setStyleSheet(
            "QPushButton { background: #0b1220; color: #cbd5e1; border: 1px solid #2a3b57; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #182338; }"
        )
        action_row.addWidget(self.limpar_transcricao_button)

        self.copiar_transcricao_button = QPushButton("Copiar")
        self.copiar_transcricao_button.clicked.connect(self._copiar_transcricao)
        self.copiar_transcricao_button.setToolTip("Copiar transcrição para a área de transferência")
        self.copiar_transcricao_button.setStyleSheet(
            "QPushButton { background: #0b1220; color: #cbd5e1; border: 1px solid #2a3b57; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #182338; }"
        )
        action_row.addWidget(self.copiar_transcricao_button)

        self.copiar_relatorio_button = QPushButton("Copiar relatório")
        self.copiar_relatorio_button.clicked.connect(self._copiar_relatorio)
        self.copiar_relatorio_button.setToolTip("Copiar o relatório do atendimento")
        self.copiar_relatorio_button.setStyleSheet(
            "QPushButton { background: #172554; color: #dbeafe; border: 1px solid #3b82f6; border-radius: 8px; padding: 6px 10px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background: #1e3a8a; }"
        )
        action_row.addWidget(self.copiar_relatorio_button)

        header_layout.addLayout(action_row)
        content_layout.addWidget(header)

        self.cards = {}
        cards_layout = QGridLayout()
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(10)
        for idx, (label, value) in enumerate([
            ("Status", "Aberto"),
            ("Módulo", "—"),
            ("Prioridade", "—"),
            ("Qualidade", "—"),
        ]):
            card = QFrame()
            card.setProperty("class", "card")
            card.setStyleSheet("QFrame.card { background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; }")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #94a3b8; font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;")
            value_widget = QLabel(value)
            value_widget.setStyleSheet("color: #f8fafc; font-size: 18px; font-weight: 700; letter-spacing: -0.03em;")
            self.cards[label.lower()] = value_widget
            card_layout.addWidget(label_widget)
            card_layout.addWidget(value_widget)
            cards_layout.addWidget(card, idx // 2, idx % 2)
        content_layout.addLayout(cards_layout)

        self._historico: list[dict[str, str]] = []

        self.console_hint = QLabel("Status do atendimento: pronto")
        self.console_hint.setStyleSheet(
            "font-size: 10pt; font-weight: 700; color: #cbd5e1; background: #0b1220; border: 1px solid #1e293b; border-radius: 8px; padding: 8px 10px; margin: 4px 0;"
        )
        content_layout.addWidget(self.console_hint)

        self.section_title_gravacao = QLabel("Gravação")
        self.section_title_gravacao.setProperty("class", "section-title")
        self.section_title_gravacao.setStyleSheet("font-size: 12pt; font-weight: 700; color: #0f172a; margin-top: 4px; margin-bottom: 2px;")
        self.section_title_transcricao = QLabel("Transcrição")
        self.section_title_transcricao.setProperty("class", "section-title")
        self.section_title_transcricao.setStyleSheet("font-size: 12pt; font-weight: 700; color: #0f172a; margin-top: 4px; margin-bottom: 2px;")
        self.section_title_dados = QLabel("Dados do chamado")
        self.section_title_dados.setProperty("class", "section-title")
        self.section_title_dados.setStyleSheet("font-size: 12pt; font-weight: 700; color: #0f172a; margin-top: 4px; margin-bottom: 2px;")
        self.section_title_relatorio = QLabel("Relatório")
        self.section_title_relatorio.setProperty("class", "section-title")
        self.section_title_relatorio.setStyleSheet("font-size: 12pt; font-weight: 700; color: #0f172a; margin-top: 4px; margin-bottom: 2px;")

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setUsesScrollButtons(False)
        self.tab_widget.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #1e293b; border-radius: 12px; background: #0b1220; }"
            "QTabBar::tab { background: #0f172a; color: #cbd5e1; border: 1px solid #1e293b; border-top-left-radius: 10px; border-top-right-radius: 10px; padding: 7px 12px; margin-right: 4px; }"
            "QTabBar::tab:selected { background: #111827; color: #f8fafc; font-weight: 700; border: 1px solid #334155; }"
        )

        atendimento_tab = QWidget()
        atendimento_layout = QVBoxLayout(atendimento_tab)
        atendimento_layout.setContentsMargins(12, 12, 12, 12)
        atendimento_layout.setSpacing(10)
        atendimento_layout.addWidget(self.section_title_gravacao)

        self.conversa = QTextEdit()
        self.conversa.setPlaceholderText("Cole a conversa do atendimento...")
        self.conversa.setMinimumHeight(160)
        self.conversa.setStyleSheet(
            "QTextEdit { background: #0b1220; border: 1px solid #1e293b; border-radius: 10px; color: #e2e8f0; padding: 8px; }"
            "QTextEdit:focus { border: 1px solid #60a5fa; }"
        )
        self.conversa.textChanged.connect(self._atualizar_assistente_automatico)
        atendimento_layout.addWidget(QLabel("Conversa do cliente"))
        atendimento_layout.addWidget(self.conversa)

        self.assistente_notas = QTextEdit()
        self.assistente_notas.setPlaceholderText("Anotações do analista: o assistente pode usar isso para completar o chamado.")
        self.assistente_notas.setMinimumHeight(120)
        self.assistente_notas.setStyleSheet(
            "QTextEdit { background: #0b1220; border: 1px solid #1e293b; border-radius: 10px; color: #e2e8f0; padding: 8px; }"
            "QTextEdit:focus { border: 1px solid #a78bfa; }"
        )
        self.assistente_notas.textChanged.connect(self._atualizar_assistente_automatico)
        atendimento_layout.addWidget(QLabel("Anotações do analista"))
        atendimento_layout.addWidget(self.assistente_notas)

        transcript_tab = QWidget()
        transcript_layout = QVBoxLayout(transcript_tab)
        transcript_layout.setContentsMargins(12, 12, 12, 12)
        transcript_layout.setSpacing(10)
        transcript_layout.addWidget(self.section_title_transcricao)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.dispositivo_combo = QComboBox()
        self.dispositivo_combo.addItem("Padrão do sistema")
        default_input = None
        try:
            default_input = getattr(audio_mod.sd, "default", None)
            if default_input is not None:
                default_input = getattr(default_input, "device", None)
                if isinstance(default_input, (list, tuple)) and default_input:
                    default_input = int(default_input[0])
        except Exception:  # pragma: no cover - depende do ambiente do usuário.
            default_input = None
        try:
            for item in audio_mod.listar_dispositivos():
                nome = f"{item.get('index')} - {item.get('name')}"
                self.dispositivo_combo.addItem(nome)
                if default_input is not None and int(item.get("index", -1)) == default_input:
                    self.dispositivo_combo.setCurrentIndex(self.dispositivo_combo.count() - 1)
        except Exception as exc:
            logger.warning("Não foi possível listar dispositivos: %s", exc)
        self.dispositivo_combo.setMinimumWidth(220)
        self.dispositivo_combo.currentIndexChanged.connect(self._atualizar_label_dispositivo)
        controls.addWidget(self.dispositivo_combo)

        self.captura_cliente_checkbox = QCheckBox("Capturar cliente via loopback (Windows)")
        self.captura_cliente_checkbox.setChecked(False)
        self.captura_cliente_checkbox.setToolTip(
            "A gravação do cliente via loopback exige consentimento e política interna da empresa. "
            "Use apenas quando houver autorização formal."
        )
        controls.addWidget(self.captura_cliente_checkbox)

        self.testar_microfone_button = QPushButton("Testar microfone")
        self.testar_microfone_button.clicked.connect(self._teste_microfone)
        controls.addWidget(self.testar_microfone_button)
        controls.addStretch()
        transcript_layout.addLayout(controls)

        self.dispositivo_label = QLabel("Dispositivo em uso: padrão do sistema")
        if self.dispositivo_combo.currentIndex() > 0:
            self.dispositivo_label.setText(f"Dispositivo em uso: {self.dispositivo_combo.currentText()}")
        self.dispositivo_label.setStyleSheet("font-size: 10pt; font-weight: 700; color: #334155; background: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 8px; padding: 6px 8px;")
        transcript_layout.addWidget(self.dispositivo_label)

        self.nivel_microfone = QProgressBar()
        self.nivel_microfone.setRange(0, 100)
        self.nivel_microfone.setValue(0)
        self.nivel_microfone.setTextVisible(True)
        self.nivel_microfone.setFormat("Nível: %p%")
        self.nivel_microfone.setStyleSheet(
            "QProgressBar { border: 1px solid #cbd5e1; border-radius: 8px; background: #e2e8f0; text-align: center; min-height: 22px; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a34a, stop:1 #22c55e); border-radius: 6px; }"
        )
        transcript_layout.addWidget(self.nivel_microfone)

        self.loopback_warn = QLabel(
            "Aviso: gravar a voz do cliente exige consentimento e conformidade com a política de gravação da empresa."
        )
        self.loopback_warn.setWordWrap(True)
        self.loopback_warn.setStyleSheet(
            "font-size: 10px; color: #fbbf24; background: #2a1b00; border: 1px solid #b45309; border-radius: 8px; padding: 6px 8px;"
        )
        transcript_layout.addWidget(self.loopback_warn)

        self.transcricao_microfone = QTextEdit()
        self.transcricao_microfone.setPlaceholderText("A transcrição do microfone aparecerá aqui...")
        self.transcricao_microfone.setMinimumHeight(260)
        self.transcricao_microfone.setStyleSheet(
            "QTextEdit { background: #0b1220; border: 1px solid #1e293b; border-radius: 10px; color: #e2e8f0; padding: 8px; }"
            "QTextEdit:focus { border: 1px solid #7dd3fc; }"
        )
        transcript_layout.addWidget(QLabel("Transcrição em tempo real"))
        transcript_layout.addWidget(self.transcricao_microfone)

        dados_tab = QWidget()
        dados_layout = QVBoxLayout(dados_tab)
        dados_layout.setContentsMargins(12, 12, 12, 12)
        dados_layout.setSpacing(10)
        dados_layout.addWidget(self.section_title_dados)
        self.assistente_campos = QTextEdit()
        self.assistente_campos.setReadOnly(True)
        self.assistente_campos.setPlaceholderText("Dados relevantes aparecendo aqui...")
        self.assistente_campos.setMinimumHeight(150)
        self.assistente_campos.setStyleSheet("QTextEdit { background: #0f172a; border: 1px solid #1e293b; }")
        dados_layout.addWidget(QLabel("Dados relevantes"))
        dados_layout.addWidget(self.assistente_campos)

        checklist_tab = QWidget()
        checklist_layout = QVBoxLayout(checklist_tab)
        checklist_layout.setContentsMargins(12, 12, 12, 12)
        checklist_layout.setSpacing(10)
        self.checklist = QTextEdit()
        self.checklist.setReadOnly(True)
        self.checklist.setPlaceholderText("Checklist do atendimento aparecerá aqui...")
        self.checklist.setMinimumHeight(170)
        self.checklist.setStyleSheet("QTextEdit { background: #0f172a; border: 1px solid #1e293b; }")
        checklist_layout.addWidget(QLabel("Checklist / pendências"))
        checklist_layout.addWidget(self.checklist)

        resumo_tab = QWidget()
        resumo_layout = QVBoxLayout(resumo_tab)
        resumo_layout.setContentsMargins(12, 12, 12, 12)
        resumo_layout.setSpacing(10)
        resumo_layout.addWidget(self.section_title_relatorio)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Resumo final do chamado...")
        self.output.setMinimumHeight(190)
        self.output.setStyleSheet("QTextEdit { background: #0f172a; border: 1px solid #1e293b; }")
        resumo_layout.addWidget(QLabel("Resumo final"))
        resumo_layout.addWidget(self.output)

        historico_tab = QWidget()
        historico_layout = QVBoxLayout(historico_tab)
        historico_layout.setContentsMargins(12, 12, 12, 12)
        historico_layout.setSpacing(10)
        self.historico_view = QTextEdit()
        self.historico_view.setReadOnly(True)
        self.historico_view.setMinimumHeight(180)
        self.historico_view.setStyleSheet("QTextEdit { background: #0f172a; border: 1px solid #1e293b; }")
        historico_layout.addWidget(QLabel("Histórico recente"))
        historico_layout.addWidget(self.historico_view)

        self.tab_widget.addTab(atendimento_tab, "Atendimento")
        self.tab_widget.addTab(transcript_tab, "Transcrição")
        self.tab_widget.addTab(dados_tab, "Dados")
        self.tab_widget.addTab(checklist_tab, "Checklist")
        self.tab_widget.addTab(resumo_tab, "Resumo")
        self.tab_widget.addTab(historico_tab, "Histórico")
        self.tab_widget.currentChanged.connect(self._sincronizar_navegacao)
        content_layout.addWidget(self.tab_widget)
        root_layout.addWidget(content, 1)

        self._atualizar_status_gravador()
        self._atualizar_status()
        self._atualizar_assistente()
        self._atualizar_checklist()
        self._atualizar_historico()
        self._atualizar_output("Aplicação desktop N1 Flow iniciada. Novo atendimento em andamento.")
        self.tab_widget.setCurrentIndex(0)
        if self.nav_buttons:
            for label, button in self.nav_buttons.items():
                button.setChecked(label == "Atendimento")

    def _sincronizar_navegacao(self, index: int) -> None:
        labels = ["Atendimento", "Transcrição", "Dados", "Checklist", "Resumo", "Histórico"]
        for label, button in self.nav_buttons.items():
            button.setChecked(label == labels[index])

    def _diagnosticar_microfone(self) -> str:
        try:
            import speech_recognition as sr
        except ImportError:
            return (
                f"SpeechRecognition/PyAudio não estão instalados no ambiente. "
                f"Este interpretador é {sys.executable}. "
                f"Comando exato: \"{sys.executable}\" -m pip install SpeechRecognition PyAudio"
            )

        try:
            dispositivos = sr.Microphone.list_microphone_names()
        except Exception:
            return "O sistema não conseguiu listar microfones. Verifique permissões e driver de áudio."

        if not dispositivos:
            return "Nenhum microfone foi detectado pelo sistema. Conecte o dispositivo ou instale o driver correto."
        return f"Microfone detectado: {len(dispositivos)} entrada(s) disponível(is). Verifique a entrada padrão e as permissões do Windows."

    def _abrir_configuracoes(self) -> None:
        if sys.platform == "win32":
            try:
                os.startfile("ms-settings:privacy-microphone")
                QMessageBox.information(
                    self,
                    "Configurações do microfone",
                    "As configurações do Windows foram abertas. Permita o acesso do microfone para este aplicativo e retorne aqui.",
                )
                return
            except Exception as exc:  # pragma: no cover - depende do sistema do usuário.
                QMessageBox.warning(self, "Configurações do microfone", f"Não foi possível abrir as configurações do Windows: {exc}")
                return
        QMessageBox.information(
            self,
            "Configurações do microfone",
            "Ative o microfone do sistema e permita o acesso de áudio para a aplicação no sistema operacional.",
        )

    def _atualizar_status(self) -> None:
        self.cards["status"].setText(self._chamado.status.title())
        self.cards["módulo"].setText(self._chamado.modulo or "—")
        self.cards["prioridade"].setText(self._chamado.prioridade.title() if self._chamado.prioridade else "—")
        resultado = validar(self._chamado, self._perfil)
        self.cards["qualidade"].setText(f"{resultado.nota}/100")
        if hasattr(self, "sidebar_estado"):
            self.sidebar_estado.setText(self._chamado.status.title() or "Em andamento")
        self._atualizar_assistente()
        self._atualizar_checklist()

    def _atualizar_label_dispositivo(self) -> None:
        if hasattr(self, "dispositivo_label"):
            if not hasattr(self, "dispositivo_combo"):
                self.dispositivo_label.setText("Dispositivo em uso: padrão do sistema")
                return
            if self.dispositivo_combo.currentIndex() <= 0:
                self.dispositivo_label.setText("Dispositivo em uso: padrão do sistema")
            else:
                self.dispositivo_label.setText(f"Dispositivo em uso: {self.dispositivo_combo.currentText()}")

    def _nome_dispositivo(self) -> str:
        if not hasattr(self, "dispositivo_combo"):
            return "padrão do sistema"
        try:
            if self.dispositivo_combo.currentIndex() <= 0:
                return "padrão do sistema"
            texto = self.dispositivo_combo.currentText()
            return str(texto)
        except Exception:
            return "padrão do sistema"

    def _atualizar_medidor_volume(self) -> None:
        if not hasattr(self, "nivel_microfone"):
            return
        if self._gravador_instancia is None or not self._gravador_ativo:
            self.nivel_microfone.setValue(0)
            return
        pico = self._gravador_instancia.ultimo_pico()
        valor = min(100, max(0, int(round(pico * 1000))))
        self.nivel_microfone.setValue(valor)
        if pico < 0.01:
            self.nivel_microfone.setFormat("Nível: %p% (mudo)")
        else:
            self.nivel_microfone.setFormat("Nível: %p%")

    def _dispositivo_selecionado(self) -> int | str | None:
        if not hasattr(self, "dispositivo_combo"):
            return None
        indice = self.dispositivo_combo.currentIndex()
        if indice <= 0:
            return None
        texto = self.dispositivo_combo.currentText()
        prefixo = texto.split(" - ", 1)[0]
        try:
            return int(prefixo)
        except ValueError:
            return texto

    def _registrar_erro_audio(self, exc: Exception, contexto: str) -> None:
        logger.exception("%s", contexto)
        mensagem = f"{contexto}: {type(exc).__name__}: {exc}"
        self._gravador_ativo = False
        self._estado_gravacao = "erro"
        QTimer.singleShot(0, lambda: self._atualizar_status_gravador())
        QTimer.singleShot(0, lambda: self._atualizar_output(mensagem))
        QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Erro de áudio", mensagem))

    def _processar_queue_transcricao(self) -> None:
        while not self._transcricao_queue.empty():
            item = self._transcricao_queue.get_nowait()
            tipo = item.get("tipo")
            if tipo == "erro":
                self._registrar_erro_audio(item["erro"], str(item.get("contexto", "Erro de áudio")))
                continue
            if tipo == "arquivo":
                caminho = Path(str(item["caminho"]))
                self._estado_gravacao = "transcrevendo"
                self._atualizar_status_gravador()

                def _transcrever_arquivo_em_thread(path: Path) -> None:
                    try:
                        resultado = pipeline_mod.processar_audio(path)
                        texto = resultado[0].texto if hasattr(resultado[0], "texto") else str(resultado[0])
                        self._transcricao_queue.put({"tipo": "texto", "texto": texto})
                    except Exception as exc:  # pragma: no cover - depende do ambiente do usuário
                        self._transcricao_queue.put({"tipo": "erro", "erro": exc, "contexto": "Erro na transcrição do áudio"})

                threading.Thread(target=_transcrever_arquivo_em_thread, args=(caminho,), daemon=True).start()
                continue
            if tipo == "arquivo_duplo":
                microfone = Path(str(item["microfone"]))
                cliente = Path(str(item["cliente"]))
                self._estado_gravacao = "transcrevendo"
                self._atualizar_status_gravador()

                def _transcrever_dupla_em_thread(microfone_path: Path, cliente_path: Path) -> None:
                    try:
                        analista = transcricao_mod.transcrever(microfone_path)
                        cliente_result = transcricao_mod.transcrever(cliente_path)
                        texto = transcricao_mod.formatar_conversa_intercalada(
                            analista.segmentos,
                            cliente_result.segmentos,
                            rotulo_analista="Analista",
                            rotulo_cliente="Cliente",
                        )
                        self._transcricao_queue.put({"tipo": "texto_duplo", "texto": texto})
                    except Exception as exc:  # pragma: no cover - depende do ambiente do usuário
                        self._transcricao_queue.put({"tipo": "erro", "erro": exc, "contexto": "Erro na transcrição do áudio do cliente e do analista"})

                threading.Thread(target=_transcrever_dupla_em_thread, args=(microfone, cliente), daemon=True).start()
                continue
            if tipo == "texto":
                texto = str(item.get("texto", "")).strip()
                self._estado_gravacao = "pronto"
                self._gravador_ativo = False
                if texto:
                    atual = self.transcricao_microfone.toPlainText().strip()
                    nova = f"{atual}\n\n{texto}" if atual else texto
                    self.transcricao_microfone.setPlainText(nova)
                    self.conversa.setPlainText(f"{self.conversa.toPlainText().strip()}\n\n{texto}".strip())
                    self._atualizar_output(f"Transcrição concluída:\n\n{texto}")
                else:
                    self._atualizar_output("Áudio gravado, mas a transcrição não retornou texto. Revise o arquivo manualmente.")
                self._atualizar_status_gravador()
                continue
            if tipo == "texto_duplo":
                texto = str(item.get("texto", "")).strip()
                self._estado_gravacao = "pronto"
                self._gravador_ativo = False
                if texto:
                    atual = self.transcricao_microfone.toPlainText().strip()
                    nova = f"{atual}\n\n{texto}" if atual else texto
                    self.transcricao_microfone.setPlainText(nova)
                    self.conversa.setPlainText(f"{self.conversa.toPlainText().strip()}\n\n{texto}".strip())
                    self._atualizar_output(f"Transcrição intercalada concluída:\n\n{texto}")
                else:
                    self._atualizar_output("Áudio gravado, mas a transcrição intercalada não retornou texto.")
                self._atualizar_status_gravador()

    def _atualizar_status_gravador(self) -> None:
        if self._gravador_ativo:
            self.microfone_button.setText("⏹ Parar")
            self.microfone_button.setProperty("active", True)
            tempo = 0.0 if self._gravacao_inicio is None else time.monotonic() - self._gravacao_inicio
            status_text = f"Microfone: Gravando ({tempo:05.1f}s)"
            self.console_hint.setText("Status do atendimento: gravando")
            self.console_hint.setStyleSheet(
                "font-size: 11px; font-weight: 700; color: #bbf7d0; background: #11271b; border: 1px solid #166534; border-radius: 8px; padding: 7px 10px;"
            )
        elif self._estado_gravacao == "transcrevendo":
            self.microfone_button.setText("⏳ Transcrevendo")
            self.microfone_button.setProperty("active", False)
            status_text = "Microfone: Transcrevendo"
            self.console_hint.setText("Status do atendimento: transcrevendo")
            self.console_hint.setStyleSheet(
                "font-size: 11px; font-weight: 700; color: #fde68a; background: #2a1b00; border: 1px solid #b45309; border-radius: 8px; padding: 7px 10px;"
            )
        elif self._estado_gravacao == "erro":
            self.microfone_button.setText("⚠ Gravar")
            self.microfone_button.setProperty("active", False)
            status_text = "Microfone: Erro"
            self.console_hint.setText("Status do atendimento: erro")
            self.console_hint.setStyleSheet(
                "font-size: 11px; font-weight: 700; color: #fecaca; background: #3f1010; border: 1px solid #b91c1c; border-radius: 8px; padding: 7px 10px;"
            )
        else:
            self.microfone_button.setText("🎙 Gravar")
            self.microfone_button.setProperty("active", False)
            status_text = "Microfone: Pronto"
            self.console_hint.setText("Status do atendimento: pronto")
            self.console_hint.setStyleSheet(
                "font-size: 11px; font-weight: 700; color: #cbd5e1; background: #0b1220; border: 1px solid #1e293b; border-radius: 8px; padding: 7px 10px;"
            )

        self.microfone_button.style().unpolish(self.microfone_button)
        self.microfone_button.style().polish(self.microfone_button)
        if hasattr(self, "microfone_status"):
            self.microfone_status.setText(status_text)
            self.microfone_status.setStyleSheet(
                "font-size: 12px; font-weight: 700; margin-left: 4px; color: #4ade80;"
                if self._gravador_ativo
                else "font-size: 12px; font-weight: 700; margin-left: 4px; color: #94a3b8;"
            )

    def _proximas_perguntas(self) -> list[str]:
        itens: list[str] = []
        if not self._chamado.contato_nome:
            itens.append("Pergunte o nome do cliente e confirme o contato antes de fechar o registro.")
        if not self._chamado.telefone:
            itens.append("Confirme o telefone do cliente para evitar retrabalho no próximo nível.")
        if not self._chamado.descricao:
            itens.append("Peça a descrição do problema, impacto e quando começou.")
        if not self._chamado.modulo:
            itens.append("Pergunte em qual módulo ou tela o problema acontece.")
        if not self._chamado.passos_reproducao:
            itens.append("Peça os passos para reprodução em ordem bem simples.")
        if not self._chamado.evidencias:
            itens.append("Solicite print, log, erro ou evidência antes de escalar.")
        if not itens:
            itens.append("Registro completo: revise o resumo final e confirme prioridade e SLA.")
        return itens

    def _atualizar_assistente(self) -> None:
        linhas = []
        for label, valor in (
            ("Contato", self._chamado.contato_nome),
            ("Empresa", self._chamado.empresa),
            ("Módulo", self._chamado.modulo),
            ("Versão", self._chamado.versao),
            ("Prioridade", self._chamado.prioridade),
            ("Status", self._chamado.status),
            ("Descrição", self._chamado.descricao),
        ):
            if valor:
                linhas.append(f"{label}: {valor}")
        if not linhas:
            linhas.append("Nenhuma informação relevante capturada ainda.")

        proximas = self._proximas_perguntas()
        if proximas:
            linhas.append("")
            linhas.append("Próximo passo:")
            linhas.extend(f"- {item}" for item in proximas[:4])

        sugestoes = sugestoes_do_assistente(self._chamado)
        if sugestoes:
            linhas.append("")
            linhas.append("Sugestões do assistente:")
            linhas.extend(f"- {sugestao}" for sugestao in sugestoes[:3])

        if hasattr(self, "assistente_campos"):
            self.assistente_campos.setPlainText("\n".join(linhas))

    def _atualizar_assistente_automatico(self) -> None:
        if not hasattr(self, "conversa") or not hasattr(self, "assistente_notas"):
            return
        texto_conversa = self.conversa.toPlainText().strip()
        texto_notas = self.assistente_notas.toPlainText().strip()
        if not texto_conversa and not texto_notas:
            self._atualizar_assistente()
            return

        atual = self._chamado
        if texto_conversa:
            atual = ExtratorRegras().extrair(texto_conversa, atual)
        if texto_notas:
            descricao = atual.descricao or ""
            anotacao = texto_notas.strip()
            atual.descricao = f"{descricao}\n\n{anotacao}".strip() if descricao else anotacao
        self._chamado = atual
        self._atualizar_status()

    def _atualizar_checklist(self) -> None:
        checklist = [
            ("Contato", bool(self._chamado.contato_nome), "Nome do cliente."),
            ("Telefone", bool(self._chamado.telefone), "Telefone confirmado."),
            ("Empresa", bool(self._chamado.empresa), "Empresa ou unidade envolvida."),
            ("Módulo", bool(self._chamado.modulo), "Módulo/tela afetada."),
            ("Descrição", bool(self._chamado.descricao), "Impacto e quando começou."),
            ("Reprodução", bool(self._chamado.passos_reproducao), "Passos simples da falha."),
            ("Evidência", bool(self._chamado.evidencias), "Print, log ou erro anexado."),
            ("Prioridade", bool(self._chamado.prioridade), "Prioridade definida."),
        ]
        linhas = ["Checklist do atendimento:"]
        for nome, ok, guia in checklist:
            status = "OK" if ok else "PENDENTE"
            linhas.append(f"- [{status}] {nome}: {guia}")

        faltando = [nome for nome, ok, _ in checklist if not ok]
        if faltando:
            linhas.append("")
            linhas.append("Perguntas do assistente:")
            for pergunta in self._proximas_perguntas()[:3]:
                linhas.append(f"• {pergunta}")

        if hasattr(self, "checklist"):
            self.checklist.setPlainText("\n".join(linhas))

    def _registrar_historico(self) -> None:
        titulo = self._chamado.titulo or self._chamado.contato_nome or "Atendimento sem título"
        resumo = self._chamado.gerar_chamado_final().strip()
        if not resumo:
            return
        registro = {
            "titulo": titulo,
            "status": self._chamado.status or "aberto",
            "severidade": validar(self._chamado, self._perfil).nota,
            "resumo": resumo,
        }
        self._historico.insert(0, registro)
        self._historico = self._historico[:10]
        self._atualizar_historico()

    def _atualizar_historico(self) -> None:
        if not hasattr(self, "historico_view"):
            return
        if not self._historico:
            self.historico_view.setPlainText("Nenhum atendimento recente.")
            return
        linhas = []
        for item in self._historico:
            titulo = str(item.get("titulo", "Atendimento"))
            severidade = float(item.get("severidade", 0))
            status = str(item.get("status", "aberto"))
            linhas.append(f"{titulo} | {status} | nota {severidade:.0f}/100")
        self.historico_view.setPlainText("\n\n".join(linhas))

    def _novo_atendimento(self) -> None:
        if self._gravador_ativo:
            self._gravador_ativo = False
            self._microfone_stop_event.set()
        self._chamado = Chamado()
        self.conversa.clear()
        if hasattr(self, "transcricao_microfone"):
            self.transcricao_microfone.clear()
        self.assistente_notas.clear()
        self._atualizar_status()
        self._atualizar_status_gravador()
        self._atualizar_output("Novo atendimento iniciado. A tela foi limpa e o histórico recente foi mantido.")

    def _incorporar_anotacao(self) -> None:
        anotacao = self.assistente_notas.toPlainText().strip()
        if not anotacao:
            QMessageBox.warning(self, "Anotação vazia", "Escreva algo no campo de anotações antes de usar o assistente.")
            return
        texto = self._chamado.descricao or ""
        self._chamado.descricao = f"{texto}\n\n{anotacao}".strip() if texto else anotacao
        self._atualizar_status()
        self._atualizar_output(f"Anotação incorporada ao chamado:\n\n{anotacao}")

    def _assistente_automatico(self) -> None:
        texto_conversa = self.conversa.toPlainText().strip()
        if texto_conversa:
            self._chamado = ExtratorRegras().extrair(texto_conversa, self._chamado)
        texto_notas = self.assistente_notas.toPlainText().strip()
        if texto_notas:
            descricao = self._chamado.descricao or ""
            texto_limpo = texto_notas.strip()
            self._chamado.descricao = f"{descricao}\n\n{texto_limpo}".strip() if descricao else texto_limpo

        if not self._chamado.titulo and self._chamado.descricao:
            titulo_base = self._chamado.descricao.splitlines()[0].strip()
            if titulo_base:
                self._chamado.titulo = titulo_base[:80]

        self._atualizar_status()
        sugestoes = self._proximas_perguntas()
        if not sugestoes:
            QMessageBox.information(self, "Assistente", "Nenhuma ação pendente: os dados essenciais do chamado já estão consistentes.")
            return
        mensagem = "\n".join(f"• {item}" for item in sugestoes[:6])
        QMessageBox.information(self, "Assistente de atendimento", "Próximo passo do atendimento:\n\n" + mensagem)
        self._atualizar_output("Assistente acionado.\n\n" + mensagem)

    def _adicionar_transcricao(self, texto: str) -> None:
        conversa = self.conversa.toPlainText().strip()
        nova = f"{conversa}\n\n{texto}" if conversa else texto
        self.conversa.setPlainText(nova)

        transcricao = self.transcricao_microfone.toPlainText().strip() if hasattr(self, "transcricao_microfone") else ""
        nova_transcricao = f"{transcricao}\n\n{texto}" if transcricao else texto
        if hasattr(self, "transcricao_microfone"):
            self.transcricao_microfone.setPlainText(nova_transcricao)

        self._atualizar_output(f"Transcrição adicionada:\n\n{texto}")

    def _transcrever_microfone(self) -> None:
        if self._gravador_ativo:
            self._microfone_stop_event.set()
            self._estado_gravacao = "pronto"
            self._gravador_ativo = False
            self._atualizar_status_gravador()
            self._atualizar_output("Gravação encerrada. O microfone foi desligado.")
            return

        if self._microfone_thread is not None and self._microfone_thread.is_alive():
            return

        self._microfone_stop_event.clear()
        self._gravacao_inicio = time.monotonic()
        self._gravador_ativo = True
        self._estado_gravacao = "gravando"
        self._atualizar_status_gravador()
        self._atualizar_output("Gravação iniciada. A transcrição automática começará ao parar.")
        self.dispositivo_label.setText(f"Dispositivo em uso: {self._nome_dispositivo()}")
        self._volume_timer.start(100)

        def _loop_gravacao() -> None:
            caminho_arquivo = Path(tempfile.gettempdir()) / f"n1flow_{int(time.time() * 1000)}.wav"
            caminho_cliente = Path(tempfile.gettempdir()) / f"n1flow_cliente_{int(time.time() * 1000)}.wav"
            try:
                dispositivo = self._dispositivo_selecionado()
                self._gravador_instancia = audio_mod.Gravador(dispositivo=dispositivo, caminho=caminho_arquivo)
                self._gravador_instancia.iniciar()
                while not self._microfone_stop_event.is_set():
                    if time.monotonic() - self._gravacao_inicio >= 5.0:
                        break
                    time.sleep(0.1)
                caminho_arquivo = self._gravador_instancia.parar()
                self._transcricao_queue.put({"tipo": "arquivo", "caminho": str(caminho_arquivo)})
            except Exception as exc:
                self._transcricao_queue.put({"tipo": "erro", "erro": exc, "contexto": "Erro ao gravar o áudio do microfone"})
            finally:
                self._gravador_instancia = None
                self._gravador_ativo = False
                self._estado_gravacao = "pronto"
                self._volume_timer.stop()
                self.nivel_microfone.setValue(0)
                self._atualizar_status_gravador()

        self._microfone_thread = threading.Thread(target=_loop_gravacao, daemon=True)
        self._microfone_thread.start()

    def _limpar_transcricao(self) -> None:
        self.conversa.clear()
        if hasattr(self, "transcricao_microfone"):
            self.transcricao_microfone.clear()
        self._atualizar_output("Transcrição limpa. Você pode começar uma nova gravação ou colar outra conversa.")

    def _copiar_transcricao(self) -> None:
        texto = self.transcricao_microfone.toPlainText().strip() if hasattr(self, "transcricao_microfone") else self.conversa.toPlainText().strip()
        if not texto:
            QMessageBox.warning(self, "Transcrição", "Não há texto para copiar.")
            return

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(texto)
            self._atualizar_output("Transcrição copiada para a área de transferência.")

    def _copiar_relatorio(self) -> None:
        relatorio = self.output.toPlainText().strip() or self._chamado.gerar_chamado_final()
        if not relatorio:
            QMessageBox.warning(self, "Relatório", "Não há relatório para copiar.")
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(relatorio)
            self._atualizar_output("Relatório copiado para a área de transferência.")

    def _teste_microfone(self) -> None:
        try:
            dispositivo = self._dispositivo_selecionado()
            caminho = Path(tempfile.gettempdir()) / f"n1flow_teste_{int(time.time()*1000)}.wav"
            caminho = audio_mod.gravar(segundos=3.0, dispositivo=dispositivo, caminho=caminho)
            if not caminho.exists():
                raise FileNotFoundError(f"Arquivo de teste do microfone não foi criado: {caminho}")
            audio_data, sample_rate = audio_mod.sf.read(str(caminho), dtype="float32", always_2d=False)
            pico = float(np.max(np.abs(audio_data))) if np.size(audio_data) else 0.0
            mudo = bool(audio_mod.audio_mudo(audio_data, limite=0.01))
            mensagem = (
                f"Teste do microfone concluído.\n\n"
                f"Arquivo: {caminho}\n"
                f"Pico de volume: {pico:.4f}\n"
                f"Áudio mudo: {'sim' if mudo else 'não'}\n"
                f"Sample rate: {sample_rate} Hz"
            )
            self.transcricao_microfone.setPlainText(mensagem)
            self._atualizar_output(mensagem)
            QMessageBox.information(self, "Teste do microfone", mensagem)
        except Exception as exc:
            logger.exception("Erro no teste do microfone")
            QMessageBox.critical(self, "Erro do microfone", f"{type(exc).__name__}: {exc}")

    def _inserir_transcricao_manual(self) -> None:
        texto, ok = QInputDialog.getMultiLineText(self, "Transcrição manual", "Digite a conversa do atendimento:")
        if ok and texto and texto.strip():
            self._adicionar_transcricao(texto.strip())

    def _extrair_conversa(self) -> None:
        texto = self.conversa.toPlainText().strip()
        if not texto:
            QMessageBox.warning(self, "Dados ausentes", "Cole a conversa antes de extrair.")
            return
        self._chamado = ExtratorRegras().extrair(texto, self._chamado)
        self._registrar_historico()
        self._atualizar_status()
        self._atualizar_output(self._chamado.gerar_chamado_final())

    def _validar_chamado(self) -> None:
        resultado = validar(self._chamado, self._perfil)
        linhas = [
            f"Nota: {resultado.nota}/100",
            f"SLA estimado: {resultado.sla_horas}h" if resultado.sla_horas else "SLA estimado: não informado",
            "Pendências:",
        ]
        if not resultado.pendencias:
            linhas.append("Nenhuma pendência crítica.")
        else:
            for item in resultado.pendencias:
                linhas.append(f"- {item.rotulo}: {item.pergunta}")
        self._atualizar_output("\n".join(linhas))

    def _gerar_relatorio(self) -> None:
        texto = self.transcricao_microfone.toPlainText().strip() or self.conversa.toPlainText().strip()
        if not texto:
            QMessageBox.warning(self, "Transcrição vazia", "Preencha a aba de transcrição antes de gerar o relatório.")
            return
        self._chamado = ExtratorRegras().extrair(texto, self._chamado)
        self._registrar_historico()
        self._atualizar_status()
        resultado = validar(self._chamado, self._perfil)
        relatorio = gerar_relatorio_ticket(self._chamado, resultado)
        self.output.setPlainText(relatorio)
        self._atualizar_output(relatorio)
        self.tab_widget.setCurrentIndex(4)

        salvo = salvar_atendimento_historico(self._chamado, texto, relatorio)
        self._atualizar_output(f"{relatorio}\n\nArquivo salvo em: {salvo}")

    def _gerar_resumo(self) -> None:
        self._atualizar_status()
        self._atualizar_output(self._chamado.gerar_chamado_final())

    def _salvar_json(self) -> None:
        if not self._chamado:
            QMessageBox.warning(self, "Sem dados", "Não há chamado para salvar.")
            return
        self._registrar_historico()
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar chamado", "chamado.json", "JSON Files (*.json)")
        if not caminho:
            return
        Path(caminho).write_text(self._chamado.model_dump_json(indent=2), encoding="utf-8")
        QMessageBox.information(self, "Arquivo salvo", f"Chamado salvo em:\n{caminho}")

    def _atualizar_output(self, texto: str) -> None:
        self.output.setPlainText(texto)


def main() -> int:
    if not _PYSIDE6_DISPONIVEL:
        print(
            f"PySide6 não está instalado para o interpretador {sys.executable}. "
            f"Comando exato: \"{sys.executable}\" -m pip install PySide6",
            file=sys.stderr,
        )
        return 1
    app = QApplication([])
    window = N1FlowMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
