# ruff: noqa: F405
from .username_window_context import *  # noqa: F403


class UsernameOsintMixin4:
    def _recheck_provider(self, result: CheckResult):
        site = next((item for item in self._db.sites if item.name == result.site_name), None)
        username = self._username_input.text().strip()
        if site is None or not username:
            return
        thread = QThread(self)
        worker = _CheckWorker([site], username, max_workers=1)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(
            lambda results, name=result.site_name, active_thread=thread, active_worker=worker: (
                self._on_provider_rechecked(name, results, active_thread, active_worker)
            )
        )
        worker.error.connect(
            lambda message, active_thread=thread, active_worker=worker: self._on_provider_recheck_error(
                message, active_thread, active_worker
            )
        )
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._recheck_jobs.append((thread, worker))
        thread.start()

    def _release_recheck_job(self, thread, worker):
        self._recheck_jobs = [job for job in self._recheck_jobs if job != (thread, worker)]
        worker.deleteLater()

    def _on_provider_rechecked(self, site_name, results, thread, worker):
        if results:
            self._results = [result for result in self._results if result.site_name != site_name]
            self._results.extend(results)
            self._filter_results()
        self._release_recheck_job(thread, worker)

    def _on_provider_recheck_error(self, message, thread, worker):
        self._release_recheck_job(thread, worker)
        QMessageBox.warning(self, "Provider Recheck", message)

    def _show_provider_health(self):
        summary = self._db.health_summary()
        lines = [
            "Username provider database",
            "",
            *(f"{key.replace('_', ' ').title()}: {value}" for key, value in summary.items()),
        ]
        if self._db.issues:
            lines.extend(("", "Rejected definitions:"))
            lines.extend(f"{issue.site}: {issue.message}" for issue in self._db.issues[:30])
        QMessageBox.information(self, "Provider Health", "\n".join(lines))

    def _report_false_positive(self, result: CheckResult):
        answer = QMessageBox.question(
            self,
            "False Positive Diagnostic",
            "Save a local diagnostic for this result? No network request will be sent.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        import re
        from datetime import UTC, datetime

        from laitoxx.core.settings.paths import REPORTS_DIR
        from laitoxx.shared.report_export import write_json_report

        username = self._username_input.text().strip()
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        safe_site = re.sub(r"[^A-Za-z0-9._-]+", "_", result.site_name).strip("._") or "provider"
        path = REPORTS_DIR / "username_feedback" / f"{safe_site}_{stamp}.json"
        write_json_report(
            path,
            {
                "kind": "false_positive",
                "created_at": datetime.now(UTC).isoformat(),
                "username": username,
                "site": result.site_name,
                "url": result.url,
                "profile_url": result.profile_url,
                "verdict": result.status,
                "confidence": result.confidence,
                "evidence": result.evidence,
                "http_code": result.http_code,
            },
        )
        QMessageBox.information(self, "False Positive Diagnostic", f"Saved to:\n{path}")

    def _try_load_avatar(self, results: list[CheckResult]):
        for r in results:
            if r.avatar_url:
                username = self._username_input.text().strip()
                path = self._avatar_downloader.get_cached(username, r.site_name)
                if path and os.path.exists(path):
                    self._avatar_paths[r.site_name] = path

    def _show_account_correlation(self):
        found = [result for result in self._results if result.is_found]
        if len(found) < 2:
            QMessageBox.information(self, "Account correlation", "At least two found profiles are required.")
            return

        self._btn_correlate.setEnabled(False)
        self._btn_correlate.setText(_t("osint_accounts_comparing", "Comparing..."))
        self._correlation_worker = _CorrelationWorker(
            found,
            self._username_input.text().strip(),
            self._avatar_downloader,
            self._avatar_paths,
        )
        self._correlation_worker.completed.connect(self._on_correlation_ready)
        self._correlation_worker.failed.connect(self._on_correlation_failed)
        self._correlation_worker.start()

    def _on_correlation_failed(self, message):
        self._btn_correlate.setText(_t("osint_accounts_compare", "Compare Accounts"))
        self._btn_correlate.setEnabled(True)
        self._correlation_worker = None
        QMessageBox.warning(self, _t("osint_accounts_compare", "Compare Accounts"), message)

    def _on_correlation_ready(self, comparisons, avatar_paths):
        self._avatar_paths.update(avatar_paths)
        self._btn_correlate.setText(_t("osint_accounts_compare", "Compare Accounts"))
        self._btn_correlate.setEnabled(True)
        self._correlation_worker = None
        lines = [
            "Account correlation",
            "Same username is treated only as a weak clue. Avatar evidence is used when a site exposes it.",
            "",
        ]
        for item in comparisons:
            first = item["first"]
            second = item["second"]
            has_avatar_evidence = bool(first.get("avatar_hash") and second.get("avatar_hash"))
            score = item["score"]
            if not has_avatar_evidence:
                verdict = "INSUFFICIENT EVIDENCE - do not assume these are the same person"
            elif score >= 60:
                verdict = "LIKELY SAME PERSON"
            elif score <= 48:
                verdict = "LIKELY DIFFERENT PEOPLE"
            else:
                verdict = "UNCERTAIN"
            lines.extend(
                (
                    f"{first['platform']}  ↔  {second['platform']}",
                    f"Verdict: {verdict}",
                    f"Correlation score: {score}/100",
                    "Signals: " + "; ".join(item.get("reasons", [])),
                    "",
                )
            )

        dialog = QDialog(self)
        dialog.setWindowTitle(_t("osint_accounts_compare", "Compare Accounts"))
        dialog.resize(720, 520)
        layout = QVBoxLayout(dialog)
        output = QTextEdit()
        output.setReadOnly(True)
        output.setPlainText("\n".join(lines))
        layout.addWidget(output)
        close_button = _GhostButton(_t("close", "Close"))
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def _generate_nicknames(self):
        username = self._username_input.text().strip()
        if not username:
            return
        first = self._first_name.text().strip()
        last = self._last_name.text().strip()

        gen = NicknameGenerator(username, max_variants=200)
        self._nickname_variants = gen.generate_all(first_name=first, last_name=last)

        sx, mp = gen.phonetic_group()
        self._phonetic_text.setText(f"Soundex: {sx}  ·  Metaphone: {mp}")

        lines = []
        for v in self._nickname_variants:
            marker = " \u25c0" if v.lower() == username.lower() else ""
            lines.append(f"{v}{marker}")
        self._nick_list.setPlainText("\n".join(lines))

    def _export_results(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            _t("uo_export_results", "Export"),
            "",
            "JSON (*.json);;CSV (*.csv);;Text (*.txt)",
        )
        if not path:
            return
        found = [r for r in self._results if r.is_found]
        username = self._username_input.text().strip()
        try:
            rows = [
                {
                    "site": result.site_name,
                    "url": result.url,
                    "profile_url": result.profile_url or "",
                    "category": result.category,
                    "status": result.status,
                    "confidence": result.confidence_pct,
                    "response_ms": round(result.response_time_ms),
                    "evidence": "; ".join(result.evidence),
                    "error": result.error_message or "",
                }
                for result in self._results
            ]
            if path.endswith(".json"):
                from laitoxx.shared.report_export import write_json_report

                write_json_report(
                    path,
                    {
                        "username": username,
                        "found": len(found),
                        "total": len(self._results),
                        "database": self._db.health_summary(),
                        "results": rows,
                    },
                )
            elif path.endswith(".csv"):
                from laitoxx.shared.report_export import write_csv_rows

                write_csv_rows(
                    path,
                    [
                        "site",
                        "url",
                        "profile_url",
                        "category",
                        "status",
                        "confidence",
                        "response_ms",
                        "evidence",
                        "error",
                    ],
                    rows,
                )
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"Username OSINT: @{username}\n")
                    f.write(f"Found: {len(found)} / {len(self._results)}\n\n")
                    for r in found:
                        evidence = "; ".join(r.evidence)
                        f.write(f"[{r.status}] [{r.category}] {r.site_name}: {r.url} | {evidence}\n")
                    f.write("\n")
                    portrait = DigitalPortrait(username, self._results)
                    f.write(portrait.to_text())
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _send_to_graph(self):
        from laitoxx.shared.graph.model import Edge, Graph, Node

        username = self._username_input.text().strip()
        found = [r for r in self._results if r.is_found]
        if not found:
            QMessageBox.information(self, "Info", _t("uo_no_found", "No accounts found to graph."))
            return

        graph = Graph(name=f"OSINT: @{username}", direction="LR")
        central = Node.from_type(f"@{username}", "Username")
        central.description = f"Target: {username}"
        graph.add_node(central)

        cat_nodes: dict[str, Node] = {}
        for r in found:
            cat = r.category
            if cat not in cat_nodes:
                cn = Node.from_type(f"{CATEGORY_ICONS.get(cat, '')} {cat.capitalize()}", "Category")
                cn.description = f"Category: {cat}"
                graph.add_node(cn)
                graph.add_edge(
                    Edge(
                        central.id,
                        cn.id,
                        label=cat,
                        edge_type="BelongsToCategory",
                        mermaid_line="-->",
                    )
                )
                cat_nodes[cat] = cn

            sn = Node.from_type(r.site_name, "SocialAccount")
            sn.description = r.url
            sn.metadata = {
                "url": r.url,
                "profile_url": r.profile_url or "",
                "verdict": r.status,
                "confidence": f"{r.confidence_pct}%",
                "response_ms": f"{r.response_time_ms:.0f}",
                "evidence": "; ".join(r.evidence),
            }
            graph.add_node(sn)
            graph.add_edge(
                Edge(
                    cat_nodes[cat].id,
                    sn.id,
                    label=r.status,
                    edge_type="RegisteredOn",
                    mermaid_line="-->" if r.status == "confirmed" else "-.->",
                )
            )

        for v in self._nickname_variants[:10]:
            if v.lower() != username.lower():
                an = Node.from_type(f"@{v}", "AltAccount")
                an.description = f"Possible alt: {v}"
                graph.add_node(an)
                graph.add_edge(
                    Edge(
                        central.id,
                        an.id,
                        label="alt",
                        edge_type="AltAccountOf",
                        mermaid_line="-.->",
                    )
                )

        try:
            from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow

            editor = GraphEditorWindow(self, theme_data=self.theme_data, lua_plugins=self.lua_plugins)
            editor._graph = graph
            editor._graph_name_edit.setText(graph.name)
            idx = editor._dir_combo.findText(graph.direction)
            if idx >= 0:
                editor._dir_combo.setCurrentIndex(idx)
            # Defer refresh so WebEngine has time to initialize after show()
            QTimer.singleShot(150, editor._refresh_all)
            editor.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def closeEvent(self, event):
        self._stop_search()
        for thread, worker in list(self._recheck_jobs):
            stop_and_detach_thread(thread, worker)
        self._recheck_jobs.clear()
        if self._correlation_worker and self._correlation_worker.isRunning():
            stop_and_detach_thread(self._correlation_worker)
            self._correlation_worker = None
        super().closeEvent(event)
