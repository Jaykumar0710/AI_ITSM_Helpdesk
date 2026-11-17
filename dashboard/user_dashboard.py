import streamlit as st


def show_user_dashboard(user):

    st.title("🤖 IT Support Assistant")

    st.caption(
        f"Welcome, {user['full_name']}! "
        "How can we help you today?"
    )

    # -------------------------------------------------
    # SIDEBAR
    # -------------------------------------------------

    with st.sidebar:

        st.header("Employee Portal")

        st.write(
            f"Logged in as: **{user['full_name']}**"
        )

        st.caption("Role: End User")

        st.divider()

        if st.button(
            "Logout",
            use_container_width=True
        ):

            st.session_state.user = None

            st.session_state.messages = []

            st.rerun()

    # -------------------------------------------------
    # DASHBOARD NAVIGATION
    # -------------------------------------------------

    page = st.radio(
        "Navigate",
        [
            "AI Chatbot",
            "My Tickets"
        ],
        horizontal=True
    )

    # -------------------------------------------------
    # AI CHATBOT
    # -------------------------------------------------

    if page == "AI Chatbot":

        st.info(
            "Describe your IT problem below. "
            "The AI assistant will suggest troubleshooting steps."
        )

        # We will integrate your existing chatbot here.
        st.write(
            "Your existing RAG chatbot will be integrated "
            "in this section."
        )

    # -------------------------------------------------
    # MY TICKETS
    # -------------------------------------------------

    elif page == "My Tickets":

        st.subheader("🎫 My Support Tickets")

        # We will integrate user-specific ticket retrieval here.
        st.write(
            "Your personal support tickets will appear here."
        )