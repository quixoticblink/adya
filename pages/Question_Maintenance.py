import streamlit as st
import json
import os
import pandas as pd

st.set_page_config(page_title="Question Maintenance", page_icon="🛠️", layout="wide")

import auth
if not auth.is_authenticated():
    st.warning("🔒 Login Required")
    st.write("Please sign in on the Home page.")
    st.stop()

# Admin Password Guard
auth.check_admin_password()

st.title("🛠️ Question Maintenance")
st.caption("View and update the quiz questions.")

QUESTIONS_FILE = "questions.json"

def load_questions_raw():
    if not os.path.exists(QUESTIONS_FILE):
        return []
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading questions: {e}")
        return []

# --- Current Questions ---
st.subheader("Current Questions")
questions = load_questions_raw()

if questions:
    df = pd.DataFrame(questions)
    # Reorder columns for better visibility if they exist
    cols = ["id", "topic", "marks", "prompt", "answer_type"]
    present_cols = [c for c in cols if c in df.columns]
    other_cols = [c for c in df.columns if c not in cols]
    df = df[present_cols + other_cols]
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.info(f"Total questions: {len(questions)}")
    
    # Download as CSV
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Questions as CSV",
        data=csv_data,
        file_name="questions.csv",
        mime="text/csv",
        help="Download current questions to edit in Excel/Numbers."
    )
    
else:
    st.warning("No questions found or file is empty.")

st.divider()

# --- Update Questions ---
st.subheader("Update Questions")
st.write("Upload a new **CSV** file to replace the current set of questions.")
st.write("Required columns: `id`, `topic`, `marks`, `prompt`.")

uploaded_file = st.file_uploader("Upload new questions.csv", type=["csv"])

if uploaded_file is not None:
    try:
        new_df = pd.read_csv(uploaded_file)
        
        # Validation
        required_cols = {"id", "topic", "marks", "prompt"}
        missing_cols = required_cols - set(new_df.columns)
        
        if missing_cols:
            st.error(f"Missing required columns in CSV: {missing_cols}")
        else:
            # Convert to list of dicts for JSON storage
            new_data = new_df.to_dict(orient="records")
            
            st.success(f"File valid! Contains {len(new_data)} questions.")
            st.dataframe(new_df.head(), use_container_width=True)
            
            if st.button("🚨 Overwrite Questions File", type="primary"):
                # Ensure marks are integers if possible, handle cleanup
                # (JSON serialization handles basics, but let's ensure types if needed)
                with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
                st.toast("Questions updated successfully!", icon="✅")
                st.session_state.clear() # Clear cache to force reload
                st.rerun()
                    
    except Exception as e:
        st.error(f"Failed to parse CSV: {e}")
