"""
Strength & Failure Computation Engine
=======================================
Compute rock-strength and failure parameters from sonic / density logs.

Parameters implemented
----------------------

1. Brittleness Index  (Rickman et al. 2008):
       BI = 0.5 × ( (E − E_min)/(E_max − E_min)
                   + (ν − ν_max)/(ν_min − ν_max) )
   where E = dynamic Young's Modulus, ν = dynamic Poisson's ratio.
   BI ranges 0 (ductile) → 1 (brittle).

2. Internal Friction Angle  (Lal 1999):
       φ = asin( (Vp − 1000) / (Vp + 1000) )         [Vp in m/s]
   Alternate (Chang et al. 2006):
       φ = 57.8 − 105 · ν

3. UCS — Unconfined Compressive Strength (Bradford et al. 1998):
       UCS = 2·c·cos(φ) / (1 − sin(φ))
   where c (cohesion) is derived from the Mohr–Coulomb criterion
   (user-supplied or estimated from empirical correlations).

4. Fracture Initiation Pressure  (Hubbert & Willis):
       Pfrac = 3·Shmin − SHmax − Pp + T
   where T = tensile strength (user parameter, default 0 MPa).

5. Mohr–Coulomb Failure Criterion:
       τ = c + σ_n · tan(φ)
   The module computes:
     • Cohesion  c  from UCS and φ :
           c = UCS · (1 − sin(φ)) / (2 · cos(φ))
     • Failure angle  θ = 45° + φ/2
     • Coulomb Stress  σ_1_fail = UCS + σ_3 · tan²(45° + φ/2)
       (maximum principal stress at failure for a given confining stress σ_3)
"""

import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid


G_ACC = 9.80665  # m/s²


# ══════════════════════════════════════════════════════════════════
#  BRITTLENESS INDEX
# ══════════════════════════════════════════════════════════════════

def brittleness_index(E: np.ndarray, nu: np.ndarray) -> np.ndarray:
    """
    Brittleness Index (Rickman et al. 2008).

    BI = 0.5 × [ (E − E_min)/(E_max − E_min)
                + (ν − ν_max)/(ν_min − ν_max) ]

    Returns values in [0, 1].  1 = most brittle.
    """
    E_min, E_max = np.nanmin(E), np.nanmax(E)
    nu_min, nu_max = np.nanmin(nu), np.nanmax(nu)

    with np.errstate(divide="ignore", invalid="ignore"):
        E_norm = (E - E_min) / (E_max - E_min) if E_max != E_min else np.zeros_like(E)
        nu_norm = (nu - nu_max) / (nu_min - nu_max) if nu_min != nu_max else np.zeros_like(nu)

    bi = 0.5 * (E_norm + nu_norm)
    bi = np.clip(bi, 0.0, 1.0)
    return bi


# ══════════════════════════════════════════════════════════════════
#  FRICTION ANGLE
# ══════════════════════════════════════════════════════════════════

