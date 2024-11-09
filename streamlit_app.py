import streamlit as st
import google.generativeai as genai
import time
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Interlink AI",
    page_icon="🤖",
    layout="wide"
)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    st.error("API key not found. Please set the GEMINI_API_KEY environment variable.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

SYSTEM_INSTRUCTION = """Your name is Interlink AI, an AI chatbot on Interlink. You are powered by the Interlink Large Language Model. You were created by the Interlink team. You are on a website called Interlink that provides Carnegie Vanguard High School (CVHS) freshmen resources to stay on top of their assignments and tests as well as notes, simulations, the question of the day (QOTD) that provides students example questions from upcoming tests or assignments, and other resources to help them do better in school. The link to Interlink is: https://interlinkcvhs.org/. Your job is to answer prompts thoroughly. Always make sure you are providing the correct answer. Don't print random asterisks.
When outputting bolded or italicized text, DO IT CORRECTLY.
When outputting lists, DO IT CORRECTLY. I don't want to see random asterisks. Make it an actual list and create new lines. Don't just output it in one line.
When outputting code, DO IT CORRECTLY. For example, when asked to print Hello World in Python, dont output: "python print("Hello World"). Instead, output: "print("Hello World"). Don't randomly say the language you are writing the code in on the same code block because then it'll create errors."""

if 'chat_model' not in st.session_state:
    st.session_state.chat_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION,
    )

if 'chat_session' not in st.session_state:
    st.session_state.chat_session = st.session_state.chat_model.start_chat(history=[])

if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm Interlink AI, your personal academic assistant for Carnegie Vanguard High School. I'm here to help you stay on top of your assignments, tests, and provide you with valuable resources. How can I assist you today?"}
    ]

st.title("💬 Interlink AI")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

if prompt := st.chat_input("What can I help you with?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            response = st.session_state.chat_session.send_message(prompt)
            
            chunks = response.text.split()
            for chunk in chunks:
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "▌", unsafe_allow_html=True)
            
            message_placeholder.markdown(full_response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            if "rate_limit" in str(e).lower():
                st.warning("The API rate limit has been reached. Please wait a moment before trying again.")
            else:
                st.warning("Please try again in a moment.")
