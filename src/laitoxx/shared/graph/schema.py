"""Graph type, shape, and style schema constants."""

from __future__ import annotations

NODE_TYPE_DEFAULTS: dict[str, dict] = {
    "Person": {
        "shape": "round",
        "style": "fill:#FFD700,stroke:#8B4513,stroke-width:2px,color:#000",
    },
    "Email": {
        "shape": "rect",
        "style": "fill:#ADD8E6,stroke:#1E90FF,stroke-width:2px,color:#000",
    },
    "Phone": {
        "shape": "rect",
        "style": "fill:#98FB98,stroke:#228B22,stroke-width:2px,color:#000",
    },
    "Website": {
        "shape": "rect",
        "style": "fill:#DDA0DD,stroke:#8B008B,stroke-width:2px,color:#000",
    },
    "Company": {
        "shape": "diamond",
        "style": "fill:#90EE90,stroke:#2E8B57,stroke-width:2px,color:#000",
    },
    "IP": {
        "shape": "rect",
        "style": "fill:#F08080,stroke:#8B0000,stroke-width:2px,color:#000",
    },
    "Address": {
        "shape": "rect",
        "style": "fill:#FFDAB9,stroke:#D2691E,stroke-width:2px,color:#000",
    },
    "Document": {
        "shape": "rect",
        "style": "fill:#E6E6FA,stroke:#483D8B,stroke-width:2px,color:#000",
    },
    "Custom": {
        "shape": "rect",
        "style": "fill:#CCCCCC,stroke:#555555,stroke-width:1px,color:#000",
    },
    "Vulnerability": {
        "shape": "hexagon",
        "style": "fill:#F94144,stroke:#7F1D1D,stroke-width:3px,color:#FFF",
    },
    "Domain": {
        "shape": "round",
        "style": "fill:#A78BFA,stroke:#6D28D9,stroke-width:2px,color:#000",
    },
    "URL": {
        "shape": "rect",
        "style": "fill:#67E8F9,stroke:#0891B2,stroke-width:2px,color:#000",
    },
    "ASN": {
        "shape": "hexagon",
        "style": "fill:#FBBF24,stroke:#B45309,stroke-width:2px,color:#000",
    },
    "Network": {
        "shape": "hexagon",
        "style": "fill:#FB923C,stroke:#C2410C,stroke-width:2px,color:#000",
    },
    "DNS": {
        "shape": "circle",
        "style": "fill:#2DD4BF,stroke:#0F766E,stroke-width:2px,color:#000",
    },
    "Service": {
        "shape": "rect",
        "style": "fill:#60A5FA,stroke:#1D4ED8,stroke-width:2px,color:#000",
    },
    "Database": {
        "shape": "round",
        "style": "fill:#38BDF8,stroke:#0369A1,stroke-width:2px,color:#000",
    },
    "AdminPanel": {
        "shape": "diamond",
        "style": "fill:#FB7185,stroke:#BE123C,stroke-width:2px,color:#000",
    },
    "RemoteAccess": {
        "shape": "rect",
        "style": "fill:#F59E0B,stroke:#B45309,stroke-width:2px,color:#000",
    },
    "Software": {
        "shape": "rect",
        "style": "fill:#818CF8,stroke:#4338CA,stroke-width:2px,color:#000",
    },
    "Certificate": {
        "shape": "flag",
        "style": "fill:#34D399,stroke:#047857,stroke-width:2px,color:#000",
    },
    "Organization": {
        "shape": "rect",
        "style": "fill:#A3E635,stroke:#4D7C0F,stroke-width:2px,color:#000",
    },
    "Cloud": {
        "shape": "round",
        "style": "fill:#93C5FD,stroke:#2563EB,stroke-width:2px,color:#000",
    },
    "ThreatIndicator": {
        "shape": "circle",
        "style": "fill:#FCA5A5,stroke:#B91C1C,stroke-width:2px,color:#000",
    },
    "TONWallet": {
        "shape": "hexagon",
        "style": "fill:#2AABEE,stroke:#075985,stroke-width:2px,color:#FFF",
    },
    "TONNFT": {
        "shape": "round",
        "style": "fill:#818CF8,stroke:#4338CA,stroke-width:2px,color:#FFF",
    },
    "TONCollection": {
        "shape": "hexagon",
        "style": "fill:#A78BFA,stroke:#6D28D9,stroke-width:2px,color:#FFF",
    },
    "TelegramGift": {
        "shape": "diamond",
        "style": "fill:#F472B6,stroke:#9D174D,stroke-width:2px,color:#FFF",
    },
    "TelegramProfile": {
        "shape": "circle",
        "style": "fill:#38BDF8,stroke:#0369A1,stroke-width:2px,color:#FFF",
    },
    "BlockchainEvent": {
        "shape": "rect",
        "style": "fill:#FBBF24,stroke:#B45309,stroke-width:2px,color:#111827",
    },
    "Jetton": {
        "shape": "round",
        "style": "fill:#34D399,stroke:#047857,stroke-width:2px,color:#052E2B",
    },
    # Username OSINT node types
    "Username": {
        "shape": "round",
        "style": "fill:#FF6B6B,stroke:#C0392B,stroke-width:3px,color:#000",
    },
    "SocialAccount": {
        "shape": "rect",
        "style": "fill:#74B9FF,stroke:#0984E3,stroke-width:2px,color:#000",
    },
    "AltAccount": {
        "shape": "round",
        "style": "fill:#FDCB6E,stroke:#F39C12,stroke-width:2px,color:#000",
    },
    "Category": {
        "shape": "hexagon",
        "style": "fill:#A29BFE,stroke:#6C5CE7,stroke-width:2px,color:#000",
    },
}

NODE_TYPES = list(NODE_TYPE_DEFAULTS.keys())

NODE_SHAPES: dict[str, tuple[str, str, str]] = {
    "Прямоугольник": ("rect", "[", "]"),
    "Скруглённый": ("round", "(", ")"),
    "Круг": ("circle", "((", "))"),
    "Ромб": ("diamond", "{", "}"),
    "Шестиугольник": ("hexagon", "{{", "}}"),
    "Флаг": ("flag", ">", "]"),
    "Трапеция": ("trapez", "[/", "/]"),
}

SHAPE_ID_TO_TOKENS: dict[str, tuple[str, str]] = {v[0]: (v[1], v[2]) for v in NODE_SHAPES.values()}

EDGE_TYPES = [
    "Connected",
    "WorksFor",
    "Owns",
    "RelatedTo",
    "Communicates",
    "LocatedAt",
    "MemberOf",
    "Custom",
    # Username OSINT edge types
    "RegisteredOn",
    "SamePersonAs",
    "AltAccountOf",
    "BelongsToCategory",
]

EDGE_LINE_TYPES: dict[str, str] = {
    "Arrow -->": "-->",
    "Thick Arrow ==>": "==>",
    "Dotted -..->": "-.->",
    "Open ---": "---",
    "Open Dotted -...-": "-...-",
    "Double Arrow <-->": "<-->",
}
