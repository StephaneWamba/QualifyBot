"""Audio format conversion service for Twilio Media Streams."""

import io
import struct
from typing import Optional

from pydub import AudioSegment

from src.core.logging import get_logger

logger = get_logger(__name__)


class AudioConverter:
    """Service for converting audio formats."""

    @staticmethod
    def mp3_to_pcmu(mp3_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """
        Convert MP3 audio to PCMU (G.711 μ-law) format.

        Args:
            mp3_bytes: MP3 audio bytes
            sample_rate: Target sample rate (default 8000 Hz for Twilio)

        Returns:
            PCMU audio bytes
        """
        try:
            # Load MP3 audio
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))

            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)

            # Resample to target sample rate (8000 Hz for Twilio)
            if audio.frame_rate != sample_rate:
                audio = audio.set_frame_rate(sample_rate)

            # Convert to 16-bit PCM
            audio = audio.set_sample_width(2)  # 16-bit

            # Export as raw PCM16
            pcm16_bytes = audio.raw_data

            # Convert PCM16 to PCMU (μ-law)
            pcmu_bytes = AudioConverter._pcm16_to_pcmu(pcm16_bytes)

            logger.debug(
                "Audio converted MP3 → PCMU",
                original_size=len(mp3_bytes),
                pcmu_size=len(pcmu_bytes),
                sample_rate=sample_rate,
            )

            return pcmu_bytes

        except Exception as e:
            logger.error("Audio conversion error", error=str(e))
            raise

    @staticmethod
    def _pcm16_to_pcmu(pcm16_bytes: bytes) -> bytes:
        """
        Convert PCM16 to PCMU (G.711 μ-law).

        Args:
            pcm16_bytes: PCM16 audio bytes (16-bit signed integers)

        Returns:
            PCMU audio bytes (8-bit μ-law encoded)
        """
        pcmu_samples = []

        # Process 16-bit samples (2 bytes each)
        for i in range(0, len(pcm16_bytes), 2):
            # Read 16-bit signed integer (little-endian)
            pcm16_sample = struct.unpack("<h", pcm16_bytes[i : i + 2])[0]

            # Convert to μ-law
            pcmu_byte = AudioConverter._linear_to_mulaw(pcm16_sample)
            pcmu_samples.append(pcmu_byte)

        return bytes(pcmu_samples)

    @staticmethod
    def _linear_to_mulaw(linear: int) -> int:
        """
        Convert linear PCM sample to μ-law.

        Args:
            linear: 16-bit signed linear PCM sample (-32768 to 32767)

        Returns:
            8-bit μ-law encoded sample (0 to 255)
        """
        # Clamp to valid range
        if linear > 32767:
            linear = 32767
        elif linear < -32768:
            linear = -32768

        # Get sign bit
        sign = 0 if linear >= 0 else 0x80
        linear = abs(linear)

        # Add bias
        linear += 33

        # Find exponent (0-7)
        exponent = 7
        for exp in range(8):
            if linear <= (0x1F << (exp + 2)):
                exponent = exp
                break

        # Calculate mantissa (4 bits)
        mantissa = (linear >> (exponent + 3)) & 0x0F

        # Combine sign, exponent, and mantissa
        mulaw = sign | (exponent << 4) | mantissa

        # Invert all bits
        return mulaw ^ 0xFF

    @staticmethod
    def pcmu_to_pcm16(pcmu_bytes: bytes) -> bytes:
        """
        Convert PCMU (G.711 μ-law) to PCM16 format.

        Args:
            pcmu_bytes: PCMU audio bytes

        Returns:
            PCM16 audio bytes (16-bit signed integers)
        """
        pcm16_samples = []

        for pcmu_byte in pcmu_bytes:
            # Invert bits
            pcmu_byte = pcmu_byte ^ 0xFF

            # Extract sign, exponent, mantissa
            sign = (pcmu_byte & 0x80) >> 7
            exponent = (pcmu_byte & 0x70) >> 4
            mantissa = pcmu_byte & 0x0F

            # Decode to linear
            if exponent == 0:
                linear = (mantissa << 3) + 132
            else:
                linear = ((mantissa << 3) + 132) << (exponent - 1)

            # Apply sign
            if sign:
                linear = -linear

            # Clamp to 16-bit range
            if linear > 32767:
                linear = 32767
            elif linear < -32768:
                linear = -32768

            # Pack as 16-bit signed integer (little-endian)
            pcm16_samples.append(struct.pack("<h", linear))

        return b"".join(pcm16_samples)


# Singleton instance
audio_converter = AudioConverter()


