import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports.engine import ReportEngine

engine = ReportEngine()
engine.generate_pdf_report(2026, 6, "scratch/test_report.pdf")
print("PDF generated successfully!")
