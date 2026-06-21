import logging
import re

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None
    QWebEngineSettings = None
    logging.warning("PyQt6-WebEngine not installed. Maps will not be rendered.")

from laitoxx.interfaces.gui.translator import translator
from laitoxx.interfaces.gui.worker import Worker, stop_and_detach_thread


class NetworkInfoWindow(QDialog):
    osint_data_ready = pyqtSignal(dict)

    def __init__(self, parent=None, mode="ip", theme_data=None):
        super().__init__(parent)
        self.mode = mode
        self.theme_data = theme_data or {}
        if mode == "ip":
            self.setWindowTitle(translator.get("ni_title_ip"))
        elif mode == "mac":
            self.setWindowTitle(translator.get("ni_title_mac"))
        else:
            self.setWindowTitle(translator.get("ni_title_website"))
        self.resize(1100, 750)
        self.setWindowOpacity(0.92)  # Add glass effect / transparency
        self.osint_data_ready.connect(self._on_osint_data_ready)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top Bar (Search)
        top_bar = QHBoxLayout()
        self.input_field = QLineEdit()
        if mode == "ip":
            self.input_field.setPlaceholderText(translator.get("ni_placeholder_ip"))
        elif mode == "mac":
            self.input_field.setPlaceholderText(translator.get("ni_placeholder_mac"))
        else:
            self.input_field.setPlaceholderText(translator.get("ni_placeholder_domain"))
        self.input_field.returnPressed.connect(self.run_search)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
            }
        """)

        self.search_btn = QPushButton(translator.get("ni_search"))
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
        """)
        self.search_btn.clicked.connect(self.run_search)

        top_bar.addWidget(self.input_field)
        top_bar.addWidget(self.search_btn)
        layout.addLayout(top_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate animation
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left: Tabs (Console Output & Data)
        self.tabs = QTabWidget()
        self.console_tab = QWidget()
        console_layout = QVBoxLayout(self.console_tab)
        console_layout.setContentsMargins(0, 0, 0, 0)
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        console_layout.addWidget(self.console_output)
        self.tabs.addTab(self.console_tab, translator.get("ni_terminal"))

        splitter.addWidget(self.tabs)

        # Right: Map (For IP and MAC mode)
        if self.mode in ("ip", "mac"):
            map_container = QWidget()
            map_layout = QVBoxLayout(map_container)
            map_layout.setContentsMargins(0, 0, 0, 0)

            if QWebEngineView:
                self.map_view = QWebEngineView()
                settings = self.map_view.settings()
                settings.setAttribute(
                    QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                    True,
                )
                settings.setAttribute(
                    QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
                )
                self._load_empty_map()
                map_layout.addWidget(self.map_view)
            else:
                self.map_view = None
                lbl = QLabel(
                    "Map view requires PyQt6-WebEngine.\nPlease install it via 'pip install PyQt6-WebEngine'"
                )
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("color: #ff5555; font-size: 14px;")
                map_layout.addWidget(lbl)

            splitter.addWidget(map_container)
            splitter.setSizes([550, 550])
        else:
            self.map_view = None
            splitter.setSizes([1100])

        self._worker_thread = None
        self._worker = None
        self.lat = 0.0
        self.lon = 0.0

        self._apply_theme()

    def _apply_theme(self):
        bg = self.theme_data.get("bg_color", "#1a1a1a")
        fg = self.theme_data.get("text_color", "#ffffff")
        bdr = self.theme_data.get("border_color", "#444444")

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

    def _load_empty_map(
        self, lat=20.0, lon=0.0, zoom=2, marker_text=None, target_ip=""
    ):
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
            self.console_output.append("This usually happens on Windows if 'geopandas'/'fiona' or C++ Build Tools are missing, or if OpenStreetMap blocked the IP.\n")


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

    def _fetch_osint_data_bg(self):
        def worker():
            import requests

            tz_id = getattr(self, "timezone_id", "UTC")

            data = {
                "tz_id": tz_id,
                "weather": "N/A",
                "curr": "N/A",
                "lang": "N/A",
                "phone": "N/A",
                "is_day": False,
            }

            try:
                r = requests.get(
                    f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&current_weather=true&daily=sunrise,sunset&timezone=auto",
                    timeout=5,
                ).json()
                cw = r.get("current_weather", {})
                data["weather"] = (
                    f"{cw.get('temperature', '?')}°C, Wind: {cw.get('windspeed', '?')}km/h"
                )
                daily = r.get("daily", {})
                if daily and daily.get("sunrise") and daily.get("sunset"):
                    cTime = cw.get("time")
                    data["is_day"] = (
                        cTime >= daily["sunrise"][0] and cTime <= daily["sunset"][0]
                    )
            except Exception:
                pass

            target_ip = getattr(self, "resolved_ip", "")
            if target_ip:
                try:
                    r = requests.get(
                        f"https://api.ipapi.is/?q={target_ip}", timeout=5
                    ).json()
                    loc = r.get("location", {})

                    if loc.get("currency_code"):
                        data["curr"] = loc.get("currency_code")

                    if loc.get("calling_code"):
                        data["phone"] = f"+{loc.get('calling_code').replace('+', '')}"
                except Exception:
                    pass

            # Fetch Geo Data using osmnx
            try:
                import json

                import osmnx as ox

                tags = {
                    "building": True,
                    "amenity": True,
                    "leisure": True,
                }
                gdf = ox.features_from_point((self.lat, self.lon), tags=tags, dist=200)
                if not gdf.empty:
                    # Drop columns that have complex types
                    for col in gdf.columns:
                        if col == "geometry":
                            continue
                        gdf[col] = gdf[col].apply(
                            lambda x: str(x) if isinstance(x, (list, dict)) else x
                        )
                    data["geojson"] = json.loads(gdf.to_json())
            except Exception as e:
                import logging

                logging.warning(f"OSMNX error: {e}")
                data["osmnx_error"] = str(e)

            # Freifunk OpenWiFiMap bridge to Apple WPS (for IP mode)
            if (
                self.mode == "ip"
                and getattr(self, "lat", 0) != 0
                and getattr(self, "lon", 0) != 0
            ):
                try:
                    min_lon, min_lat = self.lon - 0.005, self.lat - 0.005
                    max_lon, max_lat = self.lon + 0.005, self.lat + 0.005
                    bbox = f"{min_lon},{min_lat},{max_lon},{max_lat}"
                    r = requests.get(
                        f"https://api.openwifimap.net/view_nodes_spatial?bbox={bbox}",
                        timeout=5,
                    )
                    if r.status_code == 200:
                        rows = r.json().get("rows", [])
                        bssid_pool = []
                        for row in rows:
                            node_id = row.get("id", "")
                            clean_id = node_id.lower().replace(":", "").strip()
                            if len(clean_id) == 12:
                                try:
                                    base_int = int(clean_id, 16)
                                    for offset in [-1, 0, 1, 2, 3, 4]:
                                        mutated_int = base_int + offset
                                        hex_str = f"{mutated_int:012x}"
                                        mac = ":".join(
                                            hex_str[i : i + 2] for i in range(0, 12, 2)
                                        )
                                        bssid_pool.append(mac)
                                except ValueError:
                                    pass

                        if bssid_pool:
                            import os

                            import urllib3

                            from laitoxx.features.network.mac_lookup import (
                                query_apple_wloc,
                            )

                            urllib3.disable_warnings()
                            os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = (
                                "python"
                            )

                            wloc_accumulated = []
                            # query first 10 candidates to avoid spamming
                            for bssid in bssid_pool[:10]:
                                locs = query_apple_wloc(bssid)
                                if locs and len(locs) > 1:
                                    # Found a hit!
                                    for k, v in locs.items():
                                        wloc_accumulated.append(
                                            {"mac": k, "lat": v[0], "lon": v[1]}
                                        )
                                    break  # We got the massive response, stop polling

                            if wloc_accumulated:
                                self.wloc_data = wloc_accumulated
                except Exception as e:
                    import logging

                    logging.warning(f"Freifunk Apple bridge error: {e}")

            self.osint_data_ready.emit(data)

        import threading

        threading.Thread(target=worker, daemon=True).start()

    def run_search(self):
        target = self.input_field.text().strip()
        if not target:
            return

        self.progress_bar.setVisible(True)
        self.console_output.clear()
        self.console_output.append(f"Starting analysis for {target}...\n")
        self.search_btn.setEnabled(False)
        self._load_empty_map(marker_text=f"Locating {target}...")

        # Stop previous worker if running
        if self._worker_thread:
            stop_and_detach_thread(self._worker_thread, self._worker)
            self._worker_thread = None
            self._worker = None

        # Import dynamically to avoid circular imports
        if self.mode == "ip":
            from laitoxx.features.network.ip_info import get_ip

            func = get_ip
            input_data = {"ip": target}
        elif self.mode == "mac":
            from laitoxx.features.network.mac_lookup import search_mac_address

            func = search_mac_address
            input_data = {"mac": target}
        else:
            from laitoxx.features.web_audit.website_info import get_website_info

            func = get_website_info
            input_data = target

        self._worker = Worker(func, input_data)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker.finished.connect(self._on_search_finished)
        self._worker.update.connect(self._handle_output)
        self._worker.error.connect(
            lambda e: self.console_output.append(f"\n[ERROR] {e}")
        )

        self._worker_thread.start()

    def closeEvent(self, event):
        if self._worker_thread:
            stop_and_detach_thread(self._worker_thread, self._worker)
        super().closeEvent(event)

    def _handle_output(self, text: str):
        # Auto-scroll prep
        scrollbar = self.console_output.verticalScrollBar()
        was_at_bottom = scrollbar.value() == scrollbar.maximum()

        # Parse Terminal Output to Normalized HTML
        text = text.replace("\x1b[0m", "")  # Just in case there are stray ANSI codes
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Headers
            if line.startswith("┌─["):
                header = line.replace("┌─[", "").split("]")[0].strip()
                self.console_output.append(
                    f"<br><div style='background-color: rgba(60,60,60,0.5); padding: 5px; border-radius: 4px; border-left: 3px solid #00ffcc;'><b><font color='#00ffcc'>{header}</font></b></div>"
                )
                continue

            # Map Coordinate parsing logic (For IP and MAC)
            if self.mode in ("ip", "mac"):
                if line.startswith("APPLE_WLOC_DATA:"):
                    try:
                        import json

                        wloc_json = line.replace("APPLE_WLOC_DATA:", "")
                        self.wloc_data = json.loads(wloc_json)
                        self._fetch_osint_data_bg()
                    except Exception as e:
                        print("Failed to parse WLOC JSON:", e)
                    continue

                if "Latitude" in line and ":" in line:
                    try:
                        val = line.split(":")[-1].strip()
                        if val and val != "None":
                            self.lat = float(val)
                    except ValueError:
                        pass
                elif "Longitude" in line and ":" in line:
                    try:
                        val = line.split(":")[-1].strip()
                        if val and val != "None":
                            self.lon = float(val)
                            if self.lat != 0.0 and self.lon != 0.0:
                                target_txt = getattr(
                                    self, "resolved_ip", self.input_field.text().strip()
                                )
                                self._load_empty_map(
                                    self.lat,
                                    self.lon,
                                    zoom=15 if self.mode == "mac" else 11,
                                    marker_text=target_txt,
                                    target_ip=target_txt,
                                )
                    except ValueError:
                        pass

            # Properties
            if line.startswith("│"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].replace("│", "").strip()
                    val = parts[1].strip()

                    if key == "IP" and self.mode == "ip":
                        self.resolved_ip = val
                    elif key == "Timezone":
                        self.timezone_id = val.split()[0] if " " in val else val
                        if self.lat != 0.0 and self.lon != 0.0:
                            self._fetch_osint_data_bg()
                    elif key == "Country":
                        match = re.search(r"\((.*?)\)", val)
                        if match:
                            self.country_code = match.group(1)

                    # Ping table specific logic
                    if "Location (Network)" in key and "Avg Ping" in val:
                        self.console_output.append(
                            "<div style='color: #00ffcc; font-weight: bold; margin-top: 10px; margin-bottom: 5px;'>🌍 Globalping Results:</div>"
                        )
                        continue

                    if "ms" in val and "[" in val and "loss" in val:
                        try:
                            avg_ping, rest = val.split("[")
                            min_max, loss = rest.split("]")
                            avg_ping = avg_ping.strip()
                            min_max = min_max.strip()
                            loss = loss.strip()

                            val_color = "#55ff55" if "0%" in loss else "#ff5555"

                            html_row = f"""<table width="100%" cellspacing="0" cellpadding="4" style="background-color: rgba(30,30,30,0.6); border: 1px solid #444; margin-bottom: 3px; border-radius: 4px;">
                                <tr>
                                    <td width="35%" style="color: #8ab4f8; font-weight: bold;">{key}</td>
                                    <td width="20%" style="color: #e0e0e0;">{avg_ping}</td>
                                    <td width="25%" align="center" style="color: #aaaaaa;">[{min_max}]</td>
                                    <td width="20%" align="right" style="color:{val_color}; font-weight: bold;">{loss}</td>
                                </tr>
                            </table>"""
                            self.console_output.append(html_row)
                            continue
                        except Exception:
                            pass

                    if val == "FAILED":
                        html_row = f"""<table width="100%" cellspacing="0" cellpadding="4" style="background-color: rgba(30,30,30,0.6); border: 1px solid #444; margin-bottom: 3px; border-radius: 4px;">
                            <tr>
                                <td width="35%" style="color: #8ab4f8; font-weight: bold;">{key}</td>
                                <td width="65%" align="center" style="color: #ff5555; font-weight: bold;">FAILED</td>
                            </tr>
                        </table>"""
                        self.console_output.append(html_row)
                        continue

                    # Apply colors based on value context
                    val_color = "#e0e0e0"
                    self.console_output.append(
                        f"<span style='color: #8ab4f8;'><b>{key}</b></span> &nbsp; <span style='color: {val_color};'>{val}</span>"
                    )
                else:
                    self.console_output.append(
                        f"<span style='color: #cccccc;'>{line.replace('│', '').strip()}</span>"
                    )
                continue

            # Ignore closing borders
            if (
                line.startswith("└─")
                or line.startswith("╔═")
                or line.startswith("║")
                or line.startswith("╚═")
            ):
                continue

            # Default text
            self.console_output.append(f"<span style='color: #bbbbbb;'>{line}</span>")

        # Auto-scroll to bottom
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _on_search_finished(self):
        self.search_btn.setEnabled(True)
        self.console_output.append(
            "<br><span style='color: #55ff55;'>[✓] Analysis complete.</span>"
        )

        # If in website mode, or if lat/lon failed to parse, stop the progress animation
        if self.mode == "website" or getattr(self, "lat", 0.0) == 0.0:
            self.progress_bar.setVisible(False)
