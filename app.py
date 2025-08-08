# app.py
import streamlit as st
import pandas as pd
import numpy as np
import random
import difflib
import io
import re

st.set_page_config(page_title="Turkish Vocabulary Quiz", layout="centered")

# -----------------------
# Helper utilities
# -----------------------
def normalize(s: str) -> str:
    return "" if s is None else re.sub(r"\s+", " ", s.strip().lower())

def split_answers(s: str):
    """Split a cell that may contain multiple acceptable answers."""
    if pd.isna(s):
        return []
    parts = re.split(r"[;,|/]+", str(s))
    return [normalize(p) for p in parts if normalize(p)]

def is_correct(user_answer: str, correct_cell: str, fuzz_threshold: float = 0.78) -> bool:
    ua = normalize(user_answer)
    if ua == "":
        return False
    candidates = split_answers(correct_cell)
    # Exact match
    for c in candidates:
        if ua == c:
            return True
    # Fuzzy match (use difflib)
    for c in candidates:
        ratio = difflib.SequenceMatcher(None, ua, c).ratio()
        if ratio >= fuzz_threshold:
            return True
    return False

def default_vocab_df():
    return pd.DataFrame({
        "turkish": ["merhaba", "ev", "kitap", "teşekkür ederim", "güzel", "su", "arkadaş", "yemek", "okul", "gün"],
        "english": ["hello", "house", "book", "thank you", "beautiful", "water", "friend", "food", "school", "day"]
    })

# -----------------------
# Load / prepare vocabulary
# -----------------------
st.title("🇹🇷 Turkish Vocabulary Quiz — Starter")

st.sidebar.header("Options")
mode = st.sidebar.selectbox("App mode", ["Quiz", "Flashcards", "Manage Vocabulary"])
direction_choice = st.sidebar.selectbox("Direction", ["Turkish → English", "English → Turkish", "Mixed"])
num_questions = st.sidebar.number_input("Number of questions", min_value=1, max_value=500, value=10, step=1)
uploaded = st.sidebar.file_uploader("Upload CSV or XLSX (columns: turkish, english)", type=["csv", "xlsx"])

# Load data (uploaded takes precedence)
if uploaded is not None:
    try:
        if uploaded.name.lower().endswith(".xlsx"):
            df = pd.read_excel(uploaded)
        else:
            df = pd.read_csv(uploaded)
        # normalize column names
        df.columns = [c.strip().lower() for c in df.columns]
        if "turkish" not in df.columns or "english" not in df.columns:
            st.sidebar.error("File must contain 'turkish' and 'english' columns.")
            df = default_vocab_df()
        else:
            df = df[["turkish", "english"]].dropna().reset_index(drop=True)
    except Exception as e:
        st.sidebar.error(f"Could not read file: {e}")
        df = default_vocab_df()
else:
    df = default_vocab_df()

# Keep working copy in session_state so Manage mode can mutate it
if "vocab_df" not in st.session_state:
    st.session_state.vocab_df = df.copy()

vocab_df = st.session_state.vocab_df

# -----------------------
# Shared UI: show summary
# -----------------------
st.markdown(f"**Vocabulary loaded:** {len(vocab_df)} words.")
if st.checkbox("Show vocabulary table"):
    st.dataframe(vocab_df)

# -----------------------
# Quiz Mode
# -----------------------
def start_quiz():
    n = min(len(vocab_df), num_questions)
    sampled = vocab_df.sample(n=n, replace=False).reset_index(drop=True)
    st.session_state.quiz_words = sampled.to_dict("records")
    # precompute direction per question
    dirs = []
    for _ in range(n):
        if direction_choice == "Mixed":
            dirs.append(random.choice(["t2e", "e2t"]))
        else:
            dirs.append("t2e" if direction_choice == "Turkish → English" else "e2t")
    st.session_state.quiz_dirs = dirs
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.results = []  # store tuples (question, user_ans, correct, was_correct)
    st.session_state.quiz_started = True

