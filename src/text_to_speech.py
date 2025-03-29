import streamlit as st
import edge_tts
import asyncio
import os
import tempfile
import logging
from typing import Dict, Any
import pygame
import io
import threading
import time
import signal

class TextToSpeech:
    """
    Handles text-to-speech functionality for the ReGee educational assistant.
    Provides methods for controlling speech synthesis with Microsoft Edge TTS.
    """
    def __init__(self):
        """Initialize the text-to-speech system with Edge TTS."""
        self.is_enabled = False  # Disabled by default
        self.voice = "en-US-GuyNeural"  # Default voice
        self.rate = "+30%"  # Default rate (normal)
        self.volume = "+100%"  # Default volume (normal)
        self.pitch = "+12Hz"  # Default pitch (normal)
        self.temp_file = None  # Temporary file for audio
        self.is_playing = False  # Track if audio is currently playing
        self.play_thread = None  # Thread for playing audio
        self.stop_requested = False  # Flag to request stop
        
        # Initialize pygame for audio playback
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("Text-to-speech system initialized with Edge TTS")
    
    def set_voice(self, voice: str) -> Dict[str, Any]:
        """
        Set the voice for speech synthesis.
        
        Args:
            voice: Voice name (e.g. 'en-US-AriaNeural', 'en-GB-RyanNeural')
            
        Returns:
            Status information
        """
        self.voice = voice
        self.logger.info(f"Voice set to {voice}")
        return {"status": "updated", "voice": voice}
    
    def set_rate(self, rate: str) -> Dict[str, Any]:
        """
        Set the speech rate.
        
        Args:
            rate: Speech rate as a percentage (e.g. '+50%', '-20%')
            
        Returns:
            Status information
        """
        self.rate = rate
        self.logger.info(f"Speech rate set to {rate}")
        return {"status": "updated", "rate": rate}
    
    def set_volume(self, volume: str) -> Dict[str, Any]:
        """
        Set the speech volume.
        
        Args:
            volume: Volume as a percentage (e.g. '+20%', '-10%')
            
        Returns:
            Status information
        """
        self.volume = volume
        self.logger.info(f"Volume set to {volume}")
        return {"status": "updated", "volume": volume}
    
    def set_pitch(self, pitch: str) -> Dict[str, Any]:
        """
        Set the speech pitch.
        
        Args:
            pitch: Pitch as a percentage (e.g. '+10%', '-15%')
            
        Returns:
            Status information
        """
        self.pitch = pitch
        self.logger.info(f"Pitch set to {pitch}")
        return {"status": "updated", "pitch": pitch}
    
    def enable(self) -> Dict[str, Any]:
        """Enable text-to-speech."""
        self.is_enabled = True
        self.logger.info("Text-to-speech enabled")
        return {"status": "enabled", "message": "Text-to-speech enabled"}
    
    def disable(self) -> Dict[str, Any]:
        """Disable text-to-speech."""
        self.is_enabled = False
        # Stop any ongoing speech
        self.stop()
        self.logger.info("Text-to-speech disabled")
        return {"status": "disabled", "message": "Text-to-speech disabled"}
    
    def speak(self, text: str) -> Dict[str, Any]:
        """
        Speak the given text using Edge TTS.
        
        Args:
            text: Text to speak
            
        Returns:
            Status information
        """
        if not self.is_enabled:
            error_msg = "Text-to-speech is not enabled"
            self.logger.warning(error_msg)
            return {"status": "error", "message": error_msg}
        
        # Stop any previously playing audio
        self.stop()
        
        try:
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                self.temp_file = fp.name
            
            # Reset stop flag
            self.stop_requested = False
            
            # Run the async TTS generation
            asyncio.run(self._generate_speech(text))
            
            # Set playing flag
            self.is_playing = True
            
            # Start audio in a separate thread to avoid blocking Streamlit
            self.play_thread = threading.Thread(target=self._play_audio)
            self.play_thread.daemon = True
            self.play_thread.start()
            
            self.logger.info(f"Started speaking text: {text[:50]}...")  # Log first 50 characters
            return {
                "status": "speaking", 
                "text": text,
                "config": self.get_tts_config()
            }
        except Exception as e:
            error_msg = f"Speech error: {str(e)}"
            self.logger.error(error_msg)
            self._cleanup_temp_file()
            self.is_playing = False
            return {"status": "error", "message": error_msg}
    
    def _play_audio(self):
        """Play audio in a separate thread."""
        try:
            # Make sure mixer is initialized
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            # Load and play audio
            pygame.mixer.music.load(self.temp_file)
            pygame.mixer.music.play()
            
            # Wait for playback to complete or stop to be requested
            while pygame.mixer.music.get_busy() and not self.stop_requested:
                pygame.time.Clock().tick(10)
            
            # Mark as not playing once done
            self.is_playing = False
            
            # Clean up
            self._cleanup_temp_file()
        except Exception as e:
            self.logger.error(f"Error in playback thread: {str(e)}")
            self.is_playing = False
            self._cleanup_temp_file()
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop any currently playing speech immediately.
        
        Returns:
            Status information
        """
        if not self.is_playing:
            return {"status": "not_playing", "message": "No speech is currently playing"}
        
        try:
            # Set stop flag for thread
            self.stop_requested = True
            
            # Stop pygame playback
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            
            # Wait a moment for thread to complete
            time.sleep(0.1)
            
            # Reset playing status
            self.is_playing = False
            
            # Clean up the temporary file
            self._cleanup_temp_file()
            
            self.logger.info("Stopped speech playback")
            return {"status": "stopped", "message": "Speech stopped"}
        except Exception as e:
            error_msg = f"Error stopping speech: {str(e)}"
            self.logger.error(error_msg)
            # Attempt to reset state
            self.is_playing = False
            return {"status": "error", "message": error_msg}
    
    async def _generate_speech(self, text: str):
        """
        Generate speech using Edge TTS (async).
        
        Args:
            text: Text to convert to speech
        """
        communicate = edge_tts.Communicate(
            text, 
            self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch
        )
        
        await communicate.save(self.temp_file)
    
    def _cleanup_temp_file(self):
        """Clean up the temporary audio file."""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.unlink(self.temp_file)
                self.temp_file = None
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary file: {e}")
    
    def get_tts_config(self) -> Dict[str, Any]:
        """
        Get configuration for TTS.
        
        Returns:
            Configuration for the TTS system
        """
        return {
            "enabled": self.is_enabled,
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "pitch": self.pitch,
            "is_playing": self.is_playing
        }
    
    async def list_voices(self):
        """
        Get list of available voices.
        
        Returns:
            List of available voice names
        """
        voices = await edge_tts.list_voices()
        return voices

def init_tts_in_session_state():
    """
    Initialize text-to-speech in Streamlit's session state if not already present.
    """
    if 'tts' not in st.session_state:
        st.session_state.tts = TextToSpeech()

def speak_response(response_text: str):
    """
    Utility function to speak a response if TTS is enabled.
    
    Args:
        response_text: Text to be spoken
    """
    if hasattr(st.session_state, 'tts') and st.session_state.tts.is_enabled:
        st.session_state.tts.speak(response_text)