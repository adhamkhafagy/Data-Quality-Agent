import streamlit as st
import pandas as pd
import json
from groq import Groq
import os
from dotenv import load_dotenv

# ---------- Setup ----------
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

st.title("Automated Data Quality Agent")


# ---------- File Reading ----------
def read_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Unsupported file format. Please upload a .csv or .xlsx file.")
    return df


# ---------- Column Masking ----------
def mask_columns(df):
    original_columns = df.columns.tolist()
    masked_columns = [f"col_{i+1}" for i in range(len(original_columns))]
    mapping = dict(zip(masked_columns, original_columns))

    masked_df = df.copy()
    masked_df.columns = masked_columns
    return masked_df, mapping


# ---------- Detection Functions ----------
def detect_missing_values(df):
    missing_counts = df.isnull().sum()
    missing_percent = (missing_counts / len(df)) * 100
    result = pd.DataFrame({
        "missing_count": missing_counts,
        "missing_percent": missing_percent
    })
    return result[result["missing_count"] > 0]


def detect_duplicates(df):
    duplicate_count = df.duplicated().sum()
    duplicate_rows = df[df.duplicated()]
    return duplicate_count, duplicate_rows


def detect_type_issues(df):
    issues = {}
    for col in df.select_dtypes(include=["object", "str"]).columns:
        numeric_convertible = pd.to_numeric(df[col], errors="coerce")
        non_numeric_count = numeric_convertible.isnull().sum() - df[col].isnull().sum()
        non_null_count = df[col].notnull().sum()
        if 0 < non_numeric_count < (non_null_count * 0.5):
            issues[col] = non_numeric_count
    return issues


def detect_outliers(df):
    outlier_report = {}
    for col in df.select_dtypes(include=["number"]).columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
        if len(outliers) > 0:
            outlier_report[col] = len(outliers)
    return outlier_report


def detect_inconsistent_categories(df):
    inconsistency_report = {}
    for col in df.select_dtypes(include=["object", "str"]).columns:
        original_unique = df[col].dropna().unique()
        normalized_unique = df[col].dropna().str.strip().str.lower().unique()
        if len(normalized_unique) < len(original_unique):
            inconsistency_report[col] = len(original_unique) - len(normalized_unique)
    return inconsistency_report


def detect_whitespace_issues(df):
    whitespace_report = {}
    for col in df.select_dtypes(include=["object", "str"]).columns:
        has_whitespace = df[col].dropna().apply(lambda x: isinstance(x, str) and x != x.strip())
        count = has_whitespace.sum()
        if count > 0:
            whitespace_report[col] = int(count)
    return whitespace_report


def detect_negative_values(df):
    negative_report = {}
    for col in df.select_dtypes(include=["number"]).columns:
        negative_count = (df[col] < 0).sum()
        if negative_count > 0:
            negative_report[col] = int(negative_count)
    return negative_report


def detect_date_format_issues(df):
    date_format_report = {}
    for col in df.select_dtypes(include=["object", "str"]).columns:
        sample = df[col].dropna().astype(str)
        slash_format = sample.str.match(r'^\d{1,2}/\d{1,2}/\d{4}$').sum()
        dash_format = sample.str.match(r'^\d{4}-\d{1,2}-\d{1,2}$').sum()
        if slash_format > 0 and dash_format > 0:
            date_format_report[col] = {"slash_format": int(slash_format), "dash_format": int(dash_format)}
    return date_format_report


def detect_constant_columns(df):
    constant_columns = []
    for col in df.columns:
        if df[col].nunique(dropna=True) == 1:
            constant_columns.append(col)
    return constant_columns


def detect_id_uniqueness_issues(df):
    id_report = {}
    for col in df.columns:
        if "id" in col.lower() or df[col].nunique(dropna=True) / len(df) > 0.9:
            duplicate_count = df[col].duplicated().sum()
            if duplicate_count > 0:
                id_report[col] = int(duplicate_count)
    return id_report


def detect_mixed_types(df):
    mixed_report = {}
    for col in df.columns:
        types_in_col = df[col].dropna().apply(lambda x: type(x).__name__).unique()
        if len(types_in_col) > 1:
            mixed_report[col] = list(types_in_col)
    return mixed_report


# ---------- Full Report ----------
def generate_report(df):
    report = {
        "missing_values": detect_missing_values(df),
        "duplicates": detect_duplicates(df)[0],
        "type_issues": detect_type_issues(df),
        "outliers": detect_outliers(df),
        "inconsistent_categories": detect_inconsistent_categories(df),
        "whitespace_issues": detect_whitespace_issues(df),
        "negative_values": detect_negative_values(df),
        "date_format_issues": detect_date_format_issues(df),
        "constant_columns": detect_constant_columns(df),
        "id_uniqueness_issues": detect_id_uniqueness_issues(df),
        "mixed_types": detect_mixed_types(df)
    }
    return report


