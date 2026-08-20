"""Native graph palette and vector glyph renderer."""

# ruff: noqa: E701, E702

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QFont, QPainter, QPainterPath

# raster surface and retain their bounded, inspectable Qt scene instead.

_TYPE_PALETTE = {
    "Person": "#fbbf24",
    "Email": "#7dd3fc",
    "Phone": "#86efac",
    "Website": "#c4b5fd",
    "Domain": "#a78bfa",
    "URL": "#67e8f9",
    "IP": "#fb7185",
    "ASN": "#fbbf24",
    "Network": "#fb923c",
    "DNS": "#2dd4bf",
    "Service": "#60a5fa",
    "Database": "#38bdf8",
    "AdminPanel": "#fb7185",
    "RemoteAccess": "#f59e0b",
    "Monitoring": "#22d3ee",
    "MessageBroker": "#fbbf24",
    "DevOps": "#a78bfa",
    "FileService": "#34d399",
    "MailService": "#7dd3fc",
    "Software": "#818cf8",
    "Certificate": "#34d399",
    "Organization": "#a3e635",
    "Company": "#86efac",
    "Cloud": "#93c5fd",
    "Vulnerability": "#f94144",
    "ThreatIndicator": "#fca5a5",
    "Document": "#ddd6fe",
    "Username": "#ff6b6b",
    "SocialAccount": "#74b9ff",
    "AltAccount": "#fdcb6e",
    "Category": "#a29bfe",
    "Address": "#fed7aa",
    "TONWallet": "#2aabee",
    "TONNFT": "#818cf8",
    "TONCollection": "#a78bfa",
    "TelegramGift": "#f472b6",
    "TelegramProfile": "#38bdf8",
    "BlockchainEvent": "#fbbf24",
    "Jetton": "#34d399",
}

_TYPE_GLYPHS = {
    "Person": "person",
    "Email": "mail",
    "Phone": "phone",
    "Website": "globe",
    "Domain": "globe",
    "URL": "link",
    "IP": "ip",
    "ASN": "network",
    "Network": "network",
    "DNS": "dns",
    "Service": "service",
    "Database": "database",
    "AdminPanel": "shield",
    "RemoteAccess": "key",
    "Software": "box",
    "Monitoring": "monitor",
    "MessageBroker": "broker",
    "DevOps": "terminal",
    "FileService": "folder",
    "MailService": "mail",
    "Certificate": "certificate",
    "Organization": "building",
    "Company": "building",
    "Cloud": "cloud",
    "Vulnerability": "alert",
    "ThreatIndicator": "alert",
    "Document": "document",
    "Username": "person",
    "SocialAccount": "person",
    "AltAccount": "person",
    "Category": "tag",
    "Address": "pin",
    "TONWallet": "tonwallet",
    "TONNFT": "nft",
    "TONCollection": "collection",
    "TelegramGift": "gift",
    "TelegramProfile": "telegram",
    "BlockchainEvent": "blockevent",
    "Jetton": "coin",
}

_TYPE_THEME_KEYS = {
    "Domain": "graph_node_domain_color",
    "Website": "graph_node_domain_color",
    "URL": "graph_node_url_color",
    "IP": "graph_node_ip_color",
    "ASN": "graph_node_asn_color",
    "Network": "graph_node_prefix_color",
    "DNS": "graph_node_dns_record_color",
    "Service": "graph_node_service_color",
    "Database": "graph_node_service_color",
    "AdminPanel": "graph_node_service_color",
    "RemoteAccess": "graph_node_service_color",
    "Monitoring": "graph_node_service_color",
    "MessageBroker": "graph_node_service_color",
    "DevOps": "graph_node_service_color",
    "FileService": "graph_node_service_color",
    "MailService": "graph_node_service_color",
    "Software": "graph_node_cpe_color",
    "Organization": "graph_node_organization_color",
    "Company": "graph_node_organization_color",
    "Vulnerability": "graph_node_cve_color",
}


