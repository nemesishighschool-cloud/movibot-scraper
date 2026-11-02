"""Exports CSV / XLSX de la base (métadonnées uniquement)."""

from __future__ import annotations

import csv
import os
import sqlite3

from .storage import COLONNES, stats


def _lignes(c: sqlite3.Connection):
    c.row_factory = sqlite3.Row
    return [dict(r) for r in c.execute(
        "SELECT " + ",".join(COLONNES) + " FROM web_media ORDER BY id")]


def exporter(chemin_db: str, dossier: str = "exports") -> dict:
    os.makedirs(dossier, exist_ok=True)
    c = sqlite3.connect(chemin_db)
    lignes = _lignes(c)
    s = stats(c)
    c.close()

    csv_path = os.path.join(dossier, "Media_web.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES)
        w.writeheader()
        w.writerows(lignes)

    xlsx_path = os.path.join(dossier, "MoviBot_Base_Web.xlsx")
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter
        wb = Workbook()
        ws = wb.active
        ws.title = "Media"
        ws.append(COLONNES)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E79")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(COLONNES))}{len(lignes)+1}"
        for r in lignes:
            ws.append([r[k] for k in COLONNES])
        for i, k in enumerate(COLONNES, 1):
            ws.column_dimensions[get_column_letter(i)].width = \
                {"title": 38, "page_url": 50, "canonical_path": 44, "synopsis": 55,
                 "poster_url": 45, "players": 45, "embed_url": 44,
                 "download_url": 44, "notes": 48}.get(k, 16)
        st = wb.create_sheet("Statistiques")
        st.append(["Indicateur", "Valeur"])
        for cell in st[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E79")
        for k, v in s.items():
            st.append([k, str(v)])
        st.column_dimensions["A"].width = 30
        st.column_dimensions["B"].width = 46
        wb.save(xlsx_path)
    except ImportError:
        xlsx_path = None

    return {"csv": csv_path, "xlsx": xlsx_path, "lignes": len(lignes), **s}