def clean_report(report):
    cleaned = {}
    for key, value in report.items():
        if isinstance(value, pd.DataFrame):
            cleaned[key] = value.to_dict()
        elif isinstance(value, dict):
            cleaned[key] = {k: int(v) if hasattr(v, "item") else v for k, v in value.items()}
        elif hasattr(value, "item"):
            cleaned[key] = value.item()
        else:
            cleaned[key] = value
    return cleaned


# ---------- Prompt Building ----------
def build_prompt(report, mapping, dtypes):
    prompt = f"""
You are a data quality expert. Below is a data quality report generated from a dataset.
Column names have been masked for privacy (e.g., col_1, col_2). Do NOT ask for real column names.

Column data types:
{dtypes}

Report:
{report}

Here is exactly what each key in the report means, so you apply the CORRECT, well-known fix
for each one rather than guessing:

- missing_values: columns with null/empty values (missing_count, missing_percent per column).
  Fix: for numeric columns, fill with mean/median; for text/categorical columns, fill with "Unknown" or the mode.
- duplicates: total number of fully duplicated rows in the dataset.
  Fix: df = df.drop_duplicates()
- type_issues: text columns that are MOSTLY numeric but contain a few invalid text values
  (e.g., "abd" mixed into a price column). The value is the count of invalid (non-numeric) entries.
  Fix: convert the column to numeric and turn the invalid values into NaN, e.g.
  df['col_x'] = pd.to_numeric(df['col_x'], errors='coerce')
- outliers: numeric columns with statistical outliers detected via the IQR method. Value is the count of outlier rows.
  Fix: either cap values to the IQR bounds or remove/flag the outlier rows.
- inconsistent_categories: text/categorical columns where the same category appears in different
  cases or with extra whitespace (e.g., "Electronics" vs "electronic "). Value is the number of
  duplicate variants found.
  Fix: df['col_x'] = df['col_x'].str.strip().str.lower()
- whitespace_issues: text columns with leading/trailing whitespace in values. Value is the count of affected rows.
  Fix: df['col_x'] = df['col_x'].str.strip()
- negative_values: numeric columns that contain negative values where negatives don't make sense
  (e.g., a price or quantity column). Value is the count of negative rows.
  Fix: investigate and either take the absolute value or set to NaN, e.g.
  df.loc[df['col_x'] < 0, 'col_x'] = None
- date_format_issues: date columns where multiple date formats are mixed (e.g., MM/DD/YYYY and YYYY-MM-DD).
  Fix: parse with pd.to_datetime(df['col_x'], errors='coerce') to standardize to a single format.
- constant_columns: columns where every value is identical, making the column uninformative.
  Fix: consider dropping the column, e.g. df = df.drop(columns=['col_x']).
- id_uniqueness_issues: columns expected to be unique identifiers that contain duplicate values.
  Value is the count of duplicated entries.
  Fix: investigate duplicates, e.g. df[df['col_x'].duplicated(keep=False)], and remove or correct them.
- mixed_types: columns containing a mix of different Python data types (e.g., strings and numbers
  mixed together) rather than one consistent type.
  Fix: standardize the column to a single type, e.g. df['col_x'] = df['col_x'].astype(str).

For EACH issue type in the report that is NOT empty (not an empty dict/list and not 0), return an entry.
Skip any issue type that is empty (empty dict, empty list, or 0).

Return ONLY a JSON array (no extra text, no markdown code fences) where each element has this exact shape:
{{
  "issue_type": "short title, e.g. Missing Values",
  "severity": "high" | "medium" | "low",
  "explanation": "a clear, simple explanation of the issue as it applies to the actual columns and values found",
  "affected_columns": ["col_x", "col_y"],
  "fix_code": "a professional Python (pandas) code snippet using the CORRECT fix described above"
}}
"""
    return prompt


# ---------- Streamlit UI ----------
uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file is not None:
    df = read_file(uploaded_file)
    st.write("### Preview of your data")
    st.dataframe(df.head())

    if st.button("Analyze Data Quality"):
        masked_df, mapping = mask_columns(df)
        full_report = generate_report(masked_df)
        cleaned_report = clean_report(full_report)
        dtypes = masked_df.dtypes.astype(str).to_dict()
        prompt = build_prompt(cleaned_report, mapping, dtypes)

        with st.spinner("Analyzing your data..."):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

        raw_output = response.choices[0].message.content
        cleaned_output = raw_output.replace("```json", "").replace("```", "").strip()

        st.write("### Data Quality Report")

        try:
            issues = json.loads(cleaned_output)

            severity_icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}

            st.write(f"Found **{len(issues)}** issue type(s) in your dataset.")

            for issue in issues:
                icon = severity_icon.get(issue.get("severity", "low"), "🟡")
                cols_str = ", ".join(issue.get("affected_columns", []))
                with st.expander(f"{icon} {issue.get('issue_type', 'Issue')} — {cols_str}"):
                    st.write(issue.get("explanation", ""))
                    st.code(issue.get("fix_code", ""), language="python")
        except Exception as e:
            st.error(f"Could not parse the report: {e}")
            st.write(raw_output)
