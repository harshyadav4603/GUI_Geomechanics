"""
Data loading utilities – handles CSV and XLSX file imports.
"""

import pandas as pd
from tkinter import filedialog, messagebox
from pathlib import Path


class DataManager:
    """Manages loaded datasets for the application."""

    def __init__(self):
        self.dataframe: pd.DataFrame | None = None
        self.filepath: str | None = None
        self._callbacks: list = []

    # ── public API ────────────────────────────────────────────────

    def subscribe(self, callback):
        """Register a callback that fires when data changes."""
        self._callbacks.append(callback)

    def _notify(self):
        for cb in self._callbacks:
            cb(self.dataframe)

    def load_file(self, path: str | None = None) -> bool:
        """
        Open a file dialog (or use *path*) and load CSV / XLSX data.
        Returns True on success.
        """
        if path is None:
            path = filedialog.askopenfilename(
                title="Load Well / Geomechanics Data",
                filetypes=[
                    ("All supported", "*.csv *.xlsx *.xls"),
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx *.xls"),
                ],
            )
        if not path:
            return False

        try:
            ext = Path(path).suffix.lower()
            if ext == ".csv":
                df = pd.read_csv(path)
            elif ext in (".xlsx", ".xls"):
                df = pd.read_excel(path, engine="openpyxl")
            else:
                messagebox.showerror("Unsupported Format",
                                     f"Cannot read '{ext}' files.\nUse CSV or XLSX.")
                return False

            if df.empty:
                messagebox.showwarning("Empty File", "The selected file contains no data.")
                return False

            self.dataframe = df
            self.filepath = path
            self._notify()
            return True

        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))
            return False

    def clear(self):
        self.dataframe = None
        self.filepath = None
        self._notify()

    @property
    def is_loaded(self) -> bool:
        return self.dataframe is not None

    @property
    def columns(self) -> list[str]:
        if self.dataframe is not None:
            return list(self.dataframe.columns)
        return []

    @property
    def shape_str(self) -> str:
        if self.dataframe is not None:
            r, c = self.dataframe.shape
            return f"{r:,} rows  ×  {c} columns"
        return "No data loaded"
