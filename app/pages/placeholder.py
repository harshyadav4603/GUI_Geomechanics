"""
Placeholder page template for modules not yet implemented.
"""

import customtkinter as ctk


class PlaceholderPage(ctk.CTkFrame):
    """Generic placeholder shown for modules under development."""

    def __init__(self, master, title: str, icon_text: str, color: str, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Title card
        card = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=14)
        card.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 10))

        ctk.CTkLabel(
            card,
            text=f"  {icon_text}   {title}",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=color,
        ).pack(padx=25, pady=20, anchor="w")

        # Center placeholder
        center = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=14)
        center.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(center, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            inner,
            text=icon_text,
            font=ctk.CTkFont(size=72),
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            inner,
            text=f"{title} Module",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=color,
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            inner,
            text="🚧  Under Development  🚧\nThis module will be available in a future release.",
            font=ctk.CTkFont(size=14),
            text_color="#888888",
            justify="center",
        ).pack(pady=(0, 20))

        # Feature bullets
        features = self._get_features(title)
        if features:
            feat_frame = ctk.CTkFrame(inner, fg_color="#0f3460", corner_radius=10)
            feat_frame.pack(padx=20, pady=5, fill="x")
            ctk.CTkLabel(
                feat_frame, text="Planned Features:",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#feca57",
            ).pack(padx=15, pady=(10, 5), anchor="w")
            for f in features:
                ctk.CTkLabel(
                    feat_frame, text=f"  •  {f}",
                    font=ctk.CTkFont(size=12), text_color="#cccccc", anchor="w",
                ).pack(padx=20, pady=1, anchor="w")
            ctk.CTkLabel(feat_frame, text="").pack(pady=4)  # spacer

    @staticmethod
    def _get_features(title: str) -> list[str]:
        mapping = {
            "STRESS": [
                "Overburden stress (Sv) calculation",
                "Pore-pressure estimation",
                "Min / Max horizontal stress (Shmin, SHmax)",
                "Stress polygon visualisation",
            ],
            "MODULI": [
                "Dynamic → Static moduli conversion",
                "Young's Modulus, Poisson's Ratio profiles",
                "Bulk & Shear modulus computation",
                "Anisotropy analysis",
            ],
            "ROCK PHYSICS": [
                "Velocity – porosity cross-plots",
                "Hashin-Shtrikman bounds",
                "Gassmann fluid substitution",
                "Rock-physics templates (RPT)",
            ],
            "STRENGTH & FAILURE": [
                "UCS & Friction-angle estimation",
                "Mohr-Coulomb failure criterion",
                "Modified Lade & Modified Wiebols-Cook",
                "Hoek-Brown criterion",
            ],
            "WELLBORE STABILITY": [
                "Breakout-width prediction",
                "Safe mud-weight window",
                "Kirsch solution for tangential stress",
                "Polar stress-plots around borehole",
            ],
        }
        return mapping.get(title, [])
