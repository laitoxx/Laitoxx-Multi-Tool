# ruff: noqa: F405
from .username_window_base import *  # noqa: F403


class _ResultRow(QFrame):
    def __init__(self, result: CheckResult, parent=None):
        super().__init__(parent)
        self.result = result
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor if result.is_found else Qt.CursorShape.ArrowCursor)
        color = _STATUS_COLORS.get(result.status, _ORANGE)
        evidence = "; ".join(result.evidence) or result.error_message or result.status.replace("_", " ")
        self.setToolTip(evidence)

        self.setStyleSheet(f"""
            _ResultRow {{
                background: {_BG_ITEM};
                border-left: 3px solid {color};
                border-radius: 4px;
                margin: 1px 0;
            }}
            _ResultRow:hover {{
                background: {_BG_ITEM_HOV};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        # Status indicator
        dot = QLabel("\u25cf")
        dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
        dot.setFixedWidth(12)
        layout.addWidget(dot)

        # Site name (bold)
        name = QLabel(result.site_name)
        name.setStyleSheet(f"color: {_TEXT_PRI}; font-size: 12px; font-weight: 600; background: transparent;")
        name.setFixedWidth(130)
        layout.addWidget(name)

        # Category icon
        cat_icon = CATEGORY_ICONS.get(result.category, "")
        cat = QLabel(cat_icon)
        cat.setFixedWidth(18)
        cat.setToolTip(result.category.capitalize())
        cat.setStyleSheet("background: transparent;")
        layout.addWidget(cat)

        # URL or status
        if result.is_found:
            url_btn = QPushButton(result.url[:50])
            url_btn.setFlat(True)
            url_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            url_btn.setStyleSheet(
                f"color: {_BLUE}; font-size: 11px; background: transparent;"
                f" border: none; text-align: left; padding: 0; text-decoration: none;"
            )
            url_btn.clicked.connect(lambda _, u=result.url: QDesktopServices.openUrl(QUrl(u)))
            layout.addWidget(url_btn, 1)
            verdict = QLabel(result.status.upper())
            verdict.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 700; background: transparent;")
            verdict.setToolTip(evidence)
            layout.addWidget(verdict)
        else:
            msg = result.status.replace("_", " ")
            if result.error_message:
                msg += f" · {result.error_message[:30]}"
            s_lbl = QLabel(msg)
            s_lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px; background: transparent;")
            layout.addWidget(s_lbl, 1)

        # Confidence
        if result.is_found and result.confidence > 0:
            pct = result.confidence_pct
            c = _GREEN if pct >= 70 else (_ORANGE if pct >= 40 else _RED)
            cl = QLabel(f"{pct}%")
            cl.setStyleSheet(
                f"color: {c}; font-size: 10px; font-weight: 700;"
                f" background: rgba(0,0,0,0.15); border-radius: 3px; padding: 0 3px;"
            )
            cl.setFixedWidth(30)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(cl)

        # WAF
        if result.waf_detected:
            w = QLabel("\U0001f6e1")
            w.setFixedWidth(14)
            w.setToolTip("WAF")
            w.setStyleSheet("background: transparent; font-size: 10px;")
            layout.addWidget(w)

        if any(item == "Provider health is degraded" for item in result.evidence):
            health = QLabel("DEGRADED")
            health.setStyleSheet(f"color: {_ORANGE}; font-size: 8px; font-weight: 700; background: transparent;")
            health.setToolTip("Recent checks for this provider were frequently inconclusive.")
            layout.addWidget(health)

        if result.is_found:
            retry_button = QPushButton("R")
            retry_button.setFixedSize(18, 18)
            retry_button.setToolTip(_t("uo_recheck_provider", "Recheck this provider"))
            retry_button.clicked.connect(lambda: self._recheck_provider())
            layout.addWidget(retry_button)

            report_button = QPushButton("!")
            report_button.setFixedSize(18, 18)
            report_button.setToolTip(_t("uo_false_positive", "Save a local false positive diagnostic"))
            report_button.clicked.connect(lambda: self._report_false_positive())
            layout.addWidget(report_button)

        # Time
        t = QLabel(f"{result.response_time_ms:.0f}ms")
        t.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 9px; background: transparent;")
        t.setFixedWidth(38)
        t.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(t)

    def _report_false_positive(self):
        handler = getattr(self.window(), "_report_false_positive", None)
        if callable(handler):
            handler(self.result)

    def _recheck_provider(self):
        handler = getattr(self.window(), "_recheck_provider", None)
        if callable(handler):
            handler(self.result)
