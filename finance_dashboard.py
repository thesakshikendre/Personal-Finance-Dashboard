import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import numpy as np
import re

st.set_page_config(page_title="Personal Finance App", page_icon="💰", layout="wide")

category_file = "categories.json"

# ---------------------------------------------------------------------
# INITIALIZE CATEGORY STORAGE
# ---------------------------------------------------------------------
if "categories" not in st.session_state:
    st.session_state.categories = {"Uncategorized": []}

if os.path.exists(category_file):
    try:
        with open(category_file, "r") as f:
            st.session_state.categories = json.load(f)
    except:
        st.warning("categories.json corrupted. Using default.")


def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f, indent=2)


def add_keyword_to_category(category, keyword):
    keyword = str(keyword).strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()


# ---------------------------------------------------------------------
# HELPERS FOR CLEANING BANK CSVs
# ---------------------------------------------------------------------
def normalize_debit_credit(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip().lower()
    if any(x in s for x in ["debit", "withdraw", "payment", "dr"]):
        return "Debit"
    if any(x in s for x in ["credit", "deposit", "cr"]):
        return "Credit"
    try:
        return "Debit" if float(s) < 0 else "Credit"
    except:
        return np.nan


def parse_amount(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.replace(",", "").str.replace(r"[^\d\.-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def parse_date(s: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(s, dayfirst=True, errors="coerce")
    missing = parsed.isna()
    parsed.loc[missing] = pd.to_datetime(s[missing], errors="coerce")
    return parsed


# ---------------------------------------------------------------------
# AUTO-CATEGORIZATION USING KEYWORDS
# ---------------------------------------------------------------------
def categorize_transactions(df):
    df["Category"] = df.get("Category", "Uncategorized")

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue

        lowered = [kw.lower().strip() for kw in keywords]
        df["Category"] = df.apply(
            lambda r: category if any(kw in r["Details"].lower() for kw in lowered) else r["Category"],
            axis=1,
        )
    return df


# ---------------------------------------------------------------------
# LOAD TRANSACTIONS FROM CSV
# ---------------------------------------------------------------------
def load_transactions(file):
    try:
        df = pd.read_csv(file, dtype=str, keep_default_na=False)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return None

    df.columns = [c.strip() for c in df.columns]

    # Try to detect columns
    def find_col(keywords):
        for col in df.columns:
            if any(k in col.lower() for k in keywords):
                return col
        return None

    col_date = find_col(["date"])
    col_details = find_col(["detail", "description", "narration"])
    col_amount = find_col(["amount", "amt", "value"])
    col_dc = find_col(["debit", "credit", "type"])

    if not (col_details and col_amount):
        st.error("CSV must contain Details and Amount columns.")
        return None

    df = df.rename(columns={
        col_date: "Date",
        col_details: "Details",
        col_amount: "Amount",
        col_dc: "Debit/Credit"
    })

    # Clean amount
    df["Amount"] = parse_amount(df["Amount"])
    df = df[df["Amount"].notna()]  # drop rows like "Amount" header accidentally inside data
    df["Amount"] = df["Amount"].abs()

    # Parse date
    if "Date" in df:
        df["Date"] = parse_date(df["Date"])
    else:
        df["Date"] = pd.NaT

    # Normalize debit/credit
    if "Debit/Credit" in df:
        df["Debit/Credit"] = df["Debit/Credit"].apply(normalize_debit_credit)
    df["Debit/Credit"] = df["Debit/Credit"].fillna(
        df["Amount"].apply(lambda x: "Debit" if x < 0 else "Credit")
    )

    df["Details"] = df["Details"].astype(str).str.strip()

    # Attach stable index for mapping after edits
    df = df.reset_index().rename(columns={"index": "_orig_index"})

    df = categorize_transactions(df)
    return df


# ---------------------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------------------
def main():
    st.title("Personal Finance Dashboard")

    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])

    if uploaded_file is None:
        st.info("Please upload a CSV file.")
        return

    df = load_transactions(uploaded_file)
    if df is None:
        return

    debits_df = df[df["Debit/Credit"] == "Debit"].copy()
    credits_df = df[df["Debit/Credit"] == "Credit"].copy()

    st.session_state.debits_df = debits_df.copy()

    tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])

    # -----------------------------------------------------------------
    # TAB 1 – EXPENSES
    # -----------------------------------------------------------------
    with tab1:
        st.subheader("Manage Categories")
        c1, c2 = st.columns([3, 1])
        new_cat = c1.text_input("New Category Name")
        if c2.button("Add"):
            if new_cat not in st.session_state.categories:
                st.session_state.categories[new_cat] = []
                save_categories()
                st.success(f"Category '{new_cat}' added.")
                st.rerun()

        st.subheader("Your Expenses")
        display_df = st.session_state.debits_df.copy()

        # Format Date for display (string)
        display_df["Date"] = display_df["Date"].dt.strftime("%d/%m/%Y")
        display_df = display_df.reset_index(drop=True)

        visible_columns = ["Date", "Details", "Amount", "Category", "_orig_index"]

        edited = st.data_editor(
            display_df[visible_columns],
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY", disabled=True),  # <-- FIXED
                "Amount": st.column_config.NumberColumn("Amount", format="%.2f INR"),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=list(st.session_state.categories.keys())
                ),
                "_orig_index": st.column_config.NumberColumn("_orig_index", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            key="editor"
        )

        if st.button("Apply Changes", type="primary"):
            count = 0
            for _, row in edited.iterrows():
                orig = int(row["_orig_index"])
                new_cat = row["Category"]
                details = row["Details"]

                mask = st.session_state.debits_df["_orig_index"] == orig
                old_cat = st.session_state.debits_df.loc[mask, "Category"].iloc[0]

                if new_cat != old_cat:
                    st.session_state.debits_df.loc[mask, "Category"] = new_cat
                    add_keyword_to_category(new_cat, details)
                    count += 1

            st.success(f"{count} changes applied.")

        st.subheader("Expense Summary")
        totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
        totals = totals.sort_values("Amount", ascending=False)

        st.dataframe(
            totals,
            column_config={"Amount": st.column_config.NumberColumn("Amount", format="%.2f INR")},
            hide_index=True,
            use_container_width=True
        )

        fig = px.pie(totals, values="Amount", names="Category", title="Expenses by Category")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------
    # TAB 2 – CREDITS
    # -----------------------------------------------------------------
    with tab2:
        st.subheader("Payments Summary")
        total = credits_df["Amount"].sum()
        st.metric("Total Payments", f"{total:,.2f} INR")

        cdisp = credits_df.copy()
        cdisp["Date"] = cdisp["Date"].dt.strftime("%d/%m/%Y")

        st.dataframe(
            cdisp[["Date", "Details", "Amount", "Category"]],
            hide_index=True,
            use_container_width=True
        )


if __name__ == "__main__":
    main()
