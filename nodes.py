import time
import os
import shutil
import json
import node_helpers
import folder_paths
import numpy as np
import torch
import random
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
from comfy.cli_args import args

# a simple image loop for your workflow. MIT License. version 0.1.5
# https://github.com/Hullabalo/ComfyUI-Loop/
# last changes 4/30/2025 :
# Better integration with classic ComfyUI workflow, compatible inputs and outputs
# - added the node LoopImageSimple in a aim to replace the LoadImageSimple. A different flavor, that's something.
# - option given in loopimagesimple to choose the image name and folder, and/or use a classic image input and mask
# - some minors modifications into Save Image. Removed compatibility with jpg/jpeg ... 
# - added the Crop Image node, woohoo javascript overdose, but it works ok with ComfyUI v0.3.10, ComfyUI_Frontend v1.6.15
# - now, 'Paste Image' hosts a optional cutting_mask input
# - small upgrade to 'Cut Image' node, added mask input and cutting_mask output
# TL;DR : I've reviewed everything.

# TODO : removing the shit out of the code, keeping the good.

class LoadImageSimple:
    # DEPRECATED. Use vanilla Load Image with 'Loop Image' node instead
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


class LoopImageSimple:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                    "image": ("IMAGE",{}),
                    "loop_image": ("BOOLEAN", {"default": False, "tooltip": "Enable image loop mode. Disable (false) to load from image input"}),
                    "loop_mask": ("BOOLEAN", {"default": False, "tooltip": "Enable mask loop mode. Disable (false) to load from optional mask input"}),
                    "filename": ("STRING",{"default": "loop_image", "tooltip": "(facultative) Filename of loop image without extension (it's .png only). Use the name of an already existing image to load it from /output or one of its subfolders. Yeah, I know that it's a too long long long description for a simple field. :)"}),
                    "folder": ("STRING",{"default": "", "tooltip": "(facultative) Name a subfolder to load from or copy the input image into. If it does not exists, it will be created into /output"}),
            },
            "optional": {
                "mask": ("MASK", {"tooltip": "Optional mask. Fire your workflow one time before connecting"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT", "STRING")
    RETURN_NAMES = ("image", "mask", "height", "width", "path")

    CATEGORY = "LOOP"
    DESCRIPTION = "Loop an image and mask. " \
    "Image is copied from image input to the folder defined in corresponding field, " \
    "and named as in filename field." \
    "You can also use those two fields to load directly an image from /output/'folder'." \
    "" \
    "Use the loop_image and loop_mask to load a new mask and/or image, or to loop the same image and/or mask."

    FUNCTION = "load_loop_image"
    
    def load_loop_image(self, image, loop_image, loop_mask, filename, folder, mask=None):
        # folder management
        if folder != "":
            folder_path = os.path.join(self.output_dir, folder)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
        else:
            folder_path = self.output_dir

        filename = f"loop_image.png" if filename == "" else filename+".png"

        image_path = os.path.join(folder_path, filename)

        # Check if the file already exists in loop folder, and that node is in a loop configuration
        if os.path.exists(image_path) and loop_image:
            # create a tensor from this file instead of using the input tensor
            img = node_helpers.pillow(Image.open, image_path)
            i = node_helpers.pillow(ImageOps.exif_transpose, img)
            
            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            img = i.convert("RGB")
            
            w = img.size[0]
            h = img.size[1]
            
            img = np.array(img).astype(np.float32) / 255.0
            img = torch.from_numpy(img)[None,]
            
            # by order, returns the optional input mask, or alpha from image, or an empty mask
            if mask is not None and loop_mask is False:
                mask_out = mask
            elif 'A' in i.getbands():
                mask_out = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask_out = 1. - torch.from_numpy(mask_out)
                mask_out = mask_out.unsqueeze(0)
            else:
                mask_out = torch.zeros((h, w), dtype=torch.float32, device="cpu")
                mask_out = mask_out.unsqueeze(0)
            
            output_image = img
            output_mask = mask_out
        else:
            # If the loop image has not been already created in /output/folder
            pil_image = Image.fromarray((image[0].cpu().numpy() * 255).astype(np.uint8))
            pil_image.save(image_path)
            
            # using input image
            output_image = image
            h, w = image.shape[1], image.shape[2]

            # by order, returns the optional input mask, or alpha from image, or an empty mask
            if mask is not None and loop_mask is False:
                output_mask = mask
            elif image.shape[3] == 4:  # if image is (RGBA), extract alpha channel
                output_mask = image[0, :, :, 3:4].permute(2, 0, 1)  # permute to (1, h, w)
            else:
                # create an empty mask
                output_mask = torch.zeros((1, h, w), dtype=torch.float32, device="cpu")

        return (output_image, output_mask, h, w, image_path)
    
    @classmethod
    def IS_CHANGED(cls, image, loop_image, loop_mask, filename, folder, mask):
        return float("NaN")
    
class SaveImageSimple:
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
        current_saving_path = os.path.dirname(image_path)

        # Convert to numpy array as float32
        i = (255. * image.cpu().numpy()).astype(np.float32)

        # Handle image shape (1, H, W, C)
        if len(i.shape) == 4 and i.shape[0] == 1:
            i = i[0]  # delete batch dimension

        img = Image.fromarray(np.rint(i).clip(0, 255).astype(np.uint8)) # Convert to uint8 using np.rint for lossless output

        # 4/29/2025 : removed the option for jpg/jpeg, compatibility is keeped with LoadImageSimple node only for png.
        # save to specified path, overwriting source image
        # if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
        #     img.save(image_path, quality=100)
        # else:
        
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

        # optionally, save a incremented copy of the image,
        # in the folder defined in Loop Image node (if undefined, default as /output)
        if save_steps == True:
            timestamp = f"{time.time():.6f}".replace(".", "")
            base, ext = os.path.splitext(filename)
            img_copy_name = f"{base}_{timestamp}{ext}"
            img_copy_path = os.path.join(current_saving_path, img_copy_name)
            shutil.copy(image_path, img_copy_path)

        result.append({
            "filename": filename,
            "subfolder": os.path.basename(current_saving_path),
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
            "optional": {
                "mask": ("MASK", {"tooltip": "Optional mask."}),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK", "INT", "INT",)
    RETURN_NAMES = ("source", "cutting", "cutting_mask", "x","y",)
    FUNCTION = "cut"
    CATEGORY = "LOOP"
    DESCRIPTION = "Cut a part of an input image."

    def cut(self, image, x, y, width, height, mask=None):
        try:
            _, img_height, img_width, _ = image.shape

            # validate crop parameters
            x = min(max(0, x), img_width - 1)
            y = min(max(0, y), img_height - 1)
            width = min(width, img_width - x)
            height = min(height, img_height - y)

            # crop image
            cut = image[:, y:y+height, x:x+width, :]

            # define cutting mask
            if mask is not None:
                cutting_mask = mask[:, y:y+width, x:x+height]
            else:
                cutting_mask = torch.zeros((1, height, width), dtype=torch.float32, device="cpu")

            return (image, cut, cutting_mask, x, y)

        except Exception as e:
            print(f"Cut error: {str(e)}")
            raise e

    @classmethod
    def IS_CHANGED(cls, image, mask, width, height, size):
        return True

class ImageCropLoop:
    """
    A ComfyUI node to generate an RGB image using pyvips.
    
    Parameters:
    - x (int): top left x origin of the crop.
    - y (int): top left y origin of the crop.
    - size (int): size of the crop (height = width). Multiple of 8
    
    hint: if you need a size wider than 2048*2048 for your crop, change size widget "max" to anything: 
    your output image crop will never exceed the max size of your input image, whatever you choose or do.
    
    Returns:
    - source: source image
    - cutting: image crop.
    - cutting_mask: empty mask
    - x: x origin
    - y: y origin
    - size: size of the crop
    """
    def __init__(self):
        self.temp_dir = folder_paths.get_temp_directory()
        self.filename_prefix = "loop_crop_temp_" + ''.join(random.choice("abcdefghijklmnopqrstuvxyz") for _ in range(5))
        self.type = "temp"
        self.preview_size = 1024 # change this to something smaller/larger if you need a fast ui or a detailed preview. 1024 is just a compromise to keep the UI responsive

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Source image."}),
                "x": ("INT", {"default": 0, "min": 0, "max": 32768, "tooltip": "x origin of the crop."}), # max 32768 is enought for 1073 Megapixels images. Much more than what you can effectively process :)
                "y": ("INT", {"default": 0, "min": 0, "max": 32768, "tooltip": "y origin of the crop."}),
                "size": ("INT", {"default":512, "min": 256, "max": 2048, "step": 8, "tooltip": "size of the crop. By 8 pixels increments."}), # step is 8 because inpaintModelConditionning output multiple of 8 latents (e.g. [[1, 16, 128, 128]] for a 1024*1024px batch of 1 image input)
            },
            "optional": {
                "mask": ("MASK", {"tooltip": "Optional mask."}),
            },
            "hidden": {
            }
        }

    RETURN_TYPES = ("IMAGE","IMAGE","MASK","INT","INT","INT")
    RETURN_NAMES = ("source","cutting","cutting_mask","x","y","size")
    FUNCTION = "click_and_crop"
    CATEGORY = "LOOP"
    DESCRIPTION = "Crop a clicked zone to the size dimensions. Output a cut image."

    def click_and_crop(self, image, x, y, size, mask=None):
        counter = 0
        results = []


        # get original dimensions (for preview, adjustement of crop size and passing to js ui)
        _, oh, ow, _ = image.shape

        # create and save preview image
        pw_filename = f"{self.filename_prefix}_{ow}_{oh}_{counter:05}.png"
        os.makedirs(self.temp_dir, exist_ok=True)
        file_path = os.path.join(self.temp_dir, pw_filename)
        pil_image = Image.fromarray((image[0].cpu().numpy() * 255).astype(np.uint8))
        # resize preview
        if self.preview_size < ow:
            ratio = self.preview_size/ow
            pil_image = pil_image.resize((int(ow*ratio), int(oh*ratio)), Image.LANCZOS)               

        pil_image.save(file_path)
        
        results.append({
            "filename": pw_filename,
            "subfolder": "",
            "type": self.type,
        })

        # adjust crop size if bigger than the image
        if size > ow:
            size = ow
            print(f"crop size is larger than the width of the image, reducing to '{ow}'")
        if size > oh:
            size = oh
            print(f"crop size is larger than the height of the image, reducing to '{oh}'")

        # adjust coords x et y if out of the border
        if x + size > ow:
            x = max(0, ow - size)
            print(f"x+crop size goes out of the borders, changing it to '{x}'")
        if y + size > oh:
            y = max(0, oh - size)
            print(f"y+crop size goes out of the borders, changing it to '{y}'")

        # extract tile
        tile = image[:, y:y+size, x:x+size, :]

        # define cutting mask
        if mask is not None:
            cutting_mask = mask[:, y:y+size, x:x+size]
        else:
            cutting_mask = torch.zeros((1, size, size), dtype=torch.float32, device="cpu")

        return {"ui": {"images": results}, "result": (image, tile, cutting_mask, x, y, size)}

    @classmethod
    def IS_CHANGED(cls, image, mask, x, y, size):
        return True
        
class ImagePasteLoop:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source": ("IMAGE",),
                "cutting": ("IMAGE",),
                "x": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8, "defaultInput": True}),
                "y": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8, "defaultInput": True}),
            },
            "optional": {
                "cutting_mask": ("MASK", {"tooltip": "Optional cutting mask."}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "paste"
    CATEGORY = "LOOP"
    DESCRIPTION = "Replace a cutting in the original image."

    def paste(self, source, cutting, x, y, cutting_mask=None):
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
            if cutting_mask is None or cutting_mask.max() == 0:
                paste_image[:, y:y+paste_height, x:x+paste_width, :] = cutting[:, :paste_height, :paste_width, :]
            else:
                _, mask_height, mask_width = cutting_mask.shape  # (batch, H, W)
                if crop_height != mask_height or crop_width != mask_width:
                    raise ValueError("Mask and cropped image must have the same dimensions.")

                # adjust mask and cropped image if needed
                cutting = cutting[:, :paste_height, :paste_width, :]
                cutting_mask = cutting_mask[:, :paste_height, :paste_width]
                cutting_mask = cutting_mask.unsqueeze(-1)

                # normalize mask (between 0 and 1 values)
                cutting_mask = cutting_mask.float() / cutting_mask.max()

                # apply mask
                paste_image[:, y:y+paste_height, x:x+paste_width, :] = (
                    cutting * cutting_mask + paste_image[:, y:y+paste_height, x:x+paste_width, :] * (1 - cutting_mask)
                )

            return (paste_image,)

        except Exception as e:
            print(f"Error while pasting : {str(e)}")
            raise e

NODE_CLASS_MAPPINGS = {
    "LoadImageSimple": LoadImageSimple,
    "LoopImageSimple": LoopImageSimple,
    "SaveImageSimple": SaveImageSimple,
    "ImageCutLoop": ImageCutLoop,
    "ImageCropLoop": ImageCropLoop,
    "ImagePasteLoop": ImagePasteLoop
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageSimple": "Load Image (LOOP) DEPRECATED : use Loop Image instead",
    "LoopImageSimple": "Loop Image (LOOP)",
    "SaveImageSimple": "Save Image (LOOP)",
    "ImageCutLoop": "Cut Image (LOOP)",
    "ImageCropLoop": "Crop Image (LOOP)",
    "ImagePasteLoop": "Paste Image (LOOP)"
}