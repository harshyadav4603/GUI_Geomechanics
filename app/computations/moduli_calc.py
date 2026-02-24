"""
Elastic Moduli Computation Engine  (Dynamic Output)
====================================================
Compute **dynamic** elastic moduli directly from sonic-log data,
plus acoustic / shear impedance and compressibility.

Formulas implemented
--------------------
**Dynamic moduli (from sonic logs):**

1. Poisson's Ratio:
       ν = (Vp² − 2·Vs²) / (2·(Vp² − Vs²))

2. Young's Modulus:
       E = ρ · Vs² · (3·Vp² − 4·Vs²) / (Vp² − Vs²)

3. Shear Modulus (Rigidity):
       G = ρ · Vs²

4. Bulk Modulus:
       K = ρ · (Vp² − 4/3 · Vs²)

5. Lamé's First Parameter:
       λ = ρ · (Vp² − 2·Vs²)

6. P-wave Modulus:
       M = ρ · Vp²

7. Acoustic Impedance:
       AI = ρ · Vp

8. Shear Impedance:
       SI = ρ · Vs

9. Compressibility:
       β = 1 / K

**Auxiliary ratios:**

10. Vp/Vs ratio
11. λρ (Lambda-Rho) = ρ·(Vp² − 2·Vs²)
12. μρ (Mu-Rho)    = ρ·Vs²
"""

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════
#  DYNAMIC MODULI
# ══════════════════════════════════════════════════════════════════

