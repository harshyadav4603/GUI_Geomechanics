"""
Geomechanics GUI – Main Application Window
============================================
Entry point that assembles the sidebar navigation and page container.
"""

# Initialise matplotlib backend BEFORE any other matplotlib import
import matplotlib
matplotlib.use("TkAgg")

import sys
import traceback
import customtkinter as ctk
from PIL import Image

from app.icons import get_icon
from app.data_loader import DataManager
from app.pages.landing import LandingPage
from app.pages.home import HomePage
from app.pages.stress import StressPage
from app.pages.moduli import ModuliPage
from app.pages.strength import StrengthPage
from app.pages.seismic import SeismicPage
from app.pages.placeholder import PlaceholderPage


# ── Theme ─────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ── Navigation definitions ────────────────────────────────────────
NAV_ITEMS = [
    {"key": "landing",   "label": "HOME",                  "icon": "home",     "color": "#00d4ff"},
    {"key": "home",      "label": "GEOMECH",               "icon": "home",     "color": "#00d4ff"},
    {"key": "stress",    "label": "STRESS",                 "icon": "stress",   "color": "#ff6b6b"},
    {"key": "moduli",    "label": "MODULI",                 "icon": "moduli",   "color": "#feca57"},
    {"key": "strength",  "label": "STRENGTH &\nFAILURE",    "icon": "strength", "color": "#ff9ff3"},
    {"key": "seismic",   "label": "SEISMIC",                "icon": "home",     "color": "#8ecae6"},
]


class GeomechanicsApp(ctk.CTk):
    """Root application window."""

    WIDTH = 1280
    HEIGHT = 780
    GEOMECH_KEYS = {"home", "stress", "moduli", "strength"}

    def __init__(self):
        super().__init__()

        # ── catch silent Tk callback errors ───────────────────────
        self.report_callback_exception = self._on_tk_error

        # ── window setup ──────────────────────────────────────────
        self.title("Geomechanics Workbench")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(960, 600)

        # ── shared data manager ───────────────────────────────────
        self.dm = DataManager()

        # ── layout: sidebar | content ─────────────────────────────
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Show landing page by default
        self._select_page("landing")

    # ══════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ══════════════════════════════════════════════════════════════
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=170, corner_radius=0,
                                     fg_color="#0a0a1a")
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(len(NAV_ITEMS) + 2, weight=1)

        # App logo / title at the top
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=10, pady=(18, 8), sticky="ew")

        ctk.CTkLabel(
            logo_frame, text="⛏ GeoMech",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#00d4ff",
        ).pack(anchor="center")

        ctk.CTkLabel(
            logo_frame, text="Workbench  v1.0",
            font=ctk.CTkFont(size=10),
            text_color="#555555",
        ).pack(anchor="center")

        sep = ctk.CTkFrame(self.sidebar, height=2, fg_color="#1a1a2e")
        sep.grid(row=1, column=0, sticky="ew", padx=12, pady=6)

        # Navigation buttons
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.nav_rows: dict[str, int] = {}
        self._ctk_icons: dict[str, ctk.CTkImage] = {}

        for idx, item in enumerate(NAV_ITEMS):
            pil_img = get_icon(item["icon"], size=36)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(28, 28))
            self._ctk_icons[item["key"]] = ctk_img

            btn = ctk.CTkButton(
                self.sidebar,
                text=item["label"],
                image=ctk_img,
                compound="top",
                width=150, height=72,
                corner_radius=10,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="transparent",
                hover_color="#16213e",
                text_color="#cccccc",
                anchor="center",
                command=lambda k=item["key"]: self._select_page(k),
            )
            btn.grid(row=idx + 2, column=0, padx=10, pady=3)
            self.nav_buttons[item["key"]] = btn
            self.nav_rows[item["key"]] = idx + 2

    def _update_sidebar_visibility(self, active_key: str):
        """Show geomechanics nav items only while inside geomechanics pages."""
        show_geomech = active_key in self.GEOMECH_KEYS

        for key, btn in self.nav_buttons.items():
            if key in self.GEOMECH_KEYS and not show_geomech:
                btn.grid_remove()
            elif key == "seismic" and active_key != "seismic":
                btn.grid_remove()
            else:
                row = self.nav_rows[key]
                btn.grid(row=row, column=0, padx=10, pady=3)

    # ══════════════════════════════════════════════════════════════
    #  CONTENT AREA
    # ══════════════════════════════════════════════════════════════
    def _build_content_area(self):
        self.content = ctk.CTkFrame(self, fg_color="#0d1117", corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Pre-create pages (lazy dict)
        self.pages: dict[str, ctk.CTkFrame] = {}

    @staticmethod
    def _on_tk_error(exc_type, exc_value, exc_tb):
        """Print Tk callback exceptions to stderr instead of swallowing them."""
        traceback.print_exception(exc_type, exc_value, exc_tb)

    def _get_page(self, key: str) -> ctk.CTkFrame:
        if key in self.pages:
            return self.pages[key]

        try:
            if key == "landing":
                page = LandingPage(
                    self.content,
                    on_open_geomech=lambda: self._select_page("home"),
                    on_open_seismic=lambda: self._select_page("seismic"),
                )
            elif key == "home":
                page = HomePage(self.content, data_manager=self.dm)
            elif key == "stress":
                page = StressPage(self.content, data_manager=self.dm)
            elif key == "moduli":
                page = ModuliPage(self.content, data_manager=self.dm)
            elif key == "strength":
                page = StrengthPage(self.content, data_manager=self.dm)
            elif key == "seismic":
                page = SeismicPage(self.content)
            else:
                # Find matching nav item for title/color
                info = next((n for n in NAV_ITEMS if n["key"] == key), None)
                title = info["label"].replace("\n", " ") if info else key.upper()
                color = info["color"] if info else "#ffffff"
                icon_map = {
                    "stress": "🔴", "moduli": "📈", "rock": "🪨",
                    "strength": "💪", "wellbore": "🕳️",
                }
                page = PlaceholderPage(self.content, title=title,
                                        icon_text=icon_map.get(key, "📦"), color=color)
        except Exception:
            traceback.print_exc()
            # Fallback to a simple error frame
            page = ctk.CTkFrame(self.content, fg_color="#0d1117")
            ctk.CTkLabel(page, text=f"Error loading {key} page – see terminal",
                         text_color="#ff6b6b", font=ctk.CTkFont(size=16)).pack(
                             expand=True)

        self.pages[key] = page
        return page

    def _select_page(self, key: str):
        self._update_sidebar_visibility(key)

        # Hide all visible pages
        for p in self.pages.values():
            p.grid_forget()

        # Highlight active nav button
        for k, btn in self.nav_buttons.items():
            item = next(n for n in NAV_ITEMS if n["key"] == k)
            if k == key:
                btn.configure(fg_color="#0f3460", text_color=item["color"])
            else:
                btn.configure(fg_color="transparent", text_color="#cccccc")

        page = self._get_page(key)
        page.grid(row=0, column=0, sticky="nsew")


# ── Entry point ───────────────────────────────────────────────────
def main():
    app = GeomechanicsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
