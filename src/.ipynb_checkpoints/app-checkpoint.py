# app.py
import streamlit as st
import json
import os
import base64
import time
from typing import Dict, Any, List, Optional
import logging

# Import components
from document_processor import DocumentProcessor 
from vector_store import VectorStore
from retrieval import RetrievalSystem
from intent_classifier import IntentClassifier
from intent_handler import IntentHandlerManager, SessionState
from question_generator import QuestionGenerator
from answer_evaluator import AnswerEvaluator
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
    st.session_state.speech_input = None
    st.session_state.awaiting_response = False

def initialize_systems():
    """Initialize all the required systems."""
    # Only initialize once
    if st.session_state.initialized:
        return

    # Document Processor
    st.session_state.document_processor = DocumentProcessor(
        embedding_model="all-MiniLM-L6-v2",
        chunk_size=300,
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
    st.session_state.answer_evaluator = AnswerEvaluator(
        llm_backend='ollama',
        use_local_llm=False,
        use_ollama=True
    )
    
    # Speech recognition
    st.session_state.speech_recognition = SpeechRecognition()
    
    # Register the speech result callback
    st.session_state.speech_recognition.register_result_callback(
        lambda text: speech_to_text_callback(text)
    )

    # Intent classifier
    st.session_state.intent_classifier = IntentClassifier()
    
    # Intent handler manager
    st.session_state.intent_handler = IntentHandlerManager(
        document_processor=st.session_state.document_processor,
        retrieval_system=st.session_state.retrieval_system,
        question_generator=st.session_state.question_generator,
        answer_evaluator=st.session_state.answer_evaluator,
        speech_recognition=st.session_state.speech_recognition
    )
    
    st.session_state.initialized = True
    logger.info("All systems initialized")

def add_message(role: str, content: str, **kwargs):
    """Add a message to the conversation history."""
    st.session_state.messages.append({"role": role, "content": content, **kwargs})

def handle_user_input(user_input: str):
    """
    Process user input and generate a response.
    This function adds the user message to history and marks it for processing.
    """
    if not user_input:
        return
    
    # Add user message to history
    add_message("user", user_input)
    
    # Mark that we're awaiting a response to this message
    st.session_state.awaiting_response = True
    
    # Force a rerun to update the UI and show the user message
    st.rerun()

def process_pending_response():
    """
    Process the most recent user message and generate a response if needed.
    This function checks if there's a pending user message without a response,
    generates the response, and adds it to the message history.
    """
    if st.session_state.awaiting_response:
        # Get the most recent user message
        user_input = st.session_state.messages[-1]["content"]
        
        # Use the intent classifier to determine intent
        intent_data = st.session_state.intent_classifier.classify(user_input)
        intent_type = intent_data.get("intent", "unknown")
        
        # Process the intent
        response = st.session_state.intent_handler.handle_intent(intent_type, intent_data)
        
        # Add assistant message to history
        add_message("assistant", response.get("text", "I'm not sure how to respond to that."))
        
        # Handle special response types
        if "question" in response:
            st.session_state.current_question = response["question"]
        
        if "session_summary" in response:
            st.session_state.session_summary = response["session_summary"]
        
        # Mark that we've processed the response
        st.session_state.awaiting_response = False

def speech_to_text_callback(text: str):
    """Callback function for handling speech recognition results."""
    logger.info(f"Speech recognition callback received: {text}")
    
    # Store the recognized speech in the session state
    st.session_state.speech_input = text
    
    # Process the speech input as a user message
    handle_user_input(text)

def process_uploaded_file(uploaded_file):
    """Process an uploaded document."""
    # Save the file temporarily
    file_path = os.path.join("./uploads", uploaded_file.name)
    os.makedirs("./uploads", exist_ok=True)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Process the document using the document processor
    result = st.session_state.document_processor.process_document(file_path)
    
    if result.get("success", False):
        st.session_state.documents.append(file_path)
        st.session_state.document_names.append(uploaded_file.name)
        
        # Get topics from the document processor if available
        if "topics" in result:
            for topic in result["topics"]:
                if topic not in st.session_state.topics:
                    st.session_state.topics.append(topic)
                
        # Add a confirmation message to the chat
        add_message("assistant", f"I've processed '{uploaded_file.name}'. You can now start a review session.")
        
        return True
    else:
        # Handle processing failure
        error_msg = result.get("error", "Unknown error occurred during document processing")
        add_message("assistant", f"I couldn't process '{uploaded_file.name}'. Error: {error_msg}")
        return False

def main():
    """Main Streamlit app function."""
    st.set_page_config(
        page_title="ReGee - Educational Review Assistant",
        page_icon="📚",
        layout="wide"
    )
    
    # Initialize systems
    initialize_systems()
    
    # Process any pending responses before rendering the UI
    process_pending_response()
    
    # Display custom CSS and JavaScript for speech recognition
    if 'speech_recognition' in st.session_state:
        st.markdown(st.session_state.speech_recognition.get_js_code(), unsafe_allow_html=True)
    
    # App title and description
    st.title("📚 ReGee - Educational Review Assistant")
    st.markdown("""
    Upload your learning materials and let ReGee help you review by asking questions about the content.
    ReGee will help you think critically by quizzing you rather than explaining concepts.
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
    
    # Add a placeholder for typing indicators when waiting for a response
    if st.session_state.awaiting_response:
        with st.chat_message("assistant"):
            st.write("Thinking...")
    
    # Chat input
    user_input = st.chat_input("Type your message here or press Ctrl+Space to speak")
    if user_input:
        handle_user_input(user_input)

if __name__ == "__main__":
    main()