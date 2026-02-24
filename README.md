# Geomechanical Calculations: Step-by-Step Guide

This project calculates important rock and stress properties from well log data. Each calculation is explained step by step, with both the formula and a plain English explanation. The order of calculations matches the code logic.

---

## 1. Dynamic Elastic Moduli (Rock Stiffness Properties)

**Order of Calculations:**
1. Poisson's Ratio
2. Young's Modulus
3. Shear Modulus
4. Bulk Modulus
5. Lamé’s First Parameter
6. P-wave Modulus
7. Acoustic Impedance
8. Shear Impedance
9. Compressibility
10. Vp/Vs Ratio, Lambda-Rho, Mu-Rho

- **Poisson's Ratio**
  - Formula:  \( \nu = \frac{V_p^2 - 2V_s^2}{2(V_p^2 - V_s^2)} \)
  - Explanation: Tells us how much the rock will expand sideways when squeezed. It’s worked out using the speeds of sound waves (P-wave and S-wave) through the rock.

- **Young's Modulus**
  - Formula:  \( E = \rho V_s^2 \frac{3V_p^2 - 4V_s^2}{V_p^2 - Vs^2} \)
  - Explanation: Measures how stiff the rock is. A higher value means the rock is harder to stretch or compress.

- **Shear Modulus**
  - Formula:  \( G = \rho V_s^2 \)
  - Explanation: Shows how much the rock resists being twisted or sheared.

- **Bulk Modulus**
  - Formula:  \( K = \rho (V_p^2 - \frac{4}{3}V_s^2) \)
  - Explanation: Tells us how much the rock resists being squashed from all sides at once.

- **Lamé’s First Parameter**
  - Formula:  \( \lambda = \rho (V_p^2 - 2V_s^2) \)
  - Explanation: Another measure used in rock mechanics, related to how the rock deforms.

- **P-wave Modulus**
  - Formula:  \( M = \rho V_p^2 \)
  - Explanation: Related to how compressional waves move through the rock.

- **Acoustic Impedance**
  - Formula:  \( AI = \rho V_p \)
  - Explanation: This is the product of rock density and P-wave speed. It affects how sound waves reflect inside the earth.

- **Shear Impedance**
  - Formula:  \( SI = \rho V_s \)
  - Explanation: Similar to acoustic impedance, but uses S-wave speed. It affects how shear waves reflect.

- **Compressibility**
  - Formula:  \( \beta = 1 / K \)
  - Explanation: Tells us how easy it is to squeeze the rock. A high value means the rock is easy to compress.

- **Vp/Vs Ratio, Lambda-Rho, Mu-Rho**
  - Formulas:
    - Vp/Vs ratio: \( V_p / V_s \)
    - \( \lambda\rho = \rho (V_p^2 - 2V_s^2) \)
    - \( \mu\rho = \rho V_s^2 \)
  - Explanation: These are extra ratios and products that help describe the rock’s properties in more detail.

---

## 2. Strength & Failure Parameters (How and When Rock Breaks)

**Order of Calculations:**
1. Convert units if needed (to SI)
2. Calculate Poisson's Ratio and Young's Modulus (from above)
3. Brittleness Index
4. Friction Angle (choose method)
5. Unconfined Compressive Strength (UCS)
6. Cohesion
7. Failure Angle
8. Coulomb Failure Stress
9. Compute Stresses (Sv, Pp, Shmin, SHmax)
10. Fracture Initiation Pressure

- **Brittleness Index**
  - Formula:  \( BI = 0.5 \left[ \frac{E - E_{min}}{E_{max} - E_{min}} + \frac{\nu - \nu_{max}}{\nu_{min} - \nu_{max}} \right] \)
  - Explanation: Shows if the rock is likely to break easily (brittle) or bend (ductile). Calculated using stiffness and Poisson’s ratio.

