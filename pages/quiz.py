import streamlit as st
import pandas as pd
import psycopg2
import random
import difflib

st.set_page_config(page_title="Vocabulary Quiz", layout="centered")

# -----------------------
# DB connection
# -----------------------
def get_connection():
    try:
        return psycopg2.connect(st.secrets["neon"])
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# -----------------------
# Fuzzy match helper
# -----------------------
def is_correct(user_answer: str, correct_answer: str, threshold=0.8) -> bool:
    ua = user_answer.strip().lower()
    ca = correct_answer.strip().lower()
    if ua == ca:
        return True
    return difflib.SequenceMatcher(None, ua, ca).ratio() >= threshold

st.title("📝 Vocabulary Quiz")

# -----------------------
# Load vocab from DB
# -----------------------
conn = get_connection()
if conn:
    df = pd.read_sql("SELECT turkish, english FROM vocabularies", conn)
    conn.close()
else:
    df = pd.DataFrame()

# -----------------------
# Check for enough data
# -----------------------
if df.empty:
    st.warning("No vocabulary found. Please upload some first.")
elif len(df) < 2:
    st.warning("Need at least 2 words in the database to start a quiz.")
else:
    num_questions = st.slider(
        "Number of questions",
        min_value=1,
        max_value=len(df),
        value=min(10, len(df))
    )
    direction = st.selectbox(
        "Direction",
        ["Turkish → English", "English → Turkish", "Mixed"]
    )

    if st.button("Start Quiz"):
        score = 0
        results = []
        questions = df.sample(num_questions).to_dict(orient="records")

        for i, q in enumerate(questions, start=1):
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

            user_answer = st.text_input(f"Q{i}: Translate '{question_word}'", key=f"q_{i}")
            check_btn = st.button(f"Check Q{i}", key=f"check_{i}")
            if check_btn:
                if is_correct(user_answer, answer_word):
                    st.success("✅ Correct!")
                    score += 1
                    results.append((question_word, user_answer, answer_word, True))
                else:
                    st.error(f"❌ Correct answer: {answer_word}")
                    results.append((question_word, user_answer, answer_word, False))

        st.markdown("---")
        st.subheader("📊 Results")
        st.write(f"Score: **{score} / {num_questions}**")
        if results:
            results_df = pd.DataFrame(
                results,
                columns=["Question", "Your Answer", "Correct Answer", "Correct?"]
            )
            st.dataframe(results_df)
