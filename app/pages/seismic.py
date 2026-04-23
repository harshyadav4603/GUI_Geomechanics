"""Seismic page hosting the interpretation viewer."""

import customtkinter as ctk

from app.seismic.viewer import SeismicViewerFrame


class SeismicPage(ctk.CTkFrame):
    """Page wrapper for the seismic interpretation system."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        viewer = SeismicViewerFrame(self)
        viewer.grid(row=0, column=0, sticky="nsew")
