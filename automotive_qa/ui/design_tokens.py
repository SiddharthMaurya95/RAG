"""
Maruti Suzuki — Enterprise Design Tokens
==========================================

Centralised design constants for the MQ Quality Analytics System.
All colour, typography, spacing, shadow, radius, and icon-size
tokens are defined here as plain Python values so they can be
consumed by:

  • Inline ``st.markdown`` calls (HTML / CSS variable injection)
  • The companion ``styles.css`` file (which mirrors these values)
  • Any future Streamlit component or report generator

Branding: Maruti Suzuki · Light Theme · Corporate Blue · Enterprise

Usage
-----
    from ui.design_tokens import COLORS, TYPOGRAPHY, SPACING, RADIUS, SHADOWS

Convention
----------
Token names follow a ``CATEGORY_VARIANT`` pattern.
Nested dictionaries keep related tokens grouped.
"""


# ─────────────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────────────

COLORS = {
    # ── Brand / Primary (Maruti Suzuki Corporate Blue) ──────────────
    "primary_900":  "#0A1E40",   # Deepest navy
    "primary_800":  "#0F2A5E",   # Dark navy
    "primary_700":  "#15347A",   # Deep corporate blue
    "primary_600":  "#1B3D87",   # ★ Brand primary
    "primary_500":  "#2952A3",   # Standard interactive blue
    "primary_400":  "#3A6BBF",   # Hover state
    "primary_300":  "#6B94D4",   # Lighter accent
    "primary_200":  "#A3BDE6",   # Muted accent
    "primary_100":  "#D1DEEF",   # Very light tint
    "primary_50":   "#EBF0F7",   # Background tint

    # ── Neutral / Gray ─────────────────────────────────────────────
    "neutral_900":  "#0F172A",   # Heading text
    "neutral_800":  "#1E293B",   # Body text strong
    "neutral_700":  "#334155",   # Body text
    "neutral_600":  "#475569",   # Secondary text
    "neutral_500":  "#64748B",   # Muted text / labels
    "neutral_400":  "#94A3B8",   # Placeholder
    "neutral_300":  "#CBD5E1",   # Disabled / decorative
    "neutral_200":  "#E2E8F0",   # Borders
    "neutral_100":  "#F1F5F9",   # Sidebar / surface alt
    "neutral_50":   "#F8FAFC",   # Page background
    "white":        "#FFFFFF",   # Card / surface

    # ── Semantic ───────────────────────────────────────────────────
    "success_600":  "#059669",   # Text on dark bg
    "success_500":  "#10B981",   # Primary success
    "success_100":  "#D1FAE5",   # Success bg
    "success_50":   "#ECFDF5",   # Success tint

    "warning_600":  "#D97706",
    "warning_500":  "#F59E0B",
    "warning_100":  "#FEF3C7",
    "warning_50":   "#FFFBEB",

    "error_600":    "#DC2626",
    "error_500":    "#EF4444",
    "error_100":    "#FEE2E2",
    "error_50":     "#FEF2F2",

    "info_600":     "#0284C7",
    "info_500":     "#0EA5E9",
    "info_100":     "#E0F2FE",
    "info_50":      "#F0F9FF",
}


# ─────────────────────────────────────────────────────────────────────
# TYPOGRAPHY
# ─────────────────────────────────────────────────────────────────────

FONT_FAMILY = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
FONT_FAMILY_MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"

FONT_SIZE = {
    "xs":   "11px",
    "sm":   "12px",
    "base": "14px",
    "md":   "15px",
    "lg":   "16px",
    "xl":   "18px",
    "2xl":  "20px",
    "3xl":  "24px",
    "4xl":  "28px",
    "5xl":  "32px",
    "6xl":  "36px",
}

FONT_WEIGHT = {
    "light":    300,
    "regular":  400,
    "medium":   500,
    "semibold": 600,
    "bold":     700,
    "extrabold": 800,
}

LINE_HEIGHT = {
    "tight":   1.2,
    "snug":    1.35,
    "normal":  1.5,
    "relaxed": 1.625,
    "loose":   1.8,
}

LETTER_SPACING = {
    "tighter":  "-0.025em",
    "tight":    "-0.01em",
    "normal":   "0em",
    "wide":     "0.04em",
    "wider":    "0.06em",
    "widest":   "0.08em",
}


# ─────────────────────────────────────────────────────────────────────
# SPACING  (px values — multiply by 4 for the scale factor)
# ─────────────────────────────────────────────────────────────────────

SPACING = {
    "0":   "0px",
    "0.5": "2px",
    "1":   "4px",
    "1.5": "6px",
    "2":   "8px",
    "2.5": "10px",
    "3":   "12px",
    "4":   "16px",
    "5":   "20px",
    "6":   "24px",
    "8":   "32px",
    "10":  "40px",
    "12":  "48px",
    "16":  "64px",
    "20":  "80px",
    "24":  "96px",
}


# ─────────────────────────────────────────────────────────────────────
# BORDER RADIUS
# ─────────────────────────────────────────────────────────────────────

