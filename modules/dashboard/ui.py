import streamlit as st


def dashboard_card(title, content_func):

    st.markdown(
        f"""
        <div class="dashboard-card">
            <h3>{title}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    content_func()



def apply_dashboard_style():

    st.markdown(
        """
        <style>

        .dashboard-card {

            background-color: white;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 15px;
            border: 1px solid #e5e7eb;

        }

        .dashboard-card h3 {

            margin-top:0;
            font-size:20px;
            color:#0E4D92;

        }


        div[data-testid="stMetric"] {

            background:white;
            border-radius:10px;
            padding:10px;
            border:1px solid #e5e7eb;

        }


        .block-container {

            padding-top:1.5rem;

        }


        </style>
        """,
        unsafe_allow_html=True
    )



def section_title(title):

    st.markdown(
        f"""
        <h3 style="
            color:#0E4D92;
            margin-bottom:10px;
        ">
        {title}
        </h3>
        """,
        unsafe_allow_html=True
    )