"""Color Mathematics & WCAG Accessibility Utilities.

Implements mathematically reproducible:
1. sRGB <-> CIE XYZ <-> CIE L*a*b* color space transformations.
2. ISO/CIE 11664-6:2014 CIEDE2000 (Delta-E 2000) and CIE76 color difference formulas.
3. WCAG 2.1 relative luminance and contrast ratio calculation.
"""

import math
import re
from typing import Tuple, Optional


def normalize_hex(hex_str: str) -> str:
    """Normalizes hex string to uppercase 6-character #RRGGBB."""
    clean = re.sub(r"[^0-9a-fA-F]", "", hex_str).upper()
    if len(clean) == 3:
        clean = "".join([c * 2 for c in clean])
    if len(clean) != 6:
        raise ValueError(f"Invalid hex color format: {hex_str}")
    return f"#{clean}"


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Converts hex color code to sRGB integer tuple (0-255)."""
    norm = normalize_hex(hex_str).lstrip("#")
    return int(norm[0:2], 16), int(norm[2:4], 16), int(norm[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Converts sRGB integer tuple (0-255) to hex #RRGGBB."""
    r = max(0, min(255, int(round(r))))
    g = max(0, min(255, int(round(g))))
    b = max(0, min(255, int(round(b))))
    return f"#{r:02X}{g:02X}{b:02X}"


def srgb_channel_to_linear(channel: float) -> float:
    """Applies sRGB inverse companding (gamma expansion) to normalized channel (0.0 - 1.0)."""
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def rgb_to_relative_luminance(r: int, g: int, b: int) -> float:
    """Computes WCAG 2.1 relative luminance from sRGB (0-255).

    Returns a value between 0.0 (pure black) and 1.0 (pure white).
    """
    r_lin = srgb_channel_to_linear(r / 255.0)
    g_lin = srgb_channel_to_linear(g / 255.0)
    b_lin = srgb_channel_to_linear(b / 255.0)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calculate_contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Calculates WCAG 2.1 contrast ratio between two sRGB colors.

    Formula: (L1 + 0.05) / (L2 + 0.05) where L1 is the lighter color.
    Returns contrast ratio rounded to 2 decimal places (e.g. 21.0 or 4.54).
    """
    lum1 = rgb_to_relative_luminance(*rgb1)
    lum2 = rgb_to_relative_luminance(*rgb2)
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, 2)


def rgb_to_xyz(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Converts sRGB to CIE XYZ using the D65 standard illuminant (2° observer)."""
    r_lin = srgb_channel_to_linear(r / 255.0) * 100.0
    g_lin = srgb_channel_to_linear(g / 255.0) * 100.0
    b_lin = srgb_channel_to_linear(b / 255.0) * 100.0

    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041
    return x, y, z