RADIUS = {
    "none": "0px",
    "sm":   "4px",
    "md":   "6px",
    "lg":   "8px",
    "xl":   "12px",
    "2xl":  "16px",
    "full": "9999px",
}


# ─────────────────────────────────────────────────────────────────────
# SHADOWS  (minimal / enterprise aesthetic)
# ─────────────────────────────────────────────────────────────────────

SHADOWS = {
    "none":  "none",
    "xs":    "0 1px 2px 0 rgba(0, 0, 0, 0.03)",
    "sm":    "0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.03)",
    "md":    "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.03)",
    "lg":    "0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.03)",
    "xl":    "0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03)",
    "inner": "inset 0 2px 4px 0 rgba(0, 0, 0, 0.04)",
}


# ─────────────────────────────────────────────────────────────────────
# ICON SIZES
# ─────────────────────────────────────────────────────────────────────

ICON_SIZE = {
    "xs":   "14px",
    "sm":   "16px",
    "md":   "20px",
    "lg":   "24px",
    "xl":   "28px",
    "2xl":  "32px",
    "3xl":  "40px",
    "4xl":  "48px",
    "5xl":  "56px",
}


# ─────────────────────────────────────────────────────────────────────
# TRANSITIONS
# ─────────────────────────────────────────────────────────────────────

TRANSITION = {
    "fast":    "150ms ease",
    "normal":  "200ms ease",
    "slow":    "300ms ease-in-out",
}


# ─────────────────────────────────────────────────────────────────────
# Z-INDEX SCALE
# ─────────────────────────────────────────────────────────────────────

Z_INDEX = {
    "base":    0,
    "raised":  10,
    "overlay": 100,
    "modal":   200,
    "toast":   300,
}


# ─────────────────────────────────────────────────────────────────────
# BREAKPOINTS  (informational; Streamlit controls layout internally)
# ─────────────────────────────────────────────────────────────────────

BREAKPOINTS = {
    "sm":  "640px",
    "md":  "768px",
    "lg":  "1024px",
    "xl":  "1280px",
    "2xl": "1536px",
}


# ─────────────────────────────────────────────────────────────────────
# COMPONENT-LEVEL COMPOSITE TOKENS
# ─────────────────────────────────────────────────────────────────────
# Higher-level tokens that combine primitives for specific components.
# These provide a single source-of-truth for the CSS file and any
# Python-generated HTML.

CARD = {
    "background":    COLORS["white"],
    "border":        f"1px solid {COLORS['neutral_200']}",
    "border_radius": RADIUS["xl"],
    "padding":       SPACING["6"],
    "shadow":        SHADOWS["xs"],
}

BUTTON_PRIMARY = {
    "background":       COLORS["primary_600"],
    "background_hover": COLORS["primary_500"],
    "color":            COLORS["white"],
    "font_weight":      FONT_WEIGHT["semibold"],
    "border_radius":    RADIUS["md"],
    "padding":          f"{SPACING['2.5']} {SPACING['5']}",
    "shadow":           SHADOWS["sm"],
    "transition":       TRANSITION["fast"],
}

BUTTON_SECONDARY = {
    "background":       COLORS["white"],
    "background_hover": COLORS["neutral_50"],
    "color":            COLORS["neutral_700"],
    "border":           f"1px solid {COLORS['neutral_200']}",
    "font_weight":      FONT_WEIGHT["medium"],
    "border_radius":    RADIUS["md"],
    "padding":          f"{SPACING['2.5']} {SPACING['5']}",
    "transition":       TRANSITION["fast"],
}

BUTTON_DANGER = {
    "background":       COLORS["white"],
    "background_hover": COLORS["error_50"],
    "color":            COLORS["error_600"],
    "border":           f"1px solid {COLORS['error_100']}",
    "font_weight":      FONT_WEIGHT["medium"],
    "border_radius":    RADIUS["md"],
    "padding":          f"{SPACING['2.5']} {SPACING['5']}",
    "transition":       TRANSITION["fast"],
}

INPUT = {
    "background":       COLORS["white"],
    "border":           f"1px solid {COLORS['neutral_200']}",
    "border_focus":     f"1px solid {COLORS['primary_500']}",
    "border_radius":    RADIUS["md"],
    "padding":          f"{SPACING['2.5']} {SPACING['3']}",
    "font_size":        FONT_SIZE["base"],
    "color":            COLORS["neutral_700"],
    "placeholder":      COLORS["neutral_400"],
    "shadow_focus":     f"0 0 0 3px {COLORS['primary_50']}",
    "transition":       TRANSITION["fast"],
}

BADGE = {
    "font_size":       FONT_SIZE["xs"],
    "font_weight":     FONT_WEIGHT["semibold"],
    "padding":         f"3px {SPACING['2.5']}",
    "border_radius":   RADIUS["sm"],
    "letter_spacing":  LETTER_SPACING["wide"],
    "text_transform":  "uppercase",
}

METRIC_CARD = {
    "background":     COLORS["white"],
    "border":         f"1px solid {COLORS['neutral_200']}",
    "border_radius":  RADIUS["lg"],
    "padding":        f"{SPACING['4']} {SPACING['5']}",
    "border_top":     f"3px solid {COLORS['primary_600']}",
}