- **Friction Angle**
  - Formulas:
    - Lal (1999): \( \phi = \arcsin\left(\frac{V_p - 1000}{V_p + 1000}\right) \) (degrees, $V_p$ in m/s)
    - Chang (2006): \( \phi = 57.8 - 105\nu \)
  - Explanation: Tells us how much the rock resists sliding along a crack. It can be estimated from wave speeds or Poisson’s ratio.

- **Unconfined Compressive Strength (UCS)**
  - Formula:  \( UCS = 2.28 + 4.1089 \cdot E \) (E in GPa, UCS in MPa)
  - Explanation: The maximum pressure the rock can take before it crushes, with no sideways support.

- **Cohesion**
  - Formula:  \( c = UCS \cdot \frac{1 - \sin\phi}{2 \cos\phi} \)
  - Explanation: The natural “stickiness” or strength of the rock when there’s no pressure squeezing it together.

- **Failure Angle**
  - Formula:  \( \theta = 45^\circ + \phi/2 \)
  - Explanation: The angle at which the rock is most likely to break under stress.

- **Coulomb Failure Stress**
  - Formula:  \( \sigma_{1,fail} = UCS + \sigma_3 \tan^2(45^\circ + \phi/2) \)
  - Explanation: The maximum stress the rock can handle before it fails, considering outside pressure.

- **Fracture Initiation Pressure**
  - Formula:  \( P_{frac} = 3 \cdot Sh_{min} - SH_{max} - P_p + T \)
  - Explanation: The pressure needed to start a crack in the rock. This depends on the rock’s strength and the stresses around it.

---

## 3. Stress Calculations (Forces Acting on the Rock)

**Order of Calculations:**
1. Compute Overburden/Vertical Stress
2. Compute Vertical Stress Gradient
3. Compute Effective Vertical Stress
4. Compute Pore Pressure (Hydrostatic)
5. Compute Dynamic Poisson's Ratio
6. Compute Minimum Horizontal Stress
7. Compute Maximum Horizontal Stress
8. Compute Effective Horizontal Stresses
9. Compute Stress Ratios

- **Overburden/Vertical Stress**
  - Formula:  \( S_v(z) = \int_0^z \rho(z') g dz' \)
  - Explanation: The weight of all the rock above a certain depth. This is the main force squeezing the rock from above.

- **Vertical Stress Gradient**
  - Formula:  \( \frac{dS_v}{dz} \)
  - Explanation: How quickly the vertical stress increases as you go deeper.

- **Effective Vertical Stress**
  - Formula:  \( S_{v,eff} = S_v - P_p \)
  - Explanation: The actual stress carried by the rock itself, after subtracting the pressure from fluids in the pores.

- **Pore Pressure (Hydrostatic)**
  - Formula:  \( P_{p,hydro} = \rho_{water} g z \)
  - Explanation: The pressure from water or fluids in the rock’s pores, increasing with depth.

- **Minimum Horizontal Stress**
  - Formula:  \( Sh_{min} = \frac{\nu}{1-\nu}(S_v - P_p) + P_p \)
  - Explanation: The smallest squeezing force acting sideways on the rock. Important for predicting when fractures might open.

- **Maximum Horizontal Stress**
  - Formula:  \( SH_{max} = \frac{\nu}{1-\nu}(S_v - P_p)(1 + \epsilon_{ratio}) + P_p \)
  - Explanation: The largest sideways force. Also important for understanding how the rock will break.

- **Effective Horizontal Stresses**
  - Formulas:
    - \( Sh_{min,eff} = Sh_{min} - P_p \)
    - \( SH_{max,eff} = SH_{max} - P_p \)
  - Explanation: The sideways stresses after subtracting fluid pressure.

- **Stress Ratios**
  - Formulas:
    - \( K0_{min} = Sh_{min} / S_v \)
    - \( K0_{max} = SH_{max} / S_v \)
  - Explanation: These compare the sideways stresses to the vertical stress, helping to describe the stress state in the rock.

---

## References
- The calculations are based on published research and standard geomechanics formulas. For more details, see the code in the `app/computations/` folder.
