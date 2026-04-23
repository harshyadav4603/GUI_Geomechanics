"""
Landing Page - top-level module selection.
"""

import customtkinter as ctk


class LandingPage(ctk.CTkFrame):
    """Top-level home page with Geomechanics and Seismic entry points."""

    def __init__(self, master, on_open_geomech, on_open_seismic, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_open_geomech = on_open_geomech
        self.on_open_seismic = on_open_seismic

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_cards()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#101722", corner_radius=14)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 14))

        ctk.CTkLabel(
            header,
            text="GEOMECHANICS WORKBENCH",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#00d4ff",
        ).pack(anchor="w", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            header,
            text="Choose a workspace to continue",
            font=ctk.CTkFont(size=14),
            text_color="#96a0ad",
        ).pack(anchor="w", padx=20, pady=(0, 16))

    def _build_cards(self):
        geomech = ctk.CTkFrame(self, fg_color="#132238", corner_radius=14, border_width=2, border_color="#1f4a82")
        geomech.grid(row=1, column=0, sticky="nsew", padx=(24, 12), pady=(0, 24))

        ctk.CTkLabel(
            geomech,
            text="Geomechanics",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#f2f6ff",
        ).pack(anchor="w", padx=20, pady=(20, 4))

        ctk.CTkLabel(
            geomech,
            text="Stress, moduli, and strength workflows with data upload and analysis pages.",
            font=ctk.CTkFont(size=13),
            text_color="#9fb0c8",
            justify="left",
            wraplength=420,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        ctk.CTkButton(
            geomech,
            text="Open Geomechanics",
            height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0f6ac8",
            hover_color="#1680ea",
            command=self.on_open_geomech,
        ).pack(anchor="w", padx=20, pady=(0, 20))

        seismic = ctk.CTkFrame(self, fg_color="#1d1d22", corner_radius=14, border_width=2, border_color="#3c3f46")
        seismic.grid(row=1, column=1, sticky="nsew", padx=(12, 24), pady=(0, 24))

        ctk.CTkLabel(
            seismic,
            text="Seismic",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#f2f6ff",
        ).pack(anchor="w", padx=20, pady=(20, 4))

        ctk.CTkLabel(
            seismic,
            text="Seismic module entry point is prepared. Full workflows can be added next.",
            font=ctk.CTkFont(size=13),
            text_color="#a8adb7",
            justify="left",
            wraplength=420,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        ctk.CTkButton(
            seismic,
            text="Open Seismic",
            height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#494f59",
            hover_color="#5e6672",
            command=self.on_open_seismic,
        ).pack(anchor="w", padx=20, pady=(0, 20))