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
    
    # Normalize all string values and handle NaNs using a lambda expression
    clean_val = lambda x: str(x).strip() if not pd.isna(x) else None
    for col in df.columns:
        df[col] = df[col].apply(clean_val)
        
    # Ensure all required database fields exist in the DataFrame (initialize missing ones to None)
    required_cols = [
        'SBPR No', 'FTIR No', 'FTIR Report Date', 'Reply Date', 'Status', 'FC-OK', 
        'Product MODEL Code', 'Sales Model Code', 'Segmentation', 'VIN', 'Engine No', 
        'Transmission No', 'Date Registered', 'Date of Incident', 'Using Time (km)', 
        'Reported Company', 'Issued Company', 'Outbreak Country', 'Manufacturer Factory', 
        'Subject', 'C Measure', 'Customer Complaint', 'Trouble Code (Complaint)', 
        'Trouble Code Defect', 'Checked Contents', 'Checked Results', 'Repair Status', 
        'Repair Contents', 'Problem Solved', 'Action Judgement', 'Causal Parts No (Drawing Parts No)', 
        'Causal Parts Name', 'Supplier of Causal Parts', 'Production Base', 
        'Parts Availability', 'File Name', 'Quality'
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
    
    # Standardize dates
    df['FTIR Report Date'] = df['FTIR Report Date'].apply(parse_date)
    df['Reply Date'] = df['Reply Date'].apply(parse_date)
    df['Date Registered'] = df['Date Registered'].apply(parse_date)
    df['Date of Incident'] = df['Date of Incident'].apply(parse_date)
    
    # Computed columns
    df['using_km_int'] = df['Using Time (km)'].apply(clean_km)
    
    # Year/month extraction
    df['extracted_ym'] = df['FTIR Report Date'].apply(extract_year_month)
    df['report_year'] = df['extracted_ym'].apply(lambda x: x[0])
    df['report_month'] = df['extracted_ym'].apply(lambda x: x[1])
    
    # Compute resolved and sbpr flags using lambdas
    df['is_resolved'] = df['Problem Solved'].apply(lambda val: 1 if val and str(val).lower() in ('resolved', 'solved') else 0)
    df['has_sbpr'] = df['SBPR No'].apply(lambda val: 1 if val and str(val).lower() not in ('nan', '') else 0)
    
    # Connect to DB and fetch existing hashes and FTIRs to filter duplicates in batch
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT row_hash, ftir_no FROM records")
    existing_rows = cursor.fetchall()
    existing_hashes = {r[0] for r in existing_rows if r[0]}
    existing_ftirs = {str(r[1]).strip() for r in existing_rows if r[1]}
    
    # Filter out duplicate records
    df_new = df[~df['row_hash'].isin(existing_hashes) & ~df['FTIR No'].isin(existing_ftirs)]
    
    print(f"Filtered duplicates: {len(df_new)} new records to insert.")
    
    new_records = []
    
    # Insert new records
    for idx, row in df_new.iterrows():
        # Generate summary
        summary = None
        if llm_client:
            try:
                prompt = (
                    f"Summarize the following vehicle quality record in exactly 2 sentences. "
                    f"Highlight the issue and the repair action.\n"
                    f"Subject: {row['Subject']}\n"
                    f"Checked Results: {row['Checked Results']}\n"
                    f"Repair: {row['Repair Contents']}\n"
                    f"Causal Part: {row['Causal Parts Name']}\n"
                    f"Summary:"
                )
                summary = llm_client.generate_summary(prompt)
            except Exception as ex:
                print(f"LLM Summary failed for {row['FTIR No']}, falling back to heuristic: {ex}")
                
        if not summary:
            summary = generate_heuristic_summary(row)
            
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
            row['SBPR No'], row['FTIR No'], row['FTIR Report Date'], row['Reply Date'], row['Status'], row['FC-OK'],
            row['Product MODEL Code'], row['Sales Model Code'], row['Segmentation'], row['VIN'], row['Engine No'],
            row['Transmission No'], row['Date Registered'], row['Date of Incident'], row['Using Time (km)'],
            row['Reported Company'], row['Issued Company'], row['Outbreak Country'], row['Manufacturer Factory'],
            row['Subject'], row['C Measure'], row['Customer Complaint'], row['Trouble Code (Complaint)'],
            row['Trouble Code Defect'], row['Checked Contents'], row['Checked Results'], row['Repair Status'],
            row['Repair Contents'], row['Problem Solved'], row['Action Judgement'], row['Causal Parts No (Drawing Parts No)'],
            row['Causal Parts Name'], row['Supplier of Causal Parts'], row['Production Base'],
            row['Parts Availability'], row['File Name'], row['Quality'], row['row_hash'], row['using_km_int'],
            row['report_year'], row['report_month'], row['is_resolved'], row['has_sbpr'], summary
        ))
        
        row_id = cursor.lastrowid
        new_records.append({
            'id': row_id,
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
        
    conn.commit()
    conn.close()
    
    print(f"Ingested {len(new_records)} new records.")
    
    # Refresh materialized views if there were any updates
    if new_records:
        refresh_materialized_views(db_path)
        
    return new_records
