Personal Finance Overview

Author: Sakshi Kendre

Role: Data Analyst

Overview
Below is an interactive Streamlit application for the analysis of personal finance data in a CSV file. It also helps users to categorize their expenses, add custom categories, and visualize spending patterns with ease.
Features
- Upload and process transaction CSV files
- Automatic keyword-based expense categorization
- Administer and add new customized categories
- Editing categories interactively

- Persistent category learning, using categories.json
View summaries and visualizations of expenses.

Separate views for Expenses - Debits and for Payments - Credits

Project Structure
finance_dashboard.py  – Main Streamlit application
categories.json       Representatives of categories and their learnt keywords
How Categorization Works
All transactions are marked as Uncategorized by default. The categories and keywords are kept in categories.json. The transaction details are matched against the stored keywords in a case-insensitive way. When users assign categories manually, the transaction details are stored as keywords, which enhances the categorization in the future.

Technologies Used
Python
Streamlit

Pandas
Plotly

JSON
Requirements
streamlit
pandas
plotly

Running the Application
Run the following command:
streamlit run finance_dashboard.py
CSV File Requirements
The CSV must include the following:

- Date
- Information
- Quantity

- Debit/Credit
Usage 1. Upload the CSV file 2. Review categorized transactions 3. Add or edit categories 4. Apply changes 5. Review summaries and charts Future Improvements - Export categorized data Trend analysis - Multi-account support License Open for learning and personal use.
