# sidebar_speech.py
import streamlit as st
from streamlit.components.v1 import html

class SidebarSpeechRecognition:
    """
    A class that provides speech recognition functionality in the Streamlit sidebar.
    This offers a minimalist interface for speech recognition verification before sending to chat.
    """
    def __init__(self, callback_function=None):
        """
        Initialize sidebar speech recognition component.
        
        Args:
            callback_function: Function to call when speech is confirmed
        """
        self.callback_function = callback_function
        self.is_enabled = False
        
        # Initialize recognized_text in session state if not exists
        if "recognized_text" not in st.session_state:
            st.session_state.recognized_text = ""
    
    def render(self):
        """Render the speech recognition interface in the sidebar"""
        with st.sidebar:
            st.subheader("Speech Recognition")
            
            # Toggle for enabling/disabling
            enabled = st.toggle("Enable Speech Recognition", value=self.is_enabled)
            
            # Update state if changed
            if enabled != self.is_enabled:
                self.is_enabled = enabled
                st.session_state.speech_sidebar_enabled = enabled
                
                # Reset recognized text when enabling/disabling
                st.session_state.recognized_text = ""
            
            # Only show the interface if enabled
            if self.is_enabled:
                # Create a container for the speech UI
                speech_container = st.container()
                
                with speech_container:
                    # Add speech recognition JavaScript
                    components_height = 150  # Enough height for the small interface
                    html_component = self._get_speech_component()
                    html(html_component, height=components_height)
                    
                    # Placeholder for recognized text
                    if "recognized_text" not in st.session_state:
                        st.session_state.recognized_text = ""
                    
                    # Always show recognized text box (empty or with content)
                    recognized_text = st.session_state.recognized_text if "recognized_text" in st.session_state else ""
                    
                    # Use a container with custom styling
                    speech_result_container = st.container()
                    with speech_result_container:
                        st.markdown("""
                        <style>
                        .speech-result-box {
                            border: 1px solid #ddd;
                            border-radius: 4px;
                            padding: 8px 12px;
                            background-color: #f9f9f9;
                            min-height: 60px;
                            margin-bottom: 10px;
                            font-size: 14px;
                        }
                        .speech-result-placeholder {
                            color: #888;
                            font-style: italic;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        # Display either recognized text or placeholder
                        if recognized_text:
                            st.markdown(f"""
                            <div class="speech-result-box">
                                {recognized_text}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Buttons to send to chat or clear
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Send to Chat", key="send_to_chat_btn"):
                                    self._send_to_chat(recognized_text)
                            with col2:
                                if st.button("Clear", key="clear_speech_btn"):
                                    st.session_state.recognized_text = ""
                                    st.rerun()
                        else:
                            # Show empty box with placeholder text
                            st.markdown("""
                            <div class="speech-result-box speech-result-placeholder">
                                Recognized speech will appear here...
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Instructions when no text is recognized yet
                            st.caption("Click the microphone button or press Ctrl+Space to start speaking")
            else:
                st.caption("Enable speech recognition to use voice input")

    def _send_to_chat(self, text):
        """Send recognized text to chat via callback function"""
        if self.callback_function and text.strip():
            self.callback_function(text)
            # Clear the recognized text after sending
            st.session_state.recognized_text = ""
            st.rerun()
    
    def _get_speech_component(self):
        """Get the HTML/JS component for speech recognition"""
        return """
        <div id="sidebar-speech-container" style="margin: 10px 0;">
            <div id="sidebar-speech-ui" style="display: flex; flex-direction: column; align-items: center;">
                <button id="sidebar-mic-button" class="sidebar-speech-button">
                    🎤
                </button>
                <div id="sidebar-speech-status" style="margin-top: 5px; font-size: 12px; color: #555;">
                    Ready
                </div>
            </div>
        </div>

        <style>
        .sidebar-speech-button {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 10px;
            text-align: center;
            display: inline-block;
            font-size: 18px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 50%;
            width: 45px;
            height: 45px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .sidebar-speech-button:hover {
            background-color: #45a049;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
        }
        
        .sidebar-speech-button.listening {
            background-color: #f44336;
            animation: sidebar-pulse 1.5s infinite;
        }
        
        @keyframes sidebar-pulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 8px rgba(244, 67, 54, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
        }
        </style>
        
        <script>
        // Sidebar Speech Recognition
        (function() {
            // Create speech recognition object
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                console.error("Speech recognition not supported in this browser");
                document.getElementById("sidebar-speech-status").textContent = "Not supported in this browser";
                document.getElementById("sidebar-mic-button").disabled = true;
                document.getElementById("sidebar-mic-button").style.backgroundColor = "#ccc";
                return;
            }
            
            const recognition = new SpeechRecognition();
            recognition.lang = 'en-US';
            recognition.interimResults = true; // Enable interim results to show real-time updates
            recognition.maxAlternatives = 1;
            
            let isListening = false;
            let finalTranscript = ''; // Store the final transcript
            
            // DOM elements
            const micButton = document.getElementById("sidebar-mic-button");
            const statusElement = document.getElementById("sidebar-speech-status");
            
            // Recognition event handlers
            recognition.onstart = function() {
                isListening = true;
                statusElement.textContent = "Listening...";
                micButton.classList.add("listening");
                finalTranscript = ''; // Reset transcript when starting new session
                
                // Show immediate feedback by updating session state
                updateSessionState('');
            };
            
            recognition.onresult = function(event) {
                // Create a transcript from all results
                let interimTranscript = '';
                
                // Combine results
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript + ' ';
                    } else {
                        interimTranscript += event.results[i][0].transcript + ' ';
                    }
                }
                
                // Update status with interim results
                statusElement.textContent = "Listening: " + interimTranscript;
                
                // Update Streamlit session state with the current transcript (final + interim)
                const currentTranscript = finalTranscript + interimTranscript;
                console.log("Current transcript:", currentTranscript);
                
                if (currentTranscript.trim() !== '') {
                    updateSessionState(currentTranscript);
                }
            };
            
            // Helper function to update session state
            function updateSessionState(transcript) {
                // Update Streamlit session state with recognized text
                const data = {
                    recognized_text: transcript.trim()
                };
                
                console.log("Updating session state with:", data.recognized_text);
                
                // Use both methods to ensure update works
                // 1. Direct Streamlit method
                if (window.parent && window.parent.postMessage) {
                    window.parent.postMessage({
                        type: "streamlit:setComponentValue",
                        value: data
                    }, "*");
                }
                
                // 2. Fetch method
                fetch("", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        "session_state": data,
                        "rerun": true
                    })
                }).catch(err => {
                    console.error("Error updating session state:", err);
                });
            }
            
            recognition.onerror = function(event) {
                console.error("Speech recognition error:", event.error);
                statusElement.textContent = "Error: " + event.error;
                isListening = false;
                micButton.classList.remove("listening");
            };
            
            recognition.onend = function() {
                isListening = false;
                statusElement.textContent = "Ready";
                micButton.classList.remove("listening");
                
                // Make sure we update one final time with the complete transcript
                if (finalTranscript) {
                    console.log("Final transcript on end:", finalTranscript);
                    updateSessionState(finalTranscript);
                }
            };
            
            recognition.onnomatch = function() {
                statusElement.textContent = "Didn't recognize that";
                setTimeout(() => {
                    statusElement.textContent = "Ready";
                }, 2000);
            };
            
            // Button click handler
            micButton.addEventListener("click", toggleRecognition);
            
            // Keyboard shortcut (Ctrl+Space)
            document.addEventListener("keydown", function(event) {
                if (event.ctrlKey && event.code === "Space") {
                    event.preventDefault();
                    toggleRecognition();
                }
            });
            
            // Toggle recognition
            function toggleRecognition() {
                if (isListening) {
                    recognition.stop();
                } else {
                    try {
                        // Clear status and show visual feedback before starting
                        statusElement.textContent = "Starting...";
                        
                        // Add a small delay to improve UX and allow visual feedback
                        setTimeout(() => {
                            recognition.start();
                        }, 150);
                    } catch (error) {
                        console.error("Error starting recognition:", error);
                        statusElement.textContent = "Error starting";
                    }
                }
            }
        })();
        </script>
        """

# Integration with app.py
def initialize_sidebar_speech(app_handle_user_input):
    """Initialize sidebar speech recognition and connect it to the main app"""
    if "speech_sidebar" not in st.session_state:
        # Create sidebar speech instance with callback to app's message handler
        st.session_state.speech_sidebar = SidebarSpeechRecognition(
            callback_function=app_handle_user_input
        )
        
    # Restore enabled state if available
    if "speech_sidebar_enabled" in st.session_state:
        st.session_state.speech_sidebar.is_enabled = st.session_state.speech_sidebar_enabled
        
    # Render the sidebar speech UI
    st.session_state.speech_sidebar.render()