if mode == "Quiz":
    st.header("Quiz")
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False

    if not st.session_state.quiz_started:
        st.write("Press **Start quiz** to begin. You can upload your CSV via the sidebar (columns: `turkish`, `english`).")
        if st.button("Start quiz"):
            start_quiz()
            st.experimental_rerun()
    else:
        # running quiz
        idx = st.session_state.index
        total = len(st.session_state.quiz_words)
        current = st.session_state.quiz_words[idx]
        qdir = st.session_state.quiz_dirs[idx]
        source = current["turkish"] if qdir == "t2e" else current["english"]
        target_cell = current["english"] if qdir == "t2e" else current["turkish"]

        st.markdown(f"**Question {idx+1} of {total}**")
        st.markdown(f"Translate: **{source}**")

        # keep per-question input stable
        ans_key = f"answer_{idx}"
        user_answer = st.text_input("Your answer", key=ans_key)

        check = st.button("Check answer")
        if check:
            correct_flag = is_correct(user_answer, target_cell)
            if correct_flag:
                st.success("✅ Correct!")
                st.session_state.score += 1
            else:
                st.error(f"❌ Not quite. Acceptable answer(s): {target_cell}")
            st.session_state.results.append({
                "question": source,
                "given": user_answer,
                "answer": target_cell,
                "correct": correct_flag,
                "direction": qdir
            })
            # move to next question or finish
            if idx + 1 < total:
                st.session_state.index += 1
                # clear the next question input to avoid showing previous answer in new input
                st.experimental_rerun()
            else:
                st.session_state.quiz_started = False
                # show summary
                st.markdown("---")
                st.header("Quiz complete")
                score = st.session_state.score
                st.write(f"Score: **{score} / {total}** ({round(score/total*100,1)}%)")
                df_results = pd.DataFrame(st.session_state.results)
                st.subheader("Review")
                st.dataframe(df_results)
                # offer download of review
                csv = df_results.to_csv(index=False).encode("utf-8")
                st.download_button("Download results (CSV)", csv, file_name="quiz_results.csv", mime="text/csv")
                # reset some session_state so next quiz can be started fresh
                st.session_state.pop("quiz_words", None)
                st.session_state.pop("quiz_dirs", None)
                st.session_state.pop("index", None)
                st.session_state.pop("score", None)
                st.session_state.pop("results", None)
                st.session_state.pop("quiz_started", None)

# -----------------------
# Flashcards Mode
# -----------------------
elif mode == "Flashcards":
    st.header("Flashcards / Study")
    st.write("Click through flashcards. You can flip to see the translation.")
    # simple random order or sequential
    seq = st.radio("Order", ["Sequential", "Random"], index=0)
    if "fc_index" not in st.session_state:
        st.session_state.fc_index = 0
    if seq == "Random" and st.button("Shuffle"):
        st.session_state.fc_order = random.sample(range(len(vocab_df)), len(vocab_df))
        st.session_state.fc_index = 0
    if "fc_order" not in st.session_state:
        st.session_state.fc_order = list(range(len(vocab_df)))

    i = st.session_state.fc_index % len(vocab_df)
    real_idx = st.session_state.fc_order[i]
    row = vocab_df.iloc[real_idx]
    flip = st.checkbox("Show translation")
    show_source = row["turkish"] if direction_choice != "English → Turkish" else row["english"]
    show_target = row["english"] if direction_choice != "English → Turkish" else row["turkish"]

    st.markdown(f"### {show_source}")
    if flip:
        st.markdown(f"**{show_target}**")

    col1, col2 = st.columns(2)
    if col1.button("Previous"):
        st.session_state.fc_index = (st.session_state.fc_index - 1) % len(vocab_df)
        st.experimental_rerun()
    if col2.button("Next"):
        st.session_state.fc_index = (st.session_state.fc_index + 1) % len(vocab_df)
        st.experimental_rerun()

# -----------------------
# Manage Vocabulary Mode
# -----------------------
elif mode == "Manage Vocabulary":
    st.header("Manage Vocabulary")
    st.write("Add / edit vocabulary here. You can download the current set and upload a new file from the sidebar.")

    with st.expander("Add a new word"):
        t_new = st.text_input("Turkish")
        e_new = st.text_input("English")
        if st.button("Add word"):
            if t_new.strip() == "" or e_new.strip() == "":
                st.warning("Both fields required.")
            else:
                new_row = {"turkish": t_new.strip(), "english": e_new.strip()}
                st.session_state.vocab_df = pd.concat([st.session_state.vocab_df, pd.DataFrame([new_row])], ignore_index=True)
                st.success("Added.")
                st.experimental_rerun()

    st.subheader("Current vocabulary")
    edited = st.experimental_data_editor(st.session_state.vocab_df, num_rows="dynamic")  # works in recent Streamlit
    if st.button("Save edits"):
        st.session_state.vocab_df = edited.copy()
        st.success("Saved edits.")

    csv = st.session_state.vocab_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download vocabulary (CSV)", csv, file_name="vocabulary.csv", mime="text/csv")

# -----------------------
# Footer / Next steps hint
# -----------------------
st.sidebar.markdown("---")
st.sidebar.markdown("Starter features:\n- Upload CSV or use sample data\n- Quiz with simple fuzzy matching\n- Flashcards\n- Manage vocabulary / download CSV\n\nNext steps you might want to add:\n- spaced-repetition scheduling\n- multiple-choice quizzes\n- user accounts / progress tracking\n- sync with Google Sheets or GitHub\n- audio pronunciation (TTS)\n\nTell me which feature you want next and I'll provide the next PR-ready change! 🚀")
