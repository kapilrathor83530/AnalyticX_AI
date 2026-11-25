# Power BI (Optional)

The native Analyticx AI dashboard is always available. Power BI is optional.

## Options

1. **Publish to Power BI Service** and embed with a Power BI Embedded license.
   - Requires Azure AD app registration.
   - Requires a capacity (A or EM SKU).

2. **Power BI REST API push dataset**
   - Push rows to a Power BI dataset.
   - Requires service principal credentials.

3. **Local PBIX manual refresh**
   - Export cleaned CSV from `/api/v1/reports/dataset/{id}/csv`.
   - Open PBIX, refresh the connection.

## What this project does NOT do

- It does not silently update your Power BI report when a dataset changes.
- It does not bypass licensing.
- It does not embed Power BI in the default UI.

If you want an embedded tile, add a `<PowerBIEmbed />` React component using the `powerbi-client-react` package and pass your own group/dataset/report IDs from environment variables.
16. Alembic Migration for New Tables
