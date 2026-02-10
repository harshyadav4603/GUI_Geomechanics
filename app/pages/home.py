"""
Home Page – data loading, preview table, and dataset summary.
"""

import customtkinter as ctk
from tkinter import ttk
import pandas as pd


class HomePage(ctk.CTkFrame):
    """Landing page with data upload and preview."""

    def __init__(self, master, data_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.dm = data_manager
        self.dm.subscribe(self._on_data_changed)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # table expands

        self._build_header()
        self._build_upload_area()
        self._build_table_area()
        self._build_status_bar()

    # ── UI sections ───────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=12)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="⛏  GEOMECHANICS  WORKBENCH",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#00d4ff",
        ).grid(row=0, column=0, padx=20, pady=15, columnspan=2, sticky="w")

        ctk.CTkLabel(
            hdr,
            text="Load your well data to begin analysis  •  Supported formats: CSV, XLSX",
            font=ctk.CTkFont(size=13),
            text_color="#888888",
        ).grid(row=1, column=0, padx=20, pady=(0, 12), columnspan=2, sticky="w")

    def _build_upload_area(self):
        frm = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=12, border_width=2,
                            border_color="#0f3460")
        frm.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        frm.grid_columnconfigure(1, weight=1)

        self.btn_load = ctk.CTkButton(
            frm, text="  📂  Load Data File", width=200, height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0f3460", hover_color="#1a5276",
            corner_radius=8,
            command=self._on_load_click,
        )
        self.btn_load.grid(row=0, column=0, padx=15, pady=15)

        self.lbl_file = ctk.CTkLabel(
            frm, text="No file loaded",
            font=ctk.CTkFont(size=13), text_color="#aaaaaa", anchor="w",
        )
        self.lbl_file.grid(row=0, column=1, padx=10, pady=15, sticky="w")

        self.btn_clear = ctk.CTkButton(
            frm, text="✕ Clear", width=80, height=34,
            fg_color="#c0392b", hover_color="#e74c3c",
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            command=self._on_clear_click,
        )
        self.btn_clear.grid(row=0, column=2, padx=15, pady=15)

    def _build_table_area(self):
        """Treeview wrapped in a themed frame for the data preview."""

        container = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=12)
        container.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container, text="  📊  Data Preview",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#feca57", anchor="w",
        ).grid(row=0, column=0, padx=15, pady=(12, 4), sticky="w")

        # --- Treeview style ---
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Geo.Treeview",
                         background="#0a0a1a",
                         foreground="#e0e0e0",
                         fieldbackground="#0a0a1a",
                         rowheight=26,
                         font=("Segoe UI", 10))
        style.configure("Geo.Treeview.Heading",
                         background="#0f3460",
                         foreground="#00d4ff",
                         font=("Segoe UI", 10, "bold"),
                         relief="flat")
        style.map("Geo.Treeview",
                   background=[("selected", "#1a5276")],
                   foreground=[("selected", "#ffffff")])

        # Treeview + scrollbars
        tree_frm = ctk.CTkFrame(container, fg_color="#0a0a1a", corner_radius=8)
        tree_frm.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        tree_frm.grid_rowconfigure(0, weight=1)
        tree_frm.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frm, style="Geo.Treeview", show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Placeholder message
        self.placeholder = ctk.CTkLabel(
            tree_frm,
            text="\n\n📁  Load a CSV or XLSX file to preview data here\n\n",
            font=ctk.CTkFont(size=14), text_color="#555555",
        )
        self.placeholder.grid(row=0, column=0, sticky="nsew")

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self, fg_color="#0f3460", corner_radius=8, height=36)
        bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 15))
        bar.grid_columnconfigure(1, weight=1)

        self.lbl_shape = ctk.CTkLabel(
            bar, text="Rows: –   Columns: –",
            font=ctk.CTkFont(size=12), text_color="#aaaaaa",
        )
        self.lbl_shape.grid(row=0, column=0, padx=15, pady=6)

        self.lbl_dtypes = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=12), text_color="#aaaaaa", anchor="e",
        )
        self.lbl_dtypes.grid(row=0, column=1, padx=15, pady=6, sticky="e")

    # ── Callbacks ─────────────────────────────────────────────────

    def _on_load_click(self):
        self.dm.load_file()

    def _on_clear_click(self):
        self.dm.clear()

    def _on_data_changed(self, df: pd.DataFrame | None):
        """Refresh all widgets when the data model changes."""
        self._populate_tree(df)
        if df is not None:
            fname = self.dm.filepath.split("/")[-1].split("\\")[-1]
            self.lbl_file.configure(text=f"📄  {fname}", text_color="#2ed573")
            r, c = df.shape
            self.lbl_shape.configure(text=f"Rows: {r:,}   |   Columns: {c}")
            # Summarise dtypes
            dt_counts = df.dtypes.value_counts()
            parts = [f"{v} {k}" for k, v in dt_counts.items()]
            self.lbl_dtypes.configure(text="Types: " + ",  ".join(parts))
        else:
            self.lbl_file.configure(text="No file loaded", text_color="#aaaaaa")
            self.lbl_shape.configure(text="Rows: –   Columns: –")
            self.lbl_dtypes.configure(text="")

    def _populate_tree(self, df: pd.DataFrame | None):
        """Fill the Treeview with the first 500 rows of the dataframe."""
        # Clear existing
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = []

        if df is None or df.empty:
            self.placeholder.lift()
            return

        self.placeholder.lower()
        cols = list(df.columns)
        self.tree["columns"] = cols

        for col in cols:
            self.tree.heading(col, text=col, anchor="w")
            max_len = max(len(str(col)), df[col].astype(str).str.len().median())
            width = min(200, max(80, int(max_len * 9)))
            self.tree.column(col, width=width, anchor="w", minwidth=60)

        for _, row in df.head(500).iterrows():
            vals = [str(v) for v in row]
            self.tree.insert("", "end", values=vals)
