"""Focused behavior slice for NetworkInfoWindow."""
# ruff: noqa: F405

from .network_info_window_context import *  # noqa: F403


class NetworkInfoWindowMixin1:
    def _apply_theme(self):
        td = resolved_theme(self.theme_data)
        bg = td["surface_base_color"]
        fg = td["text_primary_color"]
        bdr = td["border_subtle_color"]

        # We'll use a glass-like semi-transparent styling for the button
        self.setStyleSheet(f"QDialog {{ background-color: {bg}; color: {fg}; }}")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(30, 30, 30, 0.4);
                color: {fg};
                border: 1px solid {bdr};
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid #777777;
            }}
        """)
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(60, 60, 60, 0.4);
                color: {fg};
                border: 1px solid {bdr};
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(90, 90, 90, 0.6);
            }}
            QPushButton:pressed {{
                background-color: rgba(40, 40, 40, 0.8);
            }}
        """)
        if hasattr(self, "subdomain_btn"):
            self.subdomain_btn.setStyleSheet(self.search_btn.styleSheet())
        self.console_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(20, 20, 20, 0.3);
                color: #e0e0e0;
                font-family: monospace;
                font-size: 14px;
                border: 1px solid {bdr};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        self.setStyleSheet(self.styleSheet() + build_workspace_qss(td))

    def update_theme(self, theme_data: dict):
        self.theme_data = theme_data or {}
        self._apply_theme()

    def _run_subdomain_discovery(self):
        target = self.input_field.text().strip()
        if not target:
            self.subdomain_progress_bar.setFormat("Enter a domain first")
            return
        from laitoxx.features.web_audit.subdomain_discovery import (
            SubdomainDiscoveryConfig,
            discover_subdomains,
        )
        from laitoxx.shared.execution import JobControl

        self._stop_subdomain_discovery()
        self._subdomain_control = JobControl()
        self._subdomain_report = None
        self.subdomain_btn.setEnabled(False)
        self.subdomain_stop_btn.setEnabled(True)
        self.subdomain_export_btn.setEnabled(False)
        self.subdomain_graph_btn.setEnabled(False)
        self.subdomain_progress_bar.setRange(0, 0)
        self.subdomain_progress_bar.setFormat("Querying certificate transparency")
        self.subdomain_table.setRowCount(0)
        self.tabs.setCurrentWidget(self.subdomain_tab)
        config = SubdomainDiscoveryConfig(
            resolve_dns=self.subdomain_resolve.isChecked(),
            probe_http=self.subdomain_http.isChecked(),
        )

        def worker():
            try:
                report = discover_subdomains(
                    target,
                    config=config,
                    progress=self.subdomain_progress.emit,
                    control=self._subdomain_control,
                )
                self.subdomain_ready.emit(report)
            except Exception as exc:
                self.subdomain_failed.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _stop_subdomain_discovery(self):
        if self._subdomain_control is not None:
            self._subdomain_control.cancel()

    def _on_subdomain_progress(self, event):
        if event.total > 0:
            self.subdomain_progress_bar.setRange(0, event.total)
            self.subdomain_progress_bar.setValue(event.completed)
            self.subdomain_progress_bar.setFormat(
                f"{event.phase}: {event.completed}/{event.total} {event.item}".strip()
            )
        else:
            self.subdomain_progress_bar.setRange(0, 0)
            self.subdomain_progress_bar.setFormat(event.message or event.phase)

    def _on_subdomain_ready(self, report):
        self._subdomain_report = report
        self.subdomain_btn.setEnabled(True)
        self.subdomain_stop_btn.setEnabled(False)
        self.subdomain_export_btn.setEnabled(bool(report.records))
        self.subdomain_graph_btn.setEnabled(bool(report.records))
        self.subdomain_progress_bar.setRange(0, max(1, len(report.records)))
        self.subdomain_progress_bar.setValue(len(report.records))
        status = "Cancelled" if report.cancelled else "Complete"
        if report.issues:
            status = f"{status} with provider issue: {report.issues[0].message[:80]}"
        self.subdomain_progress_bar.setFormat(f"{status}: {len(report.records)} discovered")
        self._populate_subdomain_table()

    def _on_subdomain_failed(self, message):
        self.subdomain_btn.setEnabled(True)
        self.subdomain_stop_btn.setEnabled(False)
        self.subdomain_progress_bar.setRange(0, 1)
        self.subdomain_progress_bar.setValue(0)
        self.subdomain_progress_bar.setFormat(f"Error: {message[:100]}")

    def _record_matches_subdomain_filter(self, record) -> bool:
        selected = self.subdomain_filter.currentData()
        if selected == "resolved":
            return record.resolves
        if selected == "http":
            return record.http_status is not None
        if selected == "wildcard":
            return record.wildcard_observed
        return True

    def _populate_subdomain_table(self):
        if self._subdomain_report is None:
            return
        records = [record for record in self._subdomain_report.records if self._record_matches_subdomain_filter(record)]
        self.subdomain_table.setSortingEnabled(False)
        self.subdomain_table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = (
                record.hostname,
                "Yes" if record.resolves else "No",
                ", ".join(record.ipv4),
                ", ".join(record.ipv6),
                ", ".join(record.cname),
                str(record.http_status or ""),
                ", ".join(record.sources),
            )
            for column, value in enumerate(values):
                self.subdomain_table.setItem(row, column, QTableWidgetItem(value))
        self.subdomain_table.setSortingEnabled(True)
        self.subdomain_table.resizeColumnsToContents()

    def _filter_subdomains(self):
        self._populate_subdomain_table()

    def _export_subdomains(self):
        if self._subdomain_report is None:
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Subdomains",
            f"{self._subdomain_report.domain}_subdomains.json",
            "JSON (*.json);;CSV (*.csv)",
        )
        if not path:
            return
        from laitoxx.shared.report_export import write_csv_rows, write_json_report

        if selected_filter.startswith("CSV") or path.casefold().endswith(".csv"):
            rows = []
            for record in self._subdomain_report.records:
                row = record.to_dict()
                for field_name in ("ipv4", "ipv6", "cname", "sources"):
                    row[field_name] = "; ".join(row[field_name])
                rows.append(row)
            write_csv_rows(
                path,
                ["hostname", "resolves", "ipv4", "ipv6", "cname", "http_url", "http_status", "sources", "error"],
                rows,
            )
        else:
            write_json_report(path, self._subdomain_report.to_dict())

    def _open_subdomain_graph(self):
        if self._subdomain_report is None:
            return
        from laitoxx.features.web_audit.subdomain_discovery import SubdomainDiscoveryReport
        from laitoxx.features.web_audit.subdomain_graph import build_subdomain_graph
        from laitoxx.interfaces.gui.graph_editor import GraphEditorWindow

        selected_rows = {index.row() for index in self.subdomain_table.selectedIndexes()}
        selected_hosts = {
            self.subdomain_table.item(row, 0).text()
            for row in selected_rows
            if self.subdomain_table.item(row, 0) is not None
        }
        records = (
            [record for record in self._subdomain_report.records if record.hostname in selected_hosts]
            if selected_hosts
            else [record for record in self._subdomain_report.records if self._record_matches_subdomain_filter(record)]
        )
        if len(records) > 300:
            answer = QMessageBox.question(
                self,
                "Open Graph",
                "The current result contains more than 300 subdomains. Open a graph with the first 300?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            records = records[:300]
        graph_report = SubdomainDiscoveryReport(
            domain=self._subdomain_report.domain,
            records=records,
            issues=self._subdomain_report.issues,
            cached=self._subdomain_report.cached,
        )
        editor = GraphEditorWindow(self, theme_data=self.theme_data)
        editor._graph = build_subdomain_graph(graph_report)
        editor._graph_name_edit.setText(editor._graph.name)
        QTimer.singleShot(150, editor._refresh_all)
        editor.exec()

    def _load_empty_map(self, lat=20.0, lon=0.0, zoom=2, marker_text=None, target_ip=""):
        if marker_text is None:
            marker_text = translator.get("ni_waiting")
        if not self.map_view:
            return

        # Create base map HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Laitoxx Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>body, html, #map {{ height: 100vh; width: 100vw; margin: 0; padding: 0; background-color: transparent; }}
            #overlay {{
                display: block;
                position: absolute; top: 10px; right: 10px; z-index: 1000;
                background: rgba(20,20,20,0.85); color: #e0e0e0;
                padding: 15px; border-radius: 8px; border: 1px solid #444;
                font-family: sans-serif; font-size: 13px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                backdrop-filter: blur(4px);
            }}
            #legend {{
                display: block;
                position: absolute; bottom: 30px; left: 10px; z-index: 1000;
                background: rgba(20,20,20,0.85); color: #e0e0e0;
                padding: 10px; border-radius: 8px; border: 1px solid #444;
                font-family: sans-serif; font-size: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                backdrop-filter: blur(4px);
            }}
            .ov-row, .lg-row {{ margin-bottom: 5px; }}
            .ov-icon {{ display: inline-block; width: 20px; }}
            .lg-color {{ display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 2px; vertical-align: middle; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map', {{
                    center: [{lat}, {lon}],
                    zoom: {zoom},
                    worldCopyJump: true,
                    zoomControl: false
                }});
                L.control.zoom({{ position: 'bottomright' }}).addTo(map);

                // Always add default Dark map first, to prevent white screen
                var defaultTile = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{ maxZoom: 19, attribution: '© OpenStreetMap © CARTO' }}).addTo(map);

                var marker = L.marker([{lat}, {lon}]).addTo(map);
                marker.bindPopup("<b style='color: black;'>{marker_text}</b>").openPopup();
            </script>
        </body>
        </html>
        """
        self.map_view.setHtml(html, QUrl("http://localhost"))

    def _on_osint_data_ready(self, data):
        if hasattr(self, "progress_bar"):
            self.progress_bar.setVisible(False)

        if not self.map_view:
            return

        if "osmnx_error" in data:
            self.console_output.append(f"\n[WARNING] OSMNX Map Overlay failed to load:\n{data['osmnx_error']}\n")
            self.console_output.append(
                "This usually happens on Windows if 'geopandas'/'fiona' or C++ Build Tools are missing, or if OpenStreetMap blocked the IP.\n"
            )

        js_code = f"""
        (function() {{
            var existing = document.getElementById('overlay');
            if (existing) existing.remove();

            var tz_id = '{data.get("tz_id", "UTC")}';
            var localTime = "N/A";
            try {{
                localTime = new Date().toLocaleTimeString([], {{timeZone: tz_id, hour: '2-digit', minute:'2-digit'}}) + " (" + tz_id + ")";
            }} catch(e) {{}}

            var div = document.createElement('div');
            div.innerHTML = `
            <div id="overlay">
                <div class="ov-row"><span class="ov-icon">🕒</span><span id="ov-time">${{localTime}}</span></div>
                <div class="ov-row"><span class="ov-icon">⛅</span><span id="ov-weather">{data.get("weather", "N/A")}</span></div>
                <div class="ov-row"><span class="ov-icon">💵</span><span id="ov-curr">{data.get("curr", "N/A")}</span></div>
                <div class="ov-row"><span class="ov-icon">📞</span><span id="ov-phone">{data.get("phone", "N/A")}</span></div>
            </div>

            <div id="legend">
                <div class="lg-row"><span class="lg-color" style="background:#00ccff;"></span> {translator.get("ni_residential")}</div>
                <div class="lg-row"><span class="lg-color" style="background:#ffaa00;"></span> {translator.get("ni_cafes")}</div>
                <div class="lg-row"><span class="lg-color" style="background:#55ff55;"></span> {translator.get("ni_parks")}</div>
                <div class="lg-row"><span class="lg-color" style="background:#ff0055;"></span> {translator.get("ni_wifi")}</div>
            </div>
            `;
            document.body.appendChild(div);

            if ({"true" if data.get("is_day") else "false"}) {{
                if (typeof defaultTile !== 'undefined') {{
                    defaultTile.setUrl('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png');
                }}
            }}

            var geoJsonStr = {__import__("json").dumps(data.get("geojson"))};
            if (geoJsonStr && typeof L !== 'undefined') {{
                L.geoJSON(geoJsonStr, {{
                    pointToLayer: function (feature, latlng) {{
                        return L.circleMarker(latlng, {{ radius: 4 }});
                    }},
                    style: function(feature) {{
                        var color = "#00ccff";
                        var fill = "#00ccff";
                        var p = feature.properties;
                        if (p.amenity) {{
                            color = "#ffaa00"; fill = "#ffaa00";
                        }} else if (p.leisure) {{
                            color = "#55ff55"; fill = "#55ff55";
                        }} else if (p.building) {{
                            color = "#00ccff"; fill = "#00ccff";
                        }}
                        return {{
                            color: color,
                            weight: 2,
                            fillColor: fill,
                            fillOpacity: 0.35
                        }};
                    }}
                }}).addTo(map);
            }}

            // Plot WLOC WiFi Points if available
            var wlocData = {__import__("json").dumps(getattr(self, "wloc_data", []))};
            if (wlocData && wlocData.length > 0 && typeof L !== 'undefined') {{
                wlocData.forEach(function(item) {{
                    var circle = L.circleMarker([item.lat, item.lon], {{
                        radius: 5,
                        fillColor: "#ff0055",
                        color: "#000",
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.9
                    }}).addTo(map);
                    circle.bindPopup("<b style='color:black;'>WiFi: " + item.mac + "</b>");
                }});
            }}

        }})();
        """
        self.map_view.page().runJavaScript(js_code)
