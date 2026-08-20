"""Generate a reproducible third-party dependency and license inventory."""

from __future__ import annotations

import importlib.metadata as metadata
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _requirement_names(path: Path) -> list[str]:
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.match(r"[A-Za-z0-9_.-]+", line)
        if match:
            names.append(match.group(0))
    return names


def _license_name(dist: metadata.Distribution) -> str:
    value = (dist.metadata.get("License-Expression") or dist.metadata.get("License") or "").strip()
    if value and len(value) < 160 and "\n" not in value:
        return value
    classifiers = dist.metadata.get_all("Classifier") or []
    licenses = [item.rsplit("::", 1)[-1].strip() for item in classifiers if "License ::" in item]
    return ", ".join(licenses) or "See bundled upstream license text"


def generate() -> None:
    destination = ROOT / "licenses" / "python"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Third-party licenses",
        "",
        "Laitoxx is not affiliated with the projects below. Components retain their original licenses.",
        "",
        "## Scanner and fingerprint assets",
        "",
        "| Component | Usage | License | Full text |",
        "|---|---|---|---|",
        "| Masscan 1.3.2 | Downloaded from the official source release and built locally | AGPL-3.0 | `licenses/external/masscan-AGPL-3.0.txt` |",
        "| FingerprintHub rules | Packaged fingerprint subset | MIT | `licenses/external/fingerprinthub-MIT.txt` |",
        "| Nuclei Templates rules | Packaged fingerprint subset | MIT | `licenses/external/nuclei-templates-MIT.txt` |",
        "| Rapid7 Recog rules | Packaged fingerprint subset | BSD-2-Clause | `licenses/external/recog-BSD-2-Clause.txt` |",
        "| Nerva rules | Packaged fingerprint subset | Apache-2.0 | `licenses/external/nerva-Apache-2.0.txt` |",
        "| JA3 lists | Packaged fingerprint subset | BSD-3-Clause | `licenses/external/ja3-BSD-3-Clause.txt` |",
        "| HASSH metadata | Packaged fingerprint subset | BSD-3-Clause | `licenses/external/hassh-BSD-3-Clause.txt` |",
        "",
        "The packaged database intentionally excludes Nmap service probes, WhatWeb, Leetha, p0f and Wappalyzer-derived rows. "
        "Those sources have copyleft or NPSL terms which cannot be applied to the whole project without an explicit project-license decision.",
        "",
        "## Declared Python dependencies",
        "",
        "| Package | Installed version | License metadata | Upstream |",
        "|---|---:|---|---|",
    ]
    for name in _requirement_names(ROOT / "requirements.txt"):
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            lines.append(f"| {name} | not installed | inspect on installation | |")
            continue
        project_urls = dist.metadata.get_all("Project-URL") or []
        upstream = next((url.split(",", 1)[1].strip() for url in project_urls if "," in url), "")
        upstream = upstream or dist.metadata.get("Home-page") or ""
        lines.append(f"| {name} | {dist.version} | {_license_name(dist).replace('|', '/')} | {upstream} |")
        files = dist.files or []
        candidates = [
            file
            for file in files
            if file.name.casefold().startswith(("license", "licence", "copying", "notice"))
            or "licenses" in {part.casefold() for part in file.parts}
        ]
        package_dir = destination / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        for index, file in enumerate(candidates[:20], 1):
            source = Path(dist.locate_file(file))
            if source.is_file():
                package_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, package_dir / f"{index:02d}-{source.name}")
    lines.extend(
        (
            "",
            "This inventory reports the environment used to build this repository snapshot. "
            "Wheel and system-package distributions may add their own notices; retain those notices when redistributing them.",
            "",
        )
    )
    (ROOT / "THIRD_PARTY_LICENSES.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    generate()
