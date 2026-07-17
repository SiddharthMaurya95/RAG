import sqlite3
import hashlib
import re
import os
import datetime
import pandas as pd
import numpy as np
from analytics.views import refresh_materialized_views
from core.decorators import with_logging_and_exceptions

def clean_km(val):
    """Cleans using time mileage string into an integer."""
    try:
        if pd.isna(val) or val is None:
            return 0
        val_str = str(val).replace(",", "").strip()
        if not val_str:
            return 0
        return int(float(val_str.split()[0]))
    except Exception:
        return 0

def extract_year_month(date_str):
    """Extracts (year, month) integers from standard YYYY-MM-DD string."""
    if not date_str:
        return 0, 0
    try:
        parts = date_str.split("-")
        if len(parts) >= 3:
            return int(parts[0]), int(parts[1])
        # Try DD-MM-YYYY format
        parts_alt = date_str.split("-")
        if len(parts_alt) == 3 and len(parts_alt[2]) == 4:
            return int(parts_alt[2]), int(parts_alt[1])
    except Exception:
        pass
    return 0, 0

def generate_heuristic_summary(row):
    """Generates a high-quality 2-sentence summary fallback from structured fields."""
    subject = str(row.get('Subject', '')).strip()
    complaint = str(row.get('Customer Complaint', '')).strip()
    results = str(row.get('Checked Results', '')).strip()
    repair = str(row.get('Repair Contents', '')).strip()
    part = str(row.get('Causal Parts Name', '')).strip()
    
    # Handle NaNs and empty values
    subject = subject if (subject and subject.lower() != 'nan') else "Vehicle issue"
    results = results if (results and results.lower() != 'nan') else "inspected by technician"
    repair = repair if (repair and repair.lower() != 'nan') else "repaired"
    part_str = f"causal part {part.lower()}" if (part and part.lower() != 'nan') else "causal component"
    
    # Build text sentences
    sentence1 = f"Issue reported was '{subject}', related to {part_str}."
    sentence2 = f"Checked results found '{results.split('.')[0]}', and technician action was '{repair.split('.')[0]}'."
    
    # Clean spacing
    sentence1 = re.sub(r'\s+', ' ', sentence1)
    sentence2 = re.sub(r'\s+', ' ', sentence2)
    
    return f"{sentence1} {sentence2}"

def generate_root_cause(row):
    """
    Derives a concise root-cause statement from structured FTIR fields.
    Priority order:
      1. Checked Results  — technician's direct inspection finding
      2. Checked Contents + Causal Parts Name — what was checked and what part failed
      3. Customer Complaint — the originally reported symptom
      4. Subject — the FTIR header description
    Produces a single, clean declarative sentence such as:
      "Root cause: worn brake pad (causal part: disc brake pad) identified during
       inspection — customer reported noise during braking."
    """
    checked_results = str(row.get('Checked Results', '')).strip()
    checked_contents = str(row.get('Checked Contents', '')).strip()
    part = str(row.get('Causal Parts Name', '')).strip()
    complaint = str(row.get('Customer Complaint', '')).strip()
    subject = str(row.get('Subject', '')).strip()

    # Sanitise nan strings
    def _clean(val):
        return val if val and val.lower() not in ('nan', 'none', '') else ''

    checked_results   = _clean(checked_results)
    checked_contents  = _clean(checked_contents)
    part              = _clean(part)
    complaint         = _clean(complaint)
    subject           = _clean(subject)

    # Build the root-cause sentence progressively
    primary = checked_results.split('.')[0] if checked_results else ''
    secondary = checked_contents.split('.')[0] if checked_contents else ''
    symptom = (complaint or subject or 'unspecified complaint').split('.')[0]
    part_clause = f" (causal part: {part.lower()})" if part else ''

    if primary:
        root_cause = f"{primary.rstrip('.').lower()}{part_clause}, as reported: {symptom.lower()}."
    elif secondary:
        root_cause = f"{secondary.rstrip('.').lower()}{part_clause}, as reported: {symptom.lower()}."
    else:
        root_cause = f"unconfirmed — reported issue: {symptom.lower()}{part_clause}."

    # Normalise spacing
    import re
    root_cause = re.sub(r'\s+', ' ', root_cause).strip()
    return root_cause

