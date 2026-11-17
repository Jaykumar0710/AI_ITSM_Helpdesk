import streamlit as st


def show_executive_dashboard(user):

    # -------------------------------------------------
    # ROLE VERIFICATION
    # -------------------------------------------------

    if user.get("role") != "it_executive":

        st.error(
            "Access denied. "
            "This dashboard is available only to IT executives."
        )

        st.stop()

    # -------------------------------------------------
    # DASHBOARD HEADER
    # -------------------------------------------------

    st.title("🛠️ IT Executive Dashboard")

    st.caption(
        f"Welcome, {user['full_name']}! "
        "Manage IT support operations."
    )

    # -------------------------------------------------
    # SIDEBAR
    # -------------------------------------------------

    with st.sidebar:

        st.header("IT Service Desk")

        st.write(
            f"Logged in as: **{user['full_name']}**"
        )

        st.caption("Role: IT Executive")

        st.divider()

        if st.button(
            "Logout",
            use_container_width=True
        ):

            st.session_state.user = None

            st.session_state.messages = []

            st.rerun()

    # -------------------------------------------------
    # EXECUTIVE NAVIGATION
    # -------------------------------------------------

    page = st.radio(
        "Executive Navigation",
        [
            "Ticket Management",
            "Knowledge Base",
            "Analytics"
        ],
        horizontal=True
    )

    # -------------------------------------------------
    # TICKET MANAGEMENT
    # -------------------------------------------------

    if page == "Ticket Management":

        st.subheader("🎫 Ticket Management")

        st.write(
            "View, assign, and resolve employee support tickets."
        )

        # Existing ticket management integration goes here.

    # -------------------------------------------------
    # KNOWLEDGE BASE
    # -------------------------------------------------

    elif page == "Knowledge Base":

        st.subheader("📚 Knowledge Base Management")

        st.write(
            "Manage the IT support knowledge base."
        )

        # Existing knowledge-base management integration goes here.

    # -------------------------------------------------
    # ANALYTICS
    # -------------------------------------------------

    elif page == "Analytics":

        st.subheader("📊 Support Analytics")

        st.write(
            "View ticket statistics and support performance."
        )

        # Existing analytics integration goes here.