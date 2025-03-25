# app.py
import streamlit as st
from streamlit.components.v1 import html
from streamlined_custom_component import create_component
import json
import os
import base64
import time
from typing import Dict, Any, List, Optional
import logging
import re
import hashlib

# Import components
from document_processor import DocumentProcessor 
from vector_store import VectorStore
from retrieval import RetrievalSystem
from intent_classifier import IntentClassifier
from intent_handler import IntentHandlerManager, SessionState
from question_generator import QuestionGenerator
from answer_evaluator import AnswerEvaluator
from speech_recognition import speech_recognition

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

gee_gee_avatar = "https://yt3.googleusercontent.com/ytc/AIdro_ntlFIYXvx-85ML7yd7DEHYO4Ehd9VF6vE-QHCT6JYVoVw=s900-c-k-c0x00ffffff-no-rj"
user_avatar = None

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
    
    # Speech recognition specific state
    st.session_state.speech_sidebar_enabled = False
    st.session_state.recognized_text = ""
    st.session_state.speech_to_send = ""

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
        
    # Intent classifier
    st.session_state.intent_classifier = IntentClassifier()
    
    # Intent handler manager
    st.session_state.intent_handler = IntentHandlerManager(
        document_processor=st.session_state.document_processor,
        retrieval_system=st.session_state.retrieval_system,
        question_generator=st.session_state.question_generator,
        answer_evaluator=st.session_state.answer_evaluator,
    )
    
    # Set speech state
    st.session_state.intent_handler.session.speech_enabled = st.session_state.speech_enabled
    
    st.session_state.initialized = True
    logger.info("All systems initialized")

def add_message(role: str, avatar: str, content: str, **kwargs):
    """Add a message to the conversation history."""
    message_data = {"role": role, 
                    "avatar": avatar,
                    "content": content}
    
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
    add_message("user", user_avatar, user_input)
    
    # Set up processing state to show a spinner
    st.session_state.show_processing = True
    
    # Force a rerun to update the UI and show the processing indicator
    st.rerun()

def generate_assistant_response():
    """
    Process the most recent user message and generate a response.
    This is called only when show_processing is True.
    """
    try:
        # Add a slight delay before responding (adjust seconds as needed)
        time.sleep(0.3)  # 500ms delay

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
        add_message("assistant", gee_gee_avatar, response.get("text", "I'm not sure how to respond to that."), **message_kwargs)
    except Exception as e:
        # Handle errors gracefully
        logger.error(f"Error processing response: {str(e)}")
        add_message("assistant", gee_gee_avatar, f"I encountered an error while processing your request. Please try again or try rephrasing your message.")
    finally:
        # Reset processing indicators
        st.session_state.show_processing = False

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
            add_message("assistant", gee_gee_avatar, f"Processing '{uploaded_file.name}'...")
        
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
                add_message("assistant", gee_gee_avatar, f"Failed to process '{uploaded_file.name}': No content extracted.")
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
            add_message("assistant", gee_gee_avatar, f"Failed to process '{uploaded_file.name}': {str(e)}")
        return False

def display_chat_messages():
    """Display chat messages with special formatting for questions."""
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(name=message["role"], avatar=message["avatar"]):
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

def render_speech_sidebar():
    """Render the speech recognition sidebar component using streamlined_custom_component"""
    with st.sidebar:
        st.subheader("Speech Recognition")
        
        # Toggle for enabling/disabling
        speech_enabled = st.toggle("Enable Speech Recognition", value=st.session_state.speech_sidebar_enabled)
        
        # Update state if changed
        if speech_enabled != st.session_state.speech_sidebar_enabled:
            st.session_state.speech_sidebar_enabled = speech_enabled
            st.session_state.recognized_text = ""
        
        # Only show the interface if enabled
        if speech_enabled:
            # Create the speech component
            speech_component = speech_recognition()
            
            # Display the component and get its return value
            speech_result = speech_component()
            
            # Process the speech recognition results
            if speech_result:
                status = speech_result.get("status", "")
                transcript = speech_result.get("transcript", "")
                process_immediately = speech_result.get("process_immediately", False)
                
                # Display interim results (for showing feedback to the user)
                if status == "interim":
                    st.session_state.recognized_text = transcript
                
                # Handle final transcript (ready to send to chat)
                if status == "final" and transcript:
                    # Prevent duplicate processing
                    if 'last_processed_transcript' not in st.session_state or st.session_state.last_processed_transcript != transcript:
                        st.session_state.speech_to_send = transcript
                        st.session_state.last_processed_transcript = transcript
                        
                        # Force immediate processing if needed
                        if process_immediately:
                            # Process the speech input
                            text_to_send = st.session_state.speech_to_send
                            st.session_state.speech_to_send = ""  # Clear after sending
                            st.session_state.recognized_text = ""  # Clear recognized text too
                            
                            if text_to_send.strip():
                                handle_user_input(text_to_send)
                                st.rerun()  # Force a rerun to update the UI