def dynamic_poisson(Vp: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """ν_dyn = (Vp² − 2Vs²) / 2(Vp² − Vs²)"""
    Vp2, Vs2 = Vp**2, Vs**2
    denom = 2.0 * (Vp2 - Vs2)
    with np.errstate(divide="ignore", invalid="ignore"):
        nu = (Vp2 - 2.0 * Vs2) / denom
    nu = np.where((nu >= 0) & (nu < 0.5), nu, np.nan)
    return nu


def dynamic_young(rho: np.ndarray, Vp: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """E_dyn = ρ · Vs² · (3Vp² − 4Vs²) / (Vp² − Vs²)"""
    Vp2, Vs2 = Vp**2, Vs**2
    denom = Vp2 - Vs2
    with np.errstate(divide="ignore", invalid="ignore"):
        E = rho * Vs2 * (3.0 * Vp2 - 4.0 * Vs2) / denom
    E = np.where(E > 0, E, np.nan)
    return E


def dynamic_shear(rho: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """G_dyn = ρ · Vs²"""
    return rho * (Vs**2)


def dynamic_bulk(rho: np.ndarray, Vp: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """K_dyn = ρ · (Vp² − 4/3 · Vs²)"""
    K = rho * (Vp**2 - (4.0 / 3.0) * Vs**2)
    K = np.where(K > 0, K, np.nan)
    return K


def dynamic_lame(rho: np.ndarray, Vp: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """λ_dyn = ρ · (Vp² − 2Vs²)"""
    return rho * (Vp**2 - 2.0 * Vs**2)


def pwave_modulus(rho: np.ndarray, Vp: np.ndarray) -> np.ndarray:
    """M = ρ · Vp²"""
    return rho * Vp**2


# ══════════════════════════════════════════════════════════════════
#  DYNAMIC → STATIC CONVERSION
# ══════════════════════════════════════════════════════════════════

def static_young(E_dyn_GPa: np.ndarray, ratio: float = 0.5) -> np.ndarray:
    """
    Static Young's Modulus via user-tunable ratio:
        E_sta = ratio × E_dyn   (both in GPa)

    Default ratio = 0.5 (commonly 0.3 – 0.7 depending on lithology).
    """
    E_sta = ratio * E_dyn_GPa
    E_sta = np.where(E_sta > 0, E_sta, np.nan)
    return E_sta


def static_poisson(nu_dyn: np.ndarray, factor: float = 1.0) -> np.ndarray:
    """
    Static Poisson's ratio.
    By default ν_sta ≈ ν_dyn (factor = 1.0).
    Some correlations use ν_sta = factor · ν_dyn.
    """
    nu_sta = factor * nu_dyn
    nu_sta = np.where((nu_sta >= 0) & (nu_sta < 0.5), nu_sta, np.nan)
    return nu_sta


def static_shear(E_sta: np.ndarray, nu_sta: np.ndarray) -> np.ndarray:
    """G_sta = E_sta / (2·(1 + ν_sta))"""
    with np.errstate(divide="ignore", invalid="ignore"):
        G = E_sta / (2.0 * (1.0 + nu_sta))
    return np.where(G > 0, G, np.nan)


def static_bulk(E_sta: np.ndarray, nu_sta: np.ndarray) -> np.ndarray:
    """K_sta = E_sta / (3·(1 − 2ν_sta))"""
    with np.errstate(divide="ignore", invalid="ignore"):
        K = E_sta / (3.0 * (1.0 - 2.0 * nu_sta))
    return np.where(K > 0, K, np.nan)


# ══════════════════════════════════════════════════════════════════
#  IMPEDANCES & COMPRESSIBILITY
# ══════════════════════════════════════════════════════════════════

def acoustic_impedance(rho: np.ndarray, Vp: np.ndarray) -> np.ndarray:
    """Acoustic Impedance  AI = ρ · Vp   (kg/m²·s  =  Rayl)"""
    return rho * Vp


def shear_impedance(rho: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """Shear Impedance  SI = ρ · Vs   (kg/m²·s  =  Rayl)"""
    return rho * Vs


def compressibility(K: np.ndarray) -> np.ndarray:
    """Compressibility  β = 1 / K   (1/GPa when K in GPa)"""
    with np.errstate(divide="ignore", invalid="ignore"):
        beta = 1.0 / K
    return np.where(np.isfinite(beta) & (beta > 0), beta, np.nan)


# ══════════════════════════════════════════════════════════════════
#  AUXILIARY RATIOS
# ══════════════════════════════════════════════════════════════════

def vp_vs_ratio(Vp: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """Vp/Vs ratio."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(Vs != 0, Vp / Vs, np.nan)


def lambda_rho(rho: np.ndarray, Vp: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """λρ = ρ · (Vp² − 2·Vs²)"""
    return rho * (Vp**2 - 2.0 * Vs**2)


def mu_rho(rho: np.ndarray, Vs: np.ndarray) -> np.ndarray:
    """μρ = ρ · Vs²"""
    return rho * Vs**2


# ══════════════════════════════════════════════════════════════════
#  MASTER FUNCTION
# ══════════════════════════════════════════════════════════════════

def compute_all_moduli(
    depth: np.ndarray,
    rho: np.ndarray,
    Vp: np.ndarray,
    Vs: np.ndarray,
    unit_system: str = "SI",
) -> pd.DataFrame:
    """
    Compute dynamic elastic moduli, impedances, and compressibility.

    Parameters
    ----------
    depth : depth array.
    rho   : bulk density (kg/m³ for SI, g/cc for FIELD).
    Vp    : P-wave velocity (m/s for SI, km/s for SI_KMS, ft/s for FIELD).
    Vs    : S-wave velocity (m/s for SI, km/s for SI_KMS, ft/s for FIELD).
    unit_system : 'SI', 'SI_KMS', or 'FIELD'.

    Returns
    -------
    DataFrame with dynamic moduli, impedances, compressibility,
    and auxiliary ratio columns.
    """
    depth = np.asarray(depth, dtype=float)
    rho = np.asarray(rho, dtype=float)
    Vp = np.asarray(Vp, dtype=float)
    Vs = np.asarray(Vs, dtype=float)

    # For FIELD units (g/cc, ft/s) convert to SI for moduli calc,
    # then present results in GPa / appropriate field units.
    if unit_system == "FIELD":
        # g/cc → kg/m³ ;  ft/s → m/s
        rho_si = rho * 1000.0
        Vp_si = Vp * 0.3048
        Vs_si = Vs * 0.3048
    elif unit_system == "SI_KMS":
        # Density already kg/m³;  km/s → m/s
        rho_si = rho
        Vp_si = Vp * 1000.0
        Vs_si = Vs * 1000.0
    else:
        rho_si = rho
        Vp_si = Vp
        Vs_si = Vs

    # ── Dynamic moduli (Pa) ───────────────────────────────────────
    nu    = dynamic_poisson(Vp_si, Vs_si)
    E     = dynamic_young(rho_si, Vp_si, Vs_si)
    G     = dynamic_shear(rho_si, Vs_si)
    K     = dynamic_bulk(rho_si, Vp_si, Vs_si)
    lam   = dynamic_lame(rho_si, Vp_si, Vs_si)
    M     = pwave_modulus(rho_si, Vp_si)

    to_GPa = 1e-9
    E_GPa   = E * to_GPa
    G_GPa   = G * to_GPa
    K_GPa   = K * to_GPa
    lam_GPa = lam * to_GPa
    M_GPa   = M * to_GPa

    # ── Impedances ────────────────────────────────────────────────
    AI = acoustic_impedance(rho_si, Vp_si)
    SI_val = shear_impedance(rho_si, Vs_si)


    # ── Compressibility ───────────────────────────────────────────
    beta = compressibility(K_GPa)

    # ── Auxiliary ─────────────────────────────────────────────────
    vpvs = vp_vs_ratio(Vp_si, Vs_si)
    LR   = lambda_rho(rho_si, Vp_si, Vs_si)
    MR   = mu_rho(rho_si, Vs_si)

    return pd.DataFrame({
        "Depth":               depth,
        "Density":             rho,
        "Vp":                  Vp,
        "Vs":                  Vs,
        "Vp/Vs":               vpvs,
        # Dynamic moduli
        "ν":                   nu,
        "E (GPa)":             E_GPa,
        "G (GPa)":             G_GPa,
        "K (GPa)":             K_GPa,
        "λ (GPa)":             lam_GPa,
        "M (GPa)":             M_GPa,
        # Impedances
        "Acoustic Impedance":  AI,
        "Shear Impedance":     SI_val,
        # Compressibility
        "β (1/GPa)":           beta,
    })
