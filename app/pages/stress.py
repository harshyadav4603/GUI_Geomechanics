"""
STRESS Analysis Page
=====================
Full interactive page for computing and visualising geomechanical stresses.

Layout (left → right):
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
matplotlib.use("TkAgg")  # ensure TkAgg (may already be set by main.py)
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from app.computations.stress_calc import (
    compute_all_stresses,
    compute_dynamic_poisson,
    compute_overburden,
    compute_overburden_ppg,
    compute_hydrostatic_pore_pressure,
    compute_hydrostatic_pp_psi,
)


# ── Accent colours ────────────────────────────────────────────────
CLR_ACCENT  = "#ff6b6b"
CLR_BG      = "#0d1117"
CLR_CARD    = "#16213e"
CLR_CARD2   = "#1a1a2e"
CLR_INPUT   = "#0f3460"
CLR_TEXT    = "#e0e0e0"
CLR_DIM     = "#888888"


class StressPage(ctk.CTkFrame):
    """Stress analysis: column mapping → compute → plot + table."""

    def __init__(self, master, data_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.dm = data_manager
        self.dm.subscribe(self._on_data_changed)
        self.result_df: pd.DataFrame | None = None

        # Main layout: 2 columns – controls (fixed) | plots+table (expand)
        self.grid_columnconfigure(0, weight=0, minsize=340)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_controls_panel()
        self._build_output_panel()

        # Populate dropdowns if data already loaded
        if self.dm.is_loaded:
            self._refresh_column_lists()

    # ══════════════════════════════════════════════════════════════
    #  LEFT PANEL – controls, column mapping, parameters, formulas
    # ══════════════════════════════════════════════════════════════
    def _build_controls_panel(self):
        panel = ctk.CTkScrollableFrame(self, fg_color=CLR_CARD2, width=320,
                                        corner_radius=12)
        panel.grid(row=0, column=0, sticky="ns", padx=(15, 5), pady=15)
        panel.grid_columnconfigure(1, weight=1)
        self.ctrl_panel = panel

        # ── Title ─────────────────────────────────────────────────
        ctk.CTkLabel(panel, text="🔴  STRESS ANALYSIS",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=CLR_ACCENT).grid(row=0, column=0, columnspan=2,
                                                  padx=12, pady=(12, 4), sticky="w")

        # ── Unit system ───────────────────────────────────────────
        self._add_section(panel, 1, "Unit System")
        self.unit_var = ctk.StringVar(value="SI  (m, kg/m³ → Pa)")
        self.cmb_unit = ctk.CTkComboBox(
            panel, values=["SI  (m, kg/m³ → Pa)", "FIELD  (ft, g/cc → psi)"],
            variable=self.unit_var, width=240, fg_color=CLR_INPUT,
            button_color=CLR_INPUT, border_color="#1a5276",
            dropdown_fg_color=CLR_INPUT, state="readonly",
        )
        self.cmb_unit.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")

        # ── Column mapping ────────────────────────────────────────
        self._add_section(panel, 3, "Column Mapping")

        self.cmb_depth = self._add_combo(panel, 4, "Depth column")
        self.cmb_density = self._add_combo(panel, 5, "Density column")
        self.cmb_vp = self._add_combo(panel, 6, "Vp  –  P-wave velocity")
        self.cmb_vs = self._add_combo(panel, 7, "Vs  –  S-wave velocity")

        ctk.CTkLabel(panel,
            text="ν = (Vp² − 2Vs²) / 2(Vp² − Vs²)\n"
                 "Poisson's ratio computed from Vp & Vs.",
            font=ctk.CTkFont(size=10, family="Consolas"),
            text_color="#48dbfb", justify="left",
            wraplength=280,
        ).grid(row=8, column=0, columnspan=2, padx=14, pady=(2, 4), sticky="w")

        # ── Parameters ─────────────────────────────────────────────
        self._add_section(panel, 9, "Model Parameters")

        self.ent_poisson = self._add_entry(panel, 10, "Fallback ν (if no Vp/Vs)", "0.25")
        self.ent_tectonic = self._add_entry(panel, 11, "Tectonic stress", "0.0")
        self.ent_strain = self._add_entry(panel, 12, "Strain ratio (εH/εh)", "1.0")
        self.ent_water_rho = self._add_entry(panel, 13, "Water density (Pp=ρw·g·z)", "1025")

        # ── Compute button ────────────────────────────────────────
        self.btn_compute = ctk.CTkButton(
            panel, text="⚡  COMPUTE  STRESSES", height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#c0392b", hover_color="#e74c3c",
            corner_radius=8, command=self._on_compute,
        )
        self.btn_compute.grid(row=14, column=0, columnspan=2,
                               padx=12, pady=(14, 8), sticky="ew")

        # ── Formula reference ─────────────────────────────────────
        self._add_section(panel, 15, "Formulas")
        formulas = (
            "① Sv = ∫₀ᶻ ρ(z)·g·dz\n"
            "② dSv/dz = ∂Sv / ∂z\n"
            "③ Sv_eff = Sv − Pp\n"
            "④ Pp_hydro = ρ_w · g · z\n"
            "⑤ ν = (Vp²−2Vs²) / 2(Vp²−Vs²)\n"
            "⑥ Shmin = ν/(1−ν)·(Sv−Pp) + Pp + σ_t\n"
            "⑦ SHmax = ν/(1−ν)·(Sv−Pp)·(1+ε) + Pp + σ_t\n"
            "⑧ K₀_min = Shmin / Sv\n"
            "⑨ K₀_max = SHmax / Sv"
        )
        ctk.CTkLabel(panel, text=formulas, font=ctk.CTkFont(size=11, family="Consolas"),
                     text_color="#48dbfb", justify="left",
                     wraplength=300).grid(row=16, column=0, columnspan=2,
                                           padx=12, pady=(0, 12), sticky="w")

        # ── Export button ─────────────────────────────────────────
        self.btn_export = ctk.CTkButton(
            panel, text="💾  Export Results CSV", height=36,
            font=ctk.CTkFont(size=12), fg_color=CLR_INPUT,
            hover_color="#1a5276", corner_radius=6,
            command=self._on_export,
        )
        self.btn_export.grid(row=17, column=0, columnspan=2,
                              padx=12, pady=(0, 14), sticky="ew")

    # ── helper builders ───────────────────────────────────────────

    @staticmethod
    def _add_section(parent, row, text):
        sep = ctk.CTkFrame(parent, height=1, fg_color="#2c3e50")
        sep.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(10, 2))
        ctk.CTkLabel(sep, text=f"  {text}  ", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#feca57", fg_color=CLR_CARD2).place(x=12, y=-9)

    def _add_combo(self, parent, row, label_text) -> ctk.CTkComboBox:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=2, padx=12, pady=(4, 2), sticky="ew")
        ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=11),
                     text_color=CLR_DIM).pack(anchor="w")
        cmb = ctk.CTkComboBox(frame, values=["(load data first)"], width=240,
                               fg_color=CLR_INPUT, button_color=CLR_INPUT,
                               border_color="#1a5276",
                               dropdown_fg_color=CLR_INPUT, state="readonly")
        cmb.pack(anchor="w", pady=(2, 0))
        return cmb

    @staticmethod
    def _add_entry(parent, row, label_text, default) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(size=11),
                     text_color=CLR_DIM).grid(row=row, column=0, padx=12, pady=(4, 0), sticky="w")
        ent = ctk.CTkEntry(parent, width=120, fg_color=CLR_INPUT,
                            border_color="#1a5276", text_color=CLR_TEXT)
        ent.insert(0, default)
        ent.grid(row=row, column=1, padx=12, pady=(4, 2), sticky="e")
        return ent

    # ══════════════════════════════════════════════════════════════
    #  RIGHT PANEL – plots + results table
    # ══════════════════════════════════════════════════════════════
    def _build_output_panel(self):
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 15), pady=15)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=3)   # plots expand more
        right.grid_rowconfigure(1, weight=2)   # table

        self._build_plot_area(right)
        self._build_result_table(right)

    # ── Matplotlib plot ───────────────────────────────────────────

    def _build_plot_area(self, parent):
        plot_card = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=12)
        plot_card.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        plot_card.grid_columnconfigure(0, weight=1)
        plot_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(plot_card, text="  📈  Stress vs Depth Profiles",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#feca57").grid(row=0, column=0, padx=12,
                                                pady=(10, 0), sticky="w")

        # Figure
        self.fig = Figure(figsize=(10, 4.5), dpi=100, facecolor=CLR_BG)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_card)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        # Toolbar
        tb_frame = ctk.CTkFrame(plot_card, fg_color=CLR_BG, height=30)
        tb_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.toolbar = NavigationToolbar2Tk(self.canvas, tb_frame)
        self.toolbar.update()
        self.toolbar.pack(side="left")

        self._draw_empty_plots()

    def _draw_empty_plots(self):
        """Show placeholder axes before computation."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(CLR_BG)
        ax.text(0.5, 0.5, "Run computation to see stress profiles",
                ha="center", va="center", fontsize=14, color="#555555",
                transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        self.canvas.draw()

    def _draw_stress_plots(self, df: pd.DataFrame):
        """Create 4-panel depth plots after computation."""
        self.fig.clear()
        self.fig.set_facecolor(CLR_BG)

        depth = df["Depth"].values

        plot_specs = [
            {
                "title": "Overburden (Sv)",
                "curves": [
                    ("Sv (Overburden)", "#ff6b6b", "-"),
                    ("Pp (Pore Pressure)", "#48dbfb", "--"),
                ],
            },
            {
                "title": "Poisson's Ratio (ν)",
                "curves": [
                    ("Poisson Ratio (dynamic)", "#feca57", "-"),
                    ("Poisson Ratio", "#feca57", "-"),
                ],
            },
            {
                "title": "Horizontal & Eff. Stresses",
                "curves": [
                    ("Sv (Overburden)", "#ff6b6b", "-"),
                    ("Shmin", "#2ed573", "-"),
                    ("SHmax", "#ff9ff3", "-"),
                    ("Pp (Pore Pressure)", "#48dbfb", "--"),
                ],
            },
            {
                "title": "Sv Gradient & K₀",
                "curves": [
                    ("Sv Gradient", "#ff6b6b", "-"),
                    ("K0_min", "#2ed573", "--"),
                    ("K0_max", "#ff9ff3", "--"),
                ],
            },
        ]

        for idx, spec in enumerate(plot_specs):
            ax = self.fig.add_subplot(1, 4, idx + 1)
            ax.set_facecolor("#0a0a1a")
            ax.set_title(spec["title"], fontsize=9, color=CLR_TEXT, pad=6)
            ax.tick_params(colors=CLR_DIM, labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#2c3e50")

            for col, color, ls in spec["curves"]:
                if col in df.columns:
                    ax.plot(df[col].values, depth, color=color, linewidth=1.2,
                            linestyle=ls, label=col)

            ax.invert_yaxis()
            ax.set_ylabel("Depth", fontsize=8, color=CLR_DIM)
            ax.legend(fontsize=6, loc="lower right",
                      facecolor="#1a1a2e", edgecolor="#2c3e50",
                      labelcolor=CLR_TEXT)
            ax.grid(True, color="#1a2a3a", linewidth=0.5, alpha=0.5)

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    # ── Results table ─────────────────────────────────────────────

    def _build_result_table(self, parent):
        tbl_card = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=12)
        tbl_card.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        tbl_card.grid_columnconfigure(0, weight=1)
        tbl_card.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(tbl_card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="  📊  Computed Results",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#feca57").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.lbl_count = ctk.CTkLabel(hdr, text="", font=ctk.CTkFont(size=11),
                                       text_color=CLR_DIM)
        self.lbl_count.grid(row=0, column=1, padx=12, pady=8, sticky="e")

        # Treeview style
        style = ttk.Style()
        style.configure("Stress.Treeview",
                         background="#0a0a1a", foreground="#e0e0e0",
                         fieldbackground="#0a0a1a", rowheight=24,
                         font=("Segoe UI", 9))
        style.configure("Stress.Treeview.Heading",
                         background="#0f3460", foreground="#ff6b6b",
                         font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Stress.Treeview",
                   background=[("selected", "#1a5276")],
                   foreground=[("selected", "#ffffff")])

        tree_frm = ctk.CTkFrame(tbl_card, fg_color="#0a0a1a", corner_radius=8)
        tree_frm.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        tree_frm.grid_columnconfigure(0, weight=1)
        tree_frm.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frm, style="Stress.Treeview",
                                  show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(tree_frm, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

    # ══════════════════════════════════════════════════════════════
    #  CALLBACKS
    # ══════════════════════════════════════════════════════════════

    def _on_data_changed(self, df: pd.DataFrame | None):
        self._refresh_column_lists()

    def _refresh_column_lists(self):
        cols = self.dm.columns if self.dm.is_loaded else ["(load data first)"]
        cols_opt = ["-- none --"] + cols

        for cmb, options in [
            (self.cmb_depth, cols),
            (self.cmb_density, cols),
            (self.cmb_vp, cols_opt),
            (self.cmb_vs, cols_opt),
        ]:
            cmb.configure(values=options)
            if options:
                cmb.set(options[0])

        # Auto-guess columns
        if self.dm.is_loaded:
            self._auto_map_columns()

    def _auto_map_columns(self):
        """Try to auto-select columns by common name patterns."""
        cols_lower = {c.lower().strip(): c for c in self.dm.columns}

        depth_keys = ["depth", "tvd", "md", "measured depth", "tvdss",
                      "depth_m", "depth_ft", "dept"]
        density_keys = ["density", "rhob", "rho", "bulk_density", "den",
                        "bulk density", "rho_b", "den_log"]
        vp_keys = ["vp", "dtc", "p-wave", "vp_m/s", "vp_ft/s", "comp_vel",
                   "compressional", "sonic_p", "p_velocity", "v_p"]
        vs_keys = ["vs", "dts", "s-wave", "vs_m/s", "vs_ft/s", "shear_vel",
                   "shear", "sonic_s", "s_velocity", "v_s"]

        for keys, cmb in [
            (depth_keys, self.cmb_depth),
            (density_keys, self.cmb_density),
            (vp_keys, self.cmb_vp),
            (vs_keys, self.cmb_vs),
        ]:
            for k in keys:
                if k in cols_lower:
                    cmb.set(cols_lower[k])
                    break

    def _on_compute(self):
        """Validate inputs, run computation, update plots + table."""
        if not self.dm.is_loaded:
            messagebox.showwarning("No Data", "Please load a data file on the HOME page first.")
            return

        df_in = self.dm.dataframe

        # ── get column selections ─────────────────────────────────
        depth_col = self.cmb_depth.get()
        density_col = self.cmb_density.get()

        if depth_col not in df_in.columns:
            messagebox.showerror("Missing Column", "Select a valid Depth column.")
            return
        if density_col not in df_in.columns:
            messagebox.showerror("Missing Column", "Select a valid Density column.")
            return

        # ── extract arrays ────────────────────────────────────────
        try:
            depth = pd.to_numeric(df_in[depth_col], errors="coerce").dropna().values
            density = pd.to_numeric(df_in[density_col], errors="coerce").dropna().values
            min_len = min(len(depth), len(density))
            depth = depth[:min_len]
            density = density[:min_len]
        except Exception as e:
            messagebox.showerror("Data Error", f"Cannot parse Depth/Density:\n{e}")
            return

        if len(depth) < 2:
            messagebox.showerror("Insufficient Data", "Need at least 2 depth points.")
            return

        # Pore pressure – computed hydrostatically (Pp = ρw · g · z)
        Pp = None  # will be auto-computed from water density parameter

        # Vp / Vs  →  dynamic Poisson's ratio
        vp_col = self.cmb_vp.get()
        vs_col = self.cmb_vs.get()
        Vp_arr = None
        Vs_arr = None

        if vp_col in df_in.columns and vs_col in df_in.columns:
            try:
                Vp_arr = pd.to_numeric(df_in[vp_col], errors="coerce").dropna().values[:min_len]
                Vs_arr = pd.to_numeric(df_in[vs_col], errors="coerce").dropna().values[:min_len]
            except:
                Vp_arr = None
                Vs_arr = None

        # Fallback scalar Poisson's ratio (only used when Vp/Vs not available)
        try:
            poisson_fallback = float(self.ent_poisson.get())
        except ValueError:
            poisson_fallback = 0.25

        try:
            tectonic = float(self.ent_tectonic.get())
        except ValueError:
            tectonic = 0.0

        try:
            strain_ratio = float(self.ent_strain.get())
        except ValueError:
            strain_ratio = 1.0

        # Unit system
        unit = "FIELD" if "FIELD" in self.unit_var.get() else "SI"

        # ── Compute ───────────────────────────────────────────────
        try:
            self.result_df = compute_all_stresses(
                depth, density, Pp=Pp,
                Vp=Vp_arr, Vs=Vs_arr,
                poisson=poisson_fallback,
                tectonic=tectonic, strain_ratio=strain_ratio,
                unit_system=unit,
                water_density=float(self.ent_water_rho.get()),
            )
        except Exception as e:
            messagebox.showerror("Computation Error", str(e))
            return

        # ── Update UI ─────────────────────────────────────────────
        self._draw_stress_plots(self.result_df)
        self._populate_result_table(self.result_df)
        self.lbl_count.configure(
            text=f"{len(self.result_df):,} rows  |  {len(self.result_df.columns)} columns")

    def _populate_result_table(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        cols = list(df.columns)
        self.tree["columns"] = cols
        for col in cols:
            self.tree.heading(col, text=col, anchor="w")
            self.tree.column(col, width=110, anchor="w", minwidth=70)

        for _, row in df.head(1000).iterrows():
            vals = [f"{v:.4f}" if isinstance(v, float) else str(v) for v in row]
            self.tree.insert("", "end", values=vals)

    def _on_export(self):
        if self.result_df is None:
            messagebox.showinfo("No Results", "Run computation first.")
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Export Stress Results",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")],
        )
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
