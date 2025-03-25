import streamlit as st
from text_to_speech import init_tts_in_session_state, add_tts_controls_to_sidebar, speak_response

# Initialize TTS in Streamlit session state
init_tts_in_session_state()

# Add TTS controls in the sidebar
add_tts_controls_to_sidebar()

st.title("Text-to-Speech Demo")

# Input field for text
user_text = st.text_area("Enter text to speak:")

# Speak button
if st.button("Speak"):
    if user_text.strip():
        response = speak_response(user_text)
        st.success("Speaking...")
    else:
        st.warning("Please enter some text before clicking 'Speak'.")
