"""Pure exposure classification and CPE normalization rules."""

from __future__ import annotations

_SERVICE_CLASSES = {
    "database": {
        1433: "Microsoft SQL Server",
        1521: "Oracle Database",
        3306: "MySQL",
        5432: "PostgreSQL",
        5984: "CouchDB",
        6379: "Redis",
        7474: "Neo4j HTTP",
        7687: "Neo4j Bolt",
        8086: "InfluxDB",
        9042: "Cassandra",
        9200: "Elasticsearch",
        9300: "Elasticsearch transport",
        11211: "Memcached",
        27017: "MongoDB",
    },
    "admin_panel": {
        2082: "cPanel",
        2083: "cPanel TLS",
        2086: "WHM",
        2087: "WHM TLS",
        2095: "Webmail",
        2096: "Webmail TLS",
        5601: "Kibana",
        8088: "Splunk Web",
        8443: "Web admin panel",
        9000: "Management console",
        10000: "Webmin",
        15672: "RabbitMQ Management",
    },
    "remote_access": {22: "SSH", 23: "Telnet", 3389: "RDP", 5900: "VNC"},
    "devops": {
        2375: "Docker API",
        2376: "Docker API TLS",
        4646: "Nomad",
        6443: "Kubernetes API",
        8500: "Consul",
        10250: "Kubelet API",
    },
    "monitoring": {3000: "Grafana / web console", 9090: "Prometheus"},
    "message_broker": {4222: "NATS", 5672: "AMQP", 9092: "Apache Kafka"},
    "file_sharing": {21: "FTP", 139: "NetBIOS", 445: "SMB", 2049: "NFS"},
    "mail": {25: "SMTP", 110: "POP3", 143: "IMAP", 465: "SMTPS", 587: "SMTP submission", 993: "IMAPS", 995: "POP3S"},
    "web": {80: "HTTP", 443: "HTTPS", 8000: "HTTP alternate", 8080: "HTTP proxy", 8880: "HTTP alternate"},
}
_SERVICE_CLASS_LABELS = {
    "database": "Database",
    "admin_panel": "Administration panel",
    "remote_access": "Remote access",
    "devops": "DevOps / infrastructure",
    "monitoring": "Monitoring interface",
    "message_broker": "Message broker",
    "file_sharing": "File sharing",
    "mail": "Mail service",
    "web": "Web service",
    "other": "Network service",
}


def classify_service(port: int, product: str = "", module: str = "", title: str = "") -> dict[str, str]:
    """Return a stable, UI-friendly exposure classification for a service banner."""
    port = int(port)
    category, default_name = "other", f"TCP/{port}"
    for candidate, ports in _SERVICE_CLASSES.items():
        if port in ports:
            category, default_name = candidate, ports[port]
            break
    combined = " ".join((product, module, title)).casefold()
    if any(
        token in combined
        for token in (
            "phpmyadmin",
            "adminer",
            "pgadmin",
            "mongo express",
            "redis commander",
            "webmin",
            "cpanel",
            "plesk",
            "portainer",
            "jenkins",
            "rancher",
            "sonarqube",
            "opensearch dashboards",
            "rabbitmq management",
            "kubernetes dashboard",
            "admin panel",
            "management console",
        )
    ):
        category = "admin_panel"
    elif any(
        token in combined
        for token in (
            "mysql",
            "postgres",
            "mongodb",
            "mongo",
            "redis",
            "elastic",
            "opensearch",
            "mssql",
            "oracle database",
            "couchdb",
            "cassandra",
            "neo4j",
            "influxdb",
        )
    ):
        category = "database"
    elif any(token in combined for token in ("grafana", "prometheus", "zabbix", "nagios", "kibana")):
        category = "monitoring"
    elif any(token in combined for token in ("rabbitmq", "apache kafka", "activemq", "nats server")):
        category = "message_broker"
    attention = (
        "high"
        if category in {"database", "admin_panel", "remote_access", "devops"}
        else "medium"
        if category in {"file_sharing", "mail", "monitoring", "message_broker"}
        else "info"
    )
    name = product.strip() or default_name
    return {
        "category": category,
        "category_label": _SERVICE_CLASS_LABELS[category],
        "service_name": name,
        "attention": attention,
        "explanation": (
            f"Publicly observable {_SERVICE_CLASS_LABELS[category].lower()}: {name} on port {port}. "
            "The observation does not by itself prove anonymous access or a vulnerability."
        ),
    }


def cpe_metadata(value: str) -> dict[str, str]:
    """Extract the useful identity fields from CPE 2.2/2.3 without guessing."""
    raw = str(value).strip()
    parts = raw.split(":")
    if raw.startswith("cpe:2.3:") and len(parts) >= 6:
        part, vendor, product, version = parts[2:6]
    elif raw.startswith("cpe:/") and len(parts) >= 5:
        part, vendor, product, version = parts[1].removeprefix("/"), parts[2], parts[3], parts[4]
    else:
        return {"source": "Shodan InternetDB"}
    kind = {"a": "application", "o": "operating_system", "h": "hardware"}.get(part, part)
    return {
        "source": "Shodan InternetDB",
        "cpe_part": kind,
        "vendor": vendor.replace("\\_", " "),
        "product": product.replace("\\_", " "),
        "version": "" if version in {"*", "-"} else version.replace("\\_", " "),
    }
