# ruff: noqa: F405
from .theme_widget_context import *  # noqa: F403


class _HueSatWheel(QWidget):
    """Circular hue wheel + inner SV square."""

    color_changed = pyqtSignal(QColor)

    _RING_W = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self._hue = 0
        self._sat = 1.0
        self._val = 1.0
        self._alpha = 1.0
        self._dragging_ring = False
        self._dragging_sq = False
        self._cache: QPixmap | None = None

    # ── public API ──────────────────────────────────────────────────────────

    def set_color(self, color: QColor):
        h, s, v, a = (
            color.hsvHueF(),
            color.saturationF(),
            color.valueF(),
            color.alphaF(),
        )
        if h < 0:
            h = 0.0
        self._hue, self._sat, self._val, self._alpha = h, s, v, a
        self._cache = None
        self.update()

    def color(self) -> QColor:
        c = QColor.fromHsvF(self._hue, self._sat, self._val)
        c.setAlphaF(self._alpha)
        return c

    def set_alpha(self, alpha: float):
        self._alpha = max(0.0, min(1.0, alpha))
        self.update()
        self.color_changed.emit(self.color())

    # ── paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        r_outer = min(cx, cy) - 2
        r_inner = r_outer - self._RING_W

        # ── hue ring ─────────────────────────────────────────────────────
        steps = 360
        for i in range(steps):
            angle_start = i - 1
            angle_span = 2
            hue_color = QColor.fromHsvF(i / steps, 1.0, 1.0)
            pen = QPen(hue_color, self._RING_W)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawArc(
                QRectF(
                    cx - r_outer + self._RING_W / 2,
                    cy - r_outer + self._RING_W / 2,
                    (r_outer - self._RING_W / 2) * 2,
                    (r_outer - self._RING_W / 2) * 2,
                ),
                int(angle_start * 16),
                int(angle_span * 16),
            )

        # ── SV square inside ring ─────────────────────────────────────────
        sq = r_inner * math.sqrt(2) - 4
        sq_x, sq_y = cx - sq / 2, cy - sq / 2

        img_size = int(sq)
        if img_size > 0:
            px = QPixmap(img_size, img_size)
            pp = QPainter(px)
            pp.setRenderHint(QPainter.RenderHint.Antialiasing)
            for xi in range(img_size):
                sat = xi / (img_size - 1) if img_size > 1 else 1.0
                grad = QLinearGradient(0, 0, 0, img_size)
                grad.setColorAt(0, QColor.fromHsvF(self._hue, sat, 1.0))
                grad.setColorAt(1, QColor.fromHsvF(self._hue, sat, 0.0))
                pen = QPen(QBrush(grad), 1)
                pp.setPen(pen)
                pp.drawLine(xi, 0, xi, img_size)
            pp.end()
            p.drawPixmap(int(sq_x), int(sq_y), px)

            # SV crosshair
            cx_sq = sq_x + self._sat * sq
            cy_sq = sq_y + (1 - self._val) * sq
            p.setPen(QPen(QColor("white"), 2))
            p.drawEllipse(QPointF(cx_sq, cy_sq), 5, 5)
            p.setPen(QPen(QColor("black"), 1))
            p.drawEllipse(QPointF(cx_sq, cy_sq), 5, 5)

        # ── hue indicator on ring ─────────────────────────────────────────
        angle_rad = self._hue * 2 * math.pi
        mid_r = r_outer - self._RING_W / 2
        ix = cx + mid_r * math.cos(angle_rad - math.pi / 2)
        iy = cy + mid_r * math.sin(angle_rad - math.pi / 2)
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QBrush(QColor.fromHsvF(self._hue, 1.0, 1.0)))
        p.drawEllipse(QPointF(ix, iy), 7, 7)

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        self._handle_mouse(event.position(), press=True)

    def mouseMoveEvent(self, event):
        self._handle_mouse(event.position())

    def mouseReleaseEvent(self, _):
        self._dragging_ring = self._dragging_sq = False

    def _handle_mouse(self, pos: QPointF, press=False):
        cx, cy = self.width() / 2, self.height() / 2
        dx, dy = pos.x() - cx, pos.y() - cy
        dist = math.hypot(dx, dy)
        r_outer = min(cx, cy) - 2
        r_inner = r_outer - self._RING_W
        sq = r_inner * math.sqrt(2) - 4

        in_ring = r_inner <= dist <= r_outer
        in_sq = abs(dx) <= sq / 2 and abs(dy) <= sq / 2

        if press:
            self._dragging_ring = in_ring
            self._dragging_sq = in_sq and not in_ring

        if self._dragging_ring:
            self._hue = (math.atan2(dy, dx) / (2 * math.pi) + 0.25) % 1.0
            self.color_changed.emit(self.color())
            self.update()

        elif self._dragging_sq:
            self._sat = max(0.0, min(1.0, (dx + sq / 2) / sq))
            self._val = max(0.0, min(1.0, 1 - (dy + sq / 2) / sq))
            self.color_changed.emit(self.color())
            self.update()