def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Converts sRGB to CIE L*a*b* color space using D65 reference white."""
    x, y, z = rgb_to_xyz(r, g, b)

    # Reference white point for D65
    ref_x = 95.047
    ref_y = 100.000
    ref_z = 108.883

    vx = x / ref_x
    vy = y / ref_y
    vz = z / ref_z

    def f(t: float) -> float:
        if t > 0.008856:  # (6/29)^3
            return t ** (1.0 / 3.0)
        return (t * (29.0 / 6.0) ** 2) / 3.0 + (4.0 / 29.0)

    fx = f(vx)
    fy = f(vy)
    fz = f(vz)

    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b_val = 200.0 * (fy - fz)
    return L, a, b_val


def hex_to_lab(hex_str: str) -> Tuple[float, float, float]:
    """Convenience helper to convert hex string directly to CIE L*a*b*."""
    rgb = hex_to_rgb(hex_str)
    return rgb_to_lab(*rgb)


def delta_e_cie76(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """Calculates standard Euclidean CIE76 Delta-E."""
    dL = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    return round(math.sqrt(dL * dL + da * da + db * db), 4)


def delta_e_ciede2000(
    lab1: Tuple[float, float, float],
    lab2: Tuple[float, float, float],
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
) -> float:
    """Calculates ISO/CIE 11664-6:2014 CIEDE2000 color difference.

    Yields exact, reproducible perceptual difference matching human visual perception.
    Returns Delta-E rounded to 4 decimal places.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    c1 = math.sqrt(a1 * a1 + b1 * b1)
    c2 = math.sqrt(a2 * a2 + b2 * b2)
    mean_c = (c1 + c2) / 2.0

    # 1. Calculate a' and C'
    mean_c7 = mean_c ** 7
    g = 0.5 * (1.0 - math.sqrt(mean_c7 / (mean_c7 + 25.0 ** 7)))
    a1_prime = (1.0 + g) * a1
    a2_prime = (1.0 + g) * a2

    c1_prime = math.sqrt(a1_prime * a1_prime + b1 * b1)
    c2_prime = math.sqrt(a2_prime * a2_prime + b2 * b2)

    # 2. Calculate h' in degrees (0 to 360)
    def compute_h(b_val: float, a_prime: float) -> float:
        if b_val == 0 and a_prime == 0:
            return 0.0
        angle = math.degrees(math.atan2(b_val, a_prime))
        return angle if angle >= 0.0 else angle + 360.0

    h1_prime = compute_h(b1, a1_prime)
    h2_prime = compute_h(b2, a2_prime)

    # 3. Calculate dL', dC', dh', dH'
    dL_prime = L2 - L1
    dC_prime = c2_prime - c1_prime

    if c1_prime * c2_prime == 0:
        dh_prime = 0.0
    else:
        diff_h = h2_prime - h1_prime
        if abs(diff_h) <= 180.0:
            dh_prime = diff_h
        elif diff_h > 180.0:
            dh_prime = diff_h - 360.0
        else:
            dh_prime = diff_h + 360.0

    dH_prime = 2.0 * math.sqrt(c1_prime * c2_prime) * math.sin(math.radians(dh_prime / 2.0))

    # 4. Calculate weighted mean parameters
    mean_L_prime = (L1 + L2) / 2.0
    mean_C_prime = (c1_prime + c2_prime) / 2.0

    if c1_prime * c2_prime == 0:
        mean_h_prime = h1_prime + h2_prime
    else:
        diff_h = abs(h1_prime - h2_prime)
        sum_h = h1_prime + h2_prime
        if diff_h <= 180.0:
            mean_h_prime = sum_h / 2.0
        elif sum_h < 360.0:
            mean_h_prime = (sum_h + 360.0) / 2.0
        else:
            mean_h_prime = (sum_h - 360.0) / 2.0

    T = (
        1.0
        - 0.17 * math.cos(math.radians(mean_h_prime - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * mean_h_prime))
        + 0.32 * math.cos(math.radians(3.0 * mean_h_prime + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * mean_h_prime - 63.0))
    )

    # 5. Weighting functions
    d_theta = 30.0 * math.exp(-(((mean_h_prime - 275.0) / 25.0) ** 2))
    mean_c_prime7 = mean_C_prime ** 7
    R_C = 2.0 * math.sqrt(mean_c_prime7 / (mean_c_prime7 + 25.0 ** 7))
    R_T = -math.sin(math.radians(2.0 * d_theta)) * R_C

    mean_L_diff_sq = (mean_L_prime - 50.0) ** 2
    S_L = 1.0 + (0.015 * mean_L_diff_sq) / math.sqrt(20.0 + mean_L_diff_sq)
    S_C = 1.0 + 0.045 * mean_C_prime
    S_H = 1.0 + 0.015 * mean_C_prime * T

    # 6. Final CIEDE2000 Delta-E
    term_L = dL_prime / (kL * S_L)
    term_C = dC_prime / (kC * S_C)
    term_H = dH_prime / (kH * S_H)

    delta_e_sq = (term_L ** 2) + (term_C ** 2) + (term_H ** 2) + R_T * term_C * term_H
    # Prevent negative values due to floating point precision
    delta_e = math.sqrt(max(0.0, delta_e_sq))
    return round(delta_e, 4)
