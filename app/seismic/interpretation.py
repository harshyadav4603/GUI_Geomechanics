"""Interpretation data model for horizon and fault picks."""

from __future__ import annotations

import csv
from pathlib import Path


class InterpretationModel:
    """Stores and exports interpretation picks for horizons and faults."""

    def __init__(self):
        self.horizons: list[list[tuple[float, float]]] = [[]]
        self.faults: list[list[tuple[float, float]]] = [[]]
        self.active_horizon = 0

    def add_horizon(self):
        self.horizons.append([])
        self.active_horizon = len(self.horizons) - 1

    def set_active_horizon(self, index: int):
        if 0 <= index < len(self.horizons):
            self.active_horizon = index

    def add_horizon_point(self, x: float, y: float):
        self.horizons[self.active_horizon].append((x, y))

    def add_fault_point(self, x: float, y: float):
        if not self.faults:
            self.faults = [[]]
        self.faults[-1].append((x, y))

    def new_fault_segment(self):
        if self.faults and len(self.faults[-1]) == 0:
            return
        self.faults.append([])

    def clear(self):
        self.horizons = [[]]
        self.faults = [[]]
        self.active_horizon = 0

    def export_csv(self, file_path: str):
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["type", "x", "y"])

            for points in self.horizons:
                for x, y in points:
                    writer.writerow(["horizon", f"{x:.3f}", f"{y:.3f}"])

            for points in self.faults:
                for x, y in points:
                    writer.writerow(["fault", f"{x:.3f}", f"{y:.3f}"])
