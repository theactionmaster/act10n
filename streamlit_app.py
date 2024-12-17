import streamlit as st
import google.generativeai as genai
import time
import re
import os
import mimetypes

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY environment variable")

genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(
    page_title="𝙸𝚗𝚝𝚎𝚛𝚕𝚒𝚗𝚔 𝙰𝙸",
    page_icon="./favicon.ico",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    
    .stChatInputContainer {
        display: flex;
        align-items: center;
    }
    .back-button {
        width: 300px;
        margin-top: 20px;
        padding: 10px 20px;
        font-size: 18px;
        background-color: #0b1936;
        color: #5799f7;
        border: 2px solid #4a83d4;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
        box-shadow: 0 0 15px rgba(74, 131, 212, 0.3);
        position: relative;
        overflow: hidden;
        display: inline-block;
    }
    .back-button:before {
        content: 'BACK TO INTERLINK';
        display: flex;
        align-items: center;
        justify-content: center;
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #0b1936;
        transition: transform 0.3s ease;
        font-size: 18px;
        color: #5799f7;
        text-align: center;
        font-family: 'Orbitron', sans-serif;
    }
    .back-button:hover {
        background-color: #1c275c;
        color: #73abfa;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(74, 131, 212, 0.2);
    }
    .back-button:hover:before {
        transform: translateY(-100%);
        color: #73abfa;
    }
    .file-preview {
        max-height: 200px;
        overflow: hidden;
        margin-bottom: 10px;
    }
    .file-preview img, .file-preview video, .file-preview audio {
        max-width: 100%;
        max-height: 200px;
        object-fit: contain;
    }
</style>
<center>
    <a href="https://interlinkcvhs.org/" class="back-button" target="_blank" rel="noopener noreferrer">
        interlinkcvhs.org
    </a>
</center>""", unsafe_allow_html=True)

generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

def process_response(text):
    """Process the response text to improve formatting."""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if re.match(r'^\d+\.', line.strip()):
            processed_lines.append('\n' + line.strip())
        elif line.strip().startswith('*') or line.strip().startswith('-'):
            processed_lines.append('\n' + line.strip())
        else:
            processed_lines.append(line)
    
    text = '\n'.join(processed_lines)
    
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = re.sub(r'(\n[*-] .+?)(\n[^*\n-])', r'\1\n\2', text)
    
    return text.strip()

def detect_file_type(uploaded_file):
    """Enhanced file type detection with comprehensive MIME type mapping."""
    filename = uploaded_file.name
    file_ext = os.path.splitext(filename)[1].lower()
    
    mime_mappings = {
        # Image types
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg', 
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.tiff': 'image/tiff',
        
        # Video types
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo', 
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        
        # Audio types
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        
        # Document types
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.json': 'application/json',
        '.xml': 'application/xml'
    }
    
    if file_ext in mime_mappings:
        return mime_mappings[file_ext]
    
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

SYSTEM_INSTRUCTION = """Your name is Interlink AI, an AI chatbot on Interlink.
You are powered by the Interlink Large Language Model.
You were created by the Interlink team.
You are on a website called Interlink that provides Carnegie Vanguard High School (CVHS) freshmen resources to stay on top of their assignments and tests using a customized scheduling tool as well as notes, educational simulations, Quizlets, the Question of the Day (QOTD) and the Question Bank (QBank) that both provide students example questions from upcoming tests or assignments, and other resources to help them do better in school.
The link to Interlink is: https://interlinkcvhs.org/."""

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'chat_model' not in st.session_state:
        st.session_state.chat_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            system_instruction=SYSTEM_INSTRUCTION,
        )

    if 'chat_session' not in st.session_state:
        st.session_state.chat_session = st.session_state.chat_model.start_chat(history=[])

    if 'messages' not in st.session_state:
        initial_message = """Hello! I'm Interlink AI, your personal academic assistant for Carnegie Vanguard High School. How can I assist you today?"""
        
        st.session_state.messages = [
            {"role": "assistant", "content": initial_message}
        ]
    
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

def main():
    """Main Streamlit application logic."""
    initialize_session_state()

    st.title("💬 Interlink AI")

    uploaded_files = st.sidebar.file_uploader(
        "Upload images, videos, audio, or documents", 
        type=[
            # Images
            'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff',
            # Videos
            'mp4', 'avi', 'mov', 'mkv', 'webm',
            # Audio
            'mp3', 'wav', 'ogg', 'm4a',
            # Documents
            'pdf', 'doc', 'docx', 'txt', 'csv', 'xlsx', 'json', 'xml'
        ],
        help="Upload multiple files for analysis and discussion (Max 20 MB per file)",
        accept_multiple_files=True
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    if uploaded_files:
        oversized_files = []
        valid_files = []
        
        for file in uploaded_files:
            if file.size > 20 * 1024 * 1024:
                oversized_files.append(file.name)
            else:
                valid_files.append(file)
        
        if oversized_files:
            st.sidebar.warning(f"The following files exceed 20 MB and were not uploaded: {', '.join(oversized_files)}")
        
        uploaded_files = valid_files

        st.session_state.uploaded_files = uploaded_files
        
        for uploaded_file in uploaded_files:
            mime_type = detect_file_type(uploaded_file)
            
            if mime_type.startswith('image/'):
                st.sidebar.image(uploaded_file, use_container_width=True)
            elif mime_type.startswith('video/'):
                st.sidebar.video(uploaded_file)
            elif mime_type.startswith('audio/'):
                st.sidebar.audio(uploaded_file)
            else:
                st.sidebar.info(f"Uploaded: {uploaded_file.name} (Type: {mime_type})")
        
        st.sidebar.success(f"{len(uploaded_files)} file(s) uploaded! You can now ask about the files.")

    prompt = st.chat_input("What can I help you with?")

    if prompt:
        input_parts = []
        
        if st.session_state.uploaded_files:
            for file in st.session_state.uploaded_files:
                input_parts.append({
                    'mime_type': detect_file_type(file),
                    'data': file.getvalue()
                })
        
        input_parts.append(prompt)

        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                response = st.session_state.chat_session.send_message(input_parts)
                
                formatted_response = process_response(response.text)

                chunks = []
                for line in formatted_response.split('\n'):
                    chunks.extend(line.split(' '))
                    chunks.append('\n')

                for chunk in chunks:
                    if chunk != '\n':
                        full_response += chunk + ' '
                    else:
                        full_response += chunk
                    time.sleep(0.05)
                    message_placeholder.markdown("**InterlinkAI:** " + full_response + "▌", unsafe_allow_html=True)
                
                message_placeholder.markdown("**InterlinkAI:** " + full_response, unsafe_allow_html=True)
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_response
                })
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                if "rate_limit" in str(e).lower():
                    st.warning("The API rate limit has been reached. Please wait a moment before trying again.")
                else:
                    st.warning("Please try again in a moment.")

if __name__ == "__main__":
    main()
