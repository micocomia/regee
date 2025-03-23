# simple_speech_test.py
import streamlit as st
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    st.set_page_config(page_title="Simple Speech Recognition Test")
    
    st.title("Simple Speech Recognition Test")
    st.write("This is a minimal test for the Web Speech API.")
    
    # Add a simple button to trigger speech recognition
    if st.button("Start Speech Recognition"):
        st.session_state.trigger_speech = True
        st.write("Click the microphone button that appears or use keyboard shortcut.")
    
    # Display recognized speech
    if 'recognized_text' not in st.session_state:
        st.session_state.recognized_text = ""
    
    st.write("### Recognized Speech:")
    st.write(st.session_state.recognized_text if st.session_state.recognized_text else "Nothing recognized yet.")
    
    # Create a direct JavaScript implementation for testing
    js_code = """
    <script>
    // Wait for page to fully load
    window.addEventListener('DOMContentLoaded', (event) => {
        console.log('DOM fully loaded, initializing speech recognition test');
        
        // Check if speech recognition is available
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Speech Recognition is not supported in this browser. Please try Chrome or Edge.');
            console.error('Speech Recognition not supported');
            return;
        }
        
        // Create recognition object
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        // Configure
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        
        // Create UI elements
        const button = document.createElement('button');
        button.textContent = '🎤 Click to Speak';
        button.style.position = 'fixed';
        button.style.bottom = '20px';
        button.style.right = '20px';
        button.style.zIndex = '9999';
        button.style.padding = '10px 20px';
        button.style.fontSize = '16px';
        button.style.backgroundColor = '#4CAF50';
        button.style.color = 'white';
        button.style.border = 'none';
        button.style.borderRadius = '5px';
        button.style.cursor = 'pointer';
        document.body.appendChild(button);
        
        const status = document.createElement('div');
        status.textContent = 'Ready';
        status.style.position = 'fixed';
        status.style.bottom = '70px';
        status.style.right = '20px';
        status.style.zIndex = '9999';
        status.style.padding = '5px 10px';
        status.style.fontSize = '14px';
        status.style.backgroundColor = '#333';
        status.style.color = 'white';
        status.style.borderRadius = '3px';
        document.body.appendChild(status);
        
        // Track state
        let isListening = false;
        
        // Handle recognition result
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            console.log('Speech recognized:', transcript);
            status.textContent = 'Recognized: ' + transcript;
            
            // Send to Streamlit using custom events
            const event_data = new CustomEvent('streamlit:speechRecognized', {
                detail: { text: transcript }
            });
            window.dispatchEvent(event_data);
            
            // Also fill chat input if it exists
            const chatInput = document.querySelector('.stChatInput textarea');
            if (chatInput) {
                chatInput.value = transcript;
                // Trigger input event
                const inputEvent = new Event('input', { bubbles: true });
                chatInput.dispatchEvent(inputEvent);
                
                // Focus the input and submit
                chatInput.focus();
                setTimeout(() => {
                    const submitButton = document.querySelector('.stChatInput button');
                    if (submitButton) submitButton.click();
                }, 300);
            }
            
            isListening = false;
            button.textContent = '🎤 Click to Speak';
            button.style.backgroundColor = '#4CAF50';
        };
        
        // Handle errors
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            status.textContent = 'Error: ' + event.error;
            isListening = false;
            button.textContent = '🎤 Click to Speak';
            button.style.backgroundColor = '#4CAF50';
            
            // Show more detailed error
            if (event.error === 'not-allowed') {
                alert('Microphone access was denied. Please allow microphone access in your browser settings and try again.');
            }
        };
        
        // Button click handler
        button.addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
                isListening = false;
                button.textContent = '🎤 Click to Speak';
                button.style.backgroundColor = '#4CAF50';
                status.textContent = 'Stopped';
            } else {
                try {
                    recognition.start();
                    isListening = true;
                    button.textContent = '⏹️ Stop';
                    button.style.backgroundColor = '#f44336';
                    status.textContent = 'Listening...';
                    console.log('Speech recognition started');
                    
                    // Show alert to make the permission request more obvious
                    alert('Please allow microphone access when prompted by your browser.');
                } catch (error) {
                    console.error('Failed to start speech recognition:', error);
                    status.textContent = 'Error starting: ' + error.message;
                    alert('Error starting speech recognition: ' + error.message);
                }
            }
        });
        
        // Listen for custom event from Streamlit
        window.addEventListener('streamlit:speechRecognized', function(event) {
            // Update Streamlit state
            const text = event.detail.text;
            
            // Use Streamlit's component communication
            const data = {
                recognizedText: text,
                isForStreamlit: true
            };
            
            // Send to Streamlit frontend
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: data
            }, "*");
        });
        
        // Keyboard shortcut (Ctrl+Space or Cmd+Space)
        document.addEventListener('keydown', (event) => {
            if ((event.ctrlKey || event.metaKey) && event.code === 'Space') {
                event.preventDefault();
                button.click();
            }
        });
        
        console.log('Speech recognition setup complete');
    });
    </script>
    """
    
    # Inject JavaScript
    st.components.v1.html(js_code, height=100)
    
    # Handle component communication
    components_value = st.components.v1.html("", height=0)
    if components_value:
        if isinstance(components_value, dict) and 'recognizedText' in components_value:
            st.session_state.recognized_text = components_value['recognizedText']
            st.experimental_rerun()

if __name__ == "__main__":
    main()