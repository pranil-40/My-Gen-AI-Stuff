import streamlit as st

st.title("🚀 My First Streamlit App!")

st.write("Welcome to your new web app, powered by Python and uv.")

# Let's add a simple interactive widget
name = st.text_input("What is your name?")

if name:
    st.success(f"Hello {name}! Your environment is working perfectly. Try it now")