import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(layout="wide", page_title="Dynamic BI Dashboard")

st.title("📊Business Intelligence Dashboard")

# --------------------------
# Upload Dataset
# --------------------------
st.sidebar.header("📁 Upload your dataset")
uploaded_file = st.sidebar.file_uploader(
    "Upload CSV or Excel file", type=["csv", "xlsx"]
)

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, encoding="latin1")
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()
else:
    st.info("Please upload a CSV or Excel file to continue.")
    st.stop()

# Normalize Columns

df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")
rename_map = {
    "subcategory": "sub_category",
    "customer": "customer_name",
    "orderid": "order_id"
}
df.rename(columns=rename_map, inplace=True)

# Convert date-like columns to datetime
for c in df.columns:
    if "date" in c:
        df[c] = pd.to_datetime(df[c], errors="coerce")

# Sidebar Filters
st.sidebar.header("📌 Filters")

# Identify columns
categorical_cols = df.select_dtypes(exclude='number').columns.tolist()
categorical_cols = [col for col in categorical_cols if df[col].nunique() <= 100]

numeric_cols = df.select_dtypes(include='number').columns.tolist()
date_cols = df.select_dtypes(include='datetime').columns.tolist()

# Categorical filters
filters = {}
for col in categorical_cols:
    options = sorted(df[col].dropna().unique())
    selected = st.sidebar.multiselect(f"{col.title()}", options, default=options)
    if selected:
        df = df[df[col].isin(selected)]
    filters[col] = selected

# Numeric columns for KPI selection
st.sidebar.header("⚡ Select Metrics")
metric_col = st.sidebar.selectbox("Metric for KPIs / Charts", options=numeric_cols)

# Date column selection
date_col = None
if date_cols:
    date_col = st.sidebar.selectbox("Date column for time series", options=date_cols)

filtered = df.copy()

# Date range filter
if date_col:
    min_date = filtered[date_col].min()
    max_date = filtered[date_col].max()
    start_date, end_date = st.sidebar.date_input(
        f"{date_col.title()} Range", value=(min_date, max_date)
    )
    filtered = filtered[(filtered[date_col] >= pd.to_datetime(start_date)) &
                        (filtered[date_col] <= pd.to_datetime(end_date))]

# KPIs
st.markdown("### Key Performance Indicators (KPIs)")

total_metric = filtered[metric_col].sum() if metric_col else 0
avg_metric = filtered[metric_col].mean() if metric_col else 0
total_rows = filtered.shape[0]

k1, k2, k3 = st.columns(3)
k1.metric(f"Total {metric_col.title()}", f"{total_metric:,.2f}")
k2.metric(f"Average {metric_col.title()}", f"{avg_metric:,.2f}")
k3.metric("Total Records", f"{total_rows:,}")

st.markdown("---")

# Top 5 Categories / Customers
if categorical_cols:
    cat_col = st.sidebar.selectbox("Top N by Category/Customer", options=categorical_cols)
    if cat_col and metric_col:
        st.subheader(f"🏆 Top 5 {cat_col.title()} by {metric_col.title()}")
        top5 = filtered.groupby(cat_col)[metric_col].sum().reset_index().sort_values(metric_col, ascending=False).head(5)
        col1, col2 = st.columns([2,3])
        with col1:
            st.table(top5.style.format({metric_col: "{:,.2f}"}))
        with col2:
            fig = px.bar(top5.sort_values(metric_col), x=metric_col, y=cat_col, orientation="h")
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Dynamic Charts
st.subheader("📊 Charts")
chart_type = st.selectbox("Select chart type", ["Line (Time Series)", "Scatter", "Bar"])

if chart_type == "Line (Time Series)" and date_col and metric_col:
    ts_data = filtered.set_index(date_col).resample("ME")[metric_col].sum().reset_index()
    fig_ts = px.line(ts_data, x=date_col, y=metric_col, markers=True)
    st.plotly_chart(fig_ts, use_container_width=True)

elif chart_type == "Scatter" and len(numeric_cols) >= 2:
    x_col = st.selectbox("X-axis", numeric_cols, index=0)
    y_col = st.selectbox("Y-axis", numeric_cols, index=1)
    hover_col = st.selectbox("Hover Info (Optional)", categorical_cols + [None])
    fig_scatter = px.scatter(
        filtered.sample(n=min(1000,len(filtered)), random_state=1),
        x=x_col, y=y_col, hover_data=[hover_col] if hover_col else None
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

elif chart_type == "Bar" and categorical_cols and metric_col:
    bar_cat = st.selectbox("Categorical Column for Bar", categorical_cols)
    bar_data = filtered.groupby(bar_cat)[metric_col].sum().reset_index()
    fig_bar = px.bar(bar_data.sort_values(metric_col), x=bar_cat, y=metric_col)
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# Show Data + Download
st.subheader("🔍 Filtered Data Preview")
st.dataframe(filtered.reset_index(drop=True), height=400)

csv = filtered.to_csv(index=False).encode("utf-8")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    filtered.to_excel(writer, index=False, sheet_name="FilteredData")
excel_data = buffer.getvalue()

col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    st.download_button("⬇️ Download CSV", csv, "filtered_data.csv", "text/csv")
with col_dl2:
    st.download_button("⬇️ Download Excel", excel_data, "filtered_data.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")