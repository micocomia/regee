# app.py
import streamlit as st
import json
import os
import base64
import time
from typing import Dict, Any, List, Optional
import logging

# Import components
from 1_document_processor import DocumentProcessor 
from 2_vector_store import VectorStore
from 3_retrieval import RetrievalSystem
from 4_intent_classifier import IntentClassifier
from 5_intent_handlers import IntentHandlerManager, SessionState
from 6_question_generator import QuestionGenerator
from 7_answer_evaluator import AnswerEvaluator
from speech_recognition import SpeechRecognition

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.messages = []
    st.session_state.documents = []
    st.session_state.document_names = []
    st.session_state.topics = []
    st.session_state.speech_enabled = False

def initialize_systems():
    """Initialize all the required systems."""
    # Only initialize once
    if st.session_state.initialized:
        return

    # Document Processor
    st.session_state.document_processor =  DocumentProcessor(
        embedding_model="all-MiniLM-L6-v2",
        chunk_size=300,  # Adjust chunk size as needed
        chunk_overlap=50
    )
    
    # Vector store for document storage
    st.session_state.vector_store = VectorStore(
        collection_name="test_collection",
        persist_directory="./data/vector_store"
    )
    
    # Retrieval system for finding relevant content
    st.session_state.retrieval_system = RetrievalSystem(
        vector_store=st.session_state.vector_store
    )

    # Question Generator
    st.session_state.question_generator = QuestionGenerator(
        retrieval_system=st.session_state.retrieval_system,
        use_local_llm=True,
        use_ollama=False
    )

    # Answer evaluator
    st.session_state.answer_evaluator = AnswerEvaluator(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Speech recognition
    st.session_state.speech_recognition = SpeechRecognition()


    st.session_state.intent_classifier = IntentClassifier()
  
    
    # Intent handler manager
    st.session_state.intent_handler = IntentHandlerManager(
        retrieval_system=st.session_state.retrieval_system,
        answer_evaluator=st.session_state.answer_evaluator,
        speech_recognition=st.session_state.speech_recognition,
        # These would come from Person A's code
        # question_generator=st.session_state.question_generator,
        # document_processor=st.session_state.document_processor
    )
    
    st.session_state.initialized = True
    logger.info("All systems initialized")

def add_message(role: str, content: str, **kwargs):
    """Add a message to the conversation history."""
    st.session_state.messages.append({"role": role, "content": content, **kwargs})

def handle_user_input(user_input: str):
    """Process user input and generate a response."""
    if not user_input:
        return
    
    # Add user message to history
    add_message("user", user_input)
    
    # This would use Person A's intent classifier to determine intent
    # intent_data = st.session_state.intent_classifier.classify(user_input)
    # intent_type = intent_data.get("intent", "unknown")
    
    # Since we don't have Person A's code yet, use a simple mock classifier
    intent_type, intent_data = mock_intent_classifier(user_input)
    
    # Process the intent
    response = st.session_state.intent_handler.handle_intent(intent_type, intent_data)
    
    # Add assistant message to history
    add_message("assistant", response.get("text", "I'm not sure how to respond to that."))
    
    # Handle special response types
    if "question" in response:
        st.session_state.current_question = response["question"]
    
    if "session_summary" in response:
        st.session_state.session_summary = response["session_summary"]

def mock_intent_classifier(text: str) -> tuple:
    """Simple mock intent classifier until Person A's code is integrated."""
    text_lower = text.lower()
    
    # Document upload intent
    if "upload" in text_lower or "document" in text_lower:
        return "document_upload", {"text": text}
    
    # Start/Stop review intent
    if "start" in text_lower and ("review" in text_lower or "quiz" in text_lower):
        return "start_review", {"text": text}
    
    if "stop" in text_lower or "end" in text_lower or "finish" in text_lower:
        return "stop_review", {"text": text}
    
    # Review status intent
    if "status" in text_lower or "progress" in text_lower or "how am i doing" in text_lower:
        return "review_status", {"text": text}
    
    # Set question type intent
    if "multiple choice" in text_lower or "multiple-choice" in text_lower:
        return "set_question_type", {"question_type": "multiple-choice"}
    
    if "free text" in text_lower or "free-text" in text_lower or "open ended" in text_lower:
        return "set_question_type", {"question_type": "free-text"}
    
    # Set number of questions intent
    if "questions" in text_lower and any(str(i) in text_lower for i in range(1, 51)):
        # Extract the number from text
        for i in range(1, 51):
            if str(i) in text_lower:
                return "set_num_questions", {"num_questions": i}
    
    # Set difficulty intent
    if "easy" in text_lower:
        return "set_difficulty", {"difficulty": "easy"}
    if "medium" in text_lower or "moderate" in text_lower:
        return "set_difficulty", {"difficulty": "medium"}
    if "hard" in text_lower or "difficult" in text_lower:
        return "set_difficulty", {"difficulty": "hard"}
    
    # Speech control intents
    if "enable speech" in text_lower or "turn on speech" in text_lower:
        return "enable_speech", {"text": text}
    if "disable speech" in text_lower or "turn off speech" in text_lower:
        return "disable_speech", {"text": text}
    
    # Handle answer intent (default if no other intent matches)
    return "answer", {"answer": text}

def process_uploaded_file(uploaded_file):
    """Process an uploaded document."""
    # Save the file temporarily
    file_path = os.path.join("./uploads", uploaded_file.name)
    os.makedirs("./uploads", exist_ok=True)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # This would use Person A's document processor
    # result = st.session_state.document_processor.process_document(file_path)
    
    # For now, we'll just mock the processing and add a success message
    st.session_state.documents.append(file_path)
    st.session_state.document_names.append(uploaded_file.name)
    
    # Extract some mock topics from the document name
    topics = [t.strip() for t in uploaded_file.name.replace(".pdf", "").replace(".pptx", "").split("_")]
    for topic in topics:
        if topic not in st.session_state.topics and len(topic) > 3:
            st.session_state.topics.append(topic)
            
    # Add a confirmation message to the chat
    add_message("assistant", f"I've processed '{uploaded_file.name}'. You can now start a review session.")
    
    return True

def get_js_code():
    """Get JavaScript code for speech recognition and other frontend functionality."""
    return """
    <script>
    // Initialize WebSocket for speech recognition events
    const speechSocket = new WebSocket(`ws://${window.location.host}/speech`);
    
    speechSocket.onopen = function(e) {
        console.log("Speech WebSocket connection established");
    };
    
    speechSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === "speech_config") {
            // Update speech recognition config
            if (window.speechManager) {
                window.speechManager.loadConfig(data.config);
            }
        }
    };
    
    // Speech recognition class would be implemented here
    // (Implementation from speech_recognition.py JavaScript code)
    
    // Function to send speech recognition result to the backend
    function sendSpeechResult(text) {
        if (speechSocket.readyState === WebSocket.OPEN) {
            speechSocket.send(JSON.stringify({
                type: "speech_result",
                text: text
            }));
        }
    }
    
    // Function to scroll chat to bottom
    function scrollChatToBottom() {
        const chatContainer = document.querySelector('.stChatContainer');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    // Set up observer to scroll chat when new messages arrive
    document.addEventListener('DOMContentLoaded', function() {
        const observer = new MutationObserver(scrollChatToBottom);
        
        // Start observing after a delay to ensure the chat container exists
        setTimeout(() => {
            const chatContainer = document.querySelector('.stChatContainer');
            if (chatContainer) {
                observer.observe(chatContainer, { childList: true, subtree: true });
            }
        }, 1000);
        
        // Add speech button if speech is enabled
        setTimeout(() => {
            const inputArea = document.querySelector('.stChatInputContainer');
            if (inputArea && !document.getElementById('speech-button')) {
                const speechButton = document.createElement('button');
                speechButton.id = 'speech-button';
                speechButton.className = 'speech-button';
                speechButton.innerHTML = '<i class="fas fa-microphone"></i>';
                speechButton.title = 'Start speech recognition';
                
                inputArea.insertBefore(speechButton, inputArea.firstChild);
                
                speechButton.addEventListener('click', function() {
                    if (window.speechManager) {
                        if (window.speechManager.isListening) {
                            window.speechManager.stopListening();
                        } else {
                            window.speechManager.startListening();
                        }
                    }
                });
            }
        }, 1000);
    });
    </script>
    
    <style>
    .speech-button {
        background-color: #4CAF50;
        border: none;
        color: white;
        padding: 10px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 50%;
        width: 40px;
        height: 40px;
    }
    
    .speech-button.listening {
        background-color: #f44336;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    </style>
    """

def main():
    """Main Streamlit app function."""
    st.set_page_config(
        page_title="Conversational Review Chatbot",
        page_icon="📚",
        layout="wide"
    )
    
    # Initialize systems
    initialize_systems()
    
    # Display custom CSS and JavaScript
    st.markdown(get_js_code(), unsafe_allow_html=True)
    
    # App title and description
    st.title("📚 Conversational Review Chatbot")
    st.markdown("""
    Upload your learning materials and have a conversation to review the content.
    The chatbot will ask you questions and provide feedback on your answers.
    """)
    
    # Sidebar for document upload and settings
    with st.sidebar:
        st.header("📁 Upload Documents")
        uploaded_file = st.file_uploader("Upload PDF or PPTX files", type=["pdf", "pptx"], key="file_uploader")
        
        if uploaded_file is not None:
            if st.button("Process Document"):
                with st.spinner("Processing document..."):
                    success = process_uploaded_file(uploaded_file)
                    if success:
                        st.success(f"Document '{uploaded_file.name}' processed successfully!")
        
        st.header("🔧 Review Settings")
        
        # Question type selector
        question_type = st.selectbox(
            "Question Type",
            ["Multiple Choice", "Free Text"],
            index=0
        )
        
        # Number of questions slider
        num_questions = st.slider(
            "Number of Questions",
            min_value=1,
            max_value=20,
            value=5
        )
        
        # Topic selector (if topics are available)
        if st.session_state.topics:
            selected_topics = st.multiselect(
                "Focus on Specific Topics",
                options=st.session_state.topics,
                default=None
            )
        
        # Difficulty selector
        difficulty = st.select_slider(
            "Difficulty Level",
            options=["Easy", "Medium", "Hard"],
            value="Medium"
        )
        
        # Speech toggle
        speech_enabled = st.toggle("Enable Speech Interaction", value=st.session_state.speech_enabled)
        if speech_enabled != st.session_state.speech_enabled:
            st.session_state.speech_enabled = speech_enabled
            if speech_enabled:
                st.session_state.speech_recognition.enable()
                st.success("Speech recognition enabled!")
            else:
                st.session_state.speech_recognition.disable()
                st.info("Speech recognition disabled.")
        
        # Start review button
        if st.button("Start Review Session"):
            # Apply settings to the handler
            st.session_state.intent_handler.session.question_type = question_type.lower()
            st.session_state.intent_handler.session.num_questions = num_questions
            st.session_state.intent_handler.session.difficulty = difficulty.lower()
            
            if 'selected_topics' in locals() and selected_topics:
                st.session_state.intent_handler.session.current_topics = selected_topics
            
            # Use the start review intent
            response = st.session_state.intent_handler.handle_intent("start_review", {})
            add_message("assistant", response.get("text", "Let's start the review!"))
    
    # Main chat interface
    st.header("💬 Chat")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    if user_input:
        handle_user_input(user_input)

if __name__ == "__main__":
    main()