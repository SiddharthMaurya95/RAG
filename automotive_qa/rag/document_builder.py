def build_document_text(record):
    """
    Concatenates the key descriptive columns of a record into a single structured text block.
    This creates an informative text document for generating vector embeddings.
    """
    subject = str(record.get('subject', '') or record.get('Subject', '')).strip()
    complaint = str(record.get('customer_complaint', '') or record.get('Customer Complaint', '')).strip()
    checked_contents = str(record.get('checked_contents', '') or record.get('Checked Contents', '')).strip()
    checked_results = str(record.get('checked_results', '') or record.get('Checked Results', '')).strip()
    repair_contents = str(record.get('repair_contents', '') or record.get('Repair Contents', '')).strip()
    causal_parts_name = str(record.get('causal_parts_name', '') or record.get('Causal Parts Name', '')).strip()

    # Normalize nan strings
    subject = subject if subject.lower() != 'nan' else ''
    complaint = complaint if complaint.lower() != 'nan' else ''
    checked_contents = checked_contents if checked_contents.lower() != 'nan' else ''
    checked_results = checked_results if checked_results.lower() != 'nan' else ''
    repair_contents = repair_contents if repair_contents.lower() != 'nan' else ''
    causal_parts_name = causal_parts_name if causal_parts_name.lower() != 'nan' else ''

    doc_parts = []
    if subject:
        doc_parts.append(f"Subject: {subject}")
    if complaint:
        doc_parts.append(f"Customer Complaint: {complaint}")
    if checked_contents:
        doc_parts.append(f"Checked Contents: {checked_contents}")
    if checked_results:
        doc_parts.append(f"Checked Results: {checked_results}")
    if repair_contents:
        doc_parts.append(f"Repair Contents: {repair_contents}")
    if causal_parts_name:
        doc_parts.append(f"Causal Part Name: {causal_parts_name}")

    return "\n".join(doc_parts)
