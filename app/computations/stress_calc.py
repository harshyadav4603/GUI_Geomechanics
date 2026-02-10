"""
Stress Computation Engine
==========================
All geomechanical stress formulas live here, independent of the GUI.

Formulas implemented
--------------------
1. Overburden / Vertical Stress:
       Sv(z) = ∫₀ᶻ ρ(z′) · g · dz′

2. Vertical Stress Gradient:
       dSv/dz  (numerical central-difference derivative)

3. Effective Vertical Stress:
       Sv_eff = Sv − Pp

4. Pore Pressure from user column (or hydrostatic estimate):
       Pp_hydro = ρ_water · g · z

5. Dynamic Poisson's Ratio from sonic velocities:
       ν = (Vp² − 2·Vs²) / (2·(Vp² − Vs²))

6. Minimum Horizontal Stress (Eaton's model):
       Shmin = (ν / (1 − ν)) · (Sv − Pp) + Pp  +  σ_tectonic

7. Maximum Horizontal Stress (bi-axial strain model):
       SHmax = (ν / (1 − ν)) · (Sv − Pp)  ·  (1 + ε_ratio)  +  Pp  +  σ_tectonic

8. Effective Shmin / SHmax:
       Shmin_eff = Shmin − Pp
       SHmax_eff = SHmax − Pp

9. Stress Ratios (K₀):
       K0_min = Shmin / Sv
       K0_max = SHmax / Sv
"""

import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid


G = 9.80665  # m/s² – gravitational acceleration


# ── Dynamic Poisson's Ratio from Vp / Vs ─────────────────────────

