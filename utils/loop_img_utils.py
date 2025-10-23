from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
import os
import numpy as np
import torch
import torch.nn.functional as F
import re
import json
from itertools import count
import hashlib

class LoopImageUtils:
    """Utility class for managing images"""

    @staticmethod
    def save_preview_image(image: torch.Tensor, dir: str, scale: float) -> str:
        """
        Save an image tensor as JPEG in the specified folder and return filename.
        """
        img = Image.fromarray((image[0].detach().cpu().numpy() * 255).astype(np.uint8))

        if scale != 1.0:
            _, h, w, _ = image.shape
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)       

        existing = [p for p in os.listdir(dir) if p.startswith("preview_") and p.endswith(".jpeg")]
        pattern = re.compile(r"preview_(\d{5})\.jpeg")
        numbers = {int(pattern.match(f).group(1)) for f in existing if pattern.match(f)}
        counter = next(c for c in count() if c not in numbers)

        filename = f"preview_{counter:05d}.jpeg"
        file_path = os.path.join(dir, filename)
        img.save(file_path, format="JPEG", quality=60, optimize=False, progressive=False)
        
        return filename

    @staticmethod
    def save_preview_mask(mask: torch.Tensor, dir: str, scale: float = 1.0) -> str:
        """
        Save a mask image tensor as binary PNG in the specified folder and return filename.
        """
        mask_proc = mask[0] if mask.ndim == 3 else mask

        # # precise mask and super-slow preview
        # mask_np = (mask_proc.detach().clamp(0.0, 1.0).mul_(255)
        #            .byte().cpu().numpy())

        # binary mask for fast preview
        mask_proc = mask_proc.detach().clamp(0.0, 1.0)
        mask_binary = (mask_proc > 0.5).float()
        mask_np = (mask_binary * 255).byte().cpu().numpy()

        h, w = mask_np.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[..., 3] = mask_np  # alpha = intensité du masque

        pil_mask = Image.fromarray(rgba, mode="RGBA")

        if scale != 1.0:
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            pil_mask = pil_mask.resize(new_size, Image.Resampling.BILINEAR)

        base = "mask_preview_"
        existing = [f for f in os.listdir(dir) if f.startswith(base)]
        num = len(existing)
        filename = f"{base}{num:05d}.png"
        file_path = os.path.join(dir, filename)

        pil_mask.save(file_path, format="PNG", compress_level=3, optimize=True)

        return filename
    
    @staticmethod
    def load_existing_image(path: str) -> torch.Tensor:
        """
        Load an existing image from path and return a tensor (1, H, W, 3)
        """
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)

        if img.mode == 'I':
            img = img.point(lambda i: i * (1 / 255))
        img = img.convert("RGB")

        tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0)[None, ...]

        return tensor

    @staticmethod
    def save_new_image(image: torch.Tensor, path: str, metadata: PngInfo | None = None) -> torch.Tensor:
        """
        Save image to path and return input tensor.
        """
        img = Image.fromarray((image[0].cpu().numpy() * 255).astype(np.uint8))
        img.save(path, pnginfo=metadata, compress_level=0)

        return image

    @staticmethod
    def save_image_with_alpha_mask(image: torch.Tensor, mask: torch.Tensor, path: str, metadata: PngInfo | None = None) -> torch.Tensor:
        """
        Save image with mask as alpha channel to path and return input image tensor.
        """
        # keep first batch element for image [H, W, C]
        image_single = image[0] if image.ndim == 4 else image
        
        # # first batch element for mask 
        if mask.ndim == 2:  # [H, W]
            mask_single = mask.unsqueeze(0)
        elif mask.ndim == 3:  # [B, H, W] ou [1, H, W]
            mask_single = mask[:1]  # keep first mask in batch [1, H, W]
        else:
            raise ValueError(f"Mask must have shape [H, W] or [B, H, W], got {mask.shape}")
                
        # Get image dimensions
        h, w, c = image_single.shape
        
        # Resize mask to match image dimensions if needed
        mask_resized = LoopImageUtils.resize_mask(mask_single, h, w)
        
        # Clamp and prepare mask for alpha channel
        mask_clamped = mask_resized.clamp(0.0, 1.0)
        alpha_np = ((1.0 - mask_clamped[0]) * 255).cpu().numpy().astype(np.uint8) # [0] remove batch dim and invert mask for alpha
        
        image_clamped = image_single.clamp(0.0, 1.0)
        image_np = (image_clamped.cpu().numpy() * 255).astype(np.uint8)
        
        # Convert image numpy array to PIL Image
        if c == 1:  # Grayscale
            img_pil = Image.fromarray(image_np[:, :, 0], mode='L')
            img_pil = img_pil.convert('RGB')
        elif c == 3:  # RGB
            img_pil = Image.fromarray(image_np, mode='RGB')
        else:
            raise ValueError(f"Unsupported number of channels: {c}")
        
        # Add alpha channel
        img_with_alpha = img_pil.copy()
        img_with_alpha.putalpha(Image.fromarray(alpha_np, mode='L'))
        
        img_with_alpha.save(path, pnginfo=metadata, compress_level=0)
        
        return image

    @staticmethod
    def prepare_metadata(prompt: str, extra_pnginfo: str) -> PngInfo:
        """
        Feed a pngInfo object with metadata.
        """
        # metadata = None
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))
        return metadata
    
    @staticmethod
    def load_existing_mask(path: str) -> torch.Tensor:
        """
        Load an existing mask (.png) and return a mask tensor (1, H, W)
        """
        img = Image.open(path).convert("L")  # 8-bit grayscale
        img = ImageOps.exif_transpose(img)  # EXIF rotation

        mask_np = np.array(img).astype(np.float32) / 255.0
        mask_tensor = torch.from_numpy(mask_np)[None, ...]

        return mask_tensor

    @staticmethod
    def save_new_mask(mask: torch.Tensor, path: str, metadata: PngInfo | None = None) -> torch.Tensor:
        """
        save a mask (1, H, W) in a .png file and return mask tensor input
        """
        # Check shape
        assert mask.ndim == 3 and mask.shape[0] == 1, \
            f"Mask must be of shape (1, H, W), received {mask.shape}"

        # Clamp
        mask_clamped = mask.clamp(0.0, 1.0)
        mask_np = (mask_clamped[0].cpu().numpy() * 255).astype(np.uint8)
        pil_mask = Image.fromarray(mask_np, mode="L")
        # pil_mask.save(path)
        pil_mask.save(path, pnginfo=metadata, compress_level=0)

        return mask
    
    @staticmethod
    def get_mask_from_image_alpha(path: str, h: int, w: int) -> torch.Tensor:
        """
        Return a mask from alpha channel of an image file path, or empty mask
        """
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)

        if 'A' in img.getbands():
            mask_out = np.array(img.getchannel('A')).astype(np.float32) / 255.0
            mask_out = 1. - torch.from_numpy(mask_out)
            return mask_out.unsqueeze(0)
        else:
            return torch.zeros((1, h, w), dtype=torch.float32, device="cpu")

    @staticmethod
    def get_mask_from_image_tensor(image: torch.Tensor, h: int, w: int) -> torch.Tensor:
        """
        Return a mask from alpha of an Image tensor, or empty mask
        """
        if image.shape[3] == 4:  # if RGBA
            return image[0, :, :, 3:4].permute(2, 0, 1)
        else:
            return torch.zeros((1, h, w), dtype=torch.float32, device="cpu")

    @staticmethod
    def resize_mask(mask: torch.Tensor, h: int, w: int) -> torch.Tensor:
        """
        Resize a mask to h,w if != than h, w
        """
        if mask.shape[1] != h or mask.shape[2] != w:
            mask = F.interpolate(
                mask.unsqueeze(0),
                size=(h, w),
                mode='nearest'
            ).squeeze(0)
        return mask

    @staticmethod
    def get_mask_size(mask: torch.Tensor) -> tuple:
        """
        return width and height of a mask
        """
        w, h = mask.shape[-1], mask.shape[-2]
        return (w, h)
    
    @staticmethod
    def get_default_mask(h: int, w: int) -> torch.Tensor:
        """
        return a blank mask tensor of h and w size
        """
        return torch.zeros((1, h, w), dtype=torch.float32, device="cpu")
    
    @staticmethod
    def ensure_blank_image(path: str):
        """
        Create a 1x1 transparent png file if it doesn't exist.
        """
        full_path = os.path.join(path, "blank.png")
        if not os.path.exists(full_path):
            img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))  # pixel transparent
            img.save(full_path, format="PNG")

    @staticmethod
    def compute_image_hash(image: torch.Tensor) -> str:
        """
        Compute a compact perceptual hash for an image tensor.

        generates a lightweight, content-based signature used to
        quickly compare or detect changes between images. designed for speed: 
        Small visual variations (color, brightness, or minor cropping)
        typically yield similar hashes, while distinct images produce distinct
        values.
        """
        try:
            if image.is_cuda:
                image = image.detach().to("cpu")

            if image.dtype == torch.float32:
                i = (image.clamp(0, 1) * 255).byte()
            else:
                i = image.byte()
            
            # agressive downsample (16x16)
            h, w = i.shape[-3:-1]
            step_h = max(1, h // 16)
            step_w = max(1, w // 16)
            small = i[..., ::step_h, ::step_w, :]

            mean_val = torch.round(small.float().mean(dim=(0, 1)) / 32).to(torch.uint8)

            # fast stats
            arr_float = small.float()
            mean_global = torch.round(arr_float.mean())
            max_val = arr_float.max()
            min_val = arr_float.min()

            stats = torch.tensor([mean_global, max_val, min_val], dtype=torch.float32)

            data = mean_val.numpy().tobytes() + stats.numpy().tobytes()
            return hashlib.md5(data).hexdigest()

        except Exception as e:
            print(f"[HASH ERROR image] {e}")
            return None

    @staticmethod
    def compute_mask_hash(mask: torch.Tensor) -> str:
        """
        Compute a compact perceptual hash for a mask tensor.

        generates a lightweight, content-based signature used to
        quickly compare or detect changes between masks. designed for speed: 
        Small visual variations typically yield similar hashes.
        """
        try:
            if mask.is_cuda:
                mask = mask.detach().to("cpu")

            if mask.dtype == torch.float32:
                m = (mask.clamp(0, 1) * 255).to(torch.uint8)
            else:
                m = mask.to(torch.uint8)
            
            # agressive downsample (16x16) --> precise (32x32)
            h, w = m.shape[-2:]
            step_h = max(1, h // 32)
            step_w = max(1, w // 32)
            small = m[..., ::step_h, ::step_w]
            
            mean_val = torch.round(small.float().mean())
            
            # 12 bins histogram
            small_binned = (small.float() / 255 * 7).to(torch.long).clamp(0, 7)
            hist = torch.bincount(small_binned.flatten(), minlength=12)
            hist = torch.round(hist.float() / hist.sum() * 255).to(torch.uint8)
            
            data = mean_val.numpy().tobytes() + hist.numpy().tobytes()
            return hashlib.md5(data).hexdigest()
                        
        except Exception as e:
            print(f"[HASH ERROR mask] {e}")
            return None
