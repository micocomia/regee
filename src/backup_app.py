# app.py
import streamlit as st
from streamlit.components.v1 import html
import json
import os
import base64
import time
from typing import Dict, Any, List, Optional
import logging
import re

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
    st.session_state.processing_type = None 
    st.session_state.processing_start_time = None
    st.session_state.show_processing = False  # New flag for processing display
    st.session_state.processing_message = ""  # Message to show during processing

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
        use_local_llm=False,
        use_ollama=True
    )

    # Answer evaluator
    st.session_state.answer_evaluator = AnswerEvaluator(
        llm_backend='ollama',
        use_local_llm=False,
        use_ollama=True
    )
    
    # Speech recognition
    st.session_state.speech_recognition = SpeechRecognition()
    
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
    
    # Set speech state
    st.session_state.intent_handler.session.speech_enabled = st.session_state.speech_enabled
    
    st.session_state.initialized = True
    logger.info("All systems initialized")

def add_message(role: str, content: str, **kwargs):
    """Add a message to the conversation history."""
    message_data = {"role": role, "content": content}
    
    # Add any additional data (like question data)
    for key, value in kwargs.items():
        message_data[key] = value
        
    st.session_state.messages.append(message_data)

def handle_user_input(user_input: str):
    """
    Process user input and generate a response.
    This function adds the user message to history and marks it for processing.
    """
    if not user_input:
        return
    
    # Add user message to history
    add_message("user", user_input)
    
    # Set up processing state to show a spinner
    st.session_state.show_processing = True
    
    # Set the processing type and message based on the context
    if st.session_state.intent_handler.session.is_reviewing:
        if st.session_state.intent_handler.session.current_question is not None:
            st.session_state.processing_message = "Evaluating your answer..."
        else:
            st.session_state.processing_message = "Generating next question..."
    else:
        st.session_state.processing_message = "Generating question based on uploaded documents..."
    
    # Force a rerun to update the UI and show the processing indicator
    st.rerun()

def generate_assistant_response():
    """
    Process the most recent user message and generate a response.
    This is called only when show_processing is True.
    """
    try:
        # Get the most recent user message
        user_input = st.session_state.messages[-1]["content"]
        
        # Use the intent classifier to determine intent
        intent_data = st.session_state.intent_classifier.classify(user_input)
        intent_type = intent_data.get("intent", "unknown")
        
        # Check if we're awaiting feedback - simple responses treated as "continue"
        if st.session_state.intent_handler.session.awaiting_feedback:
            if intent_type == "answer" and re.match(r'^(ok|okay|sure|yes|yep|yeah|alright|fine|next|continue|go on)$', user_input.lower()):
                intent_type = "continue"
                intent_data = {"intent": "continue"}
            elif intent_type == "answer" and re.match(r'^(no|stop|im tired|end)$', user_input.lower()):
                intent_type = "stop_review"
                intent_data = {"intent": "stop_review"}
        
        # Process the intent
        response = st.session_state.intent_handler.handle_intent(intent_type, intent_data)
        
        # Prepare the assistant message
        message_kwargs = {}
        
        # Include question data if present
        if "question" in response:
            message_kwargs["question"] = response["question"]
        
        # Add any other special response data
        if "session_summary" in response:
            message_kwargs["session_summary"] = response["session_summary"]
        
        # Add assistant message to history with any special data
        add_message("assistant", response.get("text", "I'm not sure how to respond to that."), **message_kwargs)
    except Exception as e:
        # Handle errors gracefully
        logger.error(f"Error processing response: {str(e)}")
        add_message("assistant", f"I encountered an error while processing your request. Please try again or try rephrasing your message.")
    finally:
        # Reset processing indicators
        st.session_state.show_processing = False

def display_processing_indicator():
    """Display processing indicator as a simple chat message."""
    import streamlit as st
    
    if not st.session_state.processing_type:
        return
    
    # Use a simple chat message approach
    with st.chat_message("assistant"):
        # Different messages based on processing type
        if st.session_state.processing_type == "evaluating":
            message = "Evaluating your answer..."
            detail = "Comparing your response to the learning materials..."
        elif st.session_state.processing_type == "generating":
            message = "Generating your next question..."
            detail = "Creating a question from your learning materials..."
        else:
            message = "Thinking..."
            detail = "Processing your request..."
        
        # Display the message and detail
        st.write(message)
        st.caption(detail)

def add_speech_recognition_js():
    """Add custom speech recognition JavaScript that works with Streamlit."""
    js_code = st.session_state.speech_recognition.get_js_code()
    return st.components.v1.html(js_code, height=0)

def check_speech_query_params():
    """Check for speech recognition query parameters and handle them."""
    if 'speech_text' in st.query_params:
        text = st.query_params['speech_text']
        logger.info(f"Speech recognition text received via URL param: {text}")
        
        # Clear the parameter to avoid processing it again
        st.query_params.clear()
        
        # Process the recognized text
        handle_user_input(text)

