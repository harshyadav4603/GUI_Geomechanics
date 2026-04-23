"""Tkinter + Matplotlib seismic interpretation viewer."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .data import generate_synthetic_cube
from .interpretation import InterpretationModel
from .segy_loader import SegyLoadError, load_segy_cube


class QuietNavigationToolbar(NavigationToolbar2Tk):
    """Matplotlib toolbar variant without coordinate readout text."""

    def set_message(self, s):
        # Suppress the default (x, y) coordinate + value display in the toolbar.
        return


class SeismicViewerFrame(ctk.CTkFrame):
    """Interactive seismic interpretation frame with data loading and picking tools."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.cube: np.ndarray | None = None
        self.metadata: dict = {}
        self.section_cache: np.ndarray | None = None
        self.time_axis: np.ndarray | None = None

        self.interpretation = InterpretationModel()
        self.pick_artists = []
        self.image_artist = None
        self.colorbar = None

        self.view_mode = ctk.StringVar(value="Inline")
        self.cmap_name = ctk.StringVar(value="seismic")
        self.hover_text = ctk.StringVar(value="Trace: -    Time: -    Amp: -")

        self.inline_index = ctk.IntVar(value=0)
        self.crossline_index = ctk.IntVar(value=0)
        self.vmin_value = ctk.DoubleVar(value=-0.6)
        self.vmax_value = ctk.DoubleVar(value=0.6)
        self._redraw_after_id: str | None = None
        self.amp_min_limit = -1.0
        self.amp_max_limit = 1.0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_loading_page()

    def _build_loading_page(self):
        self.loading_page = ctk.CTkFrame(self, fg_color="#101722", corner_radius=14)
        self.loading_page.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)
        self.loading_page.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.loading_page,
            text="SEISMIC INTERPRETATION SYSTEM",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#8ecae6",
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 8))

        ctk.CTkLabel(
            self.loading_page,
            text="Data Loading Page: choose a SEG-Y file or generate a synthetic seismic cube.",
            font=ctk.CTkFont(size=14),
            text_color="#9fb0c8",
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 16))

        actions = ctk.CTkFrame(self.loading_page, fg_color="#16213e", corner_radius=12)
        actions.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 14))
        actions.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            actions,
            text="Load SEG-Y File",
            height=40,
            width=180,
            fg_color="#0f6ac8",
            hover_color="#1784ef",
            command=self._load_segy,
        ).grid(row=0, column=0, padx=14, pady=14)

        ctk.CTkButton(
            actions,
            text="Generate Synthetic Cube",
            height=40,
            width=200,
            fg_color="#13795b",
            hover_color="#1a9a72",
            command=self._generate_synthetic,
        ).grid(row=0, column=1, padx=14, pady=14, sticky="w")

        synth = ctk.CTkFrame(self.loading_page, fg_color="#1b2432", corner_radius=12)
        synth.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 14))
        for col in (1, 3, 5):
            synth.grid_columnconfigure(col, weight=1)

        self.inline_entry = ctk.CTkEntry(synth, width=90)
        self.crossline_entry = ctk.CTkEntry(synth, width=90)
        self.sample_entry = ctk.CTkEntry(synth, width=90)
        self.inline_entry.insert(0, "80")
        self.crossline_entry.insert(0, "120")
        self.sample_entry.insert(0, "300")

        ctk.CTkLabel(synth, text="Inline").grid(row=0, column=0, padx=(14, 6), pady=12, sticky="w")
        self.inline_entry.grid(row=0, column=1, padx=(0, 12), pady=12, sticky="w")
        ctk.CTkLabel(synth, text="Crossline").grid(row=0, column=2, padx=(0, 6), pady=12, sticky="w")
        self.crossline_entry.grid(row=0, column=3, padx=(0, 12), pady=12, sticky="w")
        ctk.CTkLabel(synth, text="Samples").grid(row=0, column=4, padx=(0, 6), pady=12, sticky="w")
        self.sample_entry.grid(row=0, column=5, padx=(0, 14), pady=12, sticky="w")

        self.metadata_label = ctk.CTkLabel(
            self.loading_page,
            text="No seismic cube loaded.",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color="#9fb0c8",
        )
        self.metadata_label.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 20))

    def _build_interpretation_page(self):
        self.interpretation_page = ctk.CTkFrame(self, fg_color="transparent")
        self.interpretation_page.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.interpretation_page.grid_columnconfigure(1, weight=1)
        self.interpretation_page.grid_rowconfigure(0, weight=1)

        controls = ctk.CTkFrame(self.interpretation_page, width=310, fg_color="#101722", corner_radius=12)
        controls.grid(row=0, column=0, sticky="nsw", padx=(8, 8), pady=8)
        controls.grid_propagate(False)

        viewer_host = ctk.CTkFrame(self.interpretation_page, fg_color="#101722", corner_radius=12)
        viewer_host.grid(row=0, column=1, sticky="nsew", padx=(8, 8), pady=8)
        viewer_host.grid_rowconfigure(1, weight=1)
        viewer_host.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            controls,
            text="Seismic Controls",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#8ecae6",
        ).pack(anchor="w", padx=14, pady=(12, 8))

        ctk.CTkButton(
            controls,
            text="Back To Data Loading",
            height=34,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._show_loading_page,
        ).pack(fill="x", padx=12, pady=(0, 10))

        self.dataset_info = ctk.CTkLabel(
            controls,
            text="Dataset: -",
            justify="left",
            anchor="w",
            text_color="#a4b0be",
            font=ctk.CTkFont(size=12),
        )
        self.dataset_info.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(controls, text="Section Type").pack(anchor="w", padx=14)
        self.mode_menu = ctk.CTkOptionMenu(
            controls,
            values=["Inline", "Crossline"],
            variable=self.view_mode,
            command=lambda _: self._redraw_section(),
        )
        self.mode_menu.pack(fill="x", padx=12, pady=(2, 10))

        self.inline_value_label = ctk.CTkLabel(controls, text="Inline: 0")
        self.inline_value_label.pack(anchor="w", padx=14)
        self.inline_slider = ctk.CTkSlider(
            controls,
            from_=0,
            to=1,
            number_of_steps=1,
            command=self._on_inline_change,
        )
        self.inline_slider.pack(fill="x", padx=12, pady=(2, 10))

        self.crossline_value_label = ctk.CTkLabel(controls, text="Crossline: 0")
        self.crossline_value_label.pack(anchor="w", padx=14)
        self.crossline_slider = ctk.CTkSlider(
            controls,
            from_=0,
            to=1,
            number_of_steps=1,
            command=self._on_crossline_change,
        )
        self.crossline_slider.pack(fill="x", padx=12, pady=(2, 10))

        ctk.CTkLabel(controls, text="Colormap").pack(anchor="w", padx=14)
        ctk.CTkOptionMenu(
            controls,
            values=["gray", "seismic", "RdBu_r", "viridis", "inferno"],
            variable=self.cmap_name,
            command=lambda _: self._redraw_section(),
        ).pack(fill="x", padx=12, pady=(2, 10))

        self.vmin_label = ctk.CTkLabel(controls, text="Vmin: -0.60")
        self.vmin_label.pack(anchor="w", padx=14)
        self.vmin_slider = ctk.CTkSlider(
            controls,
            from_=-1.0,
            to=1.0,
            number_of_steps=200,
            variable=self.vmin_value,
            command=self._on_contrast_change,
        )
        self.vmin_slider.pack(fill="x", padx=12, pady=(2, 8))

        self.vmax_label = ctk.CTkLabel(controls, text="Vmax: 0.60")
        self.vmax_label.pack(anchor="w", padx=14)
        self.vmax_slider = ctk.CTkSlider(
            controls,
            from_=-1.0,
            to=1.0,
            number_of_steps=200,
            variable=self.vmax_value,
            command=self._on_contrast_change,
        )
        self.vmax_slider.pack(fill="x", padx=12, pady=(2, 8))

        amp_frame = ctk.CTkFrame(controls, fg_color="#1b2432", corner_radius=8)
        amp_frame.pack(fill="x", padx=12, pady=(0, 10))
        amp_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(amp_frame, text="Min Amp").grid(row=0, column=0, padx=8, pady=(8, 2), sticky="w")
        ctk.CTkLabel(amp_frame, text="Max Amp").grid(row=0, column=1, padx=8, pady=(8, 2), sticky="w")

        self.vmin_entry = ctk.CTkEntry(amp_frame, width=90)
        self.vmax_entry = ctk.CTkEntry(amp_frame, width=90)
        self.vmin_entry.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")
        self.vmax_entry.grid(row=1, column=1, padx=8, pady=(0, 8), sticky="ew")

        ctk.CTkButton(
            amp_frame,
            text="Apply Range",
            command=self._apply_manual_amplitude_range,
        ).grid(row=2, column=0, padx=8, pady=(0, 8), sticky="ew")

        ctk.CTkButton(
            amp_frame,
            text="Auto Range (P2-P98)",
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._auto_amplitude_range,
        ).grid(row=2, column=1, padx=8, pady=(0, 8), sticky="ew")

        ctk.CTkButton(
            controls,
            text="Auto Track Horizon",
            fg_color="#0f6ac8",
            hover_color="#1784ef",
            command=self._auto_track_horizon,
        ).pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkButton(
            controls,
            text="New Fault Segment",
            command=self._new_fault_segment,
        ).pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkButton(
            controls,
            text="Clear Picks",
            fg_color="#c0392b",
            hover_color="#e74c3c",
            command=self._clear_picks,
        ).pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkButton(
            controls,
            text="Export Picks (CSV)",
            fg_color="#13795b",
            hover_color="#1a9a72",
            command=self._export_picks,
        ).pack(fill="x", padx=12, pady=(0, 14))

        ctk.CTkLabel(
            controls,
            text="Left-click: horizon pick\nRight-click: fault pick",
            justify="left",
            text_color="#9fb0c8",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=14)

        ctk.CTkLabel(
            controls,
            textvariable=self.hover_text,
            justify="left",
            text_color="#d9e2ec",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 12))

        ctk.CTkLabel(
            viewer_host,
            text="Seismic Viewer",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#8ecae6",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor("#0b1220")

        self.canvas = FigureCanvasTkAgg(self.figure, master=viewer_host)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))

        toolbar_frame = ctk.CTkFrame(viewer_host, fg_color="transparent")
        toolbar_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.toolbar = QuietNavigationToolbar(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(side=tk.LEFT, fill=tk.X)

        self.canvas.mpl_connect("button_press_event", self._on_mouse_click)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_hover)

    def _show_loading_page(self):
        if hasattr(self, "interpretation_page"):
            self.interpretation_page.grid_remove()
        self.loading_page.grid()

    def _show_interpretation_page(self):
        if not hasattr(self, "interpretation_page"):
            self._build_interpretation_page()
        self.loading_page.grid_remove()
        self.interpretation_page.grid()

    def _load_segy(self):
        file_path = filedialog.askopenfilename(
            title="Select SEG-Y file",
            filetypes=[("SEG-Y files", "*.sgy *.segy"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            cube, metadata = load_segy_cube(file_path)
        except SegyLoadError as exc:
            messagebox.showerror("SEG-Y Load Error", str(exc))
            return

        self._set_cube(cube, metadata)

    def _generate_synthetic(self):
        try:
            inl = max(8, int(self.inline_entry.get().strip()))
            xln = max(8, int(self.crossline_entry.get().strip()))
            smp = max(64, int(self.sample_entry.get().strip()))
        except ValueError:
            messagebox.showerror("Invalid Input", "Inline, crossline, and sample counts must be integers.")
            return

        cube, metadata = generate_synthetic_cube(
            inline_count=inl,
            crossline_count=xln,
            sample_count=smp,
        )
        self._set_cube(cube, metadata)

    def _set_cube(self, cube: np.ndarray, metadata: dict):
        self.cube = cube.astype(np.float32, copy=False)
        self.metadata = metadata
        self.interpretation.clear()

        samples = metadata.get("samples")
        if samples is not None:
            try:
                axis = np.asarray(samples, dtype=np.float32)
            except Exception:
                axis = np.arange(self.cube.shape[2], dtype=np.float32)
        else:
            axis = np.arange(self.cube.shape[2], dtype=np.float32)

        if axis.ndim != 1 or axis.size != self.cube.shape[2]:
            axis = np.arange(self.cube.shape[2], dtype=np.float32)
        self.time_axis = axis

        shape = self.cube.shape
        source = metadata.get("source", "unknown")
        source_text = metadata.get("path", "synthetic cube")

        self.metadata_label.configure(
            text=(
                f"Loaded source: {source}\n"
                f"Source detail: {source_text}\n"
                f"Dimensions: inline={shape[0]}, crossline={shape[1]}, samples={shape[2]}"
            )
        )

        self._show_interpretation_page()

        data_min = float(np.min(self.cube))
        data_max = float(np.max(self.cube))
        max_abs = max(abs(data_min), abs(data_max), 1e-6)
        self.amp_min_limit = -max_abs
        self.amp_max_limit = max_abs

        self.vmin_slider.configure(from_=self.amp_min_limit, to=self.amp_max_limit)
        self.vmax_slider.configure(from_=self.amp_min_limit, to=self.amp_max_limit)

        p2 = float(np.percentile(self.cube, 2.0))
        p98 = float(np.percentile(self.cube, 98.0))
        if p2 >= p98:
            p2 = self.amp_min_limit * 0.6
            p98 = self.amp_max_limit * 0.6
        self.vmin_value.set(p2)
        self.vmax_value.set(p98)

        self._configure_index_slider(self.inline_slider, shape[0])
        self._configure_index_slider(self.crossline_slider, shape[1])
        self.inline_slider.set(0)
        self.crossline_slider.set(0)

        self.inline_index.set(0)
        self.crossline_index.set(0)

        # Crossline sections are not valid when there is only one inline.
        mode_values = ["Inline"]
        if shape[0] > 1:
            mode_values.append("Crossline")
        self.mode_menu.configure(values=mode_values)
        if self.view_mode.get() not in mode_values:
            self.view_mode.set("Inline")

        self._sync_amplitude_controls()

        self.dataset_info.configure(
            text=(
                f"Dataset: {source}\n"
                f"Inline count: {shape[0]}\n"
                f"Crossline count: {shape[1]}\n"
                f"Samples: {shape[2]}"
            )
        )

        self._redraw_section()

    @staticmethod
    def _configure_index_slider(slider: ctk.CTkSlider, count: int):
        """Configure index sliders without creating zero step size."""
        if count <= 1:
            # Keep a valid slider domain and disable interaction for singleton axis.
            slider.configure(from_=0, to=1, number_of_steps=1, state="disabled")
        else:
            slider.configure(from_=0, to=count - 1, number_of_steps=count - 1, state="normal")

    def _schedule_redraw(self, delay_ms: int = 25):
        """Debounce redraw requests to keep UI stable during slider drags."""
        if self._redraw_after_id is not None:
            try:
                self.after_cancel(self._redraw_after_id)
            except Exception:
                pass
        self._redraw_after_id = self.after(delay_ms, self._run_scheduled_redraw)

    def _run_scheduled_redraw(self):
        self._redraw_after_id = None
        self._redraw_section()

    def _sync_amplitude_controls(self):
        self.vmin_label.configure(text=f"Vmin: {self.vmin_value.get():.3f}")
        self.vmax_label.configure(text=f"Vmax: {self.vmax_value.get():.3f}")

        if hasattr(self, "vmin_entry"):
            self.vmin_entry.delete(0, "end")
            self.vmin_entry.insert(0, f"{self.vmin_value.get():.3f}")
        if hasattr(self, "vmax_entry"):
            self.vmax_entry.delete(0, "end")
            self.vmax_entry.insert(0, f"{self.vmax_value.get():.3f}")

    def _apply_manual_amplitude_range(self):
        try:
            vmin = float(self.vmin_entry.get().strip())
            vmax = float(self.vmax_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Amplitude Range", "Enter numeric values for Min Amp and Max Amp.")
            return

        if vmin >= vmax:
            messagebox.showerror("Invalid Amplitude Range", "Min Amp must be smaller than Max Amp.")
            return

        vmin = max(self.amp_min_limit, min(vmin, self.amp_max_limit))
        vmax = max(self.amp_min_limit, min(vmax, self.amp_max_limit))
        if vmin >= vmax:
            messagebox.showerror("Invalid Amplitude Range", "Chosen values collapse after clipping to data limits.")
            return

        self.vmin_value.set(vmin)
        self.vmax_value.set(vmax)
        self._sync_amplitude_controls()
        self._schedule_redraw()

    def _auto_amplitude_range(self):
        if self.cube is None:
            return
        vmin = float(np.percentile(self.cube, 2.0))
        vmax = float(np.percentile(self.cube, 98.0))
        if vmin >= vmax:
            vmin = self.amp_min_limit * 0.6
            vmax = self.amp_max_limit * 0.6
        self.vmin_value.set(vmin)
        self.vmax_value.set(vmax)
        self._sync_amplitude_controls()
        self._schedule_redraw()

    def _current_section(self) -> np.ndarray:
        if self.cube is None:
            return np.empty((0, 0), dtype=np.float32)

        mode = self.view_mode.get()
        if mode == "Crossline" and self.cube.shape[0] <= 1:
            mode = "Inline"

        if mode == "Inline":
            idx = int(self.inline_index.get())
            idx = min(max(0, idx), self.cube.shape[0] - 1)
            raw = self.cube[idx, :, :]
        else:
            idx = int(self.crossline_index.get())
            idx = min(max(0, idx), self.cube.shape[1] - 1)
            raw = self.cube[:, idx, :]

        # Convert from (trace, sample) to (sample, trace) for display.
        return raw.T

    def _redraw_section(self):
        if self.cube is None:
            return

        if self.vmin_value.get() >= self.vmax_value.get():
            self.vmax_value.set(min(1.0, self.vmin_value.get() + 0.05))

        section = self._current_section()
        self.section_cache = section

        self.ax.clear()
        self.image_artist = self.ax.imshow(
            section,
            cmap=self.cmap_name.get(),
            aspect="auto",
            interpolation="nearest",
            vmin=float(self.vmin_value.get()),
            vmax=float(self.vmax_value.get()),
            origin="upper",
        )

        if self.view_mode.get() == "Inline":
            current_inline = int(self.inline_index.get())
            self.ax.set_title(f"Inline {current_inline}")
            self.ax.set_xlabel("Trace Number")
        else:
            current_crossline = int(self.crossline_index.get())
            self.ax.set_title(f"Crossline {current_crossline}")
            self.ax.set_xlabel("Trace Number")

        self.ax.set_ylabel("Two-Way Time (ms)")

        # Keep index-based image coordinates for robust picking, but label Y as TWT.
        if self.time_axis is not None and section.shape[0] > 0:
            tick_count = min(9, section.shape[0])
            tick_idx = np.unique(np.linspace(0, section.shape[0] - 1, num=tick_count, dtype=int))
            self.ax.set_yticks(tick_idx)
            self.ax.set_yticklabels([f"{float(self.time_axis[i]):.1f}" for i in tick_idx])

        # Keep one persistent colorbar and update its mappable on redraw.
        # Repeated remove() calls can fail during rapid slider callbacks.
        if self.colorbar is None:
            self.colorbar = self.figure.colorbar(self.image_artist, ax=self.ax, fraction=0.028, pad=0.02)
        else:
            try:
                self.colorbar.update_normal(self.image_artist)
            except Exception:
                # Recover if the previous colorbar axis was invalidated.
                self.colorbar = self.figure.colorbar(self.image_artist, ax=self.ax, fraction=0.028, pad=0.02)
        self.colorbar.set_label("Amplitude")

        self._draw_picks()
        self.canvas.draw_idle()

    def _draw_picks(self):
        for artist in self.pick_artists:
            artist.remove()
        self.pick_artists.clear()

        for points in self.interpretation.horizons:
            if not points:
                continue
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            artist, = self.ax.plot(xs, ys, color="#00d4ff", linewidth=2.0, marker="o", markersize=3)
            self.pick_artists.append(artist)

        for points in self.interpretation.faults:
            if not points:
                continue
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            artist, = self.ax.plot(xs, ys, color="#ff6b6b", linewidth=2.0, marker="x", markersize=4)
            self.pick_artists.append(artist)

    def _on_inline_change(self, value: float):
        idx = int(round(value))
        self.inline_index.set(idx)
        self.inline_value_label.configure(text=f"Inline: {idx}")
        if self.view_mode.get() == "Inline":
            self._schedule_redraw()

    def _on_crossline_change(self, value: float):
        idx = int(round(value))
        self.crossline_index.set(idx)
        self.crossline_value_label.configure(text=f"Crossline: {idx}")
        if self.view_mode.get() == "Crossline":
            self._schedule_redraw()

    def _on_contrast_change(self, _value: float):
        self._sync_amplitude_controls()
        self._schedule_redraw()

    def _on_mouse_hover(self, event):
        if self.section_cache is None or event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return

        x_idx = int(round(event.xdata))
        y_idx = int(round(event.ydata))
        n_samples, n_traces = self.section_cache.shape

        if 0 <= x_idx < n_traces and 0 <= y_idx < n_samples:
            amp = float(self.section_cache[y_idx, x_idx])
            twt = float(self.time_axis[y_idx]) if self.time_axis is not None and y_idx < len(self.time_axis) else float(y_idx)
            self.hover_text.set(f"Trace: {x_idx}    TWT: {twt:.2f} ms    Amp: {amp:.4f}")

    def _on_mouse_click(self, event):
        if event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return

        x = float(event.xdata)
        y = float(event.ydata)

        if event.button == 1:
            self.interpretation.add_horizon_point(x, y)
        elif event.button == 3:
            self.interpretation.add_fault_point(x, y)
        else:
            return

        self._draw_picks()
        self.canvas.draw_idle()

    def _new_fault_segment(self):
        self.interpretation.new_fault_segment()

    def _clear_picks(self):
        self.interpretation.clear()
        self._redraw_section()

    def _export_picks(self):
        file_path = filedialog.asksaveasfilename(
            title="Export Picks",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not file_path:
            return

        self.interpretation.export_csv(file_path)
        messagebox.showinfo("Export Complete", f"Picks exported to:\n{file_path}")

    def _auto_track_horizon(self):
        if self.section_cache is None:
            return

        points = self.interpretation.horizons[self.interpretation.active_horizon]
        if not points:
            messagebox.showinfo("Auto Track", "Add at least one horizon pick before auto tracking.")
            return

        start_x, start_y = points[-1]
        section = self.section_cache
        n_samples, n_traces = section.shape

        seed_x = int(round(start_x))
        seed_y = int(round(start_y))
        if not (0 <= seed_x < n_traces and 0 <= seed_y < n_samples):
            return

        window = 8
        tracked = []
        current_y = seed_y
        for x in range(seed_x, n_traces):
            y0 = max(0, current_y - window)
            y1 = min(n_samples, current_y + window + 1)
            local = section[y0:y1, x]
            if local.size == 0:
                continue
            rel = int(np.argmax(np.abs(local)))
            current_y = y0 + rel
            tracked.append((float(x), float(current_y)))

        for x, y in tracked:
            self.interpretation.add_horizon_point(x, y)

        self._draw_picks()
        self.canvas.draw_idle()