def friction_angle_lal(Vp_ms: np.ndarray) -> np.ndarray:
    """
    Internal friction angle — Lal (1999):
        φ = asin( (Vp − 1000) / (Vp + 1000) )    [Vp in m/s]

    Returns φ in degrees.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        arg = (Vp_ms - 1000.0) / (Vp_ms + 1000.0)
    arg = np.clip(arg, -1.0, 1.0)
    phi = np.degrees(np.arcsin(arg))
    phi = np.where(phi > 0, phi, np.nan)   # physical: φ > 0
    return phi


def friction_angle_chang(nu: np.ndarray) -> np.ndarray:
    """
    Internal friction angle — Chang et al. (2006):
        φ = 57.8 − 105 × ν     [degrees]
    """
    phi = 57.8 - 105.0 * nu
    phi = np.where((phi > 0) & (phi < 90), phi, np.nan)
    return phi


# ══════════════════════════════════════════════════════════════════
#  MOHR–COULOMB  (UCS, cohesion, failure stress)
# ══════════════════════════════════════════════════════════════════

def ucs_from_E(E_GPa: np.ndarray) -> np.ndarray:
    """
    UCS empirical estimate (Bradford et al. 1998 – sandstone):
        UCS = 2.28 + 4.1089 · E   (E in GPa, UCS in MPa)
    """
    ucs = 2.28 + 4.1089 * E_GPa
    return np.where(ucs > 0, ucs, np.nan)


def cohesion_from_ucs(UCS: np.ndarray, phi_deg: np.ndarray) -> np.ndarray:
    """
    Mohr–Coulomb cohesion from UCS and friction angle:
        c = UCS · (1 − sin φ) / (2 · cos φ)
    """
    phi_rad = np.radians(phi_deg)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = UCS * (1.0 - np.sin(phi_rad)) / (2.0 * np.cos(phi_rad))
    return np.where(c > 0, c, np.nan)


def failure_angle(phi_deg: np.ndarray) -> np.ndarray:
    """Failure angle  θ = 45 + φ/2  (degrees)."""
    return 45.0 + phi_deg / 2.0


def coulomb_failure_stress(UCS: np.ndarray, phi_deg: np.ndarray,
                           sigma3: float = 0.0) -> np.ndarray:
    """
    Maximum principal stress at failure (Mohr–Coulomb):
        σ₁_fail = UCS + σ₃ · tan²(45° + φ/2)
    """
    theta = np.radians(45.0 + phi_deg / 2.0)
    tan2 = np.tan(theta) ** 2
    return UCS + sigma3 * tan2


# ══════════════════════════════════════════════════════════════════
#  FRACTURE INITIATION PRESSURE
# ══════════════════════════════════════════════════════════════════

def fracture_initiation_pressure(
    Shmin: np.ndarray,
    SHmax: np.ndarray,
    Pp: np.ndarray,
    T: float = 0.0,
) -> np.ndarray:
    """
    Fracture initiation pressure (Hubbert & Willis):
        Pfrac = 3·Shmin − SHmax − Pp + T

    Parameters
    ----------
    Shmin  : minimum horizontal stress (MPa or same unit).
    SHmax  : maximum horizontal stress.
    Pp     : pore pressure.
    T      : tensile strength (default 0).
    """
    return 3.0 * Shmin - SHmax - Pp + T


# ══════════════════════════════════════════════════════════════════
#  HELPER — horizontal stresses (Eaton) for Pfrac calc
# ══════════════════════════════════════════════════════════════════

def _compute_stresses(depth: np.ndarray, rho_si: np.ndarray,
                      nu: np.ndarray, rho_water: float = 1025.0
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return Sv, Pp, Shmin, SHmax in Pa then convert to MPa."""
    # Overburden
    integrand = rho_si * G_ACC
    Sv_inc = cumulative_trapezoid(integrand, depth, initial=0)
    # Add overburden above first measurement (assume constant ρ from surface)
    Sv_above = rho_si[0] * G_ACC * depth[0]
    Sv = Sv_inc + Sv_above
    Sv_MPa = Sv * 1e-6

    # Hydrostatic Pp
    Pp_MPa = rho_water * G_ACC * depth * 1e-6

    # Eaton Shmin
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = nu / (1.0 - nu)
    Shmin_MPa = ratio * (Sv_MPa - Pp_MPa) + Pp_MPa

    # SHmax (biaxial, ε_ratio = 0.0)
    SHmax_MPa = ratio * (Sv_MPa - Pp_MPa) + Pp_MPa  # same as Shmin when ε=0

    return Sv_MPa, Pp_MPa, Shmin_MPa, SHmax_MPa


# ══════════════════════════════════════════════════════════════════
#  MASTER FUNCTION
# ══════════════════════════════════════════════════════════════════

