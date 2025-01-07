import time
import os
import shutil
import json
import node_helpers
import folder_paths
import numpy as np
import torch
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
from comfy.cli_args import args

# a simple image loop for your workflow. MIT License
# https://github.com/Hullabalo/ComfyUI-Loop/

class LoadImageSimple:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
                    "image": ("STRING",{"default": "image.png", "tooltip": "Name of an image file located in output folder."}),
                    }
                }

    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT", "STRING")
    RETURN_NAMES = ("image", "mask", "height", "width", "path")
    CATEGORY = "LOOP"
    DESCRIPTION = "Load an image from output folder."
    FUNCTION = "load_image"
    

    def load_image(self, image):

        image = os.path.join(self.output_dir, image)
        img = node_helpers.pillow(Image.open, image)

        output_images = []
        output_masks = []
        w, h = None, None

        i = node_helpers.pillow(ImageOps.exif_transpose, img)

        if i.mode == 'I':
            i = i.point(lambda i: i * (1 / 255))
        img = i.convert("RGB")

        if len(output_images) == 0:
            w = img.size[0]
            h = img.size[1]

        img = np.array(img).astype(np.float32) / 255.0
        img = torch.from_numpy(img)[None,]
        if 'A' in i.getbands():
            mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
        output_images.append(img)
        output_masks.append(mask.unsqueeze(0))

        output_image = output_images[0]
        output_mask = output_masks[0]

        return (output_image, output_mask, h, w, image)
    
    @classmethod
    def IS_CHANGED(s, image):
        return float("NaN")

class SaveImageSimple:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Image datas."}),
                "image_path": ("STRING", {"default": "/path/to/image.ext", "defaultInput": True, "tooltip": "Full path of the saved image."}),
                "save_steps": ("BOOLEAN", {"default": False, "tooltip": "Save a copy next to the saved image with a timestamp as suffix."}),
            },
            "optional": {
                "mask": ("MASK", {"tooltip": "Optional mask to use as alpha channel."}),
            },
            "hidden": {
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "LOOP"
    DESCRIPTION = "Saves the input image, optionally add a mask as alpha channel."

    def save_images(self, image, image_path, save_steps, prompt=None, extra_pnginfo=None, mask=None):
        result = list()
        filename = os.path.basename(image_path)

        # Convert to numpy array as float32
        i = (255. * image.cpu().numpy()).astype(np.float32)

        # Handle image shape (1, H, W, C)
        # print(f"Image {filename} shape: {i.shape}") # debug
        if len(i.shape) == 4 and i.shape[0] == 1:
            i = i[0]  # delete batch dimension

        img = Image.fromarray(np.rint(i).clip(0, 255).astype(np.uint8)) # Convert to uint8 using np.rint for lossless output

        # save to specified path, overwriting source image
        if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
            img.save(image_path, quality=100)
        else:
            # Add mask as alpha channel if provided
            if mask is not None:
                m = (255. * mask.cpu().numpy()).astype(np.uint8)
                if len(m.shape) == 4:
                    m = m[0]
                m = np.squeeze(m)
                m = 255 - m
                m = np.rint(m).clip(0, 255).astype(np.uint8) # m = np.clip(m, 0, 255).astype(np.uint8)

                # Ensure mask size matches image size
                if m.shape[:2] != (img.height, img.width):
                    print(f"Error : Mask size {m.shape[:2]} doesn't match image size {(img.height, img.width)}.")

                # force mask resize
                # if m.shape[:2] != (img.height, img.width):
                    # m = Image.fromarray(m)
                    # m = m.resize((img.width, img.height), resample=Image.BILINEAR)
                    # m = np.array(m)
                else:
                    img = img.convert("RGBA")
                    alpha = Image.fromarray(m)
                    r, g, b = img.split()[:3]
                    img = Image.merge("RGBA", (r, g, b, alpha))

            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            img.save(image_path, pnginfo=metadata, compress_level=0)

        # keep a copy of image with increment
        if save_steps == True:
            timestamp = f"{time.time():.6f}".replace(".", "")
            base, ext = os.path.splitext(filename)
            img_copy_name = f"{base}_{timestamp}{ext}"
            img_copy_path = os.path.join(self.output_dir, img_copy_name)
            shutil.copy(image_path, img_copy_path)

        result.append({
            "filename": filename,
            "subfolder": "",
            "type": "output"
        })

        return {"ui": {"images": result}}

class ImageCutLoop:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "x": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8}),
                "y": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8}),
                "width": ("INT", {"default": 512, "min": 8, "max": 4096, "step": 8}),
                "height": ("INT", {"default": 512, "min": 8, "max": 4096, "step": 8}),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "INT", "INT",)
    RETURN_NAMES = ("source", "cutting","x","y",)
    FUNCTION = "cut"
    CATEGORY = "LOOP"
    DESCRIPTION = "Cut a part of an input image."

    def cut(self, image, x, y, width, height):
        try:
            _, img_height, img_width, _ = image.shape

            # validate crop parameters
            x = min(max(0, x), img_width - 1)
            y = min(max(0, y), img_height - 1)
            width = min(width, img_width - x)
            height = min(height, img_height - y)

            # crop image
            cut = image[:, y:y+height, x:x+width, :]

            return (image, cut, x, y)

        except Exception as e:
            print(f"Cut error: {str(e)}")
            raise e

