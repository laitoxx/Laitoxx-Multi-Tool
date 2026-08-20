"""Focused behavior slice for TongueWindow."""
# ruff: noqa: F405

from .tongue_window_context import *  # noqa: F403


class TongueWindowMixin3:
    def _populate_report(self):
        report = self.report or {}
        summary = report.get("summary") or {}
        primary = report.get("primary_investigation") or report
        primary_summary = primary.get("summary") or {}
        chain = report.get("chain_resolution") or primary.get("chain_resolution") or {}
        graph_data = report.get("graph") or {}
        node_count = len(graph_data.get("nodes") or [])
        edge_count = len(graph_data.get("edges") or [])
        self.stats.setText(
            _t(
                "tongue_stats",
                "{nodes} entities · {edges} relations",
                nodes=node_count,
                edges=edge_count,
            )
        )
        self._populate_chain_overview(primary, chain)
        display_summary = dict(summary)
        for key in (
            "transactions_loaded",
            "movements_parsed",
            "history_newest",
            "history_oldest",
            "history_truncated",
            "history_anchor_loaded",
        ):
            if key in primary_summary:
                display_summary[key] = primary_summary[key]
        cards = "".join(
            f"<tr><td><b>{escape(str(key).replace('_', ' '))}</b></td><td>{escape(str(value))}</td></tr>"
            for key, value in display_summary.items()
        )
        coverage = ""
        if primary_summary.get("history_truncated"):
            coverage = (
                f"<p><b>{escape(_t('tongue_history_partial', 'Partial history'))}:</b> "
                f"{escape(_t('tongue_history_partial_text', 'the selected profile limit was reached; older activity remains available on-chain.'))}</p>"
            )
        discovery = report.get("telegram_discovery") or {}
        profile = discovery.get("profile") or {}
        telegram_summary = ""
        if discovery:
            title = escape(
                str(profile.get("title") or profile.get("username") or discovery.get("target") or "Telegram")
            )
            username = escape(str(profile.get("username") or ""))
            description = escape(str(profile.get("description") or "Public description is unavailable."))
            gifts = discovery.get("gift_candidates") or []
            addresses = discovery.get("ton_candidates") or []
            pivot_text = (
                f"Found {len(gifts)} public Gift reference(s) and {len(addresses)} TON address candidate(s). "
                "Double-click an entity to investigate it."
                if gifts or addresses
                else "No public Gift or TON address was exposed by this profile. Private data is not inferred."
            )
            telegram_summary = (
                f"<h3>Telegram profile</h3><p><b>{title}</b> {username}</p>"
                f"<p>{description}</p><p>{escape(pivot_text)}</p>"
            )
        self.summary.setHtml(
            f"<h2>{escape(str(primary_summary.get('title') or primary_summary.get('seed') or summary.get('seed') or summary.get('seed_raw') or 'TONgue'))}</h2>"
            f"<p>{escape(_t('tongue_evidence_note', 'Relationships are confidence-scored public observations, not identity claims.'))}</p>"
            f"{telegram_summary}"
            f"{coverage}"
            f"<table cellspacing='8'>{cards}</table>"
        )
        self.raw_json.setPlainText(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        self._populate_entities()
        self._populate_timeline()
        graph, omitted_nodes, omitted_edges = report_to_graph(report)
        notice = ""
        if omitted_nodes or omitted_edges:
            notice = _t(
                "tongue_graph_limited",
                "Safety projection omitted {nodes} entities and {edges} relations; full data remains in JSON.",
                nodes=omitted_nodes,
                edges=omitted_edges,
            )
        self.graph_notice.setText(notice)
        self.graph_editor.set_graph(graph, notice or _t("tongue_graph_ready", "Evidence graph ready"))

    def _populate_chain_overview(self, primary: dict, chain: dict) -> None:
        status = str(chain.get("status") or "not_checked")
        discovery = (self.report or {}).get("telegram_discovery") or {}
        if discovery and not chain and not (discovery.get("gift_candidates") or discovery.get("ton_candidates")):
            status = "telegram_only"
        labels = {
            "exported": (_t("tongue_exported", "Exported to TON"), "ON-CHAIN", "ton"),
            "not_exported": (_t("tongue_not_exported", "Hosted in Telegram only"), "TELEGRAM ONLY", "telegram"),
            "index_pending": (
                _t("tongue_index_pending", "Export confirmed; contract lookup pending"),
                "INDEX PENDING",
                "ton",
            ),
            "source_error": (_t("tongue_source_error", "Blockchain source unavailable"), "SOURCE ERROR", "warning"),
            "not_checked": (_t("tongue_not_checked", "Blockchain state not checked"), "NOT CHECKED", "ton"),
            "telegram_only": (
                _t("tongue_telegram_found", "Telegram profile found; no public TON link"),
                "TELEGRAM FOUND",
                "telegram",
            ),
        }
        title, badge, icon_mode = labels.get(status, labels["not_checked"])
        self.chain_state.setText(title)
        self.chain_badge.setText(badge)
        self.chain_state_icon.set_mode(icon_mode)
        default_message = (
            discovery.get("message")
            if status == "telegram_only"
            else _t(
                "tongue_chain_waiting_text",
                "Telegram owner and TON owner are verified independently.",
            )
        )
        self.chain_message.setText(str(chain.get("message") or default_message))
        self.chain_card.setProperty("chainState", status)
        self.chain_card.style().unpolish(self.chain_card)
        self.chain_card.style().polish(self.chain_card)

        gift = primary.get("gift") or primary.get("public_gift") or {}
        discovered_username = (discovery.get("profile") or {}).get("username")
        profiles = gift.get("public_profiles") or (primary.get("summary") or {}).get("public_profiles") or []
        if discovered_username and discovered_username not in profiles:
            profiles = [discovered_username, *profiles]
        values = {
            "telegram": ", ".join(map(str, profiles)),
            "item": str(chain.get("item_address") or ""),
            "owner": str(chain.get("owner_address") or ""),
            "collection": str(chain.get("collection_address") or ""),
        }
        for key, field in self.address_fields.items():
            field.setText(values.get(key, ""))

        sources = []
        if gift.get("source_url"):
            sources.append(
                {
                    "name": "Telegram collectible page",
                    "status": "fetched",
                    "url": gift.get("source_url"),
                }
            )
        sources.extend(chain.get("sources") or [])
        sources.extend(discovery.get("sources") or [])
        self.source_table.setRowCount(len(sources))
        for row_index, source in enumerate(sources):
            detail = source.get("url") or source.get("message") or ""
            if source.get("items_checked"):
                detail = f"{detail} · {source['items_checked']} items"
            for column, value in enumerate(
                (
                    source.get("name") or "",
                    source.get("status") or "",
                    detail,
                )
            ):
                item = QTableWidgetItem(str(value))
                item.setToolTip(json.dumps(source, ensure_ascii=False, indent=2, default=str))
                self.source_table.setItem(row_index, column, item)
        self.source_table.resizeColumnToContents(0)
        self.source_table.resizeColumnToContents(1)

    def _copy_address(self, key: str) -> None:
        field = self.address_fields.get(key)
        if field and field.text().strip():
            QApplication.clipboard().setText(field.text().strip())

    def _open_address(self, key: str) -> None:
        field = self.address_fields.get(key)
        value = field.text().strip() if field else ""
        if not value:
            return
        if key == "telegram":
            username = value.split(",", 1)[0].strip().lstrip("@")
            url = f"https://t.me/{username}"
        else:
            url = f"https://tonviewer.com/{value}"
        QDesktopServices.openUrl(QUrl(url))

    def _populate_entities(self):
        rows = list(((self.report or {}).get("graph") or {}).get("nodes") or [])
        self.entities.setSortingEnabled(False)
        self.entities.setRowCount(len(rows))
        for index, row in enumerate(rows):
            details = row.get("details") or {}
            confidence = row.get("confidence", details.get("confidence", "-"))
            evidence = row.get("evidence") or details.get("evidence") or ""
            if not isinstance(evidence, str):
                evidence = json.dumps(evidence, ensure_ascii=False, default=str)
            values = (row.get("type", ""), row.get("label") or row.get("id", ""), confidence, evidence)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(json.dumps(row, ensure_ascii=False, indent=2, default=str))
                self.entities.setItem(index, column, item)
        self.entities.setSortingEnabled(True)
        self.entities.resizeColumnsToContents()

    def _timeline_rows(self) -> list[dict]:
        report = self.report or {}
        primary = report.get("primary_investigation") or {}
        rows = [row for row in report.get("history") or [] if isinstance(row, dict)]
        for asset, events in (report.get("timelines") or {}).items():
            rows.extend({"timeline_asset": asset, **event} for event in events if isinstance(event, dict))
        rows.extend(row for row in report.get("movements") or [] if isinstance(row, dict))
        rows.extend(row for row in report.get("identity_transitions") or [] if isinstance(row, dict))
        if isinstance(primary, dict) and primary is not report:
            rows.extend(row for row in primary.get("history") or [] if isinstance(row, dict))
            rows.extend(row for row in primary.get("movements") or [] if isinstance(row, dict))
            rows.extend(row for row in primary.get("identity_transitions") or [] if isinstance(row, dict))
        unique: dict[str, dict] = {}
        for index, row in enumerate(rows):
            signature = str(
                row.get("movement_id")
                or row.get("event_id")
                or row.get("tx_hash")
                or row.get("transaction_hash")
                or f"{row.get('created_at')}:{row.get('source')}:{row.get('destination')}:{index}"
            )
            unique.setdefault(signature, row)
        return sorted(
            unique.values(),
            key=lambda row: str(row.get("transaction_time") or row.get("created_at") or ""),
            reverse=True,
        )

    def _populate_timeline(self):
        rows = self._timeline_rows()
        incoming_ton = sum(float(row.get("amount_ton") or 0) for row in rows if row.get("direction") == "in")
        outgoing_ton = sum(float(row.get("amount_ton") or 0) for row in rows if row.get("direction") == "out")
        incoming_usd = sum(float(row.get("amount_usd") or 0) for row in rows if row.get("direction") == "in")
        outgoing_usd = sum(float(row.get("amount_usd") or 0) for row in rows if row.get("direction") == "out")
        self.timeline_totals.setText(
            _t(
                "tongue_timeline_totals",
                "Incoming {in_ton:,.4f} TON (≈ ${in_usd:,.2f})  ·  Outgoing {out_ton:,.4f} TON (≈ ${out_usd:,.2f})",
                in_ton=incoming_ton,
                in_usd=incoming_usd,
                out_ton=outgoing_ton,
                out_usd=outgoing_usd,
            )
        )
        self.timeline.setSortingEnabled(False)
        self.timeline.setRowCount(len(rows))
        for index, row in enumerate(rows):
            direction = str(row.get("direction") or "")
            event = str(row.get("event_type") or row.get("relation") or "")
            if direction == "in":
                flow = _t("tongue_flow_in", "IN")
                counterparty = str(row.get("source") or "")
            elif direction == "out":
                flow = _t("tongue_flow_out", "OUT")
                counterparty = str(row.get("destination") or "")
            else:
                flow = event
                old_owner = str(row.get("old_owner") or "")
                new_owner = str(row.get("new_owner") or "")
                counterparty = f"{old_owner} → {new_owner}".strip(" →")
            amount_ton = row.get("amount_ton")
            if amount_ton is None:
                amount_ton = row.get("price_ton")
            ton_text = f"{float(amount_ton):,.6f}" if amount_ton is not None else "-"
            amount_usd = row.get("amount_usd")
            usd_text = f"≈ ${float(amount_usd):,.2f}" if amount_usd is not None else "-"
            evidence = row.get("comment") or row.get("classification") or row.get("evidence") or ""
            if not isinstance(evidence, str):
                evidence = " · ".join(map(str, evidence))
            values = (
                row.get("transaction_time") or row.get("created_at") or "",
                flow,
                counterparty,
                ton_text,
                usd_text,
                row.get("timeline_asset") or row.get("nft_address") or evidence,
            )
            for column, value in enumerate(values):
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False, default=str)
                item = QTableWidgetItem(value)
                item.setToolTip(json.dumps(row, ensure_ascii=False, indent=2, default=str))
                self.timeline.setItem(index, column, item)
        self.timeline.setSortingEnabled(True)

    def _filter_entities(self, text: str):
        needle = text.casefold().strip()
        for row in range(self.entities.rowCount()):
            haystack = " ".join(
                self.entities.item(row, column).text()
                for column in range(self.entities.columnCount())
                if self.entities.item(row, column)
            ).casefold()
            self.entities.setRowHidden(row, bool(needle and needle not in haystack))

    def _investigate_entity_row(self, row: int, _column: int) -> None:
        item = self.entities.item(row, 1)
        type_item = self.entities.item(row, 0)
        if item is None or type_item is None:
            return
        try:
            entity = json.loads(item.toolTip()) if item.toolTip() else {}
        except (TypeError, ValueError):
            entity = {}
        entity_type = str(entity.get("type") or type_item.text()).casefold()
        entity_id = str(entity.get("id") or "")
        value = str(entity.get("label") or item.text()).strip()
        if entity_id.startswith(("gift:", "ton:", "wallet:")):
            value = entity_id.split(":", 1)[1]
        kinds = {
            "telegram_profile": "telegram",
            "telegram_username": "telegram",
            "telegram_gift": "gift",
            "gift": "gift",
            "nft": "nft",
            "wallet": "wallet",
        }
        kind = kinds.get(entity_type)
        if not kind:
            return
        index = self.kind_combo.findData(kind)
        if index >= 0:
            self.kind_combo.setCurrentIndex(index)
        self.target_input.setText(value)
        self.target_input.setFocus()
        self.status.setText(_t("tongue_pivot_ready", "Target selected. Press Search & investigate to continue."))
