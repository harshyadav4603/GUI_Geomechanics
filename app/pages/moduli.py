"""
MODULI Analysis Page
=====================
Compute & visualise dynamic and static elastic moduli from sonic logs.

Layout mirrors the Stress page:
  ┌──────────────┬──────────────────────────────────────────┐
  │  Controls    │  Plots  (matplotlib embedded)            │
  │  & Formulas  │                                          │
  │              ├──────────────────────────────────────────┤
  │              │  Results table (computed columns)         │
  └──────────────┴──────────────────────────────────────────┘
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from app.computations.moduli_calc import compute_all_moduli


# ── Accent colours ────────────────────────────────────────────────
CLR_ACCENT = "#feca57"
CLR_BG     = "#0d1117"
CLR_CARD   = "#16213e"
CLR_CARD2  = "#1a1a2e"
CLR_INPUT  = "#0f3460"
CLR_TEXT   = "#e0e0e0"
CLR_DIM    = "#888888"


class ModuliPage(ctk.CTkFrame):
    """Elastic moduli: column mapping → compute → plot + table."""

    def __init__(self, master, data_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.dm = data_manager
        self.dm.subscribe(self._on_data_changed)
        self.result_df: pd.DataFrame | None = None

        self.grid_columnconfigure(0, weight=0, minsize=340)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_controls_panel()
        self._build_output_panel()

        if self.dm.is_loaded:
            self._refresh_column_lists()

    # ══════════════════════════════════════════════════════════════
    #  LEFT PANEL — controls
    # ══════════════════════════════════════════════════════════════
    def _build_controls_panel(self):
        panel = ctk.CTkScrollableFrame(self, fg_color=CLR_CARD2, width=320,
                                        corner_radius=12)
        panel.grid(row=0, column=0, sticky="ns", padx=(15, 5), pady=15)
        panel.grid_columnconfigure(1, weight=1)
        self.ctrl = panel

        # Title
        ctk.CTkLabel(panel, text="📈  ELASTIC MODULI",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=CLR_ACCENT).grid(row=0, column=0, columnspan=2,
                                                  padx=12, pady=(12, 4), sticky="w")

        # Unit system
        self._section(panel, 1, "Unit System")
        self.unit_var = ctk.StringVar(value="SI  (m, kg/m³, km/s)")
        self.cmb_unit = ctk.CTkComboBox(
            panel, values=["SI  (m, kg/m³, km/s)",
                           "SI  (m, kg/m³, m/s)",
                           "FIELD  (ft, g/cc, ft/s)"],
            variable=self.unit_var, width=240, fg_color=CLR_INPUT,
            button_color=CLR_INPUT, border_color="#1a5276",
            dropdown_fg_color=CLR_INPUT, state="readonly")
        self.cmb_unit.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")

        # Column mapping (4 required columns)
        self._section(panel, 3, "Column Mapping")
        self.cmb_depth   = self._combo(panel, 4, "Depth")
        self.cmb_density = self._combo(panel, 5, "Density (ρ)")
        self.cmb_vp      = self._combo(panel, 6, "Vp  –  P-wave velocity")
        self.cmb_vs      = self._combo(panel, 7, "Vs  –  S-wave velocity")

        # Compute
        self.btn_compute = ctk.CTkButton(
            panel, text="⚡  COMPUTE  MODULI", height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#b8860b", hover_color="#daa520",
            corner_radius=8, command=self._on_compute)
        self.btn_compute.grid(row=8, column=0, columnspan=2,
                               padx=12, pady=(14, 8), sticky="ew")

        # Formulas card
        self._section(panel, 9, "Dynamic Moduli Formulas")
        formulas_dyn = (
            "① ν  = (Vp²−2Vs²) / 2(Vp²−Vs²)\n"
            "② E  = ρVs²(3Vp²−4Vs²) / (Vp²−Vs²)\n"
            "③ G  = ρ·Vs²\n"
            "④ K  = ρ·(Vp² − ⁴⁄₃Vs²)\n"
            "⑤ λ  = ρ·(Vp² − 2Vs²)\n"
            "⑥ M  = ρ·Vp²"
        )
        ctk.CTkLabel(panel, text=formulas_dyn,
                     font=ctk.CTkFont(size=11, family="Consolas"),
                     text_color="#48dbfb", justify="left",
                     wraplength=300).grid(row=10, column=0, columnspan=2,
                                           padx=12, pady=(0, 6), sticky="w")

        self._section(panel, 11, "Impedances & Compress.")
        formulas_imp = (
            "⑦ AI = ρ · Vp   (Acoustic Impedance)\n"
            "⑧ SI = ρ · Vs   (Shear Impedance)\n"
            "⑨ β  = 1 / K    (Compressibility)"
        )
        ctk.CTkLabel(panel, text=formulas_imp,
                     font=ctk.CTkFont(size=11, family="Consolas"),
                     text_color="#2ed573", justify="left",
                     wraplength=300).grid(row=12, column=0, columnspan=2,
                                           padx=12, pady=(0, 12), sticky="w")

        # Export
        self.btn_export = ctk.CTkButton(
            panel, text="💾  Export Results CSV", height=36,
            font=ctk.CTkFont(size=12), fg_color=CLR_INPUT,
            hover_color="#1a5276", corner_radius=6,
            command=self._on_export)
        self.btn_export.grid(row=13, column=0, columnspan=2,
                              padx=12, pady=(0, 14), sticky="ew")

    # ── widget helpers ────────────────────────────────────────────

    @staticmethod
    def _section(parent, row, text):
        sep = ctk.CTkFrame(parent, height=1, fg_color="#2c3e50")
        sep.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(10, 2))
        ctk.CTkLabel(sep, text=f"  {text}  ",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#feca57", fg_color=CLR_CARD2).place(x=12, y=-9)

    def _combo(self, parent, row, label) -> ctk.CTkComboBox:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=2, padx=12, pady=(4, 2), sticky="ew")
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=11),
                     text_color=CLR_DIM).pack(anchor="w")
        cmb = ctk.CTkComboBox(frame, values=["(load data first)"], width=240,
                               fg_color=CLR_INPUT, button_color=CLR_INPUT,
                               border_color="#1a5276",
                               dropdown_fg_color=CLR_INPUT, state="readonly")
        cmb.pack(anchor="w", pady=(2, 0))
        return cmb

    @staticmethod
    def _entry(parent, row, label, default) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=11),
                     text_color=CLR_DIM).grid(row=row, column=0, padx=12,
                                               pady=(4, 0), sticky="w")
        ent = ctk.CTkEntry(parent, width=120, fg_color=CLR_INPUT,
                            border_color="#1a5276", text_color=CLR_TEXT)
        ent.insert(0, default)
        ent.grid(row=row, column=1, padx=12, pady=(4, 2), sticky="e")
        return ent

    # ══════════════════════════════════════════════════════════════
    #  RIGHT PANEL — plots + table
    # ══════════════════════════════════════════════════════════════
    def _build_output_panel(self):
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 15), pady=15)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=3)
        right.grid_rowconfigure(1, weight=2)

        self._build_plot_area(right)
        self._build_result_table(right)

    def _build_plot_area(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=12)
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(card, text="  📈  Dynamic Moduli vs Depth",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#feca57").grid(row=0, column=0, padx=12,
                                                pady=(10, 0), sticky="w")

        self.fig = Figure(figsize=(10, 4.5), dpi=100, facecolor=CLR_BG)
        self.canvas = FigureCanvasTkAgg(self.fig, master=card)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        tb = ctk.CTkFrame(card, fg_color=CLR_BG, height=30)
        tb.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.toolbar = NavigationToolbar2Tk(self.canvas, tb)
        self.toolbar.update()
        self.toolbar.pack(side="left")

        self._draw_empty()

    def _draw_empty(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(CLR_BG)
        ax.text(0.5, 0.5, "Run computation to see moduli profiles",
                ha="center", va="center", fontsize=14, color="#555555",
                transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        self.canvas.draw()

    def _draw_plots(self, df: pd.DataFrame):
        self.fig.clear()
        self.fig.set_facecolor(CLR_BG)
        depth = df["Depth"].values

        specs = [
            {
                "title": "Poisson's Ratio",
                "curves": [
                    ("ν", "#48dbfb", "-"),
                ],
            },
            {
                "title": "E, G, K (GPa)",
                "curves": [
                    ("E (GPa)", "#ff6b6b", "-"),
                    ("G (GPa)", "#feca57", "-"),
                    ("K (GPa)", "#48dbfb", "-"),
                ],
            },
            {
                "title": "Impedances",
                "curves": [
                    ("Acoustic Impedance", "#ff9ff3", "-"),
                    ("Shear Impedance", "#00d2d3", "-"),
                ],
            },
            {
                "title": "λ, M & Vp/Vs",
                "curves": [
                    ("λ (GPa)", "#ff9ff3", "-"),
                    ("M (GPa)", "#00d2d3", "-"),
                    ("Vp/Vs", "#ff6b6b", "--"),
                ],
            },
        ]

        for idx, sp in enumerate(specs):
            ax = self.fig.add_subplot(1, 4, idx + 1)
            ax.set_facecolor("#0a0a1a")
            ax.set_title(sp["title"], fontsize=9, color=CLR_TEXT, pad=6)
            ax.tick_params(colors=CLR_DIM, labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#2c3e50")

            for col, color, ls in sp["curves"]:
                if col in df.columns:
                    ax.plot(df[col].values, depth, color=color,
                            linewidth=1.2, linestyle=ls, label=col)

            ax.invert_yaxis()
            ax.set_ylabel("Depth", fontsize=8, color=CLR_DIM)
            ax.legend(fontsize=6, loc="lower right",
                      facecolor="#1a1a2e", edgecolor="#2c3e50",
                      labelcolor=CLR_TEXT)
            ax.grid(True, color="#1a2a3a", linewidth=0.5, alpha=0.5)

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    # ── results table ─────────────────────────────────────────────

    def _build_result_table(self, parent):
        card = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=12)
        card.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="  📊  Computed Results",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#feca57").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.lbl_count = ctk.CTkLabel(hdr, text="", font=ctk.CTkFont(size=11),
                                       text_color=CLR_DIM)
        self.lbl_count.grid(row=0, column=1, padx=12, pady=8, sticky="e")

        style = ttk.Style()
        style.configure("Moduli.Treeview",
                         background="#0a0a1a", foreground="#e0e0e0",
                         fieldbackground="#0a0a1a", rowheight=24,
                         font=("Segoe UI", 9))
        style.configure("Moduli.Treeview.Heading",
                         background="#0f3460", foreground="#feca57",
                         font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Moduli.Treeview",
                   background=[("selected", "#1a5276")],
                   foreground=[("selected", "#ffffff")])

        tf = ctk.CTkFrame(card, fg_color="#0a0a1a", corner_radius=8)
        tf.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        tf.grid_columnconfigure(0, weight=1)
        tf.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(tf, style="Moduli.Treeview",
                                  show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

    # ══════════════════════════════════════════════════════════════
    #  CALLBACKS
    # ══════════════════════════════════════════════════════════════

    def _on_data_changed(self, df):
        self._refresh_column_lists()

    def _refresh_column_lists(self):
        cols = self.dm.columns if self.dm.is_loaded else ["(load data first)"]
        for cmb in (self.cmb_depth, self.cmb_density, self.cmb_vp, self.cmb_vs):
            cmb.configure(values=cols)
            if cols:
                cmb.set(cols[0])
        if self.dm.is_loaded:
            self._auto_map()

    def _auto_map(self):
        low = {c.lower().strip(): c for c in self.dm.columns}
        mapping = {
            self.cmb_depth:   ["depth", "tvd", "md", "measured depth", "tvdss",
                               "depth_m", "depth_ft", "dept"],
            self.cmb_density: ["density", "rhob", "rho", "bulk_density", "den",
                               "bulk density", "rho_b"],
            self.cmb_vp:      ["vp", "dtc", "p-wave", "vp_m/s", "vp_ft/s",
                               "comp_vel", "compressional", "v_p"],
            self.cmb_vs:      ["vs", "dts", "s-wave", "vs_m/s", "vs_ft/s",
                               "shear_vel", "shear", "v_s"],
        }
        for cmb, keys in mapping.items():
            for k in keys:
                if k in low:
                    cmb.set(low[k])
                    break

    def _on_compute(self):
        if not self.dm.is_loaded:
            messagebox.showwarning("No Data",
                                   "Load a data file on the HOME page first.")
            return

        df_in = self.dm.dataframe
        d_col = self.cmb_depth.get()
        r_col = self.cmb_density.get()
        vp_col = self.cmb_vp.get()
        vs_col = self.cmb_vs.get()

        for col, name in [(d_col, "Depth"), (r_col, "Density"),
                          (vp_col, "Vp"), (vs_col, "Vs")]:
            if col not in df_in.columns:
                messagebox.showerror("Missing Column",
                                     f"Select a valid {name} column.")
                return

        try:
            arrs = {}
            for col, key in [(d_col, "depth"), (r_col, "rho"),
                             (vp_col, "Vp"), (vs_col, "Vs")]:
                arrs[key] = pd.to_numeric(df_in[col], errors="coerce").dropna().values
            n = min(len(v) for v in arrs.values())
            for k in arrs:
                arrs[k] = arrs[k][:n]
        except Exception as e:
            messagebox.showerror("Data Error", str(e))
            return

        if n < 2:
            messagebox.showerror("Insufficient Data",
                                 "Need at least 2 depth points.")
            return

        unit_str = self.unit_var.get()
        if "FIELD" in unit_str:
            unit = "FIELD"
        elif "km/s" in unit_str:
            unit = "SI_KMS"
        else:
            unit = "SI"

        try:
            self.result_df = compute_all_moduli(
                arrs["depth"], arrs["rho"], arrs["Vp"], arrs["Vs"],
                unit_system=unit)
        except Exception as e:
            messagebox.showerror("Computation Error", str(e))
            return

        self._draw_plots(self.result_df)
        self._fill_table(self.result_df)
        self.lbl_count.configure(
            text=f"{len(self.result_df):,} rows  |  "
                 f"{len(self.result_df.columns)} columns")

    def _fill_table(self, df):
        self.tree.delete(*self.tree.get_children())
        cols = list(df.columns)
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c, anchor="w")
            self.tree.column(c, width=110, anchor="w", minwidth=70)
        for _, row in df.head(1000).iterrows():
            vals = [f"{v:.4f}" if isinstance(v, float) else str(v) for v in row]
            self.tree.insert("", "end", values=vals)

    def _on_export(self):
        if self.result_df is None:
            messagebox.showinfo("No Results", "Run computation first.")
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Export Moduli Results", defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")])
        if not path:
            return
        try:
            if path.endswith(".xlsx"):
                self.result_df.to_excel(path, index=False, engine="openpyxl")
            else:
                self.result_df.to_csv(path, index=False)
            messagebox.showinfo("Exported", f"Results saved to\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
