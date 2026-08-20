# ruff: noqa: F405
from .advanced_web_scanner_support import *  # noqa: F403


class _GraphView(QGraphicsView):
    entity_selected = pyqtSignal(object)

    def __init__(self, parent=None, theme_data=None):
        super().__init__(parent)
        self._theme = theme_data or {}
        self.setRenderHints(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.set_theme(self._theme)

    def set_theme(self, theme_data):
        self._theme = theme_data or {}
        canvas = self._theme.get("graph_canvas_bg_color", self._theme.get("text_area_bg_color", "#0e1118"))
        border = self._theme.get("text_area_border_color", self._theme.get("border_color", "#343a40"))
        self.setStyleSheet(f"background: {canvas}; border: 1px solid {border}; border-radius: 8px;")

    def fit_graph(self):
        if self.scene() and self.scene().items():
            self.fitInView(
                self.scene().itemsBoundingRect().adjusted(-50, -50, 50, 50), Qt.AspectRatioMode.KeepAspectRatio
            )
            if self.transform().m11() < 0.42:
                self.resetTransform()
                self.scale(0.62, 0.62)
                self.centerOn(getattr(self, "_root_scene_pos", QPointF()))

    def zoom_in(self):
        self.scale(1.2, 1.2)

    def zoom_out(self):
        self.scale(1 / 1.2, 1 / 1.2)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    @staticmethod
    def _display_data(report, show_all_services: bool):
        if show_all_services:
            return list(report.entities), list(report.relations)
        entities = {entity.id: entity for entity in report.entities}
        parents = {}
        for relation in report.relations:
            if relation.relation == "exposes" and entities.get(relation.target, Entity("", "")).kind == "service":
                parents[relation.target] = relation.source
        groups = {}
        for service_id, parent_id in parents.items():
            service = entities[service_id]
            # Keep investigation-worthy interfaces visible as first-class
            # nodes. Only generic/repetitive ports are collapsed.
            if service.metadata.get("category") not in {
                "database",
                "admin_panel",
                "remote_access",
                "devops",
                "monitoring",
                "message_broker",
            }:
                groups.setdefault(parent_id, []).append(service)
        collapsed = {parent: items for parent, items in groups.items() if len(items) > 4}
        if not collapsed:
            return list(report.entities), list(report.relations)

        service_map = {}
        display_entities = [
            entity for entity in report.entities if not any(entity in items for items in collapsed.values())
        ]
        display_relations = []
        for parent, services in collapsed.items():
            parent_value = parent.split(":", 1)[1]
            ports = sorted({item.metadata.get("port") for item in services if item.metadata.get("port") is not None})
            group = Entity(
                "service_group",
                f"{parent_value} · {len(services)} services",
                metadata={
                    "count": len(services),
                    "ports": ports,
                    "services": [item.value for item in services],
                    "explanation": "Repeated service nodes are grouped for readability. Enable expanded services to inspect each port as a node.",
                },
            )
            display_entities.append(group)
            service_map.update({item.id: group.id for item in services})
            display_relations.append(
                Relation(parent, group.id, "exposes_services", "Graph aggregation", "high", True, f"Ports: {ports}")
            )
        seen = set()
        for relation in report.relations:
            if relation.relation == "exposes" and relation.target in service_map:
                continue
            source = service_map.get(relation.source, relation.source)
            target = service_map.get(relation.target, relation.target)
            key = (source, target, relation.relation, relation.source_name)
            if source == target or key in seen:
                continue
            seen.add(key)
            display_relations.append(
                Relation(
                    source,
                    target,
                    relation.relation,
                    relation.source_name,
                    relation.confidence,
                    relation.current,
                    relation.evidence,
                )
            )
        return display_entities, display_relations

    @staticmethod
    def _radial_layout(entity_ids, adjacency, root_id):
        """Place the investigation target at the origin and preserve branch locality."""
        if root_id not in entity_ids:
            root_id = next(iter(entity_ids), "")
        if not root_id:
            return {}, {}, ""
        parents, depths, children = {root_id: None}, {root_id: 0}, {root_id: []}
        queue = [root_id]
        while queue:
            current = queue.pop(0)
            for peer in sorted(adjacency.get(current, ())):
                if peer not in parents:
                    parents[peer] = current
                    depths[peer] = depths[current] + 1
                    children.setdefault(current, []).append(peer)
                    children.setdefault(peer, [])
                    queue.append(peer)

        def leaf_weight(node):
            nested = children.get(node, [])
            return sum(leaf_weight(child) for child in nested) or 1

        positions = {root_id: (0.0, 0.0)}

        def assign(node, start, end):
            nested = children.get(node, [])
            total = sum(leaf_weight(child) for child in nested) or 1
            cursor = start
            for child in nested:
                span = (end - start) * leaf_weight(child) / total
                angle = cursor + span / 2
                radius = 270.0 * depths[child]
                positions[child] = (math.cos(angle) * radius, math.sin(angle) * radius)
                assign(child, cursor, cursor + span)
                cursor += span

        assign(root_id, -math.pi, math.pi)
        disconnected = [item for item in entity_ids if item not in positions]
        for index, entity_id in enumerate(disconnected):
            angle = (2 * math.pi * index / max(1, len(disconnected))) - math.pi / 2
            positions[entity_id] = (math.cos(angle) * 270.0, math.sin(angle) * 270.0)
            depths[entity_id] = 1
        return positions, depths, root_id

    def show_report(self, report, show_all_services=False):
        scene = QGraphicsScene(self)
        display_entities, display_relations = self._display_data(report, show_all_services)
        unique = {entity.id: entity for entity in display_entities}
        selected_ids = list(unique)[:140]
        selected_ids.extend(entity.id for entity in unique.values() if entity.kind == "cve")
        entities = [unique[entity_id] for entity_id in dict.fromkeys(selected_ids)]
        entity_ids = {entity.id for entity in entities}
        root_id = f"{report.target.kind}:{report.target.value.casefold()}"

        adjacency = {entity.id: set() for entity in entities}
        for relation in display_relations:
            if relation.source in adjacency and relation.target in adjacency:
                adjacency[relation.source].add(relation.target)
                adjacency[relation.target].add(relation.source)
        positions, depths, root_id = self._radial_layout(entity_ids, adjacency, root_id)
        self._root_scene_pos = QPointF(*positions.get(root_id, (0.0, 0.0)))

        for relation in display_relations[:250]:
            if relation.source not in entity_ids or relation.target not in entity_ids:
                continue
            x1, y1 = positions[relation.source]
            x2, y2 = positions[relation.target]
            source_width = 240 if unique[relation.source].kind == "cve" else 200
            target_width = 240 if unique[relation.target].kind == "cve" else 200
            dx, dy = x2 - x1, y2 - y1
            distance = max(1.0, math.hypot(dx, dy))
            unit_x, unit_y = dx / distance, dy / distance
            start = QPointF(x1 + unit_x * source_width / 2, y1 + unit_y * 26)
            end = QPointF(x2 - unit_x * target_width / 2, y2 - unit_y * 26)
            path = QPainterPath(start)
            middle_x, middle_y = (start.x() + end.x()) / 2, (start.y() + end.y()) / 2
            bend = min(34.0, distance * 0.12)
            path.quadTo(QPointF(middle_x - unit_y * bend, middle_y + unit_x * bend), end)
            color = self._theme.get(
                f"graph_edge_{relation.confidence}_color",
                "#3ddc97"
                if relation.confidence == "high"
                else "#e9c46a"
                if relation.confidence == "medium"
                else "#6c757d",
            )
            edge = QGraphicsPathItem(path)
            pen = QPen(QColor(color), 2.2 if relation.current else 1.3)
            if relation.current is False:
                pen.setStyle(Qt.PenStyle.DashLine)
            edge.setPen(pen)
            edge.setZValue(-2)
            edge.setToolTip(f"{relation.relation}\n{relation.source_name}\n{relation.evidence}")
            scene.addItem(edge)
            if unique[relation.target].kind == "cve":
                relation_label = QGraphicsSimpleTextItem(relation.relation.replace("_", " "))
                relation_label.setBrush(QBrush(QColor(self._theme.get("text_secondary_color", "#adb5bd"))))
                relation_label.setPos(middle_x - relation_label.boundingRect().width() / 2, middle_y - 18)
                scene.addItem(relation_label)

        for entity in entities:
            x, y = positions[entity.id]
            width, height = (240, 88) if entity.kind == "cve" else (200, 66)
            color = self._theme.get(f"graph_node_{entity.kind}_color", ENTITY_COLORS.get(entity.kind, "#9775fa"))
            node = QGraphicsRectItem(x - width / 2, y - height / 2, width, height)
            node.setBrush(QBrush(QColor(color)))
            node.setPen(
                QPen(QColor(self._theme.get("graph_node_border_color", "#ffffff")), 2 if entity.id == root_id else 1)
            )
            node.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
            node.setData(0, entity)
            node.setToolTip(
                f"{entity.kind}: {entity.value}\n{json.dumps(entity.metadata, ensure_ascii=False, indent=2)}"
            )
            scene.addItem(node)
            text_color = QColor(self._theme.get("graph_node_text_color", "#ffffff"))
            kind = entity.kind.upper()
            if entity.metadata.get("pivot_suppressed"):
                kind += " · SHARED EDGE"
            kind_label = QGraphicsSimpleTextItem(kind, node)
            kind_label.setBrush(QBrush(text_color))
            kind_label.setPos(x - width / 2 + 9, y - height / 2 + 5)
            label = QGraphicsSimpleTextItem(entity.value[:38], node)
            label.setBrush(QBrush(text_color))
            label.setPos(x - width / 2 + 9, y - 7)
            if entity.kind == "cve":
                detail = f"CVSS {entity.metadata.get('cvss', '-')} · {str(entity.metadata.get('severity', 'unrated')).upper()}"
                if entity.metadata.get("known_exploited"):
                    detail += " · KEV"
                subtitle = QGraphicsSimpleTextItem(detail, node)
                subtitle.setBrush(QBrush(text_color))
                subtitle.setPos(x - width / 2 + 9, y + 17)
            elif entity.kind == "service":
                detail = entity.metadata.get("category_label", "Network service")
                if entity.metadata.get("product"):
                    detail += f" · {entity.metadata['product']}"
                subtitle = QGraphicsSimpleTextItem(detail[:42], node)
                subtitle.setBrush(QBrush(text_color))
                subtitle.setPos(x - width / 2 + 9, y + 17)
        scene.selectionChanged.connect(self._emit_selection)
        self.setScene(scene)
        self.fit_graph()

    def _emit_selection(self):
        selected = self.scene().selectedItems() if self.scene() else []
        if selected and selected[0].data(0):
            self.entity_selected.emit(selected[0].data(0))
