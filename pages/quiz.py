import streamlit as st
import pandas as pd
import psycopg2
import random
import difflib

st.set_page_config(page_title="Vocabulary Quiz", layout="centered")

def get_connection():
    try:
        return psycopg2.connect(st.secrets["neon"])
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def is_correct(user_answer: str, correct_answer: str, threshold=0.8) -> bool:
    ua = user_answer.strip().lower()
    ca = correct_answer.strip().lower()
    if ua == ca:
        return True
    return difflib.SequenceMatcher(None, ua, ca).ratio() >= threshold

conn = get_connection()
if conn:
    df = pd.read_sql("SELECT turkish, english FROM vocabularies", conn)
    conn.close()
else:
    df = pd.DataFrame()

st.title("📝 Vocabulary Quiz")

if df.empty:
    st.warning("No vocabulary found. Please upload some first.")
    st.stop()

if len(df) < 5:
    st.warning("Need at least 5 words in the database to start a quiz.")
    st.stop()

max_questions = min(100, len(df))

if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False

if not st.session_state.quiz_started:
    with st.form("quiz_setup"):
        num_questions = st.slider(
            "Number of questions",
            min_value=5,
            max_value=max_questions,
            value=10
        )
        direction = st.selectbox(
            "Direction",
            ["Turkish → English", "English → Turkish", "Mixed"]
        )
        submitted = st.form_submit_button("Start Quiz")

        if submitted:
            st.session_state.questions = df.sample(num_questions).to_dict(orient="records")
            st.session_state.direction = direction

            # Determine direction per question and store it (important for Mixed)
            directions_per_question = []
            for _ in range(num_questions):
                if direction == "Mixed":
                    directions_per_question.append(random.choice(["t2e", "e2t"]))
                else:
                    directions_per_question.append("t2e" if direction == "Turkish → English" else "e2t")

            st.session_state.directions_per_question = directions_per_question
            st.session_state.answers = [""] * num_questions
            st.session_state.quiz_started = True
            st.rerun()

else:
    num_questions = len(st.session_state.questions)
    st.write(f"Quiz started: {num_questions} questions | Direction: {st.session_state.direction}")

    with st.form("quiz_questions"):
        answers = []
        for i, q in enumerate(st.session_state.questions, start=1):
            dir_choice = st.session_state.directions_per_question[i-1]
            if dir_choice == "t2e":
                question_word = q["turkish"]
            else:
                question_word = q["english"]

            default_answer = st.session_state.answers[i-1] if i-1 < len(st.session_state.answers) else ""
            user_input = st.text_input(f"Q{i}: Translate '{question_word}'", value=default_answer, key=f"q_{i}")
            answers.append(user_input)

        submitted = st.form_submit_button("Submit Answers")

        if submitted:
            st.session_state.answers = answers

            score = 0
            results = []
            for i, q in enumerate(st.session_state.questions):
                user_answer = answers[i]
                dir_choice = st.session_state.directions_per_question[i]
                if dir_choice == "t2e":
                    correct_answer = q["english"]
                    question_word = q["turkish"]
                else:
                    correct_answer = q["turkish"]
                    question_word = q["english"]

                correct = is_correct(user_answer, correct_answer)
                if correct:
                    score += 1
                results.append({
                    "Question": question_word,
                    "Your Answer": user_answer,
                    "Correct Answer": correct_answer,
                    "Correct": "✅" if correct else "❌"
                })

            st.session_state.quiz_started = False

            st.markdown("---")
            st.subheader("📊 Quiz Results")
            st.write(f"Your score: **{score} / {num_questions}**")
            results_df = pd.DataFrame(results)
            st.dataframe(results_df)
