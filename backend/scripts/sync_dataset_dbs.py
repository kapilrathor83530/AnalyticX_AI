import sqlite3
import shutil
import os
import json
from pathlib import Path

# Ensure paths exist
Path('storage/uploads').mkdir(parents=True, exist_ok=True)
Path('backend/storage/uploads').mkdir(parents=True, exist_ok=True)
csv_src = Path('backend/storage/uploads/btech_aiml_sem6_results.csv')
csv_dst = Path('storage/uploads/btech_aiml_sem6_results.csv')

if csv_src.exists():
    shutil.copy(csv_src, csv_dst)
elif csv_dst.exists():
    shutil.copy(csv_dst, csv_src)

file_size = os.path.getsize(csv_dst)

for db_path in ['analyticx.db', 'backend/analyticx.db']:
    if not os.path.exists(db_path):
        continue
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check if dataset 197 or btech dataset exists
    cur.execute("SELECT id FROM datasets WHERE name LIKE '%B.Tech%AI/ML%'")
    row = cur.fetchone()
    stored_path = 'storage/uploads/btech_aiml_sem6_results.csv'
    
    if row:
        ds_id = row[0]
        cur.execute("""
            UPDATE datasets 
            SET name='B.Tech AI/ML 6th Sem Results (68 Students)', 
                stored_path=?, 
                row_count=68, 
                column_count=22, 
                size_bytes=?, 
                quality_score=98.5, 
                is_sample=1 
            WHERE id=?
        """, (stored_path, file_size, ds_id))
    else:
        cur.execute("""
            INSERT INTO datasets (
                name, original_filename, stored_path, size_bytes, 
                row_count, column_count, status, quality_score, is_sample, version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'Analysis Ready', 98.5, 1, 1, datetime('now'))
        """, (
            'B.Tech AI/ML 6th Sem Results (68 Students)', 
            'btech_aiml_sem6_results.csv', 
            stored_path, 
            file_size, 
            68, 
            22
        ))
        ds_id = cur.lastrowid
    
    # Make sure dashboard exists
    cur.execute("SELECT id FROM dashboards WHERE dataset_id = ?", (ds_id,))
    dash_row = cur.fetchone()
    if not dash_row:
        cur.execute("""
            INSERT INTO dashboards (
                dataset_id, name, description, is_default, created_at, updated_at
            ) VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
        """, (
            ds_id,
            "Student Performance & Examination Analytics (B.Tech AI/ML)",
            "Comprehensive BI dashboard for 6th Semester student results."
        ))
        dash_id = cur.lastrowid
    else:
        dash_id = dash_row[0]
    
    # Widgets
    cur.execute("DELETE FROM widgets WHERE dashboard_id = ?", (dash_id,))
    widgets = [
        (dash_id, "bar", "SGPA Distribution Across Cohort", json.dumps({"xAxis": "Performance_Tier", "yAxis": "Student_Name", "aggregation": "count"}), json.dumps({"x": "Performance_Tier", "y": "count"}), json.dumps({"x": 0, "y": 0}), json.dumps({"w": 6, "h": 4})),
        (dash_id, "bar", "Top 10 Students by SGPA", json.dumps({"xAxis": "Student_Name", "yAxis": "SGPA", "aggregation": "max", "sort": "desc", "limit": 10}), json.dumps({"x": "Student_Name", "y": "SGPA"}), json.dumps({"x": 6, "y": 0}), json.dumps({"w": 6, "h": 4})),
        (dash_id, "pie", "Result Status Breakdown (Pass vs Reappear vs UMC)", json.dumps({"category": "Result_Status", "value": "Student_Name", "aggregation": "count"}), json.dumps({"category": "Result_Status", "value": "count"}), json.dumps({"x": 0, "y": 4}), json.dumps({"w": 4, "h": 4})),
        (dash_id, "bar", "Core Subject Total Scores Comparison", json.dumps({"measures": ["Compiler_Design_Total", "Adv_Networks_Total", "Management_OB_Total", "ME3_Data_Analytics_Total", "Capstone_Project_Total"], "aggregation": "mean"}), json.dumps({"type": "multimeasure"}), json.dumps({"x": 4, "y": 4}), json.dumps({"w": 8, "h": 4})),
        (dash_id, "line", "Cumulative SGPA Trend Across Students", json.dumps({"xAxis": "Rank", "yAxis": "SGPA", "sort": "asc"}), json.dumps({"x": "Rank", "y": "SGPA"}), json.dumps({"x": 0, "y": 8}), json.dumps({"w": 12, "h": 4}))
    ]
    cur.executemany("""
        INSERT INTO widgets (
            dashboard_id, chart_type, title, config, data_mapping, position, size, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, widgets)

    conn.commit()
    conn.close()
    print(f"Successfully synced {db_path}: dataset ID {ds_id}, dashboard ID {dash_id}")
