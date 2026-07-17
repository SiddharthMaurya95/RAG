# =====================================================
# ✅ UI UTILITIES (Design Tokens & Theme)
# =====================================================
import os
import streamlit as st

# ─────────────────────────────────────────────────────────────────────
# DESIGN TOKENS
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

    "warning_600":  "#D97706",   # Text on dark bg
    "warning_500":  "#F59E0B",   # Primary warning
    "warning_100":  "#FEF3C7",   # Warning bg

    "error_600":    "#DC2626",   # Text on dark bg
    "error_500":    "#EF4444",   # Primary error (Red)
    "error_100":    "#FEE2E2",   # Error bg

    "info_600":     "#2563EB",   # Text on dark bg
    "info_500":     "#3B82F6",   # Primary info
    "info_100":     "#DBEAFE",   # Info bg
}

FONT_FAMILY = {
    "sans": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    "mono": "'JetBrains Mono', 'Fira Code', Consolas, Monaco, monospace"
}

FONT_SIZE = {
    "xs":   "0.75rem",    # 12px
    "sm":   "0.875rem",   # 14px
    "base": "1rem",       # 16px
    "lg":   "1.125rem",   # 18px
    "xl":   "1.25rem",    # 20px
    "2xl":  "1.5rem",     # 24px
    "3xl":  "1.875rem",   # 30px
    "4xl":  "2.25rem",    # 36px
}

FONT_WEIGHT = {
    "regular":  400,
    "medium":   500,
    "semibold": 600,
    "bold":     700,
}

SPACING = {
    "0":    "0",
    "1":    "0.25rem",  # 4px
    "2":    "0.5rem",   # 8px
    "3":    "0.75rem",  # 12px
    "4":    "1rem",     # 16px
    "5":    "1.25rem",  # 20px
    "6":    "1.5rem",   # 24px
    "8":    "2rem",     # 32px
    "10":   "2.5rem",   # 40px
    "12":   "3rem",     # 48px
    "16":   "4rem",     # 64px
}

RADIUS = {
    "none": "0",
    "sm":   "0.125rem", # 2px
    "md":   "0.375rem", # 6px (Standard cards/buttons)
    "lg":   "0.5rem",   # 8px (Large containers)
    "xl":   "0.75rem",  # 12px
    "full": "9999px",   # Pills / circles
}

SHADOWS = {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    "inner": "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)",
    "none": "none",
}

TRANSITION = {
    "fast": "150ms cubic-bezier(0.4, 0, 0.2, 1)",
    "normal": "300ms cubic-bezier(0.4, 0, 0.2, 1)",
}

ICON_SIZE = {
    "sm": "16px",
    "md": "20px",
    "lg": "24px",
    "xl": "32px",
}

# ─── CSS file path (resolved once at import time) ──────────────────
_CSS_PATH = os.path.join(os.path.dirname(__file__), "styles.css")


# ────────────────────────────────────────────────────────────────────
# PUBLIC API
# ────────────────────────────────────────────────────────────────────

def inject_design_system() -> None:
    """
    Injects the enterprise design system CSS into the current Streamlit page.
    Must be called on every rerun.
    """
    css_text = _load_css()
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)


def get_css_text() -> str:
    """
    Returns the raw CSS string without injecting it.
    """
    return _load_css()


# ────────────────────────────────────────────────────────────────────
# HTML SNIPPET BUILDERS
# ────────────────────────────────────────────────────────────────────

def brand_header(
    title: str = "MARUTI SUZUKI",
    tagline: str = "Market Quality Analytics System",
    logo_html: str = "",
    right_html: str = "",
) -> str:
    """
    Returns the HTML for the sticky brand header bar.
    """
    return f"""
    <div class="msds-header-bar">
        <div class="msds-header-brand">
            {logo_html}
            <div>
                <div class="msds-header-title">{title}</div>
                <div class="msds-header-tagline">{tagline}</div>
            </div>
        </div>
        <div class="msds-header-actions">
            {right_html}
        </div>
    </div>
    """


def status_chip(label: str, status: str = "online") -> str:
    """
    Returns an HTML status chip with a coloured dot.
    """
    return (
        f'<span class="msds-status-chip">'
        f'<span class="msds-status-dot msds-status-dot-{status}"></span>'
        f'{label}</span>'
    )