def compute_all_strength(
    depth: np.ndarray,
    rho: np.ndarray,
    Vp: np.ndarray,
    Vs: np.ndarray,
    unit_system: str = "SI",
    tensile_strength: float = 0.0,
    confining_stress: float = 0.0,
    friction_method: str = "Lal",
) -> pd.DataFrame:
    """
    Compute strength & failure parameters.

    Parameters
    ----------
    depth : depth array.
    rho   : bulk density (kg/m³ for SI, g/cc for FIELD).
    Vp    : P-wave velocity (m/s | km/s | ft/s).
    Vs    : S-wave velocity (m/s | km/s | ft/s).
    unit_system : 'SI', 'SI_KMS', or 'FIELD'.
    tensile_strength : T in MPa for fracture-initiation calc.
    confining_stress : σ₃ in MPa for Coulomb failure stress.
    friction_method : 'Lal' or 'Chang'.

    Returns
    -------
    DataFrame with strength / failure columns.
    """
    depth = np.asarray(depth, dtype=float)
    rho   = np.asarray(rho, dtype=float)
    Vp    = np.asarray(Vp, dtype=float)
    Vs    = np.asarray(Vs, dtype=float)

    # ── unit conversion to SI (m, kg/m³, m/s) ────────────────────
    if unit_system == "FIELD":
        rho_si = rho * 1000.0
        Vp_si  = Vp * 0.3048
        Vs_si  = Vs * 0.3048
        depth_m = depth * 0.3048
    elif unit_system == "SI_KMS":
        rho_si  = rho
        Vp_si   = Vp * 1000.0
        Vs_si   = Vs * 1000.0
        depth_m = depth
    else:  # SI  (m, kg/m³, m/s)
        rho_si  = rho
        Vp_si   = Vp
        Vs_si   = Vs
        depth_m = depth

    # ── dynamic moduli (for BI) ───────────────────────────────────
    Vp2, Vs2 = Vp_si ** 2, Vs_si ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        nu = (Vp2 - 2.0 * Vs2) / (2.0 * (Vp2 - Vs2))
    nu = np.where((nu >= 0) & (nu < 0.5), nu, np.nan)

    with np.errstate(divide="ignore", invalid="ignore"):
        E = rho_si * Vs2 * (3.0 * Vp2 - 4.0 * Vs2) / (Vp2 - Vs2)
    E = np.where(E > 0, E, np.nan)
    E_GPa = E * 1e-9

    # ── Brittleness Index ─────────────────────────────────────────
    bi = brittleness_index(E_GPa, nu)

    # ── Friction angle ────────────────────────────────────────────
    if friction_method == "Chang":
        phi = friction_angle_chang(nu)
    else:
        phi = friction_angle_lal(Vp_si)

    # ── UCS & Mohr–Coulomb ────────────────────────────────────────
    ucs = ucs_from_E(E_GPa)
    c   = cohesion_from_ucs(ucs, phi)
    theta = failure_angle(phi)
    sigma1_fail = coulomb_failure_stress(ucs, phi, sigma3=confining_stress)

    # ── Stresses for fracture-initiation pressure ─────────────────
    Sv_MPa, Pp_MPa, Shmin_MPa, SHmax_MPa = _compute_stresses(
        depth_m, rho_si, nu)
    Pfrac = fracture_initiation_pressure(Shmin_MPa, SHmax_MPa, Pp_MPa,
                                          T=tensile_strength)

    return pd.DataFrame({
        "Depth":                depth,
        "Density":              rho,
        "Vp":                   Vp,
        "Vs":                   Vs,
        # Dynamic (for reference)
        "ν":                    nu,
        "E (GPa)":              E_GPa,
        # Strength parameters
        "Brittleness Index":    bi,
        "φ (deg)":              phi,
        "UCS (MPa)":            ucs,
        "Cohesion (MPa)":       c,
        "Failure Angle (deg)":  theta,
        "σ₁_fail (MPa)":       sigma1_fail,
        # Fracture initiation
        "Sv (MPa)":             Sv_MPa,
        "Pp (MPa)":             Pp_MPa,
        "Shmin (MPa)":          Shmin_MPa,
        "SHmax (MPa)":          SHmax_MPa,
        "Pfrac (MPa)":          Pfrac,
    })
