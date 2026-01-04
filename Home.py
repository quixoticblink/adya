import streamlit as st
import auth
import utils

# -----------------------------
# Configuration
# -----------------------------
st.set_page_config(page_title="Adya", page_icon="🎓", layout="wide")
utils.use_custom_css()

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
# UI Components
# -----------------------------

def hero_header():
    st.markdown("""
        <div style='text-align: center; padding: 3rem 0; margin-bottom: 2rem;'>
            <h1 style='font-size: 3.5rem; margin-bottom: 0.5rem; background: linear-gradient(90deg, #2563EB, #7C3AED); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Adya</h1>
            <p style='font-size: 1.25rem; color: #6B7280;'>Your Personal AI Science Tutor</p>
        </div>
    """, unsafe_allow_html=True)

def subject_card(title, icon, page, color_start, color_end):
    # Streamlit doesn't support full custom DIV clicks easily without extra components, 
    # so we use a styled container + page_link button.
    with st.container():
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, {color_start}, {color_end}); padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1rem; text-align: center;'>
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>{icon}</div>
                <div style='font-weight: 600; font-size: 1.1rem;'>{title}</div>
            </div>
        """, unsafe_allow_html=True)
        st.page_link(page, label=f"Start {title}", use_container_width=True)

# -----------------------------
# Main Layout
# -----------------------------

if not st.session_state.user_email:
    # --- Landing Page ---
    hero_header()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("👋 Welcome! Please sign in to access your personalized dashboard.")
        try:
            login_url = auth.get_login_url()
            st.link_button("Sign in with Google", login_url, type="primary", use_container_width=True)
        except Exception:
            st.error("Google Auth not configured.")
else:
    # --- Dashboard ---
    with st.sidebar:
        st.success(f"Signed in: {st.session_state.user_email}")
        if st.button("Logout", type="secondary"):
            st.session_state.user_email = None
            st.rerun()
            
    # Clean Connection Status (Icon only if good, warn if bad)
    try:
        import sheets_db, gspread
        try:
            sheets_db.get_client()
            # If good, maybe show nothing or a small pill in the corner? 
            # Or just keep it as a small successful toast on load
            pass
        except Exception as e:
            st.warning(f"⚠️ Database Offline: {e}")
    except ImportError:
        st.warning("⚠️ Database: Local Mode")

    hero_header()
    
    st.markdown("### 📚 Your Subjects")
    
    # Grid Layout
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        subject_card("Chemistry", "🧪", "pages/1_Chemistry.py", "#3B82F6", "#2563EB")
    with c2:
        subject_card("Biology", "🧬", "pages/2_Biology.py", "#10B981", "#059669")
    with c3:
        subject_card("Physics", "⚛️", "pages/3_Physics.py", "#8B5CF6", "#7C3AED")
    with c4:
        subject_card("Geography", "🌍", "pages/4_Geography.py", "#F59E0B", "#D97706")
    with c5:
        subject_card("History", "📜", "pages/5_History.py", "#EC4899", "#DB2777")
        
    st.markdown("---")
    
    col_tools, col_stats = st.columns(2)
    
    with col_tools:
        st.subheader("🛠️ Tools")
        st.page_link("pages/Question_Maintenance.py", label="Manage Question Bank", icon="📥")
    
    with col_stats:
        st.subheader("📊 Analytics")
        st.page_link("pages/Feedback_History.py", label="View Progress & History", icon="📈")