def icon_container(
    emoji_or_html: str,
    variant: str = "primary",
    size: str = "md",
) -> str:
    """
    Wraps an emoji or icon in a rounded, coloured container.
    """
    return (
        f'<span class="msds-icon-container msds-icon-container-{variant} '
        f'msds-icon-container-{size}">{emoji_or_html}</span>'
    )


def metric_card(
    label: str,
    value: str,
    variant: str = "primary",
    delta: str = "",
    delta_dir: str = "up",
) -> str:
    """
    Returns a self-contained metric card HTML block.
    """
    delta_html = ""
    if delta:
        delta_html = (
            f'<div class="msds-metric-delta msds-metric-delta-{delta_dir}">'
            f'{delta}</div>'
        )
    return (
        f'<div class="msds-metric-card msds-metric-card-{variant}">'
        f'<div class="msds-metric-label">{label}</div>'
        f'<div class="msds-metric-value">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


def badge(label: str, variant: str = "primary", pill: bool = False) -> str:
    """
    Returns an inline badge HTML element.
    """
    pill_cls = " msds-badge-pill" if pill else ""
    return (
        f'<span class="msds-badge msds-badge-{variant}{pill_cls}">'
        f'{label}</span>'
    )


def section_label(text: str) -> str:
    """Returns a styled section header / overline label."""
    return f'<div class="msds-section-label">{text}</div>'


def card(content_html: str, extra_classes: str = "") -> str:
    """
    Wraps content in a standard card container.
    """
    return f'<div class="msds-card {extra_classes}">{content_html}</div>'


def alert(message: str, variant: str = "info", icon: str = "") -> str:
    """
    Returns a styled alert/banner.
    """
    icon_html = f'<span>{icon}</span>' if icon else ""
    return (
        f'<div class="msds-alert msds-alert-{variant}">'
        f'{icon_html}<span>{message}</span></div>'
    )


def footer(
    text: str = "© 2024 Maruti Suzuki India Limited. All rights reserved.",
    version: str = "Version 1.0.0",
) -> str:
    """Returns the branded page footer HTML."""
    return (
        f'<div class="msds-footer">'
        f'{text}'
        f'<span class="msds-footer-version">{version}</span>'
        f'</div>'
    )


def feature_card(icon_html: str, title: str, description: str) -> str:
    """
    Returns a single feature highlight card (used on login / landing).
    """
    return (
        f'<div class="msds-feature-card">'
        f'{icon_html}'
        f'<div>'
        f'<div class="msds-feature-title">{title}</div>'
        f'<div class="msds-feature-desc">{description}</div>'
        f'</div></div>'
    )


SUZUKI_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'viewBox="275 475.18 450 49.65" height="40" '
    'style="display:block;flex-shrink:0;">'
    '<g>'
    '<path style="fill:#9D9FA1;" d="M299.613,475.176c-7.289,6.443-15.528,'
    '11.303-24.401,15.106l31.585,22.606L305,513.732l-13.099-8.661c-4.225,'
    '-2.852-14.789-0.845-16.901,2.746l24.296,17.007c6.761-6.444,14.894,'
    '-11.619,24.507-15.528l-31.901-22.183l1.69-1.373l10.352,7.393c5.176,'
    '3.697,9.296,4.648,20.388-0.845L299.613,475.176"/>'
    '<polyline style="fill:#2D3394;" points="349.049,487.535 362.887,'
    '487.535 367.007,502.007 367.007,502.007 371.127,487.535 384.859,'
    '487.535 384.859,512.359 375.986,512.359 375.986,494.612 375.88,'
    '494.612 370.704,512.359 363.31,512.359 358.028,494.612 358.028,'
    '494.612 358.028,512.359 349.049,512.359 349.049,487.535 "/>'
    '<path style="fill:#2D3394;" d="M402.817,495.035L402.817,495.035'
    'l-2.958,8.451h5.915L402.817,495.035 M396.69,487.535h12.042l10.563,'
    '24.824h-10.458l-1.056-2.852h-10.247l-1.056,2.852h-10.458L396.69,'
    '487.535z"/>'
    '<path style="fill:#2D3394;" d="M453.098,487.535h9.824v15c0,3.169,'
    '1.796,4.226,5.07,4.226c3.169,0,5.071-1.056,5.071-4.226v-15h9.824'
    'v15.423c0,7.922-4.754,10.247-14.895,10.247c-10.035,0-14.895-2.43'
    '-14.895-10.247V487.535"/>'
    '<polyline style="fill:#2D3394;" points="493.874,493.768 484.789,'
    '493.768 484.789,487.535 512.781,487.535 512.781,493.768 503.697,'
    '493.768 503.697,512.359 493.874,512.359 493.874,493.768 "/>'
    '<rect x="514.789" y="487.535" style="fill:#2D3394;" width="9.823" '
    'height="24.824"/>'
    '<path style="fill:#2D3394;" d="M430.176,493.768h6.866c1.584,0,2.852,'
    '0.423,2.852,2.324c0,1.585-0.845,2.324-2.746,2.324h-6.972V493.768 '
    'M452.57,512.359l-8.345-7.711c6.866-1.056,6.021-7.817,6.021-10.14'
    'c0-2.746-1.479-5.07-3.38-6.021c-1.373-0.634-3.063-0.951-5.915-0.951'
    'h-20.599v24.824h9.824v-7.605h1.69l8.24,7.605H452.57z"/>'
    '<path style="fill:#2D3394;" d="M556.514,501.796c-4.753-0.739-6.76,'
    '-3.486-6.76-6.972c0-6.443,6.338-8.133,14.366-8.133c11.092,0,15.633,'
    '2.852,15.951,8.133h-11.409c0-1.056-0.634-1.584-1.479-2.007c-0.846,'
    '-0.422-2.007-0.528-3.064-0.528c-2.957,0-3.908,0.739-3.908,1.796'
    'c0,0.739,0.317,1.162,1.268,1.268l11.726,1.69c4.965,0.739,8.027,'
    '3.063,8.027,7.183c0,6.021-4.964,8.873-15.95,8.873c-7.5,0-15.738,'
    '-1.057-15.844-8.345h11.83c0,0.845,0.317,1.373,1.056,1.795c0.74,'
    '0.317,1.796,0.528,3.381,0.528c3.064,0,3.908-0.845,3.908-2.007'
    'c0-0.74-0.422-1.479-1.795-1.69L556.514,501.796"/>'
    '<path style="fill:#2D3394;" d="M583.873,487.535h9.824v15c0,3.169,'
    '1.796,4.226,5.07,4.226c3.169,0,5.071-1.056,5.071-4.226v-15h9.823'
    'v15.423c0,7.922-4.753,10.247-14.894,10.247c-10.035,0-14.894-2.43'
    '-14.894-10.247V487.535"/>'
    '<polyline style="fill:#2D3394;" points="616.197,507.078 631.092,'
    '493.768 617.253,493.768 617.253,487.535 644.296,487.535 644.296,'
    '492.922 629.824,506.127 643.979,506.127 643.979,512.359 616.197,'
    '512.359 616.197,507.078 "/>'
    '<path style="fill:#2D3394;" d="M646.937,487.535h9.823v15c0,3.169,'
    '1.796,4.226,5.07,4.226c3.17,0,5.071-1.056,5.071-4.226v-15h9.824'
    'v15.423c0,7.922-4.753,10.247-14.895,10.247c-10.034,0-14.894-2.43'
    '-14.894-10.247v-15.423"/>'
    '<rect x="715.176" y="487.535" style="fill:#2D3394;" width="9.824" '
    'height="24.824"/>'
    '<polyline style="fill:#2D3394;" points="680.951,512.359 690.457,'
    '512.359 690.246,503.486 699.859,512.359 712.324,512.359 698.698,'
    '499.683 713.064,487.535 701.126,487.535 690.457,496.091 690.457,'
    '487.535 680.951,487.535 680.951,512.359 "/>'
    '</g>'
    '</svg>'
)


def render_app_header() -> None:
    """
    Renders the enterprise Maruti Suzuki header bar at the top of
    the Streamlit page.
    """
    header_html = (
        '<div class="msds-header-bar">'
        '<div class="msds-header-brand">'
        f'{SUZUKI_LOGO_SVG}'
        '<div>'
        '<div class="msds-header-tagline">Market Quality Analytics System</div>'
        '</div>'
        '</div>'
        '<div class="msds-header-actions">'
        '<span class="msds-status-chip">'
        '<span class="msds-status-dot msds-status-dot-online"></span>'
        'Offline'
        '</span>'
        '<span class="msds-three-dot-menu" title="Menu">&#x22EE;</span>'
        '</div>'
        '</div>'
        '<div class="msds-header-spacer"></div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


@st.cache_data
def _load_css() -> str:
    """Reads and returns the content of ``styles.css``."""
    if os.path.exists(_CSS_PATH):
        with open(_CSS_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    return ""
