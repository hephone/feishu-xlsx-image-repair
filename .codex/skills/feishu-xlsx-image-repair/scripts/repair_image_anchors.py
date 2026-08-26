#!/usr/bin/env python3
"""Restore exported XLSX pictures to their native aspect ratios for WPS."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
import posixpath
import sys
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image


EMU_PER_PIXEL = 9525
DRAWINGS = "xl/drawings/"
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def column_pixels(width: float) -> int:
    return int(width * 7 + 5)


class Grid:
    def __init__(self, sheet_xml: bytes):
        root = ET.fromstring(sheet_xml)
        fmt = root.find("x:sheetFormatPr", NS)
        self.default_col = float(fmt.get("defaultColWidth", "8.43"))
        self.default_row = float(fmt.get("defaultRowHeight", "15"))
        self.cols: dict[int, int] = {}
        for definition in root.findall("x:cols/x:col", NS):
            width = column_pixels(float(definition.get("width", self.default_col)))
            for number in range(int(definition.get("min")), int(definition.get("max")) + 1):
                self.cols[number - 1] = width
        self.rows: dict[int, int] = {}
        for row in root.findall("x:sheetData/x:row", NS):
            if row.get("ht") is not None:
                self.rows[int(row.get("r")) - 1] = round(float(row.get("ht")) * 96 / 72)

    def col_size(self, index: int) -> int:
        return self.cols.get(index, column_pixels(self.default_col))

    def row_size(self, index: int) -> int:
        return self.rows.get(index, round(self.default_row * 96 / 72))

    def marker_to_pixel(self, marker: ET.Element) -> tuple[float, float]:
        col = int(marker.findtext("xdr:col", namespaces=NS))
        row = int(marker.findtext("xdr:row", namespaces=NS))
        col_offset = int(marker.findtext("xdr:colOff", "0", NS)) / EMU_PER_PIXEL
        row_offset = int(marker.findtext("xdr:rowOff", "0", NS)) / EMU_PER_PIXEL
        return sum(self.col_size(i) for i in range(col)) + col_offset, sum(self.row_size(i) for i in range(row)) + row_offset

    def pixel_to_marker(self, x: float, y: float) -> tuple[int, int, int, int]:
        col = row = 0
        x_left = y_top = 0.0
        while x >= x_left + self.col_size(col):
            x_left += self.col_size(col)
            col += 1
        while y >= y_top + self.row_size(row):
            y_top += self.row_size(row)
            row += 1
        return col, round((x - x_left) * EMU_PER_PIXEL), row, round((y - y_top) * EMU_PER_PIXEL)


def set_marker(marker: ET.Element, values: tuple[int, int, int, int]) -> None:
    col, col_off, row, row_off = values
    marker.find("xdr:col", NS).text = str(col)
    marker.find("xdr:colOff", NS).text = str(max(0, col_off))
    marker.find("xdr:row", NS).text = str(row)
    marker.find("xdr:rowOff", NS).text = str(max(0, row_off))


def workbook_maps(source_zip: zipfile.ZipFile) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    sheet_for_drawing: dict[str, str] = {}
    for name in source_zip.namelist():
        if not name.startswith("xl/worksheets/_rels/") or not name.endswith(".rels"):
            continue
        sheet_name = "xl/worksheets/" + PurePosixPath(name).name.removesuffix(".rels")
        for rel in ET.fromstring(source_zip.read(name)):
            if rel.get("Type", "").endswith("/drawing"):
                sheet_for_drawing[posixpath.normpath(str(PurePosixPath("xl/worksheets") / rel.get("Target")))] = sheet_name
    images_for_drawing: dict[str, dict[str, str]] = {}
    for name in source_zip.namelist():
        if not name.startswith(DRAWINGS + "_rels/") or not name.endswith(".rels"):
            continue
        drawing_name = DRAWINGS + PurePosixPath(name).name.removesuffix(".rels")
        images_for_drawing[drawing_name] = {rel.get("Id"): posixpath.normpath(str(PurePosixPath(DRAWINGS) / rel.get("Target"))) for rel in ET.fromstring(source_zip.read(name))}
    return sheet_for_drawing, images_for_drawing


def repair_drawing(xml: bytes, grid: Grid, images: dict[str, str], source_zip: zipfile.ZipFile) -> tuple[bytes, int]:
    root = ET.fromstring(xml)
    repaired = 0
    for anchor in root.findall("xdr:twoCellAnchor", NS):
        blip = anchor.find("xdr:pic/xdr:blipFill/a:blip", NS)
        relation_id = blip.get(f"{{{NS['r']}}}embed") if blip is not None else None
        if relation_id not in images:
            continue
        with Image.open(BytesIO(source_zip.read(images[relation_id]))) as picture:
            image_width, image_height = picture.size
        start, end = anchor.find("xdr:from", NS), anchor.find("xdr:to", NS)
        x1, y1 = grid.marker_to_pixel(start)
        x2, y2 = grid.marker_to_pixel(end)
        box_width, box_height = x2 - x1, y2 - y1
        if box_width <= 0 or box_height <= 0:
            raise RuntimeError("Picture anchor has no usable size")
        scale = min(box_width / image_width, box_height / image_height)
        width, height = image_width * scale, image_height * scale
        x, y = x1 + (box_width - width) / 2, y1 + (box_height - height) / 2
        set_marker(start, grid.pixel_to_marker(x, y))
        set_marker(end, grid.pixel_to_marker(x + width, y + height))
        for locks in anchor.findall("xdr:pic/xdr:nvPicPr/xdr:cNvPicPr/a:picLocks", NS):
            locks.set("noChangeAspect", "true")
        repaired += 1
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), repaired


def main(source: str, destination: str) -> None:
    with zipfile.ZipFile(source) as source_zip:
        sheet_for_drawing, images_for_drawing = workbook_maps(source_zip)
        repaired = 0
        with zipfile.ZipFile(destination, "w") as destination_zip:
            for info in source_zip.infolist():
                data = source_zip.read(info.filename)
                if info.filename in sheet_for_drawing and info.filename in images_for_drawing:
                    data, count = repair_drawing(data, Grid(source_zip.read(sheet_for_drawing[info.filename])), images_for_drawing[info.filename], source_zip)
                    repaired += count
                destination_zip.writestr(info.filename, data, compress_type=info.compress_type)
    if not repaired:
        raise RuntimeError("No pictures were repaired")
    print(f"Restored native aspect ratios for {repaired} pictures.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: repair_image_anchors.py SOURCE.xlsx DESTINATION.xlsx")
    main(*sys.argv[1:])
