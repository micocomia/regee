# speech_recognition.py
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

# JavaScript for frontend integration - to be included in your HTML/JS files
"""
// Speech Recognition Frontend Code

class SpeechRecognitionManager {
    constructor() {
        this.recognition = null;
        this.isEnabled = false;
        this.isContinuous = false;
        this.isListening = false;
        this.statusElement = document.getElementById('speech-status');
        this.buttonElement = document.getElementById('speech-button');
        
        // Check if browser supports speech recognition
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('Speech recognition not supported in this browser');
            this.updateStatus('Speech recognition not supported');
            return;
        }
        
        // Initialize recognition
        this.recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        this.setupRecognition();
        this.setupEventListeners();
    }
    
    setupRecognition() {
        const recognition = this.recognition;
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('Speech recognized:', transcript);
            
            // Send to backend
            this.sendToBackend(transcript);
            
            // Update UI
            this.updateStatus('Processed: ' + transcript);
            
            if (!this.isContinuous) {
                this.stopListening();
            }
        };
        
        recognition.onerror = (event) => {
            console.error('Speech recognition error', event.error);
            this.updateStatus('Error: ' + event.error);
            this.stopListening();
            
            // Send error to backend
            fetch('/api/speech/error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ error: event.error }),
            });
        };
        
        recognition.onend = () => {
            this.isListening = false;
            this.updateButtonState();
            
            // Restart if in continuous mode
            if (this.isContinuous && this.isEnabled) {
                this.startListening();
            }
        };
    }
    
    setupEventListeners() {
        // Set up button click to toggle listening
        if (this.buttonElement) {
            this.buttonElement.addEventListener('click', () => {
                if (this.isListening) {
                    this.stopListening();
                } else {
                    this.startListening();
                }
            });
        }
    }
    
    sendToBackend(transcript) {
        // Send the recognized speech to the backend
        fetch('/api/speech/result', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: transcript }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Backend response:', data);
        })
        .catch(error => {
            console.error('Error sending to backend:', error);
        });
    }
    
    startListening() {
        if (!this.isEnabled || !this.recognition) return;
        
        try {
            this.recognition.start();
            this.isListening = true;
            this.updateStatus('Listening...');
            this.updateButtonState();
        } catch (error) {
            console.error('Error starting recognition:', error);
            this.updateStatus('Error starting recognition');
        }
    }
    
    stopListening() {
        if (!this.recognition) return;
        
        try {
            this.recognition.stop();
            this.isListening = false;
            this.updateStatus('Stopped listening');
            this.updateButtonState();
        } catch (error) {
            console.error('Error stopping recognition:', error);
        }
    }
    
    enable(continuous = false) {
        this.isEnabled = true;
        this.isContinuous = continuous;
        this.recognition.continuous = continuous;
        this.updateStatus('Speech recognition enabled' + (continuous ? ' (continuous mode)' : ''));
        this.updateButtonState();
    }
    
    disable() {
        this.isEnabled = false;
        if (this.isListening) {
            this.stopListening();
        }
        this.updateStatus('Speech recognition disabled');
        this.updateButtonState();
    }
    
    updateStatus(message) {
        if (this.statusElement) {
            this.statusElement.textContent = message;
        }
        console.log('Speech recognition status:', message);
    }
    
    updateButtonState() {
        if (this.buttonElement) {
            this.buttonElement.disabled = !this.isEnabled;
            this.buttonElement.textContent = this.isListening ? 'Stop Listening' : 'Start Listening';
            this.buttonElement.classList.toggle('listening', this.isListening);
        }
    }
    
    loadConfig(config) {
        this.isEnabled = config.enabled;
        this.isContinuous = config.continuous;
        this.recognition.continuous = config.continuous;
        this.recognition.lang = config.language || 'en-US';
        this.recognition.interimResults = config.interimResults || false;
        this.recognition.maxAlternatives = config.maxAlternatives || 1;
        
        this.updateStatus(this.isEnabled ? 'Speech recognition ready' : 'Speech recognition disabled');
        this.updateButtonState();
    }
}

// Initialize speech recognition
document.addEventListener('DOMContentLoaded', function() {
    window.speechManager = new SpeechRecognitionManager();
    
    // Fetch initial configuration from backend
    fetch('/api/speech/config')
        .then(response => response.json())
        .then(config => {
            window.speechManager.loadConfig(config);
        })
        .catch(error => {
            console.error('Error loading speech config:', error);
        });
});
"""