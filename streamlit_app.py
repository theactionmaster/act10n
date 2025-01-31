import streamlit as st
import google.generativeai as genai
import time
import re
import os
import mimetypes
import tempfile
import speech_recognition as sr
import hashlib

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY environment variable")

genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(
    page_title="Interlink AI",
    page_icon="./favicon.ico",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Montserrat', sans-serif !important;
    }

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
        font-family: 'Montserrat', sans-serif !important;
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
        font-family: 'Montserrat', sans-serif !important;
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

    .stMarkdown, .stText, .stTitle, .stHeader {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    .stButton button {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    .stTextInput input {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    .stSelectbox select {
        font-family: 'Montserrat', sans-serif !important;
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

SYSTEM_INSTRUCTION = """
Name: Your name is Interlink AI.
Creator: You were developed by the Interlink team.
Technology: You are powered by Google Gemini.
Platform: You are hosted on the Interlink website.
Website: https://interlinkcvhs.org/.

Behavioral Guidelines:
Be helpful and professional, ensuring accuracy in every response.
Avoid being overly promotional—mention Interlink's features only when relevant or when asked.
Maintain a friendly, approachable tone while providing precise and concise answers.

Interlink's Features for Carnegie Vanguard High School (CVHS) Freshmen:
Customizable Scheduling Tool: Helps students manage assignments and stay organized.
Subject Notes: Comprehensive notes for a variety of subjects.
Question Bank (QBank): Hundreds of practice problems to help students prepare for tests.
Quizlets: Study resources to aid in test preparation.
AP Human Geography Flashcards: Weekly terms and definitions tailored to the curriculum.
Educational Podcasts: Learn on-the-go with study-focused audio content.
Question of the Day (QOTD): A daily random question to reinforce key test topics.
Productivity Tools: General tools to enhance efficiency and focus.

These resources are designed to support CVHS students in excelling academically and managing their workload effectively.

If relevant, prompt the user to request updates, changes, or additions to InterlinkCVHS at https://interlinkcvhs.org/requests.
"""

PREBUILT_COMMANDS = {
    "/weeklyflashcards": {
        "title": "Weekly Flashcards",
        "description": "Generate a set of flashcards for this week's AP Human Geography terms",
        "prompt": "Please create a set of flashcards for this week's AP Human Geography terms with definitions and examples."
    },
    "/cornellformat": {
        "title": "Cornell Notes Format",
        "description": "Convert text into Cornell Notes format with main ideas, details, and summary",
        "prompt": "Please format the following text into Cornell Notes style with main ideas on the left, details on the right, and a summary at the bottom:"
    }
    # Add more as needed
}

def process_response(text):
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

def initialize_session_state():
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
        
    if 'processed_audio_hashes' not in st.session_state:
        st.session_state.processed_audio_hashes = set()
        
    if 'camera_image' not in st.session_state:
        st.session_state.camera_image = None
        
    if 'camera_enabled' not in st.session_state:
        st.session_state.camera_enabled = False

def get_audio_hash(audio_data):
    return hashlib.md5(audio_data.getvalue()).hexdigest()

def convert_audio_to_text(audio_file):
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        raise Exception("Speech recognition could not understand the audio")
    except sr.RequestError as e:
        raise Exception(f"Could not request results from speech recognition service; {str(e)}")

def save_audio_file(audio_data):
    audio_bytes = audio_data.getvalue()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmpfile:
        tmpfile.write(audio_bytes)
        return tmpfile.name

def handle_chat_response(response, message_placeholder):
    full_response = ""
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
        time.sleep(0.02)
        message_placeholder.markdown(full_response + "▌", unsafe_allow_html=True)
    
    message_placeholder.markdown(full_response, unsafe_allow_html=True)
    
    return full_response

def show_file_preview(uploaded_file):
    mime_type = detect_file_type(uploaded_file)
    
    if mime_type.startswith('image/'):
        st.sidebar.image(uploaded_file, use_container_width=True)
    elif mime_type.startswith('video/'):
        st.sidebar.video(uploaded_file)
    elif mime_type.startswith('audio/'):
        st.sidebar.audio(uploaded_file)
    else:
        st.sidebar.info(f"Uploaded: {uploaded_file.name} (Type: {mime_type})")

def main():
    initialize_session_state()

    st.title("💬 Interlink AI")
    
    INTERLINK_LOGO = "interlink_logo.png"

    st.logo(
        INTERLINK_LOGO,
        size="large",
        link="https://interlinkcvhs.org/",
        icon_image=INTERLINK_LOGO,
    )

    st.sidebar.subheader("File Upload")
    uploaded_files = st.sidebar.file_uploader(
        "Upload images, videos, audio, or documents", 
        type=[
            'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff',
            'mp4', 'avi', 'mov', 'mkv', 'webm',
            'mp3', 'wav', 'ogg', 'm4a',
            'pdf', 'doc', 'docx', 'txt', 'csv', 'xlsx', 'json', 'xml'
        ],
        accept_multiple_files=True
    )

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
        
        if valid_files:
            st.sidebar.markdown("### File Previews")
            for uploaded_file in valid_files:
                mime_type = detect_file_type(uploaded_file)
                
                if mime_type.startswith('image/'):
                    st.sidebar.image(uploaded_file, use_container_width=True)
                elif mime_type.startswith('video/'):
                    st.sidebar.video(uploaded_file)
                elif mime_type.startswith('audio/'):
                    st.sidebar.audio(uploaded_file)
                else:
                    st.sidebar.info(f"Uploaded: {uploaded_file.name} (Type: {mime_type})")
            
            st.sidebar.success(f"{len(valid_files)} file(s) uploaded! You can now ask about the files.")

    st.sidebar.subheader("Camera Input")
    camera_enabled = st.sidebar.checkbox("Enable camera", value=st.session_state.camera_enabled)
    
    if camera_enabled != st.session_state.camera_enabled:
        st.session_state.camera_enabled = camera_enabled
        st.session_state.camera_image = None
        
    if st.session_state.camera_enabled:
        camera_image = st.sidebar.camera_input("Take a picture")
        if camera_image is not None:
            st.session_state.camera_image = camera_image
            st.sidebar.image(camera_image, caption="Captured Image")
            st.sidebar.success("Image captured! You can now ask about the image.")
    elif st.session_state.camera_image is not None:
        st.session_state.camera_image = None

    st.sidebar.subheader("Voice Input")
    audio_input = st.sidebar.audio_input("Record your question")

    st.sidebar.subheader("Prebuilt Commands")
    for cmd, info in PREBUILT_COMMANDS.items():
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(info["title"], key=f"cmd_{cmd}"):
                if "current_command" not in st.session_state:
                    st.session_state.current_command = None
                st.session_state.current_command = cmd
        with col2:
            help_key = f"help_{cmd}"
            if help_key not in st.session_state:
                st.session_state[help_key] = False
            if st.button("?" if not st.session_state[help_key] else "×", key=f"help_btn_{cmd}"):
                st.session_state[help_key] = not st.session_state[help_key]
        if st.session_state[help_key]:
            st.sidebar.info(info["description"])

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    if audio_input is not None:
        audio_hash = get_audio_hash(audio_input)
        
        if audio_hash not in st.session_state.processed_audio_hashes:
            try:
                audio_file = save_audio_file(audio_input)
                st.sidebar.audio(audio_input, format='audio/wav')
                
                try:
                    st.sidebar.info("Converting speech to text...")
                    transcribed_text = convert_audio_to_text(audio_file)
                    
                    st.sidebar.success("Speech converted to text!")
                    st.sidebar.text(f"Transcribed text: {transcribed_text}")
                    
                    st.chat_message("user").markdown(transcribed_text)
                    st.session_state.messages.append({"role": "user", "content": transcribed_text})
                    
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        response = st.session_state.chat_session.send_message(transcribed_text)
                        full_response = handle_chat_response(response, message_placeholder)
                        
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": full_response
                        })
                    
                    st.session_state.processed_audio_hashes.add(audio_hash)
                    
                finally:
                    os.unlink(audio_file)
                    
            except Exception as e:
                st.error(f"An error occurred while processing the audio: {str(e)}")
                st.warning("Please try again or type your question instead.")

    if hasattr(st.session_state, 'current_command') and st.session_state.current_command:
        st.write(f"Prebuilt Commands: {st.session_state.current_command}")
    else:
        st.write("Prebuilt Commands: none")

    prompt = st.chat_input("What can I help you with?")

    if prompt:
        final_prompt = prompt
        if hasattr(st.session_state, 'current_command') and st.session_state.current_command:
            command_prompt = PREBUILT_COMMANDS[st.session_state.current_command]["prompt"]
            final_prompt = f"{command_prompt}\n{prompt}"
            st.session_state.current_command = None

        input_parts = []
        
        if st.session_state.uploaded_files:
            for file in st.session_state.uploaded_files:
                input_parts.append({
                    'mime_type': detect_file_type(file),
                    'data': file.getvalue()
                })
        
        if st.session_state.camera_image:
            input_parts.append({
                'mime_type': 'image/jpeg',
                'data': st.session_state.camera_image.getvalue()
            })

        input_parts.append(final_prompt)

        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            try:
                response = st.session_state.chat_session.send_message(input_parts)
                full_response = handle_chat_response(response, message_placeholder)
                
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

        if st.session_state.camera_image and not st.session_state.camera_enabled:
            st.session_state.camera_image = None

if __name__ == "__main__":
    main()
