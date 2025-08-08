import streamlit as st
import pandas as pd
import psycopg2
from io import StringIO

st.set_page_config(page_title="Upload Vocabulary", layout="centered")

# Connect to Neon DB
def get_connection():
    return psycopg2.connect(st.secrets["neon"])

# Create table if it doesn't exist
def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vocabularies (
            id SERIAL PRIMARY KEY,
            turkish TEXT NOT NULL,
            english TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

create_table()

st.title("📤 Upload Vocabulary")

option = st.radio("Choose input method", ["Manual entry", "Upload CSV"])

if option == "Manual entry":
    turkish_word = st.text_input("Turkish")
    english_word = st.text_input("English")
    if st.button("Add to database"):
        if turkish_word.strip() and english_word.strip():
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO vocabularies (turkish, english) VALUES (%s, %s)",
                (turkish_word.strip(), english_word.strip())
            )
            conn.commit()
            cur.close()
            conn.close()
            st.success("Word added successfully!")
        else:
            st.error("Both fields are required.")

elif option == "Upload CSV":
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if "turkish" in df.columns and "english" in df.columns:
            conn = get_connection()
            cur = conn.cursor()
            for _, row in df.iterrows():
                cur.execute(
                    "INSERT INTO vocabularies (turkish, english) VALUES (%s, %s)",
                    (str(row["turkish"]).strip(), str(row["english"]).strip())
                )
            conn.commit()
            cur.close()
            conn.close()
            st.success("CSV uploaded successfully!")
        else:
            st.error("CSV must contain 'turkish' and 'english' columns.")

# Show table contents
st.subheader("Current Vocabulary in DB")
conn = get_connection()
df = pd.read_sql("SELECT turkish, english, created_at FROM vocabularies ORDER BY created_at DESC", conn)
conn.close()
st.dataframe(df)
