import re
from datetime import datetime


class MetadataForensics:
    # Known indicators of privacy leaks
    PRIVACY_LEAK_KEYS = [
        "GPS",
        "Latitude",
        "Longitude",
        "Altitude",
        "Author",
        "Creator",
        "Producer",
        "Software",
        "Camera",
        "Make",
        "Model",
        "SerialNumber",
        "LensSerialNumber",
        "OwnerName",
        "Artist",
        "Copyright",
        "DeviceManufacturer",
    ]

    @classmethod
    def calculate_privacy_score(cls, metadata: dict) -> dict:
        score = 100
        leaks = []
        for k, v in metadata.items():
            k_lower = k.lower()
            for leak_kw in cls.PRIVACY_LEAK_KEYS:
                if leak_kw.lower() in k_lower:
                    leaks.append((k, v))
                    score -= 5
                    break

        score = max(0, score)
        return {
            "score": score,
            "leaks": leaks,
            "risk_level": "High" if score < 50 else "Medium" if score < 80 else "Low",
            "message": cls._get_recommendation(score),
        }

    @classmethod
    def _get_recommendation(cls, score: int) -> str:
        if score < 50:
            return "Critical privacy leak! Use the Sanitizer to remove EXIF and Author tags before publishing."
        elif score < 80:
            return "Some identifiable data found (camera model, software). Consider sanitizing."
        return "Metadata looks relatively clean. Safe to share."

    @classmethod
    def detect_anomalies(cls, metadata: dict) -> list:
        anomalies = []

        # Helper to find keys safely
        def get_val(keys):
            for k in keys:
                if k in metadata:
                    return metadata[k]
            return None

        create_date = get_val(
            [
                "File:FileCreateDate",
                "EXIF:CreateDate",
                "Creation-Date",
                "Tika:Creation-Date",
                "XMP:CreateDate",
            ]
        )
        software = get_val(
            [
                "EXIF:Software",
                "XMP:CreatorTool",
                "Software",
                "Tika:producer",
                "Tika:creator",
            ]
        )
        mod_date = get_val(
            [
                "File:FileModifyDate",
                "EXIF:ModifyDate",
                "Last-Modified",
                "Tika:Last-Modified",
                "XMP:ModifyDate",
            ]
        )

        # 1. Date vs Software version
        if create_date and software:
            year_match = re.search(r"(19|20)\d{2}", str(create_date))
            soft_year_match = re.search(r"20\d{2}", str(software))  # Looking for e.g. Photoshop 2023
            if year_match and soft_year_match:
                c_year = int(year_match.group())
                s_year = int(soft_year_match.group())
                if s_year > c_year + 1:
                    anomalies.append(
                        f"Anomaly: Created in {c_year}, but software version implies {s_year} ({software}). Possible forgery."
                    )

        # 2. Mod < Create (Time Travel)
        if create_date and mod_date:
            try:
                c_str = str(create_date)[:10].replace(":", "-")
                m_str = str(mod_date)[:10].replace(":", "-")
                c_dt = datetime.strptime(c_str, "%Y-%m-%d")
                m_dt = datetime.strptime(m_str, "%Y-%m-%d")
                if m_dt < c_dt:
                    anomalies.append(f"Anomaly: Modified ({m_str}) before Creation ({c_str}). Timestamps tampered.")
            except Exception:
                pass

        # 3. Hidden Data or Steganography indicators
        # If filesize is much larger than typical for image dimensions (very basic heuristic)
        if "FileExtension" in metadata and metadata["FileExtension"] in [
            ".jpg",
            ".png",
            ".jpeg",
        ]:
            width = get_val(["EXIF:ExifImageWidth", "File:ImageWidth", "Exif.Photo.PixelXDimension"])
            height = get_val(
                [
                    "EXIF:ExifImageHeight",
                    "File:ImageHeight",
                    "Exif.Photo.PixelYDimension",
                ]
            )
            size = metadata.get("FileSize", 0)
            if width and height and size:
                try:
                    pixels = int(width) * int(height)
                    if metadata["FileExtension"] == ".jpg" and size / pixels > 2.5:
                        anomalies.append(
                            "Anomaly: File size is unusually large for its dimensions. Check for hidden data/steganography."
                        )
                except Exception:
                    pass

        # 4. Binwalk embedded files
        if "Binwalk:Steganography/Embedded" in metadata:
            anomalies.append(
                f"CRITICAL ANOMALY (Binwalk): Embedded files/signatures detected: {metadata['Binwalk:Steganography/Embedded']}"
            )

        # 5. Hachoir structural anomalies
        hachoir_keys = [k for k in metadata.keys() if k.startswith("Hachoir:")]
        if hachoir_keys:
            # We just add a note that Hachoir found structural data
            pass

        # 6. PDFiD anomalies
        pdfid_js = metadata.get("PDFiD:/JavaScript", 0)
        pdfid_js_upper = metadata.get("PDFiD:/JS", 0)
        pdfid_openact = metadata.get("PDFiD:/OpenAction", 0)
        if pdfid_js > 0 or pdfid_js_upper > 0:
            anomalies.append(
                f"CRITICAL ANOMALY (PDFiD): JavaScript detected inside PDF! Count: {pdfid_js + pdfid_js_upper}"
            )
        if pdfid_openact > 0:
            anomalies.append(
                "ANOMALY (PDFiD): /OpenAction detected. PDF will automatically execute an action upon opening."
            )

        return anomalies
