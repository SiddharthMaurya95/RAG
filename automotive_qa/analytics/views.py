import sqlite3
import os

def refresh_materialized_views(db_path):
    """
    Clears and rebuilds all simulated materialized views from the raw 'records' table.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Start transaction
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Refresh mv_country_month
        cursor.execute("DELETE FROM mv_country_month;")
        cursor.execute("""
            INSERT INTO mv_country_month (outbreak_country, report_year, report_month, record_count)
            SELECT 
                COALESCE(outbreak_country, 'Unknown') as outbreak_country, 
                COALESCE(report_year, 0) as report_year, 
                COALESCE(report_month, 0) as report_month, 
                COUNT(*) as record_count
            FROM records
            GROUP BY outbreak_country, report_year, report_month;
        """)

        # 2. Refresh mv_trouble_codes
        cursor.execute("DELETE FROM mv_trouble_codes;")
        cursor.execute("""
            INSERT INTO mv_trouble_codes (trouble_code, record_count)
            SELECT 
                COALESCE(trouble_code_complaint, 'Unknown') as trouble_code, 
                COUNT(*) as record_count
            FROM records
            WHERE trouble_code_complaint IS NOT NULL AND trouble_code_complaint != ''
            GROUP BY trouble_code_complaint;
        """)

        # 3. Refresh mv_dealer_summary
        cursor.execute("DELETE FROM mv_dealer_summary;")
        cursor.execute("""
            INSERT INTO mv_dealer_summary (reported_company, record_count)
            SELECT 
                COALESCE(reported_company, 'Unknown') as reported_company, 
                COUNT(*) as record_count
            FROM records
            WHERE reported_company IS NOT NULL AND reported_company != ''
            GROUP BY reported_company;
        """)

        # 4. Refresh mv_quality_dist
        cursor.execute("DELETE FROM mv_quality_dist;")
        cursor.execute("""
            INSERT INTO mv_quality_dist (quality, record_count)
            SELECT 
                COALESCE(quality, 'Unknown') as quality, 
                COUNT(*) as record_count
            FROM records
            GROUP BY quality;
        """)

        # 5. Refresh mv_escalations (Quality = 'Poor' AND unresolved problem)
        cursor.execute("DELETE FROM mv_escalations;")
        cursor.execute("""
            INSERT INTO mv_escalations (id, ftir_no, subject, reported_company, outbreak_country, trouble_code_complaint, quality, problem_solved)
            SELECT 
                id, 
                ftir_no, 
                subject, 
                reported_company, 
                outbreak_country, 
                trouble_code_complaint, 
                quality, 
                problem_solved
            FROM records
            WHERE LOWER(quality) = 'poor' AND is_resolved = 0;
        """)

        conn.commit()
        print("Materialized views refreshed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error refreshing materialized views: {e}")
        raise e
    finally:
        conn.close()
