import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

st.set_page_config(page_title="Vocabulary Uploader", layout="centered")

def get_connection():
    try:
        return psycopg2.connect(st.secrets["neon"])
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def create_table():
    conn = get_connection()
    if conn is None:
        return
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

VALID_USERS = {
    "admin": "1234",
    "teacher": "abcd"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔑 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in VALID_USERS and VALID_USERS[username] == password:
            st.session_state.logged_in = True
            st.success("✅ Login successful!")
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password.")
    st.stop()  # Stop the app here until logged in

st.title("📤 Upload Vocabulary")

option = st.radio("Choose input method", ["Manual entry", "Upload CSV"])

if option == "Manual entry":
    turkish_word = st.text_input("Turkish")
    english_word = st.text_input("English")
    if st.button("Add to database"):
        if turkish_word.strip() and english_word.strip():
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO vocabularies (turkish, english) VALUES (%s, %s)",
                    (turkish_word.strip(), english_word.strip())
                )
                conn.commit()
                cur.close()
                conn.close()
                st.success("✅ Word added successfully!")
        else:
            st.error("Both fields are required.")

elif option == "Upload CSV":
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='latin1')
            except Exception as e:
                st.error(f"Error reading CSV file: {e}")
                df = None

        if df is not None:
            # Lowercase column names for matching
            df.columns = [col.lower().strip() for col in df.columns]
            if "turkish" in df.columns and "english" in df.columns:
                conn = get_connection()
                if conn:
                    cur = conn.cursor()
                    for _, row in df.iterrows():
                        turkish_word = str(row["turkish"]).strip()
                        english_word = str(row["english"]).strip()
                        if turkish_word and english_word:
                            cur.execute(
                                "INSERT INTO vocabularies (turkish, english) VALUES (%s, %s)",
                                (turkish_word, english_word)
                            )
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("✅ CSV uploaded successfully!")
            else:
                st.error("CSV must contain 'turkish' and 'english' columns.")

st.subheader("📜 Current Vocabulary in DB")
conn = get_connection()
if conn:
    df = pd.read_sql(
        "SELECT turkish, english, created_at FROM vocabularies ORDER BY created_at DESC",
        conn
    )
    conn.close()
    if df.empty:
        st.info("No vocabulary found in database.")
    else:
        st.dataframe(df)
