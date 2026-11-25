export interface TemplateConfigField {
  key: string
  label: string
  type: 'numeric_column' | 'categorical_column' | 'date_column' | 'any_column' | 'number' | 'text' | 'agg_method'
  defaultValue?: string | number
  options?: string[]
}

export interface SQLTemplateItem {
  id: string
  title: string
  category:
    | 'Basic'
    | 'Filtering'
    | 'Sorting & Limiting'
    | 'Aggregations'
    | 'Data Quality'
    | 'String Operations'
    | 'Date & Time'
    | 'Joins & CTEs'
    | 'Advanced Analytics'
  description: string
  requiresConfig: boolean
  configFields?: TemplateConfigField[]
  generateQuery: (params: Record<string, any>, defaultTable?: string) => string
}

export const SQL_COMMAND_TEMPLATES: SQLTemplateItem[] = [
  // --- A. BASIC QUERIES ---
  {
    id: 'select_all',
    title: 'Select All Records',
    category: 'Basic',
    description: 'Retrieves all columns and rows from the dataset up to preview limit.',
    requiresConfig: false,
    generateQuery: (_, table = 'dataset') => `SELECT *\nFROM ${table}\nLIMIT 50;`,
  },
  {
    id: 'select_first_n',
    title: 'Select First N Records',
    category: 'Basic',
    description: 'Quick inspection of the first N rows with limit constraint.',
    requiresConfig: true,
    configFields: [{ key: 'limit', label: 'Number of Rows', type: 'number', defaultValue: 25 }],
    generateQuery: (p, table = 'dataset') => `SELECT *\nFROM ${table}\nLIMIT ${p.limit || 25};`,
  },
  {
    id: 'count_total_rows',
    title: 'Count Total Records',
    category: 'Basic',
    description: 'Computes the total number of records present in the table.',
    requiresConfig: false,
    generateQuery: (_, table = 'dataset') => `SELECT COUNT(*) AS total_records\nFROM ${table};`,
  },
  {
    id: 'select_distinct_values',
    title: 'Select Distinct Column Values',
    category: 'Basic',
    description: 'Lists all unique distinct values from a specified column.',
    requiresConfig: true,
    configFields: [
      { key: 'column', label: 'Column Name', type: 'any_column' },
      { key: 'limit', label: 'Max Results', type: 'number', defaultValue: 50 },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT DISTINCT "${p.column || 'column_name'}"\nFROM ${table}\nORDER BY 1 ASC\nLIMIT ${p.limit || 50};`,
  },
  {
    id: 'count_distinct_values',
    title: 'Count Distinct Values in Column',
    category: 'Basic',
    description: 'Calculates the cardinality (distinct count) of a column.',
    requiresConfig: true,
    configFields: [{ key: 'column', label: 'Target Column', type: 'any_column' }],
    generateQuery: (p, table = 'dataset') =>
      `SELECT COUNT(DISTINCT "${p.column || 'column_name'}") AS unique_values_count\nFROM ${table};`,
  },

  // --- B. FILTERING ---
  {
    id: 'filter_equals',
    title: 'Filter by Exact Value',
    category: 'Filtering',
    description: 'Filters rows where a column equals a specific value.',
    requiresConfig: true,
    configFields: [
      { key: 'column', label: 'Target Column', type: 'any_column' },
      { key: 'value', label: 'Match Value', type: 'text', defaultValue: 'Active' },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT *\nFROM ${table}\nWHERE "${p.column || 'column_name'}" = '${p.value || ''}'\nLIMIT 100;`,
  },
  {
    id: 'filter_greater_than',
    title: 'Filter Numerical Threshold (> / <)',
    category: 'Filtering',
    description: 'Filters rows exceeding or falling below a numerical threshold.',
    requiresConfig: true,
    configFields: [
      { key: 'column', label: 'Numeric Column', type: 'numeric_column' },
      { key: 'threshold', label: 'Threshold Value', type: 'number', defaultValue: 100 },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT *\nFROM ${table}\nWHERE "${p.column || 'numeric_col'}" > ${p.threshold || 0}\nORDER BY "${p.column || 'numeric_col'}" DESC\nLIMIT 100;`,
  },
  {
    id: 'filter_between_range',
    title: 'Filter Values in Range (BETWEEN)',
    category: 'Filtering',
    description: 'Retrieves records bounded within an inclusive numerical or date range.',
    requiresConfig: true,
    configFields: [
      { key: 'column', label: 'Column Name', type: 'any_column' },
      { key: 'min_val', label: 'Minimum Bound', type: 'number', defaultValue: 10 },
      { key: 'max_val', label: 'Maximum Bound', type: 'number', defaultValue: 100 },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT *\nFROM ${table}\nWHERE "${p.column || 'metric'}" BETWEEN ${p.min_val || 0} AND ${p.max_val || 100}\nLIMIT 100;`,
  },
  {
    id: 'filter_is_null',
    title: 'Filter Missing / NULL Records',
    category: 'Filtering',
    description: 'Finds rows where a specific column is NULL or empty string.',
    requiresConfig: true,
    configFields: [{ key: 'column', label: 'Column to Check', type: 'any_column' }],
    generateQuery: (p, table = 'dataset') =>
      `SELECT *\nFROM ${table}\nWHERE "${p.column || 'column_name'}" IS NULL OR "${p.column || 'column_name'}" = ''\nLIMIT 50;`,
  },

  // --- C. SORTING & LIMITING ---
  {
    id: 'order_by_desc',
    title: 'Sort by Column Descending',
    category: 'Sorting & Limiting',
    description: 'Sorts all records from highest to lowest by a chosen column.',
    requiresConfig: true,
    configFields: [
      { key: 'column', label: 'Sort Column', type: 'any_column' },
      { key: 'limit', label: 'Limit Rows', type: 'number', defaultValue: 25 },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT *\nFROM ${table}\nORDER BY "${p.column || 'column_name'}" DESC\nLIMIT ${p.limit || 25};`,
  },
  {
    id: 'top_n_records',
    title: 'Top N Highest Records',
    category: 'Sorting & Limiting',
    description: 'Retrieves the top N records with highest values in a numeric column.',
    requiresConfig: true,
    configFields: [
      { key: 'metric', label: 'Metric Column', type: 'numeric_column' },
      { key: 'limit', label: 'Top N Limit', type: 'number', defaultValue: 10 },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT *\nFROM ${table}\nORDER BY "${p.metric || 'metric'}" DESC\nLIMIT ${p.limit || 10};`,
  },

  // --- D. AGGREGATIONS ---
  {
    id: 'group_by_sum_avg',
    title: 'Group By Category & Aggregate (SUM & AVG)',
    category: 'Aggregations',
    description: 'Groups records by a dimension and computes cumulative sums and averages.',
    requiresConfig: true,
    configFields: [
      { key: 'dim_col', label: 'Grouping Dimension', type: 'categorical_column' },
      { key: 'metric_col', label: 'Metric Column', type: 'numeric_column' },
      { key: 'limit', label: 'Max Groups', type: 'number', defaultValue: 20 },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT "${p.dim_col || 'category'}",\n       COUNT(*) AS total_count,\n       ROUND(SUM("${p.metric_col || 'metric'}"), 2) AS total_${String(p.metric_col || 'metric').toLowerCase()},\n       ROUND(AVG("${p.metric_col || 'metric'}"), 2) AS avg_${String(p.metric_col || 'metric').toLowerCase()}\nFROM ${table}\nGROUP BY "${p.dim_col || 'category'}"\nORDER BY total_${String(p.metric_col || 'metric').toLowerCase()} DESC\nLIMIT ${p.limit || 20};`,
  },
  {
    id: 'having_filter_aggregation',
    title: 'Filter Aggregated Groups with HAVING',
    category: 'Aggregations',
    description: 'Filters grouped totals exceeding a minimum threshold condition.',
    requiresConfig: true,
    configFields: [
      { key: 'dim_col', label: 'Grouping Dimension', type: 'categorical_column' },
      { key: 'metric_col', label: 'Metric Column', type: 'numeric_column' },
      { key: 'min_total', label: 'Minimum Total Sum', type: 'number', defaultValue: 1000 },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT "${p.dim_col || 'category'}",\n       COUNT(*) AS frequency,\n       ROUND(SUM("${p.metric_col || 'metric'}"), 2) AS cumulative_metric\nFROM ${table}\nGROUP BY "${p.dim_col || 'category'}"\nHAVING SUM("${p.metric_col || 'metric'}") > ${p.min_total || 1000}\nORDER BY cumulative_metric DESC;`,
  },
  {
    id: 'five_number_summary_metrics',
    title: 'Descriptive Metrics (Min, Max, Avg, Count)',
    category: 'Aggregations',
    description: 'Calculates complete descriptive summary statistics for a numeric metric.',
    requiresConfig: true,
    configFields: [{ key: 'metric_col', label: 'Numeric Metric', type: 'numeric_column' }],
    generateQuery: (p, table = 'dataset') =>
      `SELECT COUNT("${p.metric_col || 'metric'}") AS non_null_count,\n       ROUND(AVG("${p.metric_col || 'metric'}"), 2) AS mean_value,\n       ROUND(MIN("${p.metric_col || 'metric'}"), 2) AS min_value,\n       ROUND(MAX("${p.metric_col || 'metric'}"), 2) AS max_value,\n       ROUND(MAX("${p.metric_col || 'metric'}") - MIN("${p.metric_col || 'metric'}"), 2) AS range_span\nFROM ${table};`,
  },

  // --- E. DATA QUALITY ---
  {
    id: 'audit_all_missing_cells',
    title: 'Data Quality: Audit Nulls Across Columns',
    category: 'Data Quality',
    description: 'Scans and sums missing / NULL counts across primary columns.',
    requiresConfig: false,
    generateQuery: (_, table = 'dataset') =>
      `SELECT\n  COUNT(*) AS total_rows,\n  SUM(CASE WHEN rowid IS NULL THEN 1 ELSE 0 END) AS null_rowids\nFROM ${table};`,
  },
  {
    id: 'find_duplicate_rows_by_key',
    title: 'Find Duplicate Occurrences by Key Column',
    category: 'Data Quality',
    description: 'Identifies values that appear more than once in an identifier column.',
    requiresConfig: true,
    configFields: [{ key: 'column', label: 'Identifier Column', type: 'any_column' }],
    generateQuery: (p, table = 'dataset') =>
      `SELECT "${p.column || 'id'}", COUNT(*) AS occurrences\nFROM ${table}\nGROUP BY "${p.column || 'id'}"\nHAVING COUNT(*) > 1\nORDER BY occurrences DESC\nLIMIT 25;`,
  },
  {
    id: 'detect_outliers_2sigma',
    title: 'Outlier Detection (2-Sigma Statistical Bounds)',
    category: 'Data Quality',
    description: 'Identifies records deviating more than 2 standard deviations from mean.',
    requiresConfig: true,
    configFields: [{ key: 'metric', label: 'Target Numeric Metric', type: 'numeric_column' }],
    generateQuery: (p, table = 'dataset') => {
      const col = p.metric || 'val'
      return `WITH stats AS (\n  SELECT AVG("${col}") AS mean_val,\n         AVG("${col}") + 2.0 * SQRT(AVG("${col}"*"${col}") - AVG("${col}")*AVG("${col}")) AS upper_bound\n  FROM ${table}\n)\nSELECT d.*, ROUND(d."${col}", 2) AS outlier_value\nFROM ${table} d, stats\nWHERE d."${col}" > stats.upper_bound\nORDER BY d."${col}" DESC\nLIMIT 25;`
    },
  },

  // --- F. STRING OPERATIONS ---
  {
    id: 'search_text_like',
    title: 'Pattern Search (LIKE %text%)',
    category: 'String Operations',
    description: 'Searches for text containing a case-insensitive pattern.',
    requiresConfig: true,
    configFields: [
      { key: 'column', label: 'Text Column', type: 'categorical_column' },
      { key: 'search_term', label: 'Search Term', type: 'text', defaultValue: 'tech' },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT *\nFROM ${table}\nWHERE LOWER("${p.column || 'text_col'}") LIKE '%${String(p.search_term || '').toLowerCase()}%'\nLIMIT 50;`,
  },
  {
    id: 'convert_text_uppercase',
    title: 'Text Standardization (UPPER & TRIM)',
    category: 'String Operations',
    description: 'Cleans whitespace and standardizes column text to uppercase.',
    requiresConfig: true,
    configFields: [{ key: 'column', label: 'Text Column', type: 'categorical_column' }],
    generateQuery: (p, table = 'dataset') =>
      `SELECT "${p.column || 'col'}", UPPER(TRIM("${p.column || 'col'}")) AS cleaned_text, COUNT(*) AS count\nFROM ${table}\nGROUP BY cleaned_text\nORDER BY count DESC\nLIMIT 25;`,
  },

  // --- G. DATE & TIME ---
  {
    id: 'group_by_month_trend',
    title: 'Monthly Trend Aggregation (strftime)',
    category: 'Date & Time',
    description: 'Groups chronological records by YYYY-MM and calculates monthly totals.',
    requiresConfig: true,
    configFields: [
      { key: 'date_col', label: 'Date Column', type: 'date_column' },
      { key: 'metric_col', label: 'Metric Column', type: 'numeric_column' },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT strftime('%Y-%m', "${p.date_col || 'date_col'}") AS month,\n       COUNT(*) AS transaction_volume,\n       ROUND(SUM("${p.metric_col || 'metric'}"), 2) AS monthly_total\nFROM ${table}\nWHERE "${p.date_col || 'date_col'}" IS NOT NULL\nGROUP BY month\nORDER BY month ASC;`,
  },
  {
    id: 'filter_recent_date_range',
    title: 'Date Range Chronological Filter',
    category: 'Date & Time',
    description: 'Filters records occurring within a specific start and end date interval.',
    requiresConfig: true,
    configFields: [
      { key: 'date_col', label: 'Date Column', type: 'date_column' },
      { key: 'start_date', label: 'Start Date (YYYY-MM-DD)', type: 'text', defaultValue: '2024-01-01' },
      { key: 'end_date', label: 'End Date (YYYY-MM-DD)', type: 'text', defaultValue: '2024-12-31' },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT *\nFROM ${table}\nWHERE date("${p.date_col || 'date_col'}") BETWEEN '${p.start_date || '2024-01-01'}' AND '${p.end_date || '2024-12-31'}'\nORDER BY "${p.date_col || 'date_col'}" ASC\nLIMIT 100;`,
  },

  // --- H. JOINS & CTES ---
  {
    id: 'cte_pre_aggregation_summary',
    title: 'Common Table Expression (CTE) Summary',
    category: 'Joins & CTEs',
    description: 'Pre-aggregates segment metrics in a WITH clause and filters top performers.',
    requiresConfig: true,
    configFields: [
      { key: 'dim_col', label: 'Dimension Column', type: 'categorical_column' },
      { key: 'metric_col', label: 'Metric Column', type: 'numeric_column' },
    ],
    generateQuery: (p, table = 'dataset') =>
      `WITH segment_totals AS (\n  SELECT "${p.dim_col || 'category'}" AS entity,\n         COUNT(*) AS count,\n         ROUND(SUM("${p.metric_col || 'sales'}"), 2) AS total_val\n  FROM ${table}\n  GROUP BY "${p.dim_col || 'category'}"\n)\nSELECT entity, count, total_val\nFROM segment_totals\nWHERE total_val > 0\nORDER BY total_val DESC\nLIMIT 20;`,
  },

  // --- I. ADVANCED ANALYTICS ---
  {
    id: 'case_when_segmentation',
    title: 'Conditional Segmentation (CASE WHEN Tiering)',
    category: 'Advanced Analytics',
    description: 'Segments records into High, Medium, and Low tiers based on metric thresholds.',
    requiresConfig: true,
    configFields: [
      { key: 'metric_col', label: 'Numerical Metric', type: 'numeric_column' },
      { key: 'tier_high', label: 'High Tier Threshold', type: 'number', defaultValue: 1000 },
      { key: 'tier_mid', label: 'Mid Tier Threshold', type: 'number', defaultValue: 500 },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT\n  CASE\n    WHEN "${p.metric_col || 'sales'}" >= ${p.tier_high || 1000} THEN 'Tier 1 - High Value'\n    WHEN "${p.metric_col || 'sales'}" >= ${p.tier_mid || 500} THEN 'Tier 2 - Medium Value'\n    ELSE 'Tier 3 - Standard'\n  END AS customer_tier,\n  COUNT(*) AS total_count,\n  ROUND(SUM("${p.metric_col || 'sales'}"), 2) AS tier_revenue\nFROM ${table}\nGROUP BY customer_tier\nORDER BY tier_revenue DESC;`,
  },
  {
    id: 'cumulative_running_total',
    title: 'Cumulative Running Total (Window Function)',
    category: 'Advanced Analytics',
    description: 'Computes progressive running total across records using window SUM() OVER().',
    requiresConfig: true,
    configFields: [
      { key: 'date_col', label: 'Chronology Column', type: 'date_column' },
      { key: 'metric_col', label: 'Metric Column', type: 'numeric_column' },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT "${p.date_col || 'date'}",\n       "${p.metric_col || 'sales'}",\n       ROUND(SUM("${p.metric_col || 'sales'}") OVER (ORDER BY "${p.date_col || 'date'}" ASC), 2) AS cumulative_running_total\nFROM ${table}\nWHERE "${p.date_col || 'date'}" IS NOT NULL\nLIMIT 50;`,
  },
  {
    id: 'ranking_dense_rank_window',
    title: 'Dense Rank Window Partition',
    category: 'Advanced Analytics',
    description: 'Assigns positional rankings (1, 2, 3...) per category using DENSE_RANK() OVER().',
    requiresConfig: true,
    configFields: [
      { key: 'cat_col', label: 'Partition Category', type: 'categorical_column' },
      { key: 'metric_col', label: 'Ranking Metric', type: 'numeric_column' },
    ],
    generateQuery: (p, table = 'dataset') =>
      `SELECT "${p.cat_col || 'category'}",\n       "${p.metric_col || 'sales'}",\n       DENSE_RANK() OVER (PARTITION BY "${p.cat_col || 'category'}" ORDER BY "${p.metric_col || 'sales'}" DESC) AS category_rank\nFROM ${table}\nLIMIT 50;`,
  },
]
