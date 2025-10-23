import os
import torch
import torchaudio
from torchaudio.functional import resample
import json
import av
import io

class LoopAudioUtils:
    """Utility class for managing audio files"""

    DEFAULT_SAMPLE_RATE = 44100

    @staticmethod
    def load_or_create_audio(audio: dict | None, path: str, load: bool = True, target_sample_rate: int = DEFAULT_SAMPLE_RATE) -> dict:
        """
        Load an existing audio file or create the file.
        """
        if os.path.exists(path) and load:
            return LoopAudioUtils.load_audio(path, target_sample_rate)
        else:
            if audio is None:
                waveform = torch.zeros((1, 1, target_sample_rate), dtype=torch.float32)
                audio = {"waveform": waveform, "sample_rate": target_sample_rate}
            LoopAudioUtils.save_audio(audio, path)
            return audio

    @staticmethod
    def load_audio(path: str, target_sample_rate: int = DEFAULT_SAMPLE_RATE) -> dict:
        """
        Load an existing audio file and return a dict with 'waveform' and 'sample_rate'.
        eventually resample to target_sample_rate.
        """
        waveform, sample_rate = torchaudio.load(path)
        if waveform.ndim == 2:
            waveform = waveform.unsqueeze(0)
        if sample_rate != target_sample_rate:
            waveform = resample(waveform, sample_rate, target_sample_rate)
            sample_rate = target_sample_rate
        return {"waveform": waveform, "sample_rate": sample_rate}

    # @staticmethod
    # def save_audio(audio: dict, path: str, metadata: dict | None = None) -> str:
    #     """
    #     Save an audio file as wav and return input path.
    #     """
    #     waveform = audio["waveform"]
    #     sample_rate = audio["sample_rate"]
    #     if waveform.ndim == 3:
    #         waveform = waveform[0]
    #     os.makedirs(os.path.dirname(path), exist_ok=True)
    #     torchaudio.save(path, waveform.cpu(), sample_rate)
    #     return path

    @staticmethod
    def save_audio(audio: dict, path: str, metadata: dict | None = None) -> str:
        """
        Save an audio file as flac (mono to up to 6 channels). return input path.
        """
        waveform = audio["waveform"]
        sample_rate = audio["sample_rate"]
        
        if waveform.ndim == 3:
            waveform = waveform[0]  # Shape: (channels, samples)
        
        num_channels = waveform.shape[0]
        
        # layout
        if num_channels == 1:
            layout = 'mono'
        elif num_channels == 2:
            layout = 'stereo'
        else:
            layout = f'{num_channels}.0'  # up to 6 channels
        
        # Transform for PyAV
        if num_channels == 1:
            frame_tensor = waveform  # (1, samples)
        else:
            frame_tensor = waveform.movedim(0, 1).reshape(1, -1) # (channels, samples) → (1, samples * channels)

        frame_data = frame_tensor.cpu().numpy()
        
        output_buffer = io.BytesIO()
        output_container = av.open(output_buffer, mode='w', format="flac")
        
        if metadata:
            for key, value in metadata.items():
                output_container.metadata[key] = str(value)
        
        out_stream = output_container.add_stream("flac", rate=sample_rate)
        
        frame = av.AudioFrame.from_ndarray(frame_data, format='flt', layout=layout)
        frame.sample_rate = sample_rate
        frame.pts = 0
        
        output_container.mux(out_stream.encode(frame))
        output_container.mux(out_stream.encode(None))
        output_container.close()

        with open(path, 'wb') as f:
            f.write(output_buffer.getbuffer())
        
        return path

    @staticmethod
    def prepare_metadata(prompt: str, extra_pnginfo: str) -> dict[str, str]:
        """
        Feed a dict with metadata.
        """
        metadata = {}
        if prompt is not None:
            metadata["prompt"] = json.dumps(prompt)
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata[x] = json.dumps(extra_pnginfo[x])
        return metadata
