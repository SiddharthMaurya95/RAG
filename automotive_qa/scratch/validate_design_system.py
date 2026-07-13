import sys
sys.path.insert(0, ".")

from ui.theme import (
    inject_design_system, get_css_text,
    brand_header, status_chip, icon_container,
    metric_card, badge, section_label, card, alert, footer, feature_card,
)

css = get_css_text()
print("theme.py — OK")
print(f"  CSS length: {len(css)} chars")
print(f"  CSS vars:   {css.count('--msds-')} references")
print(f"  Builders:   12 functions exported")
print()

h = brand_header()
print(f"  brand_header():   {len(h)} chars")

sc = status_chip("Online", "online")
print(f"  status_chip():    {len(sc)} chars")

mc = metric_card("Total", "1,234", "primary")
print(f"  metric_card():    {len(mc)} chars")

b = badge("SEARCH", "info")
print(f"  badge():          {len(b)} chars")

f = footer()
print(f"  footer():         {len(f)} chars")

fc = feature_card(icon_container("🔒", "primary", "sm"), "Secure", "Enterprise-grade security")
print(f"  feature_card():   {len(fc)} chars")

ic = icon_container("✨", "success", "lg")
print(f"  icon_container(): {len(ic)} chars")

a = alert("System ready", "success", "✓")
print(f"  alert():          {len(a)} chars")

sl = section_label("Dashboard Filters")
print(f"  section_label():  {len(sl)} chars")

c = card("<p>Content</p>", "msds-card-hover")
print(f"  card():           {len(c)} chars")

print()
print("All validations passed.")
