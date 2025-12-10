"""
Audio format conversion utilities.
Handles μ-law ↔ PCM conversion and resampling.
"""
try:
    import audioop  # Built-in for Python 3.12 and earlier
except ImportError:
    import audioop_lts as audioop  # For Python 3.13+
import base64
import logging

logger = logging.getLogger(__name__)


class AudioConverter:
    """Fast audio conversion for streaming."""
    
    @staticmethod
    def ulaw_to_pcm16(ulaw_data: bytes, sample_rate: int = 8000) -> bytes:
        """
        Convert μ-law to 16-bit PCM.
        
        Args:
            ulaw_data: μ-law encoded audio
            sample_rate: Sample rate (8000 for Smartflo)
            
        Returns:
            PCM 16-bit audio data
        """
        return audioop.ulaw2lin(ulaw_data, 2)  # 2 bytes = 16-bit
    
    @staticmethod
    def pcm16_to_ulaw(pcm_data: bytes) -> bytes:
        """
        Convert 16-bit PCM to μ-law.
        
        Args:
            pcm_data: PCM 16-bit audio data
            
        Returns:
            μ-law encoded audio
        """
        return audioop.lin2ulaw(pcm_data, 2)  # 2 bytes = 16-bit
    
    @staticmethod
    def resample(audio_data: bytes, from_rate: int, to_rate: int, sample_width: int = 2) -> bytes:
        """
        Resample audio data.
        
        Args:
            audio_data: Input audio
            from_rate: Source sample rate
            to_rate: Target sample rate
            sample_width: Bytes per sample (2 for 16-bit)
            
        Returns:
            Resampled audio data
        """
        if from_rate == to_rate:
            return audio_data
        
        return audioop.ratecv(audio_data, sample_width, 1, from_rate, to_rate, None)[0]
    
    @staticmethod
    def smartflo_to_gemini(ulaw_data: bytes) -> bytes:
        """
        Convert Smartflo audio (μ-law 8kHz) to Gemini format (PCM 16kHz).
        
        Args:
            ulaw_data: μ-law audio from Smartflo
            
        Returns:
            PCM 16-bit 16kHz audio for Gemini
        """
        # Step 1: μ-law → PCM 16-bit 8kHz
        pcm_8k = AudioConverter.ulaw_to_pcm16(ulaw_data, 8000)
        
        # Step 2: Resample 8kHz → 16kHz
        pcm_16k = AudioConverter.resample(pcm_8k, 8000, 16000, 2)
        
        return pcm_16k
    
    @staticmethod
    def gemini_to_smartflo(pcm_data: bytes, gemini_rate: int = 24000) -> bytes:
        """
        Convert Gemini audio (PCM 24kHz) to Smartflo format (μ-law 8kHz).
        
        Args:
            pcm_data: PCM audio from Gemini
            gemini_rate: Gemini's sample rate (24000 Hz)
            
        Returns:
            μ-law 8kHz audio for Smartflo
        """
        # Step 1: Resample from Gemini rate → 8kHz
        pcm_8k = AudioConverter.resample(pcm_data, gemini_rate, 8000, 2)
        
        # Step 2: PCM → μ-law
        ulaw = AudioConverter.pcm16_to_ulaw(pcm_8k)
        
        return ulaw
    
    @staticmethod
    def to_base64(audio_data: bytes) -> str:
        """Encode audio to base64 string."""
        return base64.b64encode(audio_data).decode('utf-8')
    
    @staticmethod
    def from_base64(b64_string: str) -> bytes:
        """Decode base64 string to audio bytes."""
        return base64.b64decode(b64_string)