def process_uploaded_file(uploaded_file, is_part_of_batch=False):
    """
    Process an uploaded document and provide feedback in the chat.
    
    Args:
        uploaded_file: The file to process
        is_part_of_batch: Whether this file is part of a batch upload (affects messaging)
    """
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs("./uploads", exist_ok=True)
        
        # Save the file temporarily
        file_path = os.path.join("./uploads", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Add an initial message to show upload started (only if not part of batch)
        if not is_part_of_batch:
            add_message("assistant", f"Processing '{uploaded_file.name}'...")
        
        # Process the document using the document processor
        processed_chunks = st.session_state.document_processor.process_document(file_path)
        
        # Check if we got valid results (non-empty list)
        if processed_chunks and isinstance(processed_chunks, list) and len(processed_chunks) > 0:
            # Add processed chunks to vector store
            st.session_state.vector_store.add_documents(processed_chunks)
            
            # Update session state
            st.session_state.documents.append(file_path)
            st.session_state.document_names.append(uploaded_file.name)
            
            # Extract topics from the first chunk's metadata
            if "metadata" in processed_chunks[0] and "topics" in processed_chunks[0]["metadata"]:
                topics = processed_chunks[0]["metadata"]["topics"]
                for topic in topics:
                    if topic not in st.session_state.topics:
                        st.session_state.topics.append(topic)
                    
            # Update the session to indicate documents are loaded
            st.session_state.intent_handler.session.documents_loaded = True
                
            # Update the latest assistant message with success info (only if not part of batch)
            if not is_part_of_batch:
                st.session_state.messages[-1]["content"] = (
                    f"I've successfully processed '{uploaded_file.name}'.\n\n"
                )
            else:
                # For batch processing, just log success without updating messages
                logger.info(f"Successfully processed '{uploaded_file.name}' with {len(processed_chunks)} chunks")
            
            return True
        else:
            # Handle processing failure due to empty results
            if not is_part_of_batch:
                st.session_state.messages[-1]["content"] = (
                    f"I couldn't process '{uploaded_file.name}'.\n\n"
                    f"No content was extracted from the document. Please check if it's a valid PDF or PPTX file."
                )
            else:
                # For batch processing, add a specific error message
                add_message("assistant", f"Failed to process '{uploaded_file.name}': No content extracted.")
            return False
            
    except Exception as e:
        # Handle processing failure
        logger.error(f"Error processing file: {str(e)}")
        if not is_part_of_batch:
            st.session_state.messages[-1]["content"] = (
                f"I couldn't process '{uploaded_file.name}'.\n\n"
                f"Error: {str(e)}"
            )
        else:
            # For batch processing, add a specific error message
            add_message("assistant", f"Failed to process '{uploaded_file.name}': {str(e)}")
        return False

def display_chat_messages():
    """Display chat messages with special formatting for questions."""
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            # Check if this message contains a question
            if message["role"] == "assistant" and "question" in message:
                question_data = message["question"]
                
                # Display the question text
                st.write(message["content"])
                
                # Special handling for multiple-choice questions
                if question_data.get("type") == "multiple-choice" and "options" in question_data:
                    # Create a container for options with better styling
                    options_container = st.container()
                    with options_container:
                        st.markdown("### Options:")
                        options = question_data["options"]
                        
                        # Display each option with a letter label
                        for idx, option in enumerate(options):
                            option_letter = chr(65 + idx)  # Convert to A, B, C, D
                            st.markdown(f"**{option_letter}.** {option}")
            else:
                # Regular message without question data
                st.write(message["content"])

def main():
    """Main Streamlit app function."""
    st.set_page_config(
        page_title="ReGee - Educational Review Assistant",
        page_icon="📚",
        layout="wide"
    )

    st.markdown("""
    <script>
    function checkBrowserCompatibility() {
        const isSpeechSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        const browserInfo = `Browser: ${navigator.userAgent}`;
        
        if (!isSpeechSupported) {
            document.querySelector('.stApp').insertAdjacentHTML('afterbegin', 
                `<div style="background-color: #ffcccc; padding: 10px; margin: 10px 0; border-radius: 5px;">
                    Speech recognition is not supported in your current browser. 
                    Please try using Chrome, Edge, or the latest Safari.
                    <br><small>${browserInfo}</small>
                </div>`
            );
        }
    }
    
    document.addEventListener('DOMContentLoaded', checkBrowserCompatibility);
    </script>
    """, unsafe_allow_html=True)

    # Initialize systems
    initialize_systems()
    
    # Check for speech recognition query parameters
    check_speech_query_params()
    
    # Initialize speech recognition specifically
    if st.session_state.speech_enabled:
        st.session_state.speech_recognition.enable()

    # Add custom speech recognition JavaScript
    add_speech_recognition_js()
    
    # Add data attribute for speech enabled state that JavaScript can read
    speech_enabled_attr = f"""
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        const streamlitDoc = document.querySelector('.stApp');
        if (streamlitDoc) {{
            streamlitDoc.setAttribute('data-speech-enabled', '{str(st.session_state.speech_enabled).lower()}');
        }}
    }});
    </script>
    """
    st.markdown(speech_enabled_attr, unsafe_allow_html=True)
    
    # Sidebar with app title, description and speech settings
    with st.sidebar:
        # App title and description moved to sidebar
        st.title("Instructions")
        st.markdown("""
        Upload your learning materials and let ReGee help you review by asking questions about the content.
        ReGee will help you think critically by quizzing you rather than explaining concepts.
        
        You can control the review by chatting with ReGee. Try saying:
        - "Show me the current review settings" to see your options
        - "Set question type to free text and 10 questions" to configure multiple settings at once
        - "I want easy difficulty and start the review" to set difficulty and begin
        - Upload your PDF or PPTX files directly in the chat!
        """)
        
        # Speech settings (kept in sidebar)
        st.header("Speech Settings")
        speech_enabled = st.toggle("Enable Speech Interaction", value=st.session_state.speech_enabled)
        if speech_enabled != st.session_state.speech_enabled:
            st.session_state.speech_enabled = speech_enabled
            st.session_state.intent_handler.session.speech_enabled = speech_enabled
            
            # Update the data attribute for JavaScript
            speech_attr_update = f"""
            <script>
            const streamlitDoc = document.querySelector('.stApp');
            if (streamlitDoc) {{
                streamlitDoc.setAttribute('data-speech-enabled', '{str(speech_enabled).lower()}');
            }}
            </script>
            """
            st.markdown(speech_attr_update, unsafe_allow_html=True)
            
            # Show notification
            if speech_enabled:
                st.success("Speech recognition enabled! Press Ctrl+Space or click the microphone button to start speaking.")
            else:
                st.info("Speech recognition disabled.")
    
    # Main chat interface (now only showing the chat)
    # Removed the header and description from here
    
    # Special processing path when showing a spinner
    if st.session_state.show_processing:
        display_chat_messages()
        
        with st.chat_message("assistant"):
            with st.spinner(st.session_state.processing_message):
                generate_assistant_response()
                
        st.rerun()

    # Display chat messages or placeholder if no messages
    if st.session_state.messages:
        display_chat_messages()
    else:
        # Display a placeholder when no conversation has started
        st.markdown("""
        <div style="display: flex; justify-content: center; align-items: center; height: 60vh; text-align: center;">
            <div style="padding: 2rem; border-radius: 0.5rem; background-color: #f8f9fa; max-width: 600px;">
                <h2>Start chatting with ReGee</h2>
                <p>Upload your learning materials or ask a question to begin.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Handle file uploads directly from chat input
    user_input = st.chat_input(
        "Type your message here, upload files, or press Ctrl+Space to speak",
        accept_file="multiple",
        file_type=["pdf", "pptx"]
    )
    
    # Process text input if provided
    if user_input and user_input.text:
        handle_user_input(user_input.text)
    # Process uploaded files if any
    elif user_input and user_input["files"]:
        # Add a message showing that files were uploaded
        file_names = [file.name for file in user_input["files"]]
        files_str = ", ".join(file_names)
        add_message("user", f"Uploaded: {files_str}")
        
        # Process each file
        for uploaded_file in user_input["files"]:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                success = process_uploaded_file(uploaded_file, is_part_of_batch=(len(user_input["files"]) > 1))
                if not success:
                    st.error(f"Failed to process {uploaded_file.name}")
        
        # Add a summary message for multiple files
        if len(user_input["files"]) > 1:
            add_message("assistant", f"Processed {len(user_input['files'])} files. You can now start a review session with 'Start review' command.")
        # For single file uploads, provide guidance if not already provided
        elif len(user_input["files"]) == 1 and success:
            # If the last message was just a processing confirmation, replace it with guidance
            if st.session_state.messages[-1]["role"] == "assistant" and "I've successfully processed" in st.session_state.messages[-1]["content"]:
                st.session_state.messages[-1]["content"] += "\n\nWhat would you like to do next? You can:\n- Type 'Start review' to begin a review session\n- Type 'Show settings' to configure your review session\n- Upload more materials to include in your review"
            # If it was a different kind of message, add a new guidance message
            else:
                add_message("assistant", "Now that your document is processed, you can:\n- Type 'Start review' to begin a review session\n- Type 'Show settings' to configure your review session\n- Upload more materials to include in your review")
        
        # Force a rerun to update the UI with new messages
        st.rerun()

if __name__ == "__main__":
    main()