import streamlit as st
import pandas as pd
import psycopg2
import random

st.set_page_config(page_title="Vocabulary Quiz", layout="centered")

def get_connection():
    return psycopg2.connect(st.secrets["neon"])

st.title("📝 Vocabulary Quiz")

# Load data from Neon
conn = get_connection()
df = pd.read_sql("SELECT turkish, english FROM vocabularies", conn)
conn.close()

if df.empty:
    st.warning("No vocabulary found. Please upload some first.")
else:
    num_questions = st.slider("Number of questions", 1, len(df), min(10, len(df)))
    direction = st.selectbox("Direction", ["Turkish → English", "English → Turkish", "Mixed"])

    if st.button("Start Quiz"):
        score = 0
        questions = df.sample(num_questions).to_dict(orient="records")
        for q in questions:
            if direction == "Mixed":
                dir_choice = random.choice(["t2e", "e2t"])
            else:
                dir_choice = "t2e" if direction == "Turkish → English" else "e2t"

            if dir_choice == "t2e":
                question_word = q["turkish"]
                answer_word = q["english"]
            else:
                question_word = q["english"]
                answer_word = q["turkish"]

            user_answer = st.text_input(f"Translate: {question_word}", key=question_word)
            if st.button(f"Check {question_word}"):
                if user_answer.strip().lower() == answer_word.strip().lower():
                    st.success("✅ Correct!")
                    score += 1
                else:
                    st.error(f"❌ Correct answer: {answer_word}")

        st.write(f"Final score: {score} / {num_questions}")
