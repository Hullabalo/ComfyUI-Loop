import torch
import folder_paths
import os
import time
import shutil
from comfy.comfy_types.node_typing import IO
from server import PromptServer
from .utils.loop_img_utils import LoopImageUtils as IU
from .utils.loop_latent_utils import LoopLatentUtils as LU
from .utils.loop_audio_utils import LoopAudioUtils as AU
from .utils.loop_string_utils import LoopStringUtils as SU
from .utils.loop_path_utils import LoopPathUtils as PU
from .utils.error_handler import ErrorHandler

"""
A simple image loop for your workflow. MIT License. version 0.2
https://github.com/Hullabalo/ComfyUI-Loop/
Thanks to rgthree, chrisgoringe, pythongosssss and many, many many others for their contributions, how-to's, code snippets etc.

last changes 10/23/2025 :
Better integration with last ComfyUI version. Better code structure.
- Now there's only four nodes for two main usages, looping files and visual cutting-pasting: 
  LoopAny -> SaveAny
  loop any file type : image (png), mask (png), latent (image/audio/whatever), audio (flac), string (or int/float) saved as text file.

  ImageCrop -> ImagePaste
  ImageCrop now works with last Comfy frontend, lastly tested with ComfyUI v0.3.64, ComfyUI_Frontend v1.27.10

TL;DR : Revisited code from A to Z. Crop your images and masks, loop your files, the fun way.
"""

class ImageCropLoop:
    """
    Crop an image and mask at x,y coordinates with a given size . Generate image and mask preview for interactive cropping.
    Keyboard shortcuts (with mouse pointer on preview Image) : PageUp/PageDown to Increase/decrease size
    """

    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.preview_dim = 1024 # change this if you need a detailed preview.
        self.last_img_hash = None
        self.last_filename = None
        self.last_mask_hash = None
        self.last_maskname = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "x": ("INT", {"default": 0, "min": 0, "max": 32768, "tooltip": "x origin of the crop."}), # enough for 1073 Megapixels images. Much more than what you would/could/should process :)
                "y": ("INT", {"default": 0, "min": 0, "max": 32768, "tooltip": "y origin of the crop."}),
                "size": ("INT", {"default":512, "min": 256, "max": 2048, "step": 8, "tooltip": "size of the crop. By 8 pixels increments."}),
                "color": (["black","grey","red","green","blue"], {"default": "black", "tooltip": "Color of the crop rectangle in the preview."}),
                "show_mask": ("BOOLEAN", {"default": True, "tooltip": "Show or hide preview mask"}),
            },
            "optional": {"mask": ("MASK",)},
            "hidden": {"id": "UNIQUE_ID"}
        }

    CATEGORY = "LOOP"
    DESCRIPTION = "Crop an image and mask at x,y coordinates with given size. Generate image and mask preview for interactive cropping."
    FUNCTION = "click_and_crop"
    RETURN_TYPES = ("IMAGE","IMAGE","INT","INT","INT","MASK")
    RETURN_NAMES = ("source","cut","size","x","y","cut_mask")
    
    def click_and_crop(self, image, x, y, size, color, show_mask, id, mask=None):
                
        _, h, w, _ = image.shape
        size = min(size, h, w) # max crop size to image boundaries
        x, y = abs(x), abs(y)
        x, y = max(0, min(x, w - size)), max(0, min(y, h - size)) # keep crop into image limits

        cut = image[:, y:y+size, x:x+size, :]

        # mask management
        if mask is not None:
            mask = IU.resize_mask(mask, h, w) # resize to image dimensions
            cut_mask = mask[:, y:y+size, x:x+size]
        else:
            cut_mask = IU.get_default_mask(size, size)

        # define preview scale
        scale = self.preview_dim / w if self.preview_dim < w else 1.0

        # image preview management
        current_img_hash = IU.compute_image_hash(image)
        # print(f"image_hash_changed: {current_img_hash != self.last_img_hash}") # debug

        if current_img_hash != self.last_img_hash or self.last_filename is None:
            filename = IU.save_preview_image(image, self.output_dir, scale)
            self.last_img_hash = current_img_hash
            self.last_filename = filename
        else:
            filename = self.last_filename

        # mask preview management
        if mask is not None:
            current_mask_hash = IU.compute_mask_hash(mask)
            # print(f"mask_hash_changed: {current_mask_hash != self.last_mask_hash}") # debug

            if current_mask_hash != self.last_mask_hash or self.last_maskname is None:
                maskname = IU.save_preview_mask(mask, self.output_dir, scale)
                self.last_mask_hash = current_mask_hash
                self.last_maskname = maskname
            else:
                maskname = self.last_maskname
        else:
            maskname = None
            self.last_mask_hash = None
            self.last_maskname = None

        # update preview
        try:
            # print(f"Sending crop-bridge-proxy event (id={id}, filename={filename})") # debug
            PromptServer.instance.send_sync("crop-bridge-proxy", {
                "id": id,
                "name": filename,
                "mask": maskname,
                "scale": scale,
                "original_width": w,
                "original_height": h
            })
        except Exception as e:
            ErrorHandler.handle_communication_error(e, "click_and_crop")

        return (image, cut, size, x, y, cut_mask)

    def IS_CHANGED(**kwargs):
        return float("NaN")