def main():
    """Main Streamlit app function."""
    st.set_page_config(
        page_title="ReGee - Educational Review Assistant",
        page_icon="📚",
        layout="wide"
    )

    # Initialize systems
    initialize_systems()
    
    # Sidebar Elements
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

        # Spacing to push speech recognition to the bottom
        st.markdown("<br>" * 1, unsafe_allow_html=True)

        # Add the speech recognition sidebar
        render_speech_sidebar()

    # Check if there's speech to process from the component that wasn't already processed
    if hasattr(st.session_state, "speech_to_send") and st.session_state.speech_to_send:
        text_to_send = st.session_state.speech_to_send
        # Create a simple hash of the text for comparison
        transcript_hash = hash(text_to_send.strip())
        
        # Only process if we haven't already processed this exact text
        if not hasattr(st.session_state, "last_processed_hash") or st.session_state.last_processed_hash != transcript_hash:
            st.session_state.last_processed_hash = transcript_hash
            st.session_state.speech_to_send = ""  # Clear after sending
            st.session_state.recognized_text = ""  # Clear recognized text too
            
            # Process the speech text
            if text_to_send.strip():
                handle_user_input(text_to_send)
                st.rerun()  # Force a rerun to update the UI with the new message
    
    # Special processing path
    if st.session_state.show_processing:
        display_chat_messages()
        
        with st.chat_message("assistant", avatar=gee_gee_avatar):
            typing_container = st.empty()

            if st.session_state.intent_handler.session.is_reviewing:
                # Get the intent type from the latest user message
                user_input = st.session_state.messages[-1]["content"]
                intent_data = st.session_state.intent_classifier.classify(user_input)
                intent_type = intent_data.get("intent", "unknown")
                
                # Check if the intent is not "answer" during a review session
                if intent_type != "answer" and intent_type != "continue":
                    typing_container.markdown("*...*")
                elif st.session_state.intent_handler.session.current_question is not None and st.session_state.intent_handler.session.awaiting_feedback == False:
                    typing_container.markdown("*Evaluating your answer...*")
                else:
                    typing_container.markdown("*Generating next question...*")
            else:
                typing_container.markdown("*...*")

            generate_assistant_response()

            # Clear the typing indicator before rerun
            typing_container.empty()
                
                
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
        "Type your message here, upload files, or use the speech recognition in the sidebar",
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
        
        # Process each file
        for uploaded_file in user_input["files"]:
            with st.chat_message("assistant", avatar=gee_gee_avatar):
                typing_container = st.empty()
                typing_container.markdown(f"*Processing {uploaded_file.name}...*")  # Or any subtle indicator you prefer

                success = process_uploaded_file(uploaded_file, is_part_of_batch=(len(user_input["files"]) > 1))
                if not success:
                    st.error(f"Failed to process {uploaded_file.name}")

                # Clear the typing indicator before rerun
                typing_container.empty()
        
        # Add a summary message for multiple files
        if len(user_input["files"]) > 1:
            add_message("assistant", gee_gee_avatar, f"Processed {len(user_input['files'])} files. You can now start a review session with 'Start review' command.")
        # For single file uploads, provide guidance if not already provided
        elif len(user_input["files"]) == 1 and success:
            # If the last message was just a processing confirmation, replace it with guidance
            if st.session_state.messages[-1]["role"] == "assistant" and "I've successfully processed" in st.session_state.messages[-1]["content"]:
                st.session_state.messages[-1]["content"] += "\n\nWhat would you like to do next? You can:\n- Type 'Start review' to begin a review session\n- Type 'Show settings' to configure your review session\n- Upload more materials to include in your review"
            # If it was a different kind of message, add a new guidance message
            else:
                add_message("assistant", gee_gee_avatar, "Now that your document is processed, you can:\n- Type 'Start review' to begin a review session\n- Type 'Show settings' to configure your review session\n- Upload more materials to include in your review")
        
        # Force a rerun to update the UI with new messages
        st.rerun()

if __name__ == "__main__":
    main()