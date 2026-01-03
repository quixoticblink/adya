import streamlit as st
import os

st.title("Debug Config Loading")

st.write("Checking `secrets.toml`...")

try:
    auth_config = st.secrets.get("google_auth", {})
    client_id = auth_config.get("client_id", "")
    client_secret = auth_config.get("client_secret", "")
    
    st.write(f"**Found 'google_auth' section**: {bool(auth_config)}")
    
    st.write(f"**Client ID found**: {bool(client_id)}")
    if client_id:
        st.write(f"Length: {len(client_id)}")
        st.write(f"Starts with: `{client_id[:5]}...`")
        st.write(f"Ends with: `...{client_id[-5:]}`")
        if " " in client_id:
            st.error("⚠️ Client ID contains spaces! Please remove them.")
        else:
            st.success("Client ID format looks okay (no spaces).")
            
    st.write(f"**Client Secret found**: {bool(client_secret)}")
    if client_secret:
        st.write(f"Length: {len(client_secret)}")
        if " " in client_secret:
            st.error("⚠️ Client Secret contains spaces! Please remove them.")
        else:
            st.success("Client Secret format looks okay.")

except Exception as e:
    st.error(f"Error reading secrets: {e}")
