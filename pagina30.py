import streamlit as st

def app():
    

    # Link de incorporação (Power BI -> Arquivo -> Incorporar relatório -> Site seguro ou Público)
    powerbi_url = "https://app.powerbi.com/view?r=eyJrIjoiNGFkNzk0YmUtZDE1Yy00ZGMzLThlMGYtNTk1NzI3MWZjYTkzIiwidCI6IjY1MDQ2MTVmLTRjZmMtNDk0OC1iMDZlLTI5YmFmNTAxOTVkNiJ9"

    st.components.v1.iframe(powerbi_url, width=1900, height=900, scrolling=True)