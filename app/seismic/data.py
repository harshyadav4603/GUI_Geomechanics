"""Synthetic seismic cube generation utilities."""

from __future__ import annotations

import numpy as np


def generate_synthetic_cube(
    inline_count: int = 80,
    crossline_count: int = 120,
    sample_count: int = 300,
    noise_level: float = 0.12,
    seed: int | None = 7,
) -> tuple[np.ndarray, dict]:
    """Generate a synthetic seismic cube with smooth reflectors and noise.

    The cube shape follows standard seismic indexing:
    (inline, crossline, time_sample).
    """
    rng = np.random.default_rng(seed)

    il = np.linspace(0.0, 1.0, inline_count, dtype=np.float32)
    xl = np.linspace(0.0, 1.0, crossline_count, dtype=np.float32)
    t = np.arange(sample_count, dtype=np.float32)

    ii, xx = np.meshgrid(il, xl, indexing="ij")
    cube = np.zeros((inline_count, crossline_count, sample_count), dtype=np.float32)

    reflector_params = [
        (45.0, 10.0, 8.0, 1.0, 0.9, 7.0),
        (95.0, 14.0, 10.0, -0.9, 1.4, 8.0),
        (150.0, 18.0, 12.0, 0.7, 2.1, 9.0),
        (215.0, 15.0, 10.0, -0.6, 2.8, 10.0),
    ]

    t_grid = t[None, None, :]
    for base_t, amp_i, amp_x, polarity, phase, sigma in reflector_params:
        horizon = base_t + amp_i * np.sin(2.0 * np.pi * (ii + phase))
        horizon = horizon + amp_x * np.cos(2.0 * np.pi * (1.3 * xx + 0.35 * phase))
        wavelet = np.exp(-((t_grid - horizon[:, :, None]) ** 2) / (2.0 * sigma**2))
        cube += (polarity * wavelet).astype(np.float32)

    # Add a weak dipping event to make interpretation less trivial.
    dip_plane = 0.25 * np.exp(-((t_grid - (40 + 120 * ii[:, :, None])) ** 2) / (2.0 * 14.0**2))
    cube += dip_plane.astype(np.float32)

    noise = rng.normal(0.0, noise_level, size=cube.shape).astype(np.float32)
    cube += noise

    max_abs = float(np.max(np.abs(cube)))
    if max_abs > 0:
        cube /= max_abs

    samples = np.arange(sample_count, dtype=np.float32)
    metadata = {
        "source": "synthetic",
        "shape": cube.shape,
        "inline_count": inline_count,
        "crossline_count": crossline_count,
        "sample_count": sample_count,
        "inline_indices": np.arange(inline_count, dtype=np.int32),
        "crossline_indices": np.arange(crossline_count, dtype=np.int32),
        "samples": samples,
    }
    return cube, metadata
