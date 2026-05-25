"""
lib/auth.py
Simple password protection for NSE Market Analyst.
Set DASHBOARD_PASSWORD in Streamlit Secrets or .env to enable.
"""

import streamlit as st
import os


def _get_password() -> str:
    """
    Read password fresh every call.
    Checks Streamlit Secrets first, then .env fallback.
    """
    try:
        pwd = st.secrets.get("DASHBOARD_PASSWORD", "")
        if pwd:
            return str(pwd).strip()
    except Exception:
        pass
    return os.getenv("DASHBOARD_PASSWORD", "").strip()


def check_password() -> bool:
    """
    Returns True if password protection is disabled or user has authenticated.
    Call this at the top of every page.
    """
    password = _get_password()

    # No password set — open access
    if not password:
        return True

    # Already authenticated this session
    if st.session_state.get("authenticated"):
        return True

    # Show login screen
    _show_login(password)
    return False


def _show_login(password: str):
    """Render the password gate UI."""
    st.markdown("""
    <style>
      html, body, [class*="css"] { font-size: 17px !important; }
      .block-container { max-width: 500px !important; margin: auto; padding-top: 80px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; margin-bottom:32px;">
      <div style="font-size:48px;">📊</div>
      <div style="font-size:26px; font-weight:700; color:#FF6B00; margin-top:10px;">
        NSE Market Analyst
      </div>
      <div style="font-size:14px; color:#666; margin-top:8px;">
        Private dashboard — enter password to continue
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=True):
        pwd_input = st.text_input(
            "Password",
            type="password",
            placeholder="Enter dashboard password",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button(
            "🔓 Enter Dashboard",
            use_container_width=True,
            type="primary"
        )
        if submitted:
            if pwd_input.strip() == password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")

    st.stop()


def logout_button():
    """Show a logout button in the sidebar."""
    password = _get_password()
    if password:
        st.sidebar.divider()
        if st.sidebar.button("🔒 Lock Dashboard", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()