class ImagePasteLoop:
    """
    Paste an image cut into a source image at x,y coordinates, with optional mask and blending.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source": ("IMAGE",),
                "cut": ("IMAGE",),
                "x": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8, "forceInput": True}),
                "y": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8, "forceInput": True}),
            },
            "optional": {
                "cut_mask": ("MASK", {"tooltip": "Optional cutting mask."}),
            },
        }

    CATEGORY = "LOOP"
    DESCRIPTION = "Paste an image cut into a source image at x,y coordinates, with optional mask and blending."
    FUNCTION = "paste_and_forget"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)

    def paste_and_forget(self, source, cut, x, y, cut_mask=None):

        _, sh, sw, _ = source.shape
        _, ch, cw, _ = cut.shape

        # clamp coordinates and adjust if out of bounds
        x, y = max(0, min(x, sw - 1)), max(0, min(y, sh - 1))
        w, h = min(cw, sw - x), min(ch, sh - y)

        result = source.clone()

        # no mask? direct paste.
        if cut_mask is None or cut_mask.max() == 0:
            result[:, y:y+h, x:x+w, :] = cut[:, :h, :w, :]
            return (result,)
                            
        # adjust and normalize mask
        cut_mask = cut_mask[:, :h, :w].unsqueeze(-1).float()
        cut_mask /= cut_mask.max() if cut_mask.max() > 0 else 1.0

        # blend
        region = result[:, y:y+h, x:x+w, :]
        result[:, y:y+h, x:x+w, :] = cut[:, :h, :w, :] * cut_mask + region * (1 - cut_mask)

        return (result,)            

class LoopAny:
    """
    Loop any input (image, mask, latent, audio, string...) from /output folder or one of its subfolders. 
    """
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input": (IO.ANY, ),
                "loop_file": ("BOOLEAN", {"default": False, "tooltip": "Enable image loop mode. Disable to load from image input"}),
                "filename": ("STRING",{"default": "loop_file", "tooltip": "(fac.) Filename of loop file without extension. Define/Use an existing file to load from /output or its subfolders."}),
                "subfolder": ("STRING",{"default": "", "tooltip": "(fac.) Subfolder to load or copy input file. Default root to /output"}),
                "loop_mask": ("BOOLEAN", {"default": False, "tooltip": "Enable mask loop mode. Disable to load from mask input"}),
            },
            "optional": {
                "mask": ("MASK", {})
            },
            "hidden": {"id": "UNIQUE_ID"}
        }
    
    CATEGORY = "LOOP"
    DESCRIPTION = "Loop any input (image, mask, latent, audio, string...) from /output folder or one of its subfolders."
    FUNCTION = "loop_that_thing"
    RETURN_TYPES = (IO.ANY, "STRING", "INT", "INT", "MASK")
    RETURN_NAMES = ("output", "path", "width", "height", "mask")


    def loop_that_thing(self, input, loop_file, loop_mask, subfolder, id, mask=None, filename = "loop_file"):

        w, h = 1, 1
        
        path = os.path.join(self.output_dir, subfolder.strip("/\\")) if subfolder else self.output_dir
        os.makedirs(path, exist_ok=True)
        full_path = os.path.join(path, filename)
        
        match input:
            # --- IMAGE ---
            case _ if isinstance(input, torch.Tensor) and input.ndim == 4 and input.shape[1] != 4:
                print("IMAGE TENSOR")
                full_path += ".png"

                if os.path.exists(full_path) and loop_file:
                    img_out = IU.load_existing_image(full_path)
                else:
                    img_out = IU.save_new_image(input, full_path)

                _, h, w, _ = img_out.shape

                if loop_mask:
                    mask_out = (
                        IU.get_mask_from_image_alpha(full_path, h, w)
                        if os.path.exists(full_path)
                        else IU.get_default_mask(h, w)
                    )
                else:
                    mask_out = IU.resize_mask(mask, h, w) if mask is not None else IU.get_default_mask(h, w)

                return (img_out, full_path, w, h, mask_out)

            # --- MASK ---
            case _ if isinstance(input, torch.Tensor) and input.ndim == 3:
                print("MASK TENSOR")
                full_path += ".png"

                if os.path.exists(full_path) and loop_file:
                    mask_out = IU.load_existing_mask(full_path)
                else:
                    mask_out = IU.save_new_mask(input, full_path)

                w, h = IU.get_mask_size(mask_out)

                return (mask_out, full_path, w, h, None)

            # --- LATENT ---
            case _ if isinstance(input, dict) and "samples" in input:
                samples = input["samples"]
                latent_type = input.get("type", None)
                # print("Checking LATENT : ", samples.mean(), samples.std())
                full_path += ".latent"
                if isinstance(samples, torch.Tensor):
                    s_ndim = getattr(samples, "ndim", None)

                    if s_ndim == 5 and samples.shape[1] == 16:
                        print("LATENT (QWEN, WAN)")
                        latent_out, w, h = LU.load_or_create_latent(input, full_path, loop_file)

                    elif s_ndim == 4 and samples.shape[1] == 4:
                        print("LATENT (SD 1.x / 2.x / SDXL)")
                        latent_out, w, h = LU.load_or_create_latent(input, full_path, loop_file)
                    
                    elif s_ndim == 4 and samples.shape[1] == 16:
                        print("LATENT (Flux.1, SD3, Chroma)")
                        latent_out, w, h = LU.load_or_create_latent(input, full_path, loop_file)

                    elif s_ndim == 3 and latent_type == "audio":
                        print("LATENT AUDIO (stable audio 1.0)")
                        latent_out = LU.load_or_create_audio_latent(input, full_path, loop_file)

                    elif s_ndim == 4 and latent_type == "audio":
                        print("LATENT AUDIO (ACE Step)")
                        latent_out = LU.load_or_create_audio_latent(input, full_path, loop_file)
        
                    else:
                        print(f"LATENT AUDIO or Unknown LATENT (shape={samples.shape}, type={latent_type})")
                        latent_out, w, h = LU.load_or_create_latent(input, full_path, loop_file)
                        
                    return (latent_out, full_path, w, h, None)
                else:
                    print("LATENT (non-tensor samples)")
                    return (input, full_path, w, h, None)

            # --- AUDIO ---
            case _ if isinstance(input, dict) and "waveform" in input and "sample_rate" in input:
                print("AUDIO")
                full_path += ".flac"
                audio_out = AU.load_or_create_audio(input, full_path, loop_file)
                return (audio_out, full_path, w, h, None)

            # --- STRING OR INT/FLOAT ---
            case _ if isinstance(input, (str, dict, int, float)):
                if isinstance(input, (dict, int, float)):
                    input = str(input)
                print("STRING")
                full_path += ".txt"
                string_out = SU.load_or_create_text_file(input, full_path, loop_file)
                return (string_out, full_path, w, h, None)

            # --- FALLBACK / UNEXPECTED TYPE ---
            case _:
                t = type(input)
                module_name = t.__module__
                type_name = t.__name__
                print(f"[WARN] unexpected type : {module_name}.{type_name}")
                return (input, full_path, w, h, None)

        return (input, path, w, h, mask)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        return True

class SaveAny:
    """
        Save any input (image, mask, latent, audio, string...) to /output or a specified subfolder as .png, .latent, .flac, .txt...
    """
    def __init__(self):
        IU.ensure_blank_image(folder_paths.get_temp_directory())

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input": (IO.ANY, ),
                "path": ("STRING", {"default": "/path/to/file.ext", "tooltip": "Full path of the saved file."}),
                "save_steps": ("BOOLEAN", {"default": False, "tooltip": "Save a copy next to the saved image with a timestamp as suffix."}),
                "save_metadata": ("BOOLEAN", {"default": False, "tooltip": "Save metadatas for compatible file formats."}),
                "preview": ("BOOLEAN", {"default": True, "tooltip": "Display the preview in node."}),
            },
            "optional": {
                "mask": ("MASK", {})
            },
            "hidden": {
                "id": "UNIQUE_ID",
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }
    
    CATEGORY = "LOOP"
    DESCRIPTION = "Save any input (image, mask, latent, audio, string...) to /output or a specified subfolder as .png (opt. mask as alpha), .latent, .flac, .txt... "
    FUNCTION = "save_that_thing"
    RETURN_TYPES = ()
    OUTPUT_NODE = True

    def save_that_thing(self, input, path, save_steps, save_metadata, preview, id, prompt=None, extra_pnginfo=None, mask=None):

        type = "output"
        filename, subfolders, base = PU.parse_path(path, type)

        if save_steps:
            timestamp = f"{time.time():.6f}".replace(".", "")
            name, ext = os.path.splitext(filename)
            step_filename = f"{name}_{timestamp}{ext}"
            step_path = os.path.join(base, subfolders, step_filename)
            shutil.copy(path, step_path)

        match input:
            # --- IMAGE ---
            case _ if isinstance(input, torch.Tensor) and input.ndim == 4 and input.shape[1] != 4:
                metadata = IU.prepare_metadata(prompt, extra_pnginfo) if save_metadata else None
                if mask is not None:
                    print(f"Saving IMAGE (with mask as alpha channel)")
                    IU.save_image_with_alpha_mask(input, mask, path, metadata)
                else:
                    print(f"Saving IMAGE")
                    IU.save_new_image(input, path, metadata)

            # --- MASK ---
            case _ if isinstance(input, torch.Tensor) and input.ndim == 3:
                metadata = IU.prepare_metadata(prompt, extra_pnginfo) if save_metadata else None
                print(f"Saving MASK")
                IU.save_new_mask(input, path, metadata)

            # --- LATENT ---
            case _ if isinstance(input, dict) and "samples" in input:
                samples = input["samples"]
                if isinstance(samples, torch.Tensor):
                    metadata = LU.prepare_metadata(prompt, extra_pnginfo) if save_metadata else None
                    print(f"Saving LATENT")
                    LU.save_new_latent(input, path, metadata)
                    filename, subfolders, type = "latent.svg", "", "temp"
                else:
                    print("NOT SAVED - LATENT (non-tensor samples)")
                    filename, subfolders, type = "error.svg", "", "temp"
                
            # --- AUDIO ---
            case _ if isinstance(input, dict) and "waveform" in input and "sample_rate" in input:
                metadata = AU.prepare_metadata(prompt, extra_pnginfo) if save_metadata else None
                print("Saving AUDIO")
                AU.save_audio(input, path, metadata)
                filename, subfolders, type = "audio.svg", "", "temp"

            # --- STRING OR INT/FLOAT ---
            case _ if isinstance(input, (str, dict, int, float)):
                print("Saving TEXT")
                SU.save_text_file(input, path)
                filename, subfolders, type = "text.svg", "", "temp"

            # --- FALLBACK / UNEXPECTED TYPE ---
            case _:
                t = type(input)
                module_name = t.__module__
                type_name = t.__name__
                print(f"NOT SAVED - unexpected type : {module_name}.{type_name}")
                filename, subfolders, type = "error.svg", "", "temp"

        if not preview:
            filename, subfolders, type = "blank.png", "", "temp"

        return {"ui": {"images": [{"filename": filename, "subfolder": subfolders, "type": type}]}}

    
NODE_CLASS_MAPPINGS = {
    "ImageCropLoop": ImageCropLoop,
    "ImagePasteLoop": ImagePasteLoop,
    "LoopAny": LoopAny,
    "SaveAny": SaveAny,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageCropLoop": "♾️ Image Crop",
    "ImagePasteLoop": "♾️ Paste Image",
    "LoopAny": "♾️ Loop Any",
    "SaveAny": "♾️ Save Any",
}