import streamlit as st
import auth

# -----------------------------
# Configuration
# -----------------------------
st.set_page_config(page_title="Adya Science Quiz", page_icon="🧪", layout="centered")

st.title("🧪 Adya Science Dashboard")

# -----------------------------
# Authentication Logic
# -----------------------------
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Handle OAuth callback
if "code" in st.query_params:
    code = st.query_params["code"]
    try:
        user_info = auth.exchange_code_for_user(code)
    except Exception:
        user_info = None
        
    st.query_params.clear()
    
    if user_info:
        st.session_state.user_email = user_info.get("email")
        st.rerun()
    else:
        st.error("Login failed. Please try again.")

# Check Allowlist
allowed_emails = st.secrets.get("google_auth", {}).get("allowed_emails", [])
if st.session_state.user_email and allowed_emails and st.session_state.user_email not in allowed_emails:
    st.error("⛔ Access Denied")
    st.write(f"User **{st.session_state.user_email}** is not authorized.")
    if st.button("Logout"):
        st.session_state.user_email = None
        st.rerun()
    st.stop()

# -----------------------------
# Display
# -----------------------------
if not st.session_state.user_email:
    # --- Landing Page ---
    st.info("👋 Welcome! Please sign in to access the quiz and tools.")
    
    try:
        login_url = auth.get_login_url()
        st.link_button("Sign in with Google", login_url, type="primary")
    except Exception:
        st.error("Google Auth not configured.")
        
else:
    # --- Dashboard ---
    st.success(f"✅ Signed in as: **{st.session_state.user_email}**")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚀 Start Learning")
        st.page_link("pages/1_Quiz.py", label="Go to Quiz", icon="🧪")
        
    with col2:
        st.subheader("📊 Track Progress")
        st.page_link("pages/Feedback_History.py", label="View History", icon="📜")
        
    st.divider()
    with st.expander("🛠️ Teacher Tools"):
        st.page_link("pages/Question_Maintenance.py", label="Manage Questions", icon="🛠️")
        
    if st.button("Logout", type="secondary"):
        st.session_state.user_email = None
        st.rerun()
