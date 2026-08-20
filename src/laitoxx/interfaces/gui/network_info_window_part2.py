"""Focused behavior slice for NetworkInfoWindow."""
# ruff: noqa: F405

from .network_info_window_context import *  # noqa: F403


class NetworkInfoWindowMixin2:
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
                data["weather"] = f"{cw.get('temperature', '?')}°C, Wind: {cw.get('windspeed', '?')}km/h"
                daily = r.get("daily", {})
                if daily and daily.get("sunrise") and daily.get("sunset"):
                    cTime = cw.get("time")
                    data["is_day"] = cTime >= daily["sunrise"][0] and cTime <= daily["sunset"][0]
            except Exception:
                pass

            target_ip = getattr(self, "resolved_ip", "")
            if target_ip:
                try:
                    r = requests.get(f"https://api.ipapi.is/?q={target_ip}", timeout=5).json()
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
                        gdf[col] = gdf[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
                    data["geojson"] = json.loads(gdf.to_json())
            except Exception as e:
                import logging

                logging.warning(f"OSMNX error: {e}")
                data["osmnx_error"] = str(e)

            # Freifunk OpenWiFiMap bridge to Apple WPS (for IP mode)
            if self.mode == "ip" and getattr(self, "lat", 0) != 0 and getattr(self, "lon", 0) != 0:
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
                                        mac = ":".join(hex_str[i : i + 2] for i in range(0, 12, 2))
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
                            os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

                            wloc_accumulated = []
                            # query first 10 candidates to avoid spamming
                            for bssid in bssid_pool[:10]:
                                locs = query_apple_wloc(bssid)
                                if locs and len(locs) > 1:
                                    # Found a hit!
                                    for k, v in locs.items():
                                        wloc_accumulated.append({"mac": k, "lat": v[0], "lon": v[1]})
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
            from laitoxx.features.web_audit.domain_intelligence import domain_intelligence

            func = domain_intelligence
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
        self._worker.error.connect(lambda e: self.console_output.append(f"\n[ERROR] {e}"))

        self._worker_thread.start()

    def closeEvent(self, event):
        self._stop_subdomain_discovery()
        if self._worker_thread:
            stop_and_detach_thread(self._worker_thread, self._worker)
        super().closeEvent(event)
