"""Render native product splash artwork using the bundled Qt and existing logo."""

import sys
from pathlib import Path

from qgis.PyQt.QtCore import QRectF
from qgis.PyQt.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen

app = QGuiApplication([])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
image = QImage(1040, 520, QImage.Format.Format_ARGB32)
image.fill(QColor("#102337"))
p = QPainter(image)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setPen(QPen(QColor("#1d4354"), 1))
for x in range(0, 1040, 52):
    p.drawLine(x, 0, x, 520)
for y in range(0, 520, 52):
    p.drawLine(0, y, 1040, y)
p.setPen(QPen(QColor("#5ed9cc"), 3))
p.drawLine(60, 330, 980, 330)
logo = QImage(sys.argv[1])
assert not logo.isNull()
p.drawImage(QRectF(65, 58, 118, 118), logo)


def text(x, y, size, color, value, bold=False):
    font = QFont("Helvetica", size)
    font.setBold(bold)
    p.setFont(font)
    p.setPen(QColor(color))
    p.drawText(x, y, value)


text(210, 137, 52, "#ffffff", "FinalGIS", True)
text(64, 239, 24, "#ffffff", "Geographic Intelligence & World Creation")
text(64, 286, 17, "#a3e2de", "A FINALVERSE PRODUCT")
text(64, 391, 16, "#d7e7ef", "Based on QGIS · Open-source GIS foundation")
text(
    64,
    429,
    14,
    "#abc2d1",
    "Independent derivative · QGIS contributors acknowledged · GPL-2.0-or-later",
)
p.end()
assert image.save(str(out / "splash.png"))
