"""Excel report generation for fulfillment exceptions.

This module writes a minimal XLSX file with only the Python standard library so
that the MVP remains runnable in restricted environments before dependencies are
approved internally.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from .models import ExceptionRecord

HEADERS = [
    "异常类型",
    "风险等级",
    "订单编号",
    "归属客户",
    "客户经理",
    "物流单号",
    "物流商",
    "物流模板",
    "承诺时效(天)",
    "已运输天数",
    "未更新天数",
    "最近轨迹时间",
    "最新轨迹内容",
    "目的国家",
    "建议动作",
]


def generate_excel_report(records: list[ExceptionRecord], output_dir: Path, generated_at: datetime | None = None) -> Path:
    """Generate an Excel workbook split by account manager and customer."""

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (generated_at or datetime.now()).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"fulfillment_exceptions_{timestamp}.xlsx"

    sheets: list[tuple[str, list[ExceptionRecord]]] = [("异常汇总", records)]
    by_manager: dict[str, list[ExceptionRecord]] = defaultdict(list)
    by_customer: dict[str, list[ExceptionRecord]] = defaultdict(list)
    for record in records:
        by_manager[record.account_manager].append(record)
        by_customer[record.customer_name].append(record)

    sheets.extend((_safe_sheet_name(f"经理-{manager}"), manager_records) for manager, manager_records in sorted(by_manager.items()))
    sheets.extend((_safe_sheet_name(f"客户-{customer}"), customer_records) for customer, customer_records in sorted(by_customer.items()))

    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, (_, sheet_records) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(sheet_records))
    return path


def _sheet_xml(records: list[ExceptionRecord]) -> str:
    rows = [HEADERS, *[record.to_excel_row() for record in records]]
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_column_letter(column_index)}{row_index}"
            style = ' s="1"' if row_index == 1 else ""
            cells.append(f'<c r="{cell_ref}" t="inlineStr"{style}><is><t>{escape(str(value or ""))}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetData>{''.join(row_xml)}</sheetData>
  <autoFilter ref="A1:O{max(1, len(rows))}"/>
</worksheet>'''


def _workbook_xml(sheets: list[tuple[str, list[ExceptionRecord]]]) -> str:
    sheet_entries = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _) in enumerate(sheets, start=1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{sheet_entries}</sheets></workbook>'''


def _workbook_rels(sheet_count: int) -> str:
    rels = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    rels += f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>'''


def _content_types(sheet_count: int) -> str:
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>{overrides}</Types>'''


def _root_rels() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''


def _styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font/><font><b/><color rgb="FFFFFFFF"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs></styleSheet>'''


def _safe_sheet_name(value: str) -> str:
    for char in "[]:*?/\\":
        value = value.replace(char, "-")
    return value[:31] or "未命名"


def _column_letter(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result