def compute_dynamic_poisson(Vp: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """
    Dynamic Poisson's ratio from compressional and shear wave velocities.

        ν_dyn = (Vp² − 2·Vs²) / (2·(Vp² − Vs²))

    Parameters
    ----------
    Vp : P-wave velocity array (m/s or ft/s – units cancel).
    Vs : S-wave velocity array.

    Returns
    -------
    nu : Poisson's ratio array (dimensionless, 0 – 0.5 physical range).
         Invalid values (Vp ≤ Vs, division by zero) are clipped / set to NaN.
    """
    Vp = np.asarray(Vp, dtype=float)
    Vs = np.asarray(Vs, dtype=float)

    Vp2 = Vp ** 2
    Vs2 = Vs ** 2

    denom = 2.0 * (Vp2 - Vs2)
    with np.errstate(divide="ignore", invalid="ignore"):
        nu = (Vp2 - 2.0 * Vs2) / denom

    # Physical bounds: 0 ≤ ν < 0.5  (set out-of-range to NaN)
    nu = np.where((nu >= 0) & (nu < 0.5), nu, np.nan)
    return nu


def compute_overburden(depth: np.ndarray, density: np.ndarray) -> np.ndarray:
    """
    Overburden (vertical) stress  Sv = ∫₀ᶻ ρ(z)·g·dz

    Parameters
    ----------
    depth   : 1-D array of measured depths (m or ft – consistent units).
    density : 1-D array of bulk density  (kg/m³  if SI, else see note).

    Returns
    -------
    Sv : 1-D array (same length as depth) in Pa  (if SI inputs).
         First value set = density[0] * g * depth[0].
    """
    integrand = density * G  # ρ·g  (Pa/m)
    Sv = cumulative_trapezoid(integrand, depth, initial=0)
    # At z=0 the integral is 0; replace with surface estimate
    if len(Sv) > 0:
        Sv[0] = density[0] * G * depth[0]
    return Sv


def compute_overburden_ppg(depth_ft: np.ndarray, density_gcc: np.ndarray) -> np.ndarray:
    """
    Overburden stress in **psi** from depth (ft) and density (g/cc).

    Conversion:
        Sv(psi) = 0.4335 · ∫₀ᶻ ρ(z) dz   (with ρ in g/cc, z in ft)
    """
    integrand = 0.4335 * density_gcc  # psi/ft
    Sv = cumulative_trapezoid(integrand, depth_ft, initial=0)
    if len(Sv) > 0:
        Sv[0] = 0.4335 * density_gcc[0] * depth_ft[0]
    return Sv


def compute_vertical_stress_gradient(depth: np.ndarray, Sv: np.ndarray) -> np.ndarray:
    """
    Numerical gradient  dSv/dz  using central differences.

    Returns array same length as depth.
    """
    return np.gradient(Sv, depth)


def compute_hydrostatic_pore_pressure(depth: np.ndarray,
                                       water_density: float = 1025.0) -> np.ndarray:
    """
    Hydrostatic pore pressure:  Pp = ρ_w · g · z

    Parameters
    ----------
    depth         : depth array (m).
    water_density : formation water density, default 1025 kg/m³.

    Returns Pp in Pa.
    """
    return water_density * G * depth


def compute_hydrostatic_pp_psi(depth_ft: np.ndarray,
                                water_grad: float = 0.433) -> np.ndarray:
    """Hydrostatic Pp in psi = water_grad · depth_ft."""
    return water_grad * depth_ft


def compute_effective_vertical_stress(Sv: np.ndarray, Pp: np.ndarray) -> np.ndarray:
    """
    Effective vertical stress:  Sv_eff = Sv − Pp
    (Terzaghi's effective-stress principle)
    """
    return Sv - Pp


def compute_shmin(Sv: np.ndarray, Pp: np.ndarray,
                  poisson: float | np.ndarray = 0.25,
                  tectonic: float = 0.0) -> np.ndarray:
    """
    Minimum horizontal stress – Eaton's / uniaxial-strain model:

        Shmin = ν/(1−ν) · (Sv − Pp) + Pp + σ_tectonic

    Parameters
    ----------
    Sv       : vertical (overburden) stress array.
    Pp       : pore-pressure array.
    poisson  : Poisson's ratio (scalar or array).
    tectonic : additional tectonic stress component.
    """
    nu = np.asarray(poisson)
    return (nu / (1.0 - nu)) * (Sv - Pp) + Pp + tectonic


def compute_shmax(Sv: np.ndarray, Pp: np.ndarray,
                  poisson: float | np.ndarray = 0.25,
                  tectonic: float = 0.0,
                  strain_ratio: float = 1.0) -> np.ndarray:
    """
    Maximum horizontal stress – bi-axial strain model:

        SHmax = ν/(1−ν) · (Sv − Pp) · (1 + ε_ratio) + Pp + σ_tectonic

    strain_ratio = 1.0 gives SHmax ≈ 2·(Shmin − Pp) + Pp  (isotropic).
    Increase for compressional tectonic regimes.
    """
    nu = np.asarray(poisson)
    return (nu / (1.0 - nu)) * (Sv - Pp) * (1.0 + strain_ratio) + Pp + tectonic


def compute_stress_ratios(Sv: np.ndarray, Shmin: np.ndarray,
                          SHmax: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Stress ratios (K₀):
        K0_min = Shmin / Sv
        K0_max = SHmax / Sv
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        K0_min = np.where(Sv != 0, Shmin / Sv, np.nan)
        K0_max = np.where(Sv != 0, SHmax / Sv, np.nan)
    return K0_min, K0_max


# ── Convenience: run all at once ──────────────────────────────────

def compute_all_stresses(depth: np.ndarray,
                         density: np.ndarray,
                         Pp: np.ndarray | None = None,
                         Vp: np.ndarray | None = None,
                         Vs: np.ndarray | None = None,
                         poisson: float | np.ndarray = 0.25,
                         tectonic: float = 0.0,
                         strain_ratio: float = 1.0,
                         unit_system: str = "SI") -> pd.DataFrame:
    """
    Master function – computes every stress column and returns a DataFrame.

    Parameters
    ----------
    depth        : depth array.
    density      : bulk density array.
    Pp           : pore-pressure array (if None, hydrostatic is used).
    Vp           : P-wave velocity array (if provided with Vs, ν is computed).
    Vs           : S-wave velocity array.
    poisson      : fallback Poisson's ratio (used ONLY if Vp/Vs not given).
    tectonic     : tectonic stress addition (same unit as stress).
    strain_ratio : ε_H/ε_h  for SHmax model.
    unit_system  : 'SI' (m, kg/m³ → Pa) or 'FIELD' (ft, g/cc → psi).

    Returns
    -------
    DataFrame with columns including Vp, Vs, Poisson's Ratio (if sonic
    data provided), plus all stress columns.
    """
    depth = np.asarray(depth, dtype=float)
    density = np.asarray(density, dtype=float)

    # ── Poisson's ratio: prefer Vp/Vs calculation ─────────────────
    nu_from_sonic = False
    if Vp is not None and Vs is not None:
        Vp = np.asarray(Vp, dtype=float)
        Vs = np.asarray(Vs, dtype=float)
        poisson = compute_dynamic_poisson(Vp, Vs)
        # Fill any NaN from invalid Vp/Vs with scalar fallback
        fallback = 0.25
        poisson = np.where(np.isfinite(poisson), poisson, fallback)
        nu_from_sonic = True

    if unit_system == "FIELD":
        Sv = compute_overburden_ppg(depth, density)
        if Pp is None:
            Pp = compute_hydrostatic_pp_psi(depth)
    else:
        Sv = compute_overburden(depth, density)
        if Pp is None:
            Pp = compute_hydrostatic_pore_pressure(depth)

    Pp = np.asarray(Pp, dtype=float)
    Sv_grad = compute_vertical_stress_gradient(depth, Sv)
    Sv_eff = compute_effective_vertical_stress(Sv, Pp)
    Shmin = compute_shmin(Sv, Pp, poisson, tectonic)
    SHmax = compute_shmax(Sv, Pp, poisson, tectonic, strain_ratio)
    Shmin_eff = Shmin - Pp
    SHmax_eff = SHmax - Pp
    K0_min, K0_max = compute_stress_ratios(Sv, Shmin, SHmax)

    result = {
        "Depth": depth,
        "Density": density,
    }

    # Include sonic / Poisson columns when computed from Vp/Vs
    if nu_from_sonic:
        result["Vp"] = Vp
        result["Vs"] = Vs
        result["Poisson Ratio (dynamic)"] = poisson
    else:
        # Scalar or user-column Poisson's – broadcast to array
        nu_arr = np.broadcast_to(np.asarray(poisson), depth.shape)
        result["Poisson Ratio"] = nu_arr

    result.update({
        "Sv (Overburden)": Sv,
        "Sv Gradient": Sv_grad,
        "Pp (Pore Pressure)": Pp,
        "Sv_eff (Effective)": Sv_eff,
        "Shmin": Shmin,
        "SHmax": SHmax,
        "Shmin_eff": Shmin_eff,
        "SHmax_eff": SHmax_eff,
        "K0_min": K0_min,
        "K0_max": K0_max,
    })

    return pd.DataFrame(result)