def paint_glyph(painter: QPainter, glyph: str):
    if glyph == "tonwallet":
        painter.drawRoundedRect(QRectF(-12, -8, 24, 17), 3, 3)
        painter.drawLine(-11, -7, 5, -12)
        painter.drawRoundedRect(QRectF(3, -3, 10, 7), 2, 2)
        painter.drawPoint(7, 0)
    elif glyph == "nft":
        painter.drawRoundedRect(QRectF(-11, -11, 22, 22), 4, 4)
        painter.drawEllipse(QRectF(-7, -7, 6, 6))
        path = QPainterPath()
        path.moveTo(-8, 7)
        path.lineTo(-2, 1)
        path.lineTo(2, 5)
        path.lineTo(6, 1)
        path.lineTo(9, 7)
        painter.drawPath(path)
    elif glyph == "collection":
        painter.drawRect(QRectF(-10, -7, 20, 17))
        painter.drawLine(-7, -11, 7, -11)
        painter.drawLine(-5, -7, -5, 10)
        painter.drawLine(-4, -2, 6, -2)
        painter.drawLine(-4, 4, 6, 4)
    elif glyph == "gift":
        painter.drawRect(QRectF(-11, -5, 22, 16))
        painter.drawRect(QRectF(-13, -10, 26, 6))
        painter.drawLine(0, -10, 0, 11)
        painter.drawArc(QRectF(-10, -15, 10, 7), 0, 180 * 16)
        painter.drawArc(QRectF(0, -15, 10, 7), 0, 180 * 16)
    elif glyph == "telegram":
        path = QPainterPath()
        path.moveTo(-12, -2)
        path.lineTo(12, -11)
        path.lineTo(5, 12)
        path.lineTo(-1, 5)
        path.lineTo(-7, 10)
        path.lineTo(-5, 2)
        path.closeSubpath()
        painter.drawPath(path)
    elif glyph == "blockevent":
        painter.drawRoundedRect(QRectF(-11, -10, 22, 20), 3, 3)
        painter.drawLine(-6, -5, 6, -5)
        painter.drawLine(-6, 0, 3, 0)
        painter.drawLine(-6, 5, 6, 5)
    elif glyph == "coin":
        painter.drawEllipse(QRectF(-10, -10, 20, 20))
        painter.drawLine(0, -6, 0, 6)
        painter.drawArc(QRectF(-5, -6, 10, 7), 0, 180 * 16)
        painter.drawArc(QRectF(-5, -1, 10, 7), 180 * 16, 180 * 16)
    elif glyph == "database":
        painter.drawEllipse(QRectF(-10, -11, 20, 7))
        painter.drawLine(-10, -7, -10, 10)
        painter.drawLine(10, -7, 10, 10)
        painter.drawArc(QRectF(-10, 5, 20, 10), 0, -180 * 16)
    elif glyph == "globe":
        painter.drawEllipse(QRectF(-10, -10, 20, 20))
        painter.drawLine(-10, 0, 10, 0)
        painter.drawEllipse(QRectF(-5, -10, 10, 20))
    elif glyph == "document":
        painter.drawRect(QRectF(-8, -11, 16, 22))
        painter.drawLine(-5, -4, 5, -4)
        painter.drawLine(-5, 2, 5, 2)
    elif glyph == "alert":
        path = QPainterPath()
        path.moveTo(0, -12)
        path.lineTo(11, 10)
        path.lineTo(-11, 10)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(0, -5, 0, 4)
        painter.drawPoint(0, 7)
    elif glyph == "network":
        painter.drawEllipse(QRectF(-12, -4, 7, 7))
        painter.drawEllipse(QRectF(5, -10, 7, 7))
        painter.drawEllipse(QRectF(5, 5, 7, 7))
        painter.drawLine(-5, -1, 5, -6)
        painter.drawLine(-5, 2, 5, 8)
    elif glyph == "ip":
        painter.drawRoundedRect(QRectF(-12, -9, 24, 18), 5, 5)
        font = QFont("Segoe UI", 7)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(-11, -8, 22, 16), Qt.AlignmentFlag.AlignCenter, "IP")
        painter.drawLine(-7, 11, 7, 11)
    elif glyph == "building":
        painter.drawRect(QRectF(-9, -10, 18, 20))
        for x in (-5, 1, 5):
            painter.drawLine(x, -6, x, -3)
            painter.drawLine(x, 0, x, 3)
    elif glyph == "cloud":
        painter.drawEllipse(QRectF(-11, -2, 13, 10))
        painter.drawEllipse(QRectF(-2, -8, 13, 16))
        painter.drawEllipse(QRectF(3, -2, 11, 10))
        painter.drawLine(-8, 8, 10, 8)
    elif glyph == "key":
        painter.drawEllipse(QRectF(-10, -4, 8, 8))
        painter.drawLine(-2, 0, 10, 0)
        painter.drawLine(5, 0, 5, 5)
    elif glyph == "tag":
        path = QPainterPath()
        path.moveTo(-11, -7)
        path.lineTo(4, -7)
        path.lineTo(11, 0)
        path.lineTo(4, 7)
        path.lineTo(-11, 7)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawPoint(1, 0)
    elif glyph == "mail":
        painter.drawRect(QRectF(-11, -7, 22, 14))
        painter.drawLine(-11, -7, 0, 1)
        painter.drawLine(0, 1, 11, -7)
    elif glyph == "person":
        painter.drawEllipse(QRectF(-5, -11, 10, 10))
        painter.drawArc(QRectF(-10, -2, 20, 16), 0, 180 * 16)
    elif glyph == "shield":
        path = QPainterPath()
        path.moveTo(0, -12)
        path.lineTo(10, -8)
        path.lineTo(8, 6)
        path.lineTo(0, 12)
        path.lineTo(-8, 6)
        path.lineTo(-10, -8)
        path.closeSubpath()
        painter.drawPath(path)
    elif glyph == "link":
        painter.drawArc(QRectF(-12, -7, 14, 14), 45 * 16, 220 * 16)
        painter.drawArc(QRectF(-2, -7, 14, 14), 225 * 16, 220 * 16)
        painter.drawLine(-4, 4, 4, -4)
    elif glyph == "dns":
        painter.drawEllipse(QRectF(-11, -8, 7, 7))
        painter.drawEllipse(QRectF(4, -8, 7, 7))
        painter.drawEllipse(QRectF(-4, 5, 8, 8))
        painter.drawLine(-5, -2, -1, 6)
        painter.drawLine(5, -2, 1, 6)
        painter.drawLine(-4, -5, 4, -5)
    elif glyph == "service":
        painter.drawRoundedRect(QRectF(-11, -9, 22, 18), 3, 3)
        painter.drawLine(-7, -4, 5, -4)
        painter.drawLine(-7, 1, 5, 1)
        painter.drawPoint(8, -4)
        painter.drawPoint(8, 1)
    elif glyph == "box":
        path = QPainterPath()
        path.moveTo(0, -11)
        path.lineTo(10, -5)
        path.lineTo(10, 6)
        path.lineTo(0, 12)
        path.lineTo(-10, 6)
        path.lineTo(-10, -5)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(-10, -5, 0, 1)
        painter.drawLine(10, -5, 0, 1)
        painter.drawLine(0, 1, 0, 12)
    elif glyph == "certificate":
        painter.drawRoundedRect(QRectF(-10, -11, 20, 16), 2, 2)
        painter.drawLine(-6, -6, 6, -6)
        painter.drawLine(-6, -2, 3, -2)
        painter.drawEllipse(QRectF(-4, 3, 8, 8))
        painter.drawLine(-2, 10, -4, 13)
        painter.drawLine(2, 10, 4, 13)
    elif glyph == "monitor":
        painter.drawRoundedRect(QRectF(-12, -9, 24, 16), 3, 3)
        painter.drawLine(-5, 11, 5, 11)
        painter.drawLine(0, 7, 0, 11)
        painter.drawLine(-8, 2, -4, -2)
        painter.drawLine(-4, -2, 0, 1)
        painter.drawLine(0, 1, 7, -5)
    elif glyph == "broker":
        painter.drawRoundedRect(QRectF(-11, -10, 8, 8), 2, 2)
        painter.drawRoundedRect(QRectF(3, -10, 8, 8), 2, 2)
        painter.drawRoundedRect(QRectF(-4, 4, 8, 8), 2, 2)
        painter.drawLine(-3, -6, 3, -6)
        painter.drawLine(-7, -2, -2, 5)
        painter.drawLine(7, -2, 2, 5)
    elif glyph == "terminal":
        painter.drawRoundedRect(QRectF(-12, -9, 24, 18), 3, 3)
        painter.drawLine(-7, -4, -2, 0)
        painter.drawLine(-2, 0, -7, 4)
        painter.drawLine(1, 4, 7, 4)
    elif glyph == "folder":
        path = QPainterPath()
        path.moveTo(-12, -7)
        path.lineTo(-3, -7)
        path.lineTo(0, -3)
        path.lineTo(12, -3)
        path.lineTo(10, 9)
        path.lineTo(-12, 9)
        path.closeSubpath()
        painter.drawPath(path)
    else:
        painter.drawEllipse(QPointF(0, 0), 3, 3)
