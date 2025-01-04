import time
import os
import shutil
import json
import node_helpers
import numpy as np
import torch
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
from comfy.cli_args import args

# a simple image loop for your workflows. MIT License
# https://github.com/Hullabalo/ComfyUI-Loop/
        
class LoadImageSimple:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
                    "image_path": ("STRING",{"default": "/path/to/image.png", "tooltip": "Full path (including name.ext) of image file."}),
                    }
                }


    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT", "STRING")
    RETURN_NAMES = ("image", "mask", "height", "width", "path")
    CATEGORY = "LOOP"
    DESCRIPTION = "Load an image from specified full path."
    FUNCTION = "load_image"
    

    def load_image(self, image_path):

        img = node_helpers.pillow(Image.open, image_path)

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

        return (output_image, output_mask, h, w, image_path)
    
    @classmethod
    def IS_CHANGED(s, image_path):
        return float("NaN")

class SaveImageSimple:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Image datas."}),
                "image_path": ("STRING", {"default": "/path/to/image.ext", "defaultInput": True, "tooltip": "Full path (including name.ext) of saved image."}),
                "save_steps": ("BOOLEAN", {"default": False, "tooltip": "Save a copy next to the output image with a timestamp as suffix."}),
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
        path = os.path.dirname(image_path)

        # Convert to numpy array as float32
        i = (255. * image.cpu().numpy()).astype(np.float32)

        # Handle image shape (1, H, W, C)
        # print(f"Image {filename} shape: {i.shape}") # debug
        if len(i.shape) == 4 and i.shape[0] == 1:
            i = i[0]  # delete batch dimension

        # Convert to uint8
        img = Image.fromarray(np.rint(i).clip(0, 255).astype(np.uint8)) # using np.rint for lossless output

        # save to specified path, eventually overwriting source image
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

        # optionally keep a copy of new file with an unique name
        if save_steps == True:
            timestamp = f"{time.time():.6f}".replace('.', '')  # Format: seconds.microseconds
            base, ext = os.path.splitext(filename)
            img_copy_name = f"{base}_{timestamp}{ext}"
            img_copy_path = os.path.join(path, img_copy_name)
            shutil.copy(image_path, img_copy_path)

        result.append({
            "filename": filename,
            "subfolder": path,
            "type": "output"
        })

        return {"ui": {"images": result}}

NODE_CLASS_MAPPINGS = {
    "LoadImageSimple": LoadImageSimple,
    "SaveImageSimple": SaveImageSimple
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageSimple": "Load Image (LOOP)",
    "SaveImageSimple": "Save Image (LOOP)"
}