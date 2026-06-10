import sqlite3
import hashlib
import re
import os
import datetime
import pandas as pd
import numpy as np
from analytics.views import refresh_materialized_views

def clean_km(val):
    """Cleans using time mileage string into an integer."""
    if pd.isna(val) or val is None:
        return 0
    val_str = str(val).lower()
    digits = "".join([c for c in val_str if c.isdigit()])
    return int(digits) if digits else 0

def parse_date(date_val):
    """Parses date string or object into standard YYYY-MM-DD or returns empty."""
    if pd.isna(date_val) or date_val is None:
        return None
    if isinstance(date_val, (datetime.date, datetime.datetime)):
        return date_val.strftime("%Y-%m-%d")
    
    date_str = str(date_val).strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str

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

def calculate_row_hash(row):
    """Calculates MD5 hash of critical fields to uniquely identify records."""
    ftir_no = str(row.get('FTIR No', '')).strip()
    subject = str(row.get('Subject', '')).strip()
    complaint = str(row.get('Customer Complaint', '')).strip()
    concat_str = f"{ftir_no}|{subject}|{complaint}"
    return hashlib.md5(concat_str.encode('utf-8')).hexdigest()

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
    
    # Rename columns to normalize raw Excel sheets
    df = df.rename(columns={
        'SBPR No.': 'SBPR No',
        "C'measure": 'C Measure',
        'FTIR No.': 'FTIR No',
        'Product Model Code': 'Product MODEL Code',
        'Subject (English)': 'Subject',
        'Reported Country': 'Outbreak Country',
        'Report Company': 'Reported Company',
        'Causal Parts Name (English)': 'Causal Parts Name',
        'Mileage - Using Time': 'Using Time (km)',
        'Causal Parts No.': 'Causal Parts No (Drawing Parts No)'
    })
    
    print(f"Loaded {len(df)} rows from Excel.")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    new_records = []
    
    for idx, row in df.iterrows():
        # Clean FTIR No
        ftir_no_raw = row.get('FTIR No')
        ftir_no = str(ftir_no_raw).strip() if not pd.isna(ftir_no_raw) else ''
        
        # Compute row hash
        row_hash = calculate_row_hash(row)
        
        # Check if row_hash or ftir_no already exists
        cursor.execute("SELECT id FROM records WHERE row_hash = ? OR ftir_no = ?", (row_hash, ftir_no))
        if cursor.fetchone():
            # Duplicate, skip
            continue
        
        # Parse fields
        sbpr_no = str(row.get('SBPR No', '')).strip() if not pd.isna(row.get('SBPR No')) else None
        ftir_report_date = parse_date(row.get('FTIR Report Date'))
        reply_date = parse_date(row.get('Reply Date'))
        status = str(row.get('Status', '')).strip() if not pd.isna(row.get('Status')) else None
        fc_ok = str(row.get('FC-OK', '')).strip() if not pd.isna(row.get('FC-OK')) else None
        product_model_code = str(row.get('Product MODEL Code', '')).strip() if not pd.isna(row.get('Product MODEL Code')) else None
        sales_model_code = str(row.get('Sales Model Code', '')).strip() if not pd.isna(row.get('Sales Model Code')) else None
        segmentation = str(row.get('Segmentation', '')).strip() if not pd.isna(row.get('Segmentation')) else None
        vin = str(row.get('VIN', '')).strip() if not pd.isna(row.get('VIN')) else None
        engine_no = str(row.get('Engine No', '')).strip() if not pd.isna(row.get('Engine No')) else None
        transmission_no = str(row.get('Transmission No', '')).strip() if not pd.isna(row.get('Transmission No')) else None
        date_registered = parse_date(row.get('Date Registered'))
        date_of_incident = parse_date(row.get('Date of Incident'))
        using_time_km = str(row.get('Using Time (km)', '')).strip() if not pd.isna(row.get('Using Time (km)')) else None
        reported_company = str(row.get('Reported Company', '')).strip() if not pd.isna(row.get('Reported Company')) else None
        issued_company = str(row.get('Issued Company', '')).strip() if not pd.isna(row.get('Issued Company')) else None
        outbreak_country = str(row.get('Outbreak Country', '')).strip() if not pd.isna(row.get('Outbreak Country')) else None
        manufacturer_factory = str(row.get('Manufacturer Factory', '')).strip() if not pd.isna(row.get('Manufacturer Factory')) else None
        subject = str(row.get('Subject', '')).strip() if not pd.isna(row.get('Subject')) else None
        c_measure = str(row.get('C Measure', '')).strip() if not pd.isna(row.get('C Measure')) else None
        customer_complaint = str(row.get('Customer Complaint', '')).strip() if not pd.isna(row.get('Customer Complaint')) else None
        trouble_code_complaint = str(row.get('Trouble Code (Complaint)', '')).strip() if not pd.isna(row.get('Trouble Code (Complaint)')) else None
        
        # Fallbacks for missing columns in raw sheets
        if (not customer_complaint or customer_complaint.lower() == 'nan') and subject:
            customer_complaint = subject
            
        if not trouble_code_complaint and subject:
            # Parse trouble code from subject text using regex
            match = re.search(r'\b([PBCU]\d{4})\b', subject, re.IGNORECASE)
            if match:
                trouble_code_complaint = match.group(1).upper()
                
        trouble_code_defect = str(row.get('Trouble Code Defect', '')).strip() if not pd.isna(row.get('Trouble Code Defect')) else None
        checked_contents = str(row.get('Checked Contents', '')).strip() if not pd.isna(row.get('Checked Contents')) else None
        checked_results = str(row.get('Checked Results', '')).strip() if not pd.isna(row.get('Checked Results')) else None
        repair_status = str(row.get('Repair Status', '')).strip() if not pd.isna(row.get('Repair Status')) else None
        repair_contents = str(row.get('Repair Contents', '')).strip() if not pd.isna(row.get('Repair Contents')) else None
        problem_solved = str(row.get('Problem Solved', '')).strip() if not pd.isna(row.get('Problem Solved')) else None
        action_judgement = str(row.get('Action Judgement', '')).strip() if not pd.isna(row.get('Action Judgement')) else None
        causal_parts_no = str(row.get('Causal Parts No (Drawing Parts No)', '')).strip() if not pd.isna(row.get('Causal Parts No (Drawing Parts No)')) else None
        causal_parts_name = str(row.get('Causal Parts Name', '')).strip() if not pd.isna(row.get('Causal Parts Name')) else None
        supplier_of_causal_parts = str(row.get('Supplier of Causal Parts', '')).strip() if not pd.isna(row.get('Supplier of Causal Parts')) else None
        production_base = str(row.get('Production Base', '')).strip() if not pd.isna(row.get('Production Base')) else None
        parts_availability = str(row.get('Parts Availability', '')).strip() if not pd.isna(row.get('Parts Availability')) else None
        file_name = str(row.get('File Name', '')).strip() if not pd.isna(row.get('File Name')) else None
        quality = str(row.get('Quality', '')).strip() if not pd.isna(row.get('Quality')) else None
        
        # Computed columns
        using_km_int = clean_km(using_time_km)
        report_year, report_month = extract_year_month(ftir_report_date)
        is_resolved = 1 if (problem_solved and problem_solved.lower() in ('resolved', 'solved')) else 0
        has_sbpr = 1 if (sbpr_no and sbpr_no.lower() not in ('nan', '')) else 0
        
        # Generate summary (use LLM if client is provided, otherwise fallback to heuristic)
        summary = None
        if llm_client:
            try:
                # Format request for 2 sentence summary
                prompt = (
                    f"Summarize the following vehicle quality record in exactly 2 sentences. "
                    f"Highlight the issue and the repair action.\n"
                    f"Subject: {subject}\n"
                    f"Checked Results: {checked_results}\n"
                    f"Repair: {repair_contents}\n"
                    f"Causal Part: {causal_parts_name}\n"
                    f"Summary:"
                )
                summary = llm_client.generate_summary(prompt)
            except Exception as ex:
                print(f"LLM Summary failed for {ftir_no}, falling back to heuristic: {ex}")
                
        if not summary:
            summary = generate_heuristic_summary(row)
            
        # Write to DB
        cursor.execute("""
            INSERT INTO records (
                sbpr_no, ftir_no, ftir_report_date, reply_date, status, fc_ok, 
                product_model_code, sales_model_code, segmentation, vin, engine_no, 
                transmission_no, date_registered, date_of_incident, using_time_km, 
                reported_company, issued_company, outbreak_country, manufacturer_factory, 
                subject, c_measure, customer_complaint, trouble_code_complaint, 
                trouble_code_defect, checked_contents, checked_results, repair_status, 
                repair_contents, problem_solved, action_judgement, causal_parts_no, 
                causal_parts_name, supplier_of_causal_parts, production_base, 
                parts_availability, file_name, quality, row_hash, using_km_int, 
                report_year, report_month, is_resolved, has_sbpr, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sbpr_no, ftir_no, ftir_report_date, reply_date, status, fc_ok,
            product_model_code, sales_model_code, segmentation, vin, engine_no,
            transmission_no, date_registered, date_of_incident, using_time_km,
            reported_company, issued_company, outbreak_country, manufacturer_factory,
            subject, c_measure, customer_complaint, trouble_code_complaint,
            trouble_code_defect, checked_contents, checked_results, repair_status,
            repair_contents, problem_solved, action_judgement, causal_parts_no,
            causal_parts_name, supplier_of_causal_parts, production_base,
            parts_availability, file_name, quality, row_hash, using_km_int,
            report_year, report_month, is_resolved, has_sbpr, summary
        ))
        
        # Get inserted row id and values for returning
        row_id = cursor.lastrowid
        new_records.append({
            'id': row_id,
            'ftir_no': ftir_no,
            'outbreak_country': outbreak_country,
            'product_model_code': product_model_code,
            'segmentation': segmentation,
            'trouble_code_complaint': trouble_code_complaint,
            'subject': subject,
            'checked_results': checked_results,
            'repair_contents': repair_contents,
            'causal_parts_name': causal_parts_name,
            'summary': summary
        })
        
    conn.commit()
    conn.close()
    
    print(f"Ingested {len(new_records)} new records.")
    
    # Refresh materialized views if there were any updates
    if new_records:
        refresh_materialized_views(db_path)
        
    return new_records
