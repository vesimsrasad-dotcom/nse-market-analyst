"""
lib/auth.py
Simple password protection for NSE Market Analyst.
Set DASHBOARD_PASSWORD in Streamlit Secrets or .env to enable.
"""

import streamlit as st
from lib.config import DASHBOARD_PASSWORD


def check_password() -> bool:
    """
    Returns True if password protection is disabled or user has authenticated.
    Call this at the top of every page.
    """
    # No password set — open access
    if not DASHBOARD_PASSWORD:
        return True

    # Already authenticated this session
    if st.session_state.get("authenticated"):
        return True

    # Show login screen
    _show_login()
    return False


def _show_login():
    """Render the password gate UI."""
    st.markdown("""
    <style>
      html, body, [class*="css"] { font-size: 17px !important; }
      .login-box {
        max-width: 400px; margin: 80px auto;
        background: #1A1F2E; border-radius: 14px;
        padding: 40px 36px;
        border: 1px solid rgba(255,107,0,0.3);
        box-shadow: 0 0 40px rgba(255,107,0,0.08);
      }
    </style>
    <div class="login-box">
      <div style="text-align:center; margin-bottom:28px;">
        <div style="font-size:36px;">📊</div>
        <div style="font-size:22px; font-weight:700; color:#FF6B00; margin-top:8px;">
          NSE Market Analyst
        </div>
        <div style="font-size:13px; color:#666; margin-top:6px;">
          Private dashboard — enter password to continue
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        pwd = st.text_input("Password", type="password", placeholder="Enter dashboard password")
        submitted = st.form_submit_button("Enter Dashboard", use_container_width=True, type="primary")
        if submitted:
            if pwd == DASHBOARD_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

    st.stop()


def logout_button():
    """Show a logout button in the sidebar."""
    if DASHBOARD_PASSWORD:
        st.sidebar.divider()
        if st.sidebar.button("🔒 Lock Dashboard", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()
