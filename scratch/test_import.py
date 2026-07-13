import sys
import os

sys.path.append(r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa")
from reports.engine import RGBColor
import docx.shared

print("Imported RGBColor type:", type(RGBColor))
print("docx.shared.RGBColor type:", type(docx.shared.RGBColor))
print("Is it docx.shared.RGBColor?", RGBColor is docx.shared.RGBColor)
