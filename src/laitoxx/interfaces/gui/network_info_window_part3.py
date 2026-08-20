"""Focused behavior slice for NetworkInfoWindow."""
# ruff: noqa: F405

from .network_info_window_context import *  # noqa: F403


class NetworkInfoWindowMixin3:
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
                                target_txt = getattr(self, "resolved_ip", self.input_field.text().strip())
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
                    self.console_output.append(f"<span style='color: #cccccc;'>{line.replace('│', '').strip()}</span>")
                continue

            # Ignore closing borders
            if line.startswith("└─") or line.startswith("╔═") or line.startswith("║") or line.startswith("╚═"):
                continue

            # Default text
            self.console_output.append(f"<span style='color: #bbbbbb;'>{line}</span>")

        # Auto-scroll to bottom
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _on_search_finished(self):
        self.search_btn.setEnabled(True)
        self.console_output.append("<br><span style='color: #55ff55;'>[✓] Analysis complete.</span>")

        # If in website mode, or if lat/lon failed to parse, stop the progress animation
        if self.mode == "website" or getattr(self, "lat", 0.0) == 0.0:
            self.progress_bar.setVisible(False)
