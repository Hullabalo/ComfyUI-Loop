import torch
import safetensors.torch
import os
import json


class LoopLatentUtils:
    """Utility class for managing latents"""
    
    @staticmethod
    def _load_or_create(latent: torch.Tensor, path: str, load: bool) -> torch.Tensor:
        """
        Internal method to load or create a latent.
        """
        if os.path.exists(path) and load:
            return LoopLatentUtils.load_existing_latent(path)
        else:
            return LoopLatentUtils.save_new_latent(latent, path)

    @staticmethod
    def load_or_create_latent(latent: torch.Tensor, path: str, load: bool) -> tuple[torch.Tensor, int, int]:
        """
        Load an existing latent or save it and return its size
        """
        latent_out = LoopLatentUtils._load_or_create(latent, path, load)
        w, h = LoopLatentUtils.get_latent_size(latent_out)
        return latent_out, w, h

    @staticmethod
    def load_or_create_audio_latent(latent: torch.Tensor, path: str, load: bool) -> torch.Tensor:
        """
        Load an existing latent or save it.
        """
        return LoopLatentUtils._load_or_create(latent, path, load)
    
    @staticmethod
    def load_existing_latent(path: str) -> dict[str, torch.Tensor]:
        """
        load a .latent and return a dict {'samples': tensor 4D}.
        Apply multiplier if the file is ancient.
        """
        latent = safetensors.torch.load_file(path, device="cpu") # version code comfyui
        multiplier = 1.0
        if "latent_format_version_0" not in latent:
            multiplier = 1.0 / 0.18215
        samples = {"samples": latent["latent_tensor"].float() * multiplier}
        return samples

    @staticmethod
    def save_new_latent(latent: torch.Tensor, path: str, metadata: dict | None = None) -> torch.Tensor:
        """
        Save latent to path and return
        """
        output = {
            "latent_tensor": latent["samples"].contiguous()
            if isinstance(latent, dict) and "samples" in latent
            else latent.contiguous(),
            "latent_format_version_0": torch.tensor([]),
        }
        safetensors.torch.save_file(output, path, metadata=metadata)

        return latent

    @staticmethod
    def get_latent_size(latent: torch.Tensor, latent_scale: int = 8) -> tuple[int, int]:
        """
        Return latent width and height.
        """
        samples = latent["samples"] if isinstance(latent, dict) and "samples" in latent else latent

        # torch.Tensor case
        if isinstance(samples, torch.Tensor):
            if samples.ndim >= 2:
                h = int(samples.shape[-2])
                w = int(samples.shape[-1])
                return (w * latent_scale, h * latent_scale)

        # numpy / array-like case (attempt)
        shape = getattr(samples, "shape", None)
        if shape and len(shape) >= 2:
            try:
                h = int(shape[-2])
                w = int(shape[-1])
                return (w * latent_scale, h * latent_scale)
            except Exception:
                pass

        return (0, 0)

    @staticmethod
    def prepare_metadata(prompt: str, extra_pnginfo: str) -> dict[str, str]:
        """
        Feed a dict with metadata.
        """
        prompt_info = ""
        if prompt is not None:
            prompt_info = json.dumps(prompt)

        metadata = None
        metadata = {"prompt": prompt_info}
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata[x] = json.dumps(extra_pnginfo[x])
        return metadata