class ImagePasteLoop:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source": ("IMAGE",),
                "cutting": ("IMAGE",),
                "mask": ("MASK",),
                "x": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8, "defaultInput": True}),
                "y": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8, "defaultInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "paste"
    CATEGORY = "LOOP"
    DESCRIPTION = "Replace a cutting in the original image."

    def paste(self, source, cutting, mask, x, y):
        try:
            _, orig_height, orig_width, _ = source.shape
            _, crop_height, crop_width, _ = cutting.shape

            # create a copy of original image
            paste_image = source.clone()

            # check x, y parameters to assure they are bounded into the limits
            x = min(max(0, x), orig_width - 1)
            y = min(max(0, y), orig_height - 1)

            # adjust dimensions if crop goes out of the borders
            paste_width = min(crop_width, orig_width - x)
            paste_height = min(crop_height, orig_height - y)

            # if mask is None or empty
            if mask is None or mask.max() == 0:
                paste_image[:, y:y+paste_height, x:x+paste_width, :] = cutting[:, :paste_height, :paste_width, :]
            else:
                _, mask_height, mask_width = mask.shape  # (batch, H, W)
                if crop_height != mask_height or crop_width != mask_width:
                    raise ValueError("Mask and cropped image must have the same dimensions.")

                # adjust mask and cropped image if needed
                cutting = cutting[:, :paste_height, :paste_width, :]
                mask = mask[:, :paste_height, :paste_width]
                mask = mask.unsqueeze(-1)  # add dimension if needed (H, W) -> (H, W, 1)

                # normalize mask (between 0 and 1 values)
                mask = mask.float() / mask.max()

                # apply mask
                paste_image[:, y:y+paste_height, x:x+paste_width, :] = (
                    cutting * mask + paste_image[:, y:y+paste_height, x:x+paste_width, :] * (1 - mask)
                )

            return (paste_image,)

        except Exception as e:
            print(f"Error while pasting : {str(e)}")
            raise e

NODE_CLASS_MAPPINGS = {
    "LoadImageSimple": LoadImageSimple,
    "SaveImageSimple": SaveImageSimple,
    "ImageCutLoop": ImageCutLoop,
    "ImagePasteLoop": ImagePasteLoop
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageSimple": "Load Image (LOOP)",
    "SaveImageSimple": "Save Image (LOOP)",
    "ImageCutLoop": "Cut Image (LOOP)",
    "ImagePasteLoop": "Paste Image (LOOP)"
}