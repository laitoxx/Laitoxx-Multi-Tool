import asyncio
import hashlib
import logging
import os
import platform
from datetime import datetime

# MIME detection
try:
    import magic

    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

# Kreuzberg for generic documents/text/OCRing replacement for Tika
try:
    from kreuzberg import extract_file

    HAS_KREUZBERG = True
except ImportError:
    HAS_KREUZBERG = False

# Photos
try:
    import pyexiv2

    HAS_EXIV2 = True
except ImportError:
    HAS_EXIV2 = False

# Audio/Video
try:
    from tinytag import TinyTag

    HAS_TINYTAG = True
except ImportError:
    HAS_TINYTAG = False

try:
    import mutagen  # noqa: F401 — availability check
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

# Microsoft Office deep inspection
try:
    import olefile

    HAS_OLEFILE = True
except ImportError:
    HAS_OLEFILE = False

# PDFiD for PDF Forensics
try:
    from pdfid.pdfid import PDFiD

    HAS_PDFID = True
except ImportError:
    HAS_PDFID = False

# Binwalk / Hachoir for structure anomaly
try:
    from hachoir.metadata import extractMetadata
    from hachoir.parser import createParser

    HAS_HACHOIR = True
except ImportError:
    HAS_HACHOIR = False

# PE executables
try:
    import pefile

    HAS_PEFILE = True
except ImportError:
    HAS_PEFILE = False

# Binwalk for Steganography
try:
    import binwalk

    HAS_BINWALK = True
except ImportError:
    HAS_BINWALK = False

# ADS / xattr for Zone.Identifier
try:
    import xattr

    HAS_XATTR = True
except ImportError:
    HAS_XATTR = False


class MetadataEngine:
    def __init__(self):
        pass

    def get_mime_type(self, filepath: str) -> str:
        if HAS_MAGIC:
            try:
                # python-magic format
                return magic.from_file(filepath, mime=True)
            except Exception:
                pass
        import mimetypes

        return mimetypes.guess_type(filepath)[0] or "application/octet-stream"

    def extract_metadata(self, filepath: str) -> dict:
        if not os.path.exists(filepath):
            return {"error": "File not found"}

        data = {
            "FilePath": filepath,
            "FileName": os.path.basename(filepath),
            "FileSize": os.path.getsize(filepath),
            "FileExtension": os.path.splitext(filepath)[1].lower(),
            "MD5": self._compute_hash(filepath, "md5"),
            "ExtractedWith": [],
        }

        mime = self.get_mime_type(filepath)
        data["MIMEType"] = mime

        # 1. Hachoir Binary Parsing (Check Anomalies)
        if HAS_HACHOIR:
            try:
                parser = createParser(filepath)
                if parser:
                    metadata = extractMetadata(parser)
                    if metadata:
                        data["ExtractedWith"].append("Hachoir")
                        for line in metadata.exportPlaintext():
                            if ":" in line:
                                k, v = line.split(":", 1)
                                data[f"Hachoir:{k.strip()}"] = v.strip()
            except Exception as e:
                logging.debug(f"Hachoir failed for {filepath}: {e}")

        # 2. PyExiv2 (py3exiv2) for Photos
        if HAS_EXIV2 and mime.startswith("image/"):
            try:
                with pyexiv2.Image(filepath) as img:
                    data["ExtractedWith"].append("pyexiv2(EXIF)")
                    exif = img.read_exif()
                    if exif:
                        data.update(exif)
                    xmp = img.read_xmp()
                    if xmp:
                        data.update(xmp)
                    iptc = img.read_iptc()
                    if iptc:
                        data.update(iptc)
            except Exception as e:
                logging.debug(f"pyexiv2 failed for {filepath}: {e}")

        # 3. Audio / Video (TinyTag + Mutagen)
        if HAS_TINYTAG and (mime.startswith("audio/") or mime.startswith("video/")):
            try:
                tag = TinyTag.get(filepath)
                if tag:
                    data["ExtractedWith"].append("TinyTag")
                    for k, v in tag.as_dict().items():
                        if v is not None:
                            data[f"Media:{k.capitalize()}"] = v
            except Exception:
                pass

            # Use Mutagen for deeper/raw tags
            try:
                import mutagen

                mutagen_file = mutagen.File(filepath)
                if mutagen_file is not None:
                    if "Mutagen" not in data["ExtractedWith"]:
                        data["ExtractedWith"].append("Mutagen")
                    for k, v in mutagen_file.items():
                        # Convert arrays or weird objects to string
                        data[f"Mutagen:{k}"] = str(v)
            except Exception:
                pass

        # 4. Deep Office Parsing (olefile + oletools)
        is_office = mime in [
            "application/msword",
            "application/vnd.ms-excel",
            "application/vnd.ms-powerpoint",
        ]
        if HAS_OLEFILE and (
            is_office or data["FileExtension"] in [".doc", ".xls", ".ppt"]
        ):
            if olefile.isOleFile(filepath):
                try:
                    with olefile.OleFileIO(filepath) as ole:
                        meta = ole.get_metadata()
                        data["ExtractedWith"].append("olefile")
                        for prop in meta.SUMMARY_ATTRIBS + meta.DOCSUM_ATTRIBS:
                            val = getattr(meta, prop, None)
                            if val:
                                data[f"Office:{prop}"] = str(val)
                except Exception:
                    pass

                # oleid for malicious macro/OLE checks
                try:
                    from oletools.oleid import OleID

                    oid = OleID(filepath)
                    indicators = oid.check()
                    data["ExtractedWith"].append("oleid")
                    for ind in indicators:
                        data[f"OleID:{ind.name}"] = f"{ind.value} (Risk: {ind.risk})"
                except Exception as e:
                    logging.debug(f"oleid failed: {e}")

        # 5. PE File Executables
        if HAS_PEFILE and (data["FileExtension"] in [".exe", ".dll", ".sys"]):
            try:
                pe = pefile.PE(filepath)
                data["ExtractedWith"].append("pefile")
                data["PE:Machine"] = hex(pe.FILE_HEADER.Machine)
                data["PE:TimeDateStamp"] = datetime.fromtimestamp(
                    pe.FILE_HEADER.TimeDateStamp
                ).isoformat()
                data["PE:NumberOfSections"] = pe.FILE_HEADER.NumberOfSections
                data["PE:Imphash"] = pe.get_imphash()

                # Linker Version
                data["PE:LinkerVersion"] = (
                    f"{pe.OPTIONAL_HEADER.MajorLinkerVersion}.{pe.OPTIONAL_HEADER.MinorLinkerVersion}"
                )

                # Imports
                if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                    dlls = [
                        entry.dll.decode("utf-8", "ignore")
                        for entry in pe.DIRECTORY_ENTRY_IMPORT
                        if entry.dll
                    ]
                    data["PE:ImportedDLLs"] = ", ".join(dlls)

                # Exports
                if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
                    exports = [
                        exp.name.decode("utf-8", "ignore")
                        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols
                        if exp.name
                    ]
                    data["PE:ExportedFunctionsCount"] = len(exports)
            except Exception:
                pass

        # 5.5. Binwalk for Steganography
        if HAS_BINWALK:
            try:
                # Binwalk signature scan
                # We use signature=True, quiet=True
                modules = binwalk.scan(filepath, signature=True, quiet=True)
                if modules:
                    data["ExtractedWith"].append("binwalk")
                    binwalk_findings = []
                    for module in modules:
                        for result in module.results:
                            binwalk_findings.append(
                                f"{result.offset}: {result.description}"
                            )
                    if len(binwalk_findings) > 1:  # Usually index 0 is the file itself
                        data["Binwalk:Steganography/Embedded"] = " | ".join(
                            binwalk_findings
                        )
            except Exception as e:
                logging.debug(f"Binwalk failed for {filepath}: {e}")

        # 6. Alternate Data Streams / Extended Attributes (Zone.Identifier)
        self._extract_os_attributes(filepath, data)

        # 7. Kreuzberg (General doc extraction)
        if HAS_KREUZBERG and not mime.startswith("image/"):
            try:

                async def run_kreuzberg():
                    return await extract_file(filepath)

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if not loop.is_running():
                    result = loop.run_until_complete(run_kreuzberg())
                    if result:
                        data["ExtractedWith"].append("Kreuzberg")
                        data["Kreuzberg:Mime"] = result.mime_type
                        if result.content:
                            data["Kreuzberg:TextPreview"] = result.content[:200] + "..."
            except Exception as e:
                logging.debug(f"Kreuzberg failed for {filepath}: {e}")

        # 8. PDFiD for PDF analysis
        if HAS_PDFID and filepath.lower().endswith(".pdf"):
            try:
                res = PDFiD(filepath)
                pdfid_data = {}
                for node in res.documentElement.getElementsByTagName("Keyword"):
                    name = node.getAttribute("Name")
                    count = int(node.getAttribute("Count"))
                    pdfid_data[name] = count

                if pdfid_data:
                    data["ExtractedWith"].append("PDFiD")
                    for k, v in pdfid_data.items():
                        data[f"PDFiD:{k}"] = v
            except Exception as e:
                logging.debug(f"PDFiD failed for {filepath}: {e}")

        return data

    def _extract_os_attributes(self, filepath: str, data: dict):
        if platform.system() == "Windows":
            try:
                zone_file = filepath + ":Zone.Identifier"
                if os.path.exists(zone_file):
                    with open(zone_file) as f:
                        data["ADS:Zone.Identifier"] = f.read().strip()
                        data["ExtractedWith"].append("ADS")
            except Exception:
                pass
        else:
            if HAS_XATTR:
                try:
                    attrs = xattr.listxattr(filepath)
                    if attrs:
                        data["ExtractedWith"].append("xattr")
                        for attr in attrs:
                            val = xattr.getxattr(filepath, attr)
                            try:
                                data[f"xattr:{attr}"] = val.decode("utf-8")
                            except UnicodeDecodeError:
                                data[f"xattr:{attr}"] = (
                                    f"<Binary Data: {len(val)} bytes>"
                                )
                except Exception:
                    pass

    def _compute_hash(self, filepath: str, algo: str) -> str:
        h = hashlib.new(algo)
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""


engine_instance = MetadataEngine()
