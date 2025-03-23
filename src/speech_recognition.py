# speech_recognition.py - updated with cross-platform support
import logging
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)

class SpeechRecognition:
    """
    Handles speech recognition using the Web Speech API.
    This class provides the Python backend for interfacing with the browser's speech recognition.
    """
    def __init__(self):
        """Initialize the speech recognition system."""
        self.is_enabled = False
        self.recognition_active = False
        self.continuous_mode = False
        self.on_result_callback = None
        self.on_error_callback = None
        
    def enable(self) -> Dict[str, Any]:
        """Enable speech recognition."""
        self.is_enabled = True
        return {"status": "enabled", "message": "Speech recognition enabled"}
    
    def disable(self) -> Dict[str, Any]:
        """Disable speech recognition."""
        self.is_enabled = False
        self.recognition_active = False
        return {"status": "disabled", "message": "Speech recognition disabled"}
    
    def toggle_continuous_mode(self, enabled: bool) -> Dict[str, Any]:
        """
        Toggle continuous recognition mode.
        
        Args:
            enabled: Whether to enable continuous mode
            
        Returns:
            Status information
        """
        self.continuous_mode = enabled
        mode = "continuous" if enabled else "single response"
        return {"status": "updated", "mode": mode}
    
    def register_result_callback(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for speech recognition results.
        
        Args:
            callback: Function to call with recognized text
        """
        self.on_result_callback = callback
    
    def register_error_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register callback for speech recognition errors.
        
        Args:
            callback: Function to call with error information
        """
        self.on_error_callback = callback
    
    def handle_speech_result(self, text: str) -> Dict[str, Any]:
        """
        Handle speech recognition result from frontend.
        
        Args:
            text: Recognized text
            
        Returns:
            Status information
        """
        if not self.is_enabled:
            return {"status": "error", "message": "Speech recognition is not enabled"}
            
        logger.info(f"Speech recognized: {text}")
        
        # Call the result callback if registered
        if self.on_result_callback:
            self.on_result_callback(text)
            
        # Update recognition state if not in continuous mode
        if not self.continuous_mode:
            self.recognition_active = False
            
        return {"status": "success", "text": text}
    
    def handle_speech_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle speech recognition error from frontend.
        
        Args:
            error_data: Error information
            
        Returns:
            Status information
        """
        logger.error(f"Speech recognition error: {error_data}")
        
        # Call the error callback if registered
        if self.on_error_callback:
            self.on_error_callback(error_data)
            
        # Update recognition state
        self.recognition_active = False
            
        return {"status": "error", "error": error_data}
    
    def get_frontend_config(self) -> Dict[str, Any]:
        """
        Get configuration for frontend speech recognition initialization.
        
        Returns:
            Configuration for the frontend
        """
        return {
            "enabled": self.is_enabled,
            "continuous": self.continuous_mode,
            "language": "en-US",  # Default language
            "interimResults": False,  # Only return final results
            "maxAlternatives": 1
        }

    def get_js_code(self) -> str:
        """
        Get the JavaScript code for speech recognition functionality.
        
        Returns:
            JavaScript code as a string
        """
        return """
        <script>
        // Cross-platform Speech Recognition Manager for Streamlit
        class SpeechRecognitionManager {
            constructor() {
                this.recognition = null;
                this.isEnabled = false;
                this.isContinuous = false;
                this.isListening = false;
                this.platform = this.detectPlatform();
                this.browser = this.detectBrowser();
                
                console.log(`Detected platform: ${this.platform}, browser: ${this.browser}`);
                
                // Check if browser supports speech recognition
                if ('webkitSpeechRecognition' in window) {
                    this.recognition = new webkitSpeechRecognition();
                    console.log('Using webkitSpeechRecognition');
                } else if ('SpeechRecognition' in window) {
                    this.recognition = new SpeechRecognition();
                    console.log('Using standard SpeechRecognition');
                } else {
                    console.error('Speech recognition not supported in this browser');
                    this.showNotification('Speech recognition not supported in this browser. Please try Chrome, Edge, or Safari.');
                    return;
                }
                
                this.setupRecognition();
                this.createSpeechUI();
                this.setupEventListeners();
            }
            
            detectPlatform() {
                const userAgent = navigator.userAgent.toLowerCase();
                if (userAgent.indexOf('mac') !== -1) return 'mac';
                if (userAgent.indexOf('win') !== -1) return 'windows';
                if (userAgent.indexOf('linux') !== -1) return 'linux';
                if (userAgent.indexOf('android') !== -1) return 'android';
                if (userAgent.indexOf('iphone') !== -1 || userAgent.indexOf('ipad') !== -1) return 'ios';
                return 'unknown';
            }
            
            detectBrowser() {
                const userAgent = navigator.userAgent.toLowerCase();
                if (userAgent.indexOf('edge') !== -1 || userAgent.indexOf('edg') !== -1) return 'edge';
                if (userAgent.indexOf('chrome') !== -1) return 'chrome';
                if (userAgent.indexOf('firefox') !== -1) return 'firefox';
                if (userAgent.indexOf('safari') !== -1) return 'safari';
                return 'unknown';
            }
            
            setupRecognition() {
                const recognition = this.recognition;
                recognition.lang = 'en-US';
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;
                
                // Safari-specific adjustments
                if (this.browser === 'safari') {
                    // Safari sometimes needs these explicitly set
                    recognition.continuous = false;
                    recognition.interimResults = false;
                }
                
                recognition.onstart = () => {
                    console.log('Speech recognition started');
                    this.isListening = true;
                    this.updateStatus('Listening...');
                    this.updateButtonState();
                };
                
                recognition.onresult = (event) => {
                    let transcript = '';
                    
                    // Different browsers handle results differently
                    if (event.results) {
                        // Get the latest result
                        transcript = event.results[event.results.length - 1][0].transcript;
                    } else if (event.result) {
                        // Some implementations might use a different structure
                        transcript = event.result[0].transcript;
                    }
                    
                    console.log('Speech recognized:', transcript);
                    
                    // Fill chat input with transcript
                    this.fillChatInput(transcript);
                    
                    // Update UI
                    this.updateStatus('Processed: ' + transcript);
                    
                    if (!this.isContinuous) {
                        this.stopListening();
                    }
                };
                
                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    this.updateStatus('Error: ' + event.error);
                    this.stopListening();
                };
                
                recognition.onend = () => {
                    console.log('Speech recognition ended');
                    this.isListening = false;
                    this.updateButtonState();
                    
                    // Restart if in continuous mode
                    if (this.isContinuous && this.isEnabled) {
                        this.startListening();
                    }
                };
            }
            
            setupEventListeners() {
                // Add keyboard shortcut based on platform
                document.addEventListener('keydown', (event) => {
                    // For Mac: Check for Command+Space
                    // For others: Check for Ctrl+Space
                    const isMac = this.platform === 'mac';
                    const modifierKey = isMac ? event.metaKey : event.ctrlKey;
                    
                    if (modifierKey && (event.code === 'Space' || event.keyCode === 32)) {
                        console.log(`${isMac ? 'Command' : 'Ctrl'}+Space detected for speech recognition`);
                        
                        // Don't prevent default on Mac as it conflicts with system shortcuts
                        if (!isMac) {
                            event.preventDefault();
                        }
                        
                        // Toggle listening state
                        if (this.isEnabled) {
                            if (this.isListening) {
                                this.stopListening();
                            } else {
                                this.startListening();
                            }
                        } else {
                            this.showNotification('Speech recognition is disabled. Enable it in the sidebar first.');
                        }
                    }
                });
            }
            
            createSpeechUI() {
                // Create speech button
                this.createSpeechButton();
                
                // Create status element
                this.createStatusElement();
                
                // Create keyboard shortcut hint
                this.createKeyboardHint();
            }
            
            createSpeechButton() {
                if (document.getElementById('speech-button')) return;
                
                console.log('Creating speech button');
                const button = document.createElement('button');
                button.id = 'speech-button';
                button.className = 'speech-button';
                button.textContent = '🎤';
                
                // Set appropriate tooltip based on platform
                const shortcutKey = this.platform === 'mac' ? 'Command+Space' : 'Ctrl+Space';
                button.title = `Start Listening (${shortcutKey})`;
                
                // Add to page
                document.body.appendChild(button);
                
                // Position it near the chat input
                button.style.position = 'fixed';
                button.style.bottom = '20px';
                button.style.right = '100px';
                button.style.zIndex = '1000';
                
                // Add click event
                button.addEventListener('click', () => {
                    if (this.isEnabled) {
                        if (this.isListening) {
                            this.stopListening();
                        } else {
                            this.startListening();
                        }
                    } else {
                        this.showNotification('Speech recognition is disabled. Enable it in the sidebar first.');
                    }
                });
                
                this.buttonElement = button;
                this.updateButtonState();
            }
            
            createStatusElement() {
                if (document.getElementById('speech-status-floating')) return;
                
                const statusElement = document.createElement('div');
                statusElement.id = 'speech-status-floating';
                statusElement.className = 'speech-status-floating';
                document.body.appendChild(statusElement);
                
                this.floatingStatus = statusElement;
            }
            
            createKeyboardHint() {
                // Add a keyboard shortcut hint near the chat input
                setTimeout(() => {
                    const chatInput = document.querySelector('.stChatInput');
                    if (chatInput && !document.getElementById('keyboard-hint')) {
                        const hint = document.createElement('div');
                        hint.id = 'keyboard-hint';
                        hint.className = 'keyboard-hint';
                        
                        // Different text based on platform
                        const shortcutKey = this.platform === 'mac' ? '⌘ Space' : 'Ctrl+Space';
                        hint.textContent = `Press ${shortcutKey} to speak`;
                        
                        chatInput.appendChild(hint);
                    }
                }, 1000);
            }
            
            fillChatInput(text) {
                // Find chat input and fill it
                const chatInput = document.querySelector('.stChatInput textarea');
                if (chatInput) {
                    console.log('Found chat input, filling with:', text);
                    
                    // Set the value
                    chatInput.value = text;
                    
                    // Create and dispatch input event
                    const inputEvent = new Event('input', { bubbles: true });
                    chatInput.dispatchEvent(inputEvent);
                    
                    // Focus the input
                    chatInput.focus();
                    
                    // Submit the form after a short delay
                    setTimeout(() => {
                        const submitButton = document.querySelector('.stChatInput button');
                        if (submitButton) {
                            console.log('Clicking submit button');
                            submitButton.click();
                        }
                    }, 300);
                } else {
                    console.log('Chat input not found');
                    this.showNotification('Could not find chat input to fill with speech text.');
                }
            }
            
            startListening() {
                if (!this.isEnabled) {
                    this.showNotification('Speech recognition is disabled. Enable it in the sidebar first.');
                    return;
                }
                
                if (!this.recognition) {
                    this.showNotification('Speech recognition not available in this browser.');
                    return;
                }
                
                try {
                    console.log('Starting speech recognition');
                    
                    // Safari has known issues with continuous mode
                    if (this.browser === 'safari') {
                        this.recognition.continuous = false;
                    } else {
                        this.recognition.continuous = this.isContinuous;
                    }
                    
                    this.recognition.start();
                    this.isListening = true;
                    this.updateStatus('Listening...');
                    this.updateButtonState();
                    
                    // Show a more visible notification
                    this.showNotification('🎤 Listening... Speak now!');
                } catch (error) {
                    console.error('Error starting recognition:', error);
                    this.updateStatus('Error starting recognition: ' + error.message);
                    
                    // Try to provide more helpful error messages for common issues
                    if (error.name === 'NotAllowedError') {
                        this.showNotification('Microphone access denied. Please allow microphone access in your browser settings.');
                    } else {
                        this.showNotification('Could not start speech recognition: ' + error.message);
                    }
                }
            }
            
            stopListening() {
                if (!this.recognition) return;
                
                try {
                    console.log('Stopping speech recognition');
                    this.recognition.stop();
                    this.isListening = false;
                    this.updateStatus('Stopped listening');
                    this.updateButtonState();
                } catch (error) {
                    console.error('Error stopping recognition:', error);
                }
            }
            
            updateStatus(message) {
                console.log('Speech status:', message);
                
                if (this.floatingStatus) {
                    this.floatingStatus.textContent = message;
                    this.floatingStatus.classList.add('visible');
                    
                    // Hide after 3 seconds
                    clearTimeout(this.statusTimeout);
                    this.statusTimeout = setTimeout(() => {
                        this.floatingStatus.classList.remove('visible');
                    }, 3000);
                }
            }
            
            showNotification(message) {
                // More prominent notification
                if (!document.getElementById('speech-notification')) {
                    const notification = document.createElement('div');
                    notification.id = 'speech-notification';
                    notification.className = 'speech-notification';
                    document.body.appendChild(notification);
                }
                
                const notification = document.getElementById('speech-notification');
                notification.textContent = message;
                notification.classList.add('visible');
                
                // Automatically hide after 4 seconds
                setTimeout(() => {
                    notification.classList.remove('visible');
                }, 4000);
            }
            
            updateButtonState() {
                if (this.buttonElement) {
                    this.buttonElement.disabled = !this.isEnabled;
                    this.buttonElement.textContent = this.isListening ? '🛑' : '🎤';
                    this.buttonElement.title = this.isListening ? 'Stop Listening' : 'Start Listening';
                    this.buttonElement.classList.toggle('listening', this.isListening);
                }
            }
            
            enable(continuous = false) {
                console.log('Enabling speech recognition, continuous:', continuous);
                this.isEnabled = true;
                this.isContinuous = continuous;
                
                // For Safari, always disable continuous mode as it can cause issues
                if (this.browser === 'safari') {
                    this.isContinuous = false;
                    console.log('Forced continuous mode to false for Safari compatibility');
                }
                
                this.updateStatus('Speech recognition enabled' + (this.isContinuous ? ' (continuous mode)' : ''));
                this.updateButtonState();
                this.showNotification('Speech recognition enabled! Click the microphone button or press ' + 
                                      (this.platform === 'mac' ? 'Command+Space' : 'Ctrl+Space') + 
                                      ' to start speaking.');
            }
            
            disable() {
                console.log('Disabling speech recognition');
                this.isEnabled = false;
                if (this.isListening) {
                    this.stopListening();
                }
                this.updateStatus('Speech recognition disabled');
                this.updateButtonState();
            }
            
            loadConfig(config) {
                console.log('Loading speech recognition config:', config);
                
                const wasNotEnabled = !this.isEnabled;
                
                this.isEnabled = config.enabled;
                this.isContinuous = config.continuous;
                
                // For Safari, always disable continuous mode
                if (this.browser === 'safari' && this.isContinuous) {
                    this.isContinuous = false;
                    console.log('Forced continuous mode to false for Safari compatibility');
                }
                
                // Only show notification if enabling for the first time
                if (wasNotEnabled && this.isEnabled) {
                    this.showNotification('Speech recognition enabled! Click the microphone button or press ' + 
                                         (this.platform === 'mac' ? 'Command+Space' : 'Ctrl+Space') + 
                                         ' to start speaking.');
                }
                
                this.updateStatus(this.isEnabled ? 'Speech recognition ready' : 'Speech recognition disabled');
                this.updateButtonState();
            }
        }

        // Initialize speech recognition when the page is loaded
        window.addEventListener('load', function() {
            console.log('Window loaded, initializing speech recognition');
            if (!window.speechManager) {
                window.speechManager = new SpeechRecognitionManager();
                
                // Set initial configuration
                window.speechManager.loadConfig({
                    enabled: ${str(self.is_enabled).lower()},
                    continuous: ${str(self.continuous_mode).lower()},
                    language: 'en-US',
                    interimResults: false,
                    maxAlternatives: 1
                });
            }
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
            font-size: 20px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999; /* Ensure it's above other elements */
            position: fixed;
            bottom: 20px;
            right: 20px;
        }
        
        .speech-button:hover {
            background-color: #45a049;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            transform: translateY(-2px);
        }
        
        .speech-button.listening {
            background-color: #f44336;
            animation: pulse 1.5s infinite;
        }
        
        .speech-button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
        }
        
        .speech-status-floating {
            position: fixed;
            bottom: 70px;
            right: 20px;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.3s ease;
            z-index: 1000;
            pointer-events: none;
        }
        
        .speech-status-floating.visible {
            opacity: 1;
        }
        
        .speech-notification {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #333;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            z-index: 2000;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            text-align: center;
            max-width: 80%;
        }
        
        .speech-notification.visible {
            opacity: 1;
        }
        
        .keyboard-hint {
            position: absolute;
            bottom: -22px;
            right: 10px;
            font-size: 12px;
            color: #666;
            opacity: 0.8;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 10px rgba(244, 67, 54, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
        }
        </style>
        """