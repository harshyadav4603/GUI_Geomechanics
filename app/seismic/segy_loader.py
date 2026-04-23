"""SEG-Y loading helpers using segyio."""

from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import segyio
except Exception:  # pragma: no cover - optional dependency runtime guard
    segyio = None


class SegyLoadError(RuntimeError):
    """Raised when a SEG-Y file cannot be loaded into a seismic cube."""


def _safe_numeric_array(values, dtype) -> np.ndarray:
    """Convert SEG-Y metadata vectors to numeric arrays, tolerating None."""
    if values is None:
        return np.asarray([], dtype=dtype)
    try:
        arr = np.asarray(values)
        if arr.size == 0:
            return np.asarray([], dtype=dtype)
        return arr.astype(dtype, copy=False)
    except Exception:
        return np.asarray([], dtype=dtype)


def _load_trace_fallback(segy_file) -> np.ndarray:
    """Fallback loader for SEG-Y files with missing or broken geometry."""
    trace_count_raw = getattr(segy_file, "tracecount", 0)
    trace_count = int(trace_count_raw) if trace_count_raw is not None else 0

    samples = getattr(segy_file, "samples", None)
    if samples is None:
        if trace_count > 0:
            first_trace = np.asarray(segy_file.trace[0], dtype=np.float32)
            sample_count = int(first_trace.shape[0])
        else:
            sample_count = 0
    else:
        sample_count = len(samples)

    cube = np.zeros((1, trace_count, sample_count), dtype=np.float32)

    for idx in range(trace_count):
        cube[0, idx, :] = np.asarray(segy_file.trace[idx], dtype=np.float32)
    return cube


def load_segy_cube(file_path: str) -> tuple[np.ndarray, dict]:
    """Load a seismic cube from a SEG-Y file.

    Returns:
      cube: ndarray with shape (inline, crossline, sample)
      metadata: dictionary with dimensions and coordinate arrays
    """
    if segyio is None:
        raise SegyLoadError(
            "segyio is not installed. Install it with: pip install segyio"
        )

    path = Path(file_path)
    if not path.exists():
        raise SegyLoadError(f"SEG-Y file not found: {file_path}")

    try:
        with segyio.open(str(path), "r", strict=False, ignore_geometry=True) as sf:
            sf.mmap()
            sample_axis = _safe_numeric_array(getattr(sf, "samples", None), np.float32)

            ilines = _safe_numeric_array(getattr(sf, "ilines", None), np.int32)
            xlines = _safe_numeric_array(getattr(sf, "xlines", None), np.int32)

            cube = None
            if ilines.size > 0 and xlines.size > 0:
                try:
                    cube = np.asarray(segyio.tools.cube(sf), dtype=np.float32)
                except Exception:
                    cube = None

            # Some SEG-Y files may return cube axes swapped; normalize to
            # (inline, crossline, sample) whenever geometry lengths indicate it.
            if cube is not None and cube.ndim == 3 and ilines.size > 0 and xlines.size > 0:
                shape0, shape1 = int(cube.shape[0]), int(cube.shape[1])
                il_count, xl_count = int(ilines.size), int(xlines.size)
                normal_match = shape0 == il_count and shape1 == xl_count
                swapped_match = shape0 == xl_count and shape1 == il_count
                if swapped_match and not normal_match:
                    cube = np.transpose(cube, (1, 0, 2))

            if cube is None or cube.ndim != 3:
                cube = _load_trace_fallback(sf)
                ilines = np.arange(cube.shape[0], dtype=np.int32)
                xlines = np.arange(cube.shape[1], dtype=np.int32)

            metadata = {
                "source": "segy",
                "path": str(path),
                "shape": tuple(int(v) for v in cube.shape),
                "inline_count": int(cube.shape[0]),
                "crossline_count": int(cube.shape[1]),
                "sample_count": int(cube.shape[2]),
                "inline_indices": ilines if ilines.size else np.arange(cube.shape[0], dtype=np.int32),
                "crossline_indices": xlines if xlines.size else np.arange(cube.shape[1], dtype=np.int32),
                "samples": sample_axis if sample_axis.size else np.arange(cube.shape[2], dtype=np.float32),
            }
            return cube, metadata
    except SegyLoadError:
        raise
    except Exception as exc:
        raise SegyLoadError(f"Could not read SEG-Y data: {exc}") from exc