def calculate_row_hash(row):
    """Calculates MD5 hash of critical fields to uniquely identify records."""
    ftir_no = str(row.get('FTIR No', '')).strip()
    subject = str(row.get('Subject', '')).strip()
    complaint = str(row.get('Customer Complaint', '')).strip()
    concat_str = f"{ftir_no}|{subject}|{complaint}"
    return hashlib.md5(concat_str.encode('utf-8')).hexdigest()

@with_logging_and_exceptions
def ingest_excel(excel_path, db_path, llm_client=None):
    """
    Reads an Excel file, cleans columns, deduplicates, generates summaries,
    writes to SQLite database, and returns new rows added.
    """
    print(f"Starting ingestion of: {excel_path}")
    if not os.path.exists(excel_path):
        print(f"Error: {excel_path} does not exist.")
        return []
    
    # Read Excel
    df = pd.read_excel(excel_path, sheet_name=0)
    
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Skip files that are not valid FTIR datasets (e.g. scorecards, custom dashboards)
    if 'FTIR No.' not in df.columns and 'FTIR No' not in df.columns:
        print(f"Skipping {excel_path} - not a valid FTIR dataset (missing FTIR No column).")
        return []
    
    # Handle both dash and slash variants of the mileage column to prevent duplicates
    if 'Mileage - Using Time' in df.columns and 'Mileage / Using Time' in df.columns:
        df['Mileage - Using Time'] = df['Mileage - Using Time'].fillna(df['Mileage / Using Time'])
        df = df.drop(columns=['Mileage / Using Time'])
        
    # Filter out rows where FTIR No is null or empty before we do any processing
    if 'FTIR No.' in df.columns:
        df = df[df['FTIR No.'].notna() & (df['FTIR No.'].astype(str).str.strip() != '')]
    elif 'FTIR No' in df.columns:
        df = df[df['FTIR No'].notna() & (df['FTIR No'].astype(str).str.strip() != '')]
        
    # Rename columns to normalize raw Excel sheets
    df = df.rename(columns={
        'SBPR No.': 'SBPR No',
        "C'measure": 'C Measure',
        'FTIR No.': 'FTIR No',
        'Product Model Code': 'Product MODEL Code',
        'Subject (English)': 'Subject',
        # Keep Reported Country as its own field; do NOT alias to Outbreak Country
        'Report Company': 'Reported Company',
        'Causal Parts Name (English)': 'Causal Parts Name',
        # Handle both dash and slash variants of the mileage column
        'Mileage - Using Time': 'Using Time (km)',
        'Mileage / Using Time': 'Using Time (km)',
        'Causal Parts No.': 'Causal Parts No (Drawing Parts No)',
        # New column renames
        'Department of Action Judgement': 'Dept of Action Judgement',
        'Reason of "Not to File as an SBPR"': 'Reason Not SBPR',
    })
    
    print(f"Loaded {len(df)} rows from Excel.")
    
    # Normalize all string values and handle NaNs using a lambda expression
    clean_val = lambda x: str(x).strip() if not pd.isna(x) else None
    for col in df.columns:
        df[col] = df[col].apply(clean_val)
        
    # Ensure all required database fields exist in the DataFrame (initialize missing ones to None)
    required_cols = [
        'SBPR No', 'FTIR No', 'FTIR Report Date', 'Reply Date', 'Status', 'FC-OK',
        'Product MODEL Code', 'Sales Model Code', 'Segmentation', 'VIN', 'Engine No',
        'Transmission No', 'Date Registered', 'Date of Incident', 'Using Time (km)',
        'Reported Company', 'Issued Company', 'Reported Country', 'Outbreak Country',
        'Manufacturer Factory', 'Subject', 'C Measure', 'Customer Complaint',
        'Trouble Code (Complaint)', 'Trouble Code Defect', 'Checked Contents',
        'Checked Results', 'Repair Status', 'Repair Contents', 'Problem Solved',
        'Action Judgement', 'Causal Parts No (Drawing Parts No)', 'Causal Parts Name',
        'Supplier of Causal Parts', 'Production Base', 'Parts Availability',
        'File Name', 'Quality',
        # ── New columns ─────────────────────────────────────────────────
        'Rank', 'Days Used', 'FPCR No.', 'Sales Dealer', 'Service Dealer',
        'Spec on Destination', 'Collection Request Date', 'Parts Retrieved Date',
        'Person of Action Judgement', 'Dept of Action Judgement',
        'Judgement Date', 'Reason Not SBPR', 'Approval Judgement Date',
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Handle fallbacks for missing customer complaints using lambda
    df['Customer Complaint'] = df.apply(
        lambda r: r['Subject'] if not r['Customer Complaint'] and r['Subject'] else r['Customer Complaint'], 
        axis=1
    )
    
    # Parse trouble code from subject if empty using lambda/regex
    parse_tc = lambda r: re.search(r'\b([PBCU]\d{4})\b', r['Subject'], re.IGNORECASE).group(1).upper() if (not r['Trouble Code (Complaint)'] and r['Subject'] and re.search(r'\b([PBCU]\d{4})\b', r['Subject'], re.IGNORECASE)) else r['Trouble Code (Complaint)']
    df['Trouble Code (Complaint)'] = df.apply(parse_tc, axis=1)

    # Compute row hashes
    df['row_hash'] = df.apply(
        lambda r: hashlib.md5(f"{r['FTIR No'] or ''}|{r['Subject'] or ''}|{r['Customer Complaint'] or ''}".encode('utf-8')).hexdigest(),
        axis=1
    )
    
    # Standardize dates using vectorized pandas to_datetime
    date_columns = [
        'FTIR Report Date', 'Reply Date', 'Date Registered', 
        'Date of Incident', 'Collection Request Date', 
        'Parts Retrieved Date', 'Judgement Date', 'Approval Judgement Date'
    ]
    df[date_columns] = df[date_columns].apply(pd.to_datetime, format='mixed', errors='coerce')
    for col in date_columns:
        df[col] = df[col].dt.strftime('%Y-%m-%d').where(df[col].notnull(), None)
    
    # Computed columns
    df['using_km_int'] = df['Using Time (km)'].apply(clean_km)
    
    # Days Used — robust regex extraction
    df['Days Used'] = df['Days Used'].astype(str).str.extract(r'(\d+)', expand=False)
    df['Days Used'] = pd.to_numeric(df['Days Used'], errors='coerce')
    df['Days Used'] = df['Days Used'].where(pd.notna(df['Days Used']), None)
    
    # Product MODEL Code — slice to first 3 chars
    if 'Product MODEL Code' in df.columns:
        df['Product MODEL Code'] = df['Product MODEL Code'].str.slice(0, 3)
    
    # Year/month extraction
    df['extracted_ym'] = df['FTIR Report Date'].apply(extract_year_month)
    df['report_year'] = df['extracted_ym'].apply(lambda x: x[0])
    df['report_month'] = df['extracted_ym'].apply(lambda x: x[1])
    
    # Compute resolved and sbpr flags using lambdas
    df['is_resolved'] = df['Problem Solved'].apply(lambda val: 1 if val and str(val).lower() in ('resolved', 'solved') else 0)
    df['has_sbpr'] = df['SBPR No'].apply(lambda val: 1 if val and str(val).lower() not in ('nan', '') else 0)
    
    # Connect to DB and fetch existing hashes and FTIRs to filter duplicates in batch
    from core.database import get_session, Record
    
    session = get_session(db_path)
    
    try:
        existing_rows = session.query(Record.row_hash, Record.ftir_no).all()
        existing_hashes = {r.row_hash for r in existing_rows if r.row_hash}
        existing_ftirs = {str(r.ftir_no).strip() for r in existing_rows if r.ftir_no}
        
        # Filter out duplicate records
        df_new = df[~df['row_hash'].isin(existing_hashes) & ~df['FTIR No'].isin(existing_ftirs)]
        
        print(f"Filtered duplicates: {len(df_new)} new records to insert.")
        
        new_records = []
        
        # Insert new records
        for idx, row in df_new.iterrows():
            # Generate summary and root cause using heuristic only
            summary = generate_heuristic_summary(row)
            root_cause = generate_root_cause(row)
                
            record = Record(
                sbpr_no=row['SBPR No'],
                ftir_no=row['FTIR No'],
                ftir_report_date=row['FTIR Report Date'],
                reply_date=row['Reply Date'],
                status=row['Status'],
                fc_ok=row['FC-OK'],
                product_model_code=row['Product MODEL Code'],
                sales_model_code=row['Sales Model Code'],
                segmentation=row['Segmentation'],
                vin=row['VIN'],
                engine_no=row['Engine No'],
                transmission_no=row['Transmission No'],
                date_registered=row['Date Registered'],
                date_of_incident=row['Date of Incident'],
                using_time_km=row['Using Time (km)'],
                reported_company=row['Reported Company'],
                issued_company=row['Issued Company'],
                outbreak_country=row['Outbreak Country'],
                manufacturer_factory=row['Manufacturer Factory'],
                subject=row['Subject'],
                c_measure=row['C Measure'],
                customer_complaint=row['Customer Complaint'],
                trouble_code_complaint=row['Trouble Code (Complaint)'],
                trouble_code_defect=row['Trouble Code Defect'],
                checked_contents=row['Checked Contents'],
                checked_results=row['Checked Results'],
                repair_status=row['Repair Status'],
                repair_contents=row['Repair Contents'],
                problem_solved=row['Problem Solved'],
                action_judgement=row['Action Judgement'],
                causal_parts_no=row['Causal Parts No (Drawing Parts No)'],
                causal_parts_name=row['Causal Parts Name'],
                supplier_of_causal_parts=row['Supplier of Causal Parts'],
                production_base=row['Production Base'],
                parts_availability=row['Parts Availability'],
                file_name=row['File Name'],
                quality=row['Quality'],
                # ── New fields ─────────────────────────────────────────────────────
                rank=row['Rank'],
                reported_country=row['Reported Country'],
                days_used=row['Days Used'],
                fpcr_no=row['FPCR No.'],
                sales_dealer=row['Sales Dealer'],
                service_dealer=row['Service Dealer'],
                spec_on_destination=row['Spec on Destination'],
                collection_request_date=row['Collection Request Date'],
                parts_retrieved_date=row['Parts Retrieved Date'],
                person_of_action_judgement=row['Person of Action Judgement'],
                dept_of_action_judgement=row['Dept of Action Judgement'],
                judgement_date=row['Judgement Date'],
                reason_not_sbpr=row['Reason Not SBPR'],
                approval_judgement_date=row['Approval Judgement Date'],
                # ── Computed / metadata ─────────────────────────────────────────────
                row_hash=row['row_hash'],
                using_km_int=row['using_km_int'],
                report_year=row['report_year'],
                report_month=row['report_month'],
                is_resolved=row['is_resolved'],
                has_sbpr=row['has_sbpr'],
                summary=summary,
                root_cause=root_cause
            )
            session.add(record)
            session.flush()  # Populate record.id
            
            new_records.append({
                'id': record.id,
                'ftir_no': row['FTIR No'],
                'outbreak_country': row['Outbreak Country'],
                'product_model_code': row['Product MODEL Code'],
                'segmentation': row['Segmentation'],
                'trouble_code_complaint': row['Trouble Code (Complaint)'],
                'subject': row['Subject'],
                'checked_results': row['Checked Results'],
                'repair_contents': row['Repair Contents'],
                'causal_parts_name': row['Causal Parts Name'],
                'summary': summary
            })
            
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
    
    print(f"Ingested {len(new_records)} new records.")
    
    # Refresh materialized views if there were any updates
    if new_records:
        refresh_materialized_views(db_path)
        
    return new_records
