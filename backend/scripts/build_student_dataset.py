import csv
import json
import os
from pathlib import Path
import sqlite3
import pandas as pd

raw_path = Path("backend/storage/raw_results.txt")
out_csv = Path("backend/storage/uploads/btech_aiml_sem6_results.csv")
out_csv.parent.mkdir(parents=True, exist_ok=True)

rows_data = []

def clean_val(v):
    if v is None:
        return None
    v = v.strip()
    if v in ("-", "AB", "UMC", "", "F"):
        return None
    try:
        return float(v)
    except:
        return None

with open(raw_path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        if not row or not row[0].isdigit():
            continue

        sr_no = int(row[0])
        roll = row[1].strip()
        name = row[2].strip()

        cd_int = clean_val(row[3])
        cd_ext = clean_val(row[4])
        cd_grade = row[5].strip()
        cd_tot = (cd_int or 0) + (cd_ext or 0) if (cd_int is not None or cd_ext is not None) else None

        net_int = clean_val(row[6])
        net_ext = clean_val(row[7])
        net_grade = row[8].strip()
        net_tot = (net_int or 0) + (net_ext or 0) if (net_int is not None or net_ext is not None) else None

        mgmt_int = clean_val(row[9])
        mgmt_ext = clean_val(row[10])
        mgmt_grade = row[11].strip()
        mgmt_tot = (mgmt_int or 0) + (mgmt_ext or 0) if (mgmt_int is not None or mgmt_ext is not None) else None

        me3_int = clean_val(row[12])
        me3_ext = clean_val(row[13])
        me3_grade = row[14].strip()
        me3_tot = (me3_int or 0) + (me3_ext or 0) if (me3_int is not None or me3_ext is not None) else None

        me4_int = clean_val(row[15])
        me4_ext = clean_val(row[16])
        me4_grade = row[17].strip()
        me4_tot = (me4_int or 0) + (me4_ext or 0) if (me4_int is not None or me4_ext is not None) else None

        lab_int = clean_val(row[18])
        lab_ext = clean_val(row[19])
        lab_grade = row[20].strip() if row[20].strip() != "-" else None
        lab_tot = (lab_int or 0) + (lab_ext or 0) if (lab_int is not None or lab_ext is not None) else None

        proj_int = clean_val(row[21])
        proj_ext = clean_val(row[22])
        proj_grade = row[23].strip()
        proj_tot = (proj_int or 0) + (proj_ext or 0) if (proj_int is not None or proj_ext is not None) else None

        sgpa_raw = row[24].strip() if len(row) > 24 else ""

        status = "Pass"
        sgpa = None
        if "RE-" in sgpa_raw or "F" in (cd_grade, net_grade, mgmt_grade, me3_grade, me4_grade):
            status = "Reappear"
        elif "UMC" in sgpa_raw or "UMC" in (cd_grade, net_grade, mgmt_grade):
            status = "UMC"
        elif "AB" in (cd_grade, net_grade, mgmt_grade, sgpa_raw):
            status = "Absent"

        try:
            sgpa = float(sgpa_raw)
            status = "Pass"
        except:
            pass

        tot_marks = sum(filter(None, [cd_tot, net_tot, mgmt_tot, me3_tot, me4_tot, lab_tot, proj_tot]))

        tier = "Pending"
        if sgpa:
            if sgpa >= 9.0:
                tier = "Outstanding (≥ 9.0)"
            elif sgpa >= 8.5:
                tier = "Distinction (8.5 - 8.99)"
            elif sgpa >= 8.0:
                tier = "First Class with Merit (8.0 - 8.49)"
            elif sgpa >= 7.5:
                tier = "First Class (7.5 - 7.99)"
            else:
                tier = "Second Class (< 7.5)"
        else:
            tier = f"{status}"

        rows_data.append({
            "Roll_Number": roll,
            "Student_Name": name,
            "Compiler_Design_Total": cd_tot,
            "Compiler_Design_Grade": cd_grade,
            "Adv_Networks_Total": net_tot,
            "Adv_Networks_Grade": net_grade,
            "Management_OB_Total": mgmt_tot,
            "Management_OB_Grade": mgmt_grade,
            "ME3_Data_Analytics_Total": me3_tot,
            "ME3_Data_Analytics_Grade": me3_grade,
            "ME4_Security_Mining_Total": me4_tot,
            "ME4_Security_Mining_Grade": me4_grade,
            "Analytics_Lab_Total": lab_tot,
            "Analytics_Lab_Grade": lab_grade,
            "Capstone_Project_Total": proj_tot,
            "Capstone_Project_Grade": proj_grade,
            "Total_Marks": tot_marks,
            "SGPA": sgpa,
            "Result_Status": status,
            "Performance_Tier": tier,
            "Remarks": sgpa_raw.replace("\n", " "),
        })

df = pd.DataFrame(rows_data)
df["Rank"] = df["SGPA"].rank(ascending=False, method="min")
df.to_csv(out_csv, index=False)
print(f"Clean CSV saved: {out_csv} ({len(df)} rows, {len(df.columns)} columns)")

# Insert or update in SQLite database
db_path = "backend/analyticx.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check if dataset already registered
cur.execute("SELECT id FROM datasets WHERE name LIKE '%B.Tech%AI/ML%'")
existing = cur.fetchone()

file_size = os.path.getsize(out_csv)

if existing:
    ds_id = existing[0]
    cur.execute("""
        UPDATE datasets 
        SET stored_path = ?, row_count = ?, column_count = ?, size_bytes = ?, quality_score = 98.5, is_sample = 1
        WHERE id = ?
    """, (str(out_csv), len(df), len(df.columns), file_size, ds_id))
    print(f"Updated existing dataset ID: {ds_id}")
else:
    cur.execute("""
        INSERT INTO datasets (
            name, original_filename, stored_path, size_bytes, 
            row_count, column_count, status, quality_score, is_sample, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'Analysis Ready', 98.5, 1, datetime('now'))
    """, (
        "B.Tech AI/ML 6th Sem Results (68 Students)",
        "btech_aiml_sem6_results.csv",
        str(out_csv),
        file_size,
        len(df),
        len(df.columns)
    ))
    ds_id = cur.lastrowid
    print(f"Inserted new dataset ID: {ds_id}")

conn.commit()

# Create or Update Dashboard for this dataset
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
        "Comprehensive BI dashboard for 6th Semester student results, SGPA distribution, subject comparisons, and topper ranking."
    ))
    dash_id = cur.lastrowid
    print(f"Created dashboard ID: {dash_id}")
else:
    dash_id = dash_row[0]
    print(f"Using dashboard ID: {dash_id}")

# Register widgets for this dashboard
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
print(f"Registered {len(widgets)} interactive widgets in dashboard ID {dash_id}")
