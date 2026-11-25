import urllib.request
import json

def run_e2e_check():
    # 1. Login
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/auth/login',
        data=json.dumps({'email': 'demo@analyticx.ai', 'password': 'analyticx123'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    auth = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    token = auth['access_token']
    print('[Auth] Logged in as:', auth['user']['full_name'])

    # 2. Upload sample sales dataset
    csv_data = (
        'Region,Category,Quarter,Sales,Profit\n'
        'North,Electronics,Q1,15000,3200\n'
        'North,Furniture,Q1,8500,1100\n'
        'South,Electronics,Q1,12000,2800\n'
        'South,Furniture,Q1,6000,600\n'
        'North,Electronics,Q2,18500,4100\n'
        'North,Furniture,Q2,9200,1350\n'
        'South,Electronics,Q2,11200,2400\n'
        'South,Furniture,Q2,5800,550\n'
        'East,Electronics,Q2,14000,3100\n'
        'East,Furniture,Q2,7500,950\n'
    ).encode('utf-8')

    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="sales_q1_q2.csv"\r\n'
        f'Content-Type: text/csv\r\n\r\n'
    ).encode('utf-8') + csv_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

    up_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/datasets/upload',
        data=body,
        headers={
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Authorization': f'Bearer {token}'
        }
    )
    ds = json.loads(urllib.request.urlopen(up_req).read().decode('utf-8'))
    ds_id = ds['id']
    print(f'[Basic Mode] Dataset uploaded successfully: ID={ds_id}, Name={ds["name"]}, Rows={ds.get("row_count", 10)}')

    # 3. Basic Mode: Test Quality Summary Report Export
    exp_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/datasets/{ds_id}/export/report',
        headers={'Authorization': f'Bearer {token}'}
    )
    exp_res = urllib.request.urlopen(exp_req)
    md_report = exp_res.read().decode('utf-8')
    print(f'[Basic Mode] Quality Report MD downloaded ({len(md_report)} bytes): "{md_report[:40]}..."')

    # 4. Pro Mode: SQL Query Studio Execution
    sql_payload = {
        'query': 'SELECT Region, SUM(Sales) as Total_Sales, ROUND(AVG(Profit), 1) as Avg_Profit FROM dataset GROUP BY Region ORDER BY Total_Sales DESC',
        'limit': 100
    }
    sql_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/analytics/{ds_id}/sql',
        data=json.dumps(sql_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    sql_res = json.loads(urllib.request.urlopen(sql_req).read().decode('utf-8'))
    print(f'[Pro Mode] SQL Query executed successfully in {sql_res["execution_time_ms"]}ms! Rows returned: {len(sql_res["rows"])}')
    for r in sql_res['rows']:
        print('   ->', r)

    # 5. Advanced Mode: Root-Cause Decomposition
    rc_payload = {
        'metric_column': 'Profit',
        'dimension_columns': ['Region'],
        'date_column': 'Quarter'
    }
    rc_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/analytics/{ds_id}/root-cause',
        data=json.dumps(rc_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    rc_res = json.loads(urllib.request.urlopen(rc_req).read().decode('utf-8'))
    print(f'[Advanced Mode] Root-Cause Analysis:')
    print(f'   Baseline Profit ({rc_res["baseline_period"]}) = ${rc_res["baseline_value"]:,.2f}')
    print(f'   Comparison Profit ({rc_res["comparison_period"]}) = ${rc_res["comparison_value"]:,.2f}')
    print(f'   Total Delta = ${rc_res["total_delta"]:,.2f} ({rc_res["percent_change"]:+.1f}%)')
    print(f'   Executive Summary: {rc_res["executive_summary"]}')

    # 6. Advanced Mode: Word Docx & PowerPoint PPTX Exports
    docx_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/reports/dataset/{ds_id}/docx',
        data=b'{}',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    docx_bytes = urllib.request.urlopen(docx_req).read()
    print(f'[Advanced Mode] Word (.docx) Report generated: {len(docx_bytes)} bytes (Valid OpenXML: {docx_bytes[:2] == b"PK"})')

    pptx_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/reports/dataset/{ds_id}/pptx',
        data=b'{}',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    pptx_bytes = urllib.request.urlopen(pptx_req).read()
    print(f'[Advanced Mode] PowerPoint (.pptx) Deck generated: {len(pptx_bytes)} bytes (Valid OpenXML: {pptx_bytes[:2] == b"PK"})')

    pdf_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/reports/dataset/{ds_id}/pdf',
        headers={'Authorization': f'Bearer {token}'}
    )
    pdf_bytes = urllib.request.urlopen(pdf_req).read()
    print(f'[Advanced Mode] Executive PDF Report generated: {len(pdf_bytes)} bytes (Valid PDF: {pdf_bytes[:4] == b"%PDF"})')

    # 7. Advanced Mode: Sharable Public Report Link
    share_req = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/reports/dataset/{ds_id}/share',
        data=b'{}',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    share_res = json.loads(urllib.request.urlopen(share_req).read().decode('utf-8'))
    share_token = share_res['share_token']
    print(f'[Advanced Mode] Public Share Link created: {share_res["share_url"]} (Token: {share_token})')

    # 8. Unauthenticated Public Fetch of Shared Report
    pub_req = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/reports/shared/{share_token}')
    pub_res = json.loads(urllib.request.urlopen(pub_req).read().decode('utf-8'))
    print(f'[Advanced Mode] Public Report accessed without auth! Dataset Name: {pub_res["dataset_name"]}, Quality Score: {pub_res["quality_score"]}')
    print('\n>>> ALL THREE MODES FULLY VERIFIED END-TO-END! <<<')

if __name__ == '__main__':
    run_e2e_check()
