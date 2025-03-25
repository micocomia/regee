import streamlit as st
import pyttsx3
import logging
from typing import Dict, Any

class TextToSpeech:
    """
    Handles text-to-speech functionality for the ReGee educational assistant.
    Provides methods for controlling speech synthesis with Streamlit-friendly configuration.
    """
    def __init__(self):
        """Initialize the text-to-speech system with pyttsx3."""
        self.engine = pyttsx3.init()
        self.is_enabled = False
        self.voice_id = None
        self.rate = 150  # Default rate
        self.volume = 1.0  # Default volume (float)
        
        # Store available voices
        self.available_voices = self._get_available_voices()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def _get_available_voices(self) -> Dict[str, str]:
        """
        Retrieve available voices on the system.
        
        Returns:
            Dictionary of voice names and their corresponding IDs
        """
        voices = self.engine.getProperty('voices')
        return {voice.name: voice.id for voice in voices}
    
    def enable(self) -> Dict[str, Any]:
        """Enable text-to-speech."""
        self.is_enabled = True
        self.logger.info("Text-to-speech enabled")
        return {"status": "enabled", "message": "Text-to-speech enabled"}
    
    def disable(self) -> Dict[str, Any]:
        """Disable text-to-speech."""
        self.is_enabled = False
        self.logger.info("Text-to-speech disabled")
        return {"status": "disabled", "message": "Text-to-speech disabled"}
    
    def set_voice(self, voice_name: str) -> Dict[str, Any]:
        """
        Set the voice for speech synthesis.
        
        Args:
            voice_name: Name of the voice to use
            
        Returns:
            Status information
        """
        if voice_name in self.available_voices:
            self.voice_id = self.available_voices[voice_name]
            self.engine.setProperty('voice', self.voice_id)
            self.logger.info(f"Voice set to {voice_name}")
            return {"status": "updated", "voice": voice_name}
        else:
            error_msg = f"Voice {voice_name} not found"
            self.logger.warning(error_msg)
            return {"status": "error", "message": error_msg}
    
    def set_speech_rate(self, rate: int) -> Dict[str, Any]:
        """
        Set the speech rate.
        
        Args:
            rate: Speech rate (words per minute)
            
        Returns:
            Status information
        """
        # Clamp rate between 50 and 400 words per minute
        self.rate = max(50, min(400, rate))
        self.engine.setProperty('rate', self.rate)
        self.logger.info(f"Speech rate set to {self.rate}")
        return {"status": "updated", "rate": self.rate}
    
    def set_volume(self, volume: float) -> Dict[str, Any]:
        """
        Set the speech volume.
        
        Args:
            volume: Speech volume (0 to 1)
            
        Returns:
            Status information
        """
        # Ensure volume is always a float
        self.volume = float(max(0, min(1, volume)))
        self.engine.setProperty('volume', self.volume)
        self.logger.info(f"Volume set to {self.volume}")
        return {"status": "updated", "volume": self.volume}
    
    def speak(self, text: str) -> Dict[str, Any]:
        """
        Speak the given text.
        
        Args:
            text: Text to speak
            
        Returns:
            Status information
        """
        if not self.is_enabled:
            error_msg = "Text-to-speech is not enabled"
            self.logger.warning(error_msg)
            return {"status": "error", "message": error_msg}
        
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            self.logger.info(f"Spoke text: {text[:50]}...")  # Log first 50 characters
            return {
                "status": "speaking", 
                "text": text,
                "config": self.get_tts_config()
            }
        except Exception as e:
            error_msg = f"Speech error: {str(e)}"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    def get_tts_config(self) -> Dict[str, Any]:
        """
        Get configuration for TTS.
        
        Returns:
            Configuration for the TTS system
        """
        return {
            "enabled": self.is_enabled,
            "voices": list(self.available_voices.keys()),
            "current_voice": next((name for name, id in self.available_voices.items() if id == self.voice_id), "Default"),
            "rate": self.rate,
            "volume": self.volume
        }

def init_tts_in_session_state():
    """
    Initialize text-to-speech in Streamlit's session state if not already present.
    """
    if 'tts' not in st.session_state:
        st.session_state.tts = TextToSpeech()

def add_tts_controls_to_sidebar():
    """
    Add TTS configuration controls to the Streamlit sidebar.
    """
    with st.sidebar:
        st.subheader("Text-to-Speech Settings")
        
        # TTS Enable/Disable Toggle
        tts_enabled = st.toggle("Enable Text-to-Speech", value=st.session_state.tts.is_enabled)
        if tts_enabled:
            st.session_state.tts.enable()
        else:
            st.session_state.tts.disable()
        
        # Voice Selection
        available_voices = st.session_state.tts.available_voices
        selected_voice = st.selectbox(
            "Select Voice", 
            list(available_voices.keys()),
            index=0
        )
        st.session_state.tts.set_voice(selected_voice)
        
        # Speech Rate
        speech_rate = st.slider(
            "Speech Rate (words per minute)", 
            min_value=50, 
            max_value=400, 
            value=st.session_state.tts.rate
        )
        st.session_state.tts.set_speech_rate(speech_rate)

        # Volume Slider with Fix for List Type Issue
        volume = st.slider(
            "Volume", 
            min_value=0.0, 
            max_value=1.0, 
            value=st.session_state.tts.volume[0] if isinstance(st.session_state.tts.volume, list) else st.session_state.tts.volume,
            step=0.1
        )
        st.session_state.tts.set_volume(volume)

def speak_response(response_text: str):
    """
    Utility function to speak a response if TTS is enabled.
    
    Args:
        response_text: Text to be spoken
    """
    if hasattr(st.session_state, 'tts') and st.session_state.tts.is_enabled:
        st.session_state.tts.speak(response_text)

# Streamlit App Entry Point
if __name__ == "__main__":
    st.title("Text-to-Speech App")
    
    # Initialize TTS system in session state
    init_tts_in_session_state()

    # Add sidebar controls
    add_tts_controls_to_sidebar()

    # Text input for speech synthesis
    user_input = st.text_area("Enter text to speak:")
    if st.button("Speak"):
        speak_response(user_input)