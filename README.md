Custom ComfyUI nodes for interactive image manipulation and flexible file looping. Provides four specialized nodes for cropping, pasting, looping, and saving various file types with preview capabilities.

ComfyUI-Loop is essentially a pair of nodes designed to create a simple file loop within your workflows. The operating principle is straightforward: the Save Any node saves an image by overwriting the file specified in the 'path' field, making it automatically available for the next iteration. This functionality is primarily intended for inpainting workflows.

# 0.2 version - last changes 10/23/2025 :
Better integration with last ComfyUI version. Better code structure.
- Now there's only four nodes for two main usages, looping files and visual cutting-pasting: 
  LoopAny -> SaveAny
  loop any file type : image (png), mask (png), latent (image/audio/whatever), audio (flac), string (or int/float) saved as text file.

  ImageCrop -> ImagePaste
  ImageCrop now works with last Comfy frontend, lastly tested with ComfyUI v0.3.64, ComfyUI_Frontend v1.27.10

TL;DR : Revisited code from A to Z. Crop your images and masks, loop your files, the fun way.

[loop_and_paste.webm](https://github.com/user-attachments/assets/83c2a7b8-c854-4681-9773-8110bdd753aa)

## ♾️ Image Crop
**Functionality:** Interactive image cropping with live preview. Supports some keyboard controls (PageUp/Down to resize).

**Inputs:**
| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `image` | IMAGE | - | - | Source image to crop |
| `x` | INT | 0 | 0-32768 | X-origin of crop rectangle |
| `y` | INT | 0 | 0-32768 | Y-origin of crop rectangle |
| `size` | INT | 512 | 256-2048 | Crop size (increments of 8) |
| `color` | LIST | "black" | ["black","grey","red","green","blue"] | Preview rectangle color |
| `show_mask` | boolean | True | - | show binary mask preview |
| `mask` | MASK | - | - | Optional mask (alpha channel) |

**Outputs:**
- `source`: Original image
- `cut`: Cropped image
- `size`: crop size used
- `x`: X-position used
- `y`: Y-position used
- `cut_mask`: Cropped mask

---

## ♾️ Paste Image
**Functionality:** Pastes cropped images onto source images with optional masking/blending.

**Inputs:**
| Parameter | Description |
|-----------|-------------|
| `source` | Base image to paste onto |
| `cut` | Image segment to paste |
| `x` | X-position for pasting |
| `y` | Y-position for pasting |
| `cut_mask` | Optional mask for blending |

**Outputs:**
- `image`: final image

---
[loop_and_save_any.webm](https://github.com/user-attachments/assets/d6e1c707-8403-419d-91ff-b470b1599d01)

## ♾️ Loop Any
**Functionality:** Loops various file types (images, masks, latents, audio, text) from ComfyUI's output directory or one of its subfolders

**Inputs:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input` | ANY | - | Input data to process/loop |
| `loop_file` | BOOL | False | Enable file looping mode |
| `filename` | STRING | "loop_file" | Base filename (no extension) |
| `subfolder` | STRING | "" | Output subdirectory |
| `loop_mask` | BOOL | False | Enable mask looping ( load mask from loop image alpha channel instead of mask input|
| `mask` | MASK | - | Optional input mask (conditional : image input)|

**Outputs:**
- `output`: Processed output data
- `path`: Full file path
- `width`: Output width (conditional : image/mask/latent input)
- `height`: Output height (conditional : image/mask/latent input)
- `mask`: optional mask to send to Save Any node, for saving as alpha channel (conditional : image input)

---

## ♾️ Save Any
**Functionality:** Saves various data types to 'path' directory with optional versioned backups and optional preview.

**Inputs:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input` | ANY | - | Data to save |
| `path` | STRING | "/path/to/file.ext" | Full output path |
| `save_steps` | BOOL | False | Save timestamped copies |
| `mask` | MASK | - | Optional mask (for images) |

**Saving Formats:**
- Images: `.png`
- Masks: `.png`
- Latents: `.latent`
- Audio: `.flac`
- Text: `.txt`
---

## Install
No additional dependencies are required. Search for 'Loop' in the ComfyUI Custom Nodes Manager or copy the ComfyUI-Loop folder into the Custom Nodes directory — and you're ready to go!

## Usage
Have a look at the example workflow (json or .png), for up to date informations on usage and a working example.
- in  Load Image (LOOP) node browse for an image from **output folder** (or feed the field with its name e.g. 'image.png'). **Always** work on a copy of your source file (if you don't want it to be overwritten).
- Connect the path output from Load Image (LOOP) to the image_path input of Save Image (LOOP).
- The mask input in Save Image (LOOP) is optional.
- Enable save steps if you want to keep a copy of the file at each iteration.

## Limitations
- No support for lists or batch inputs.
- Not as user friendly as I want it to be out of the box (some small lacks in code to fix later.)

## Future plans
- adding some kind of mask edit capabilities in the 'Image Crop' node
- more file format outputs
- Better code, without changing the developer ahah

I plan to revisit the code later but it works well for basic use (don't judge a fish by its ability to climb a tree, I do my best :D). 
If you encounter issues or have suggestions, ask on the repo ! :)

If you enjoy this project and want to boost its development, just leave a star (I eat them) : your support makes a difference! ♥️

**MIT License. version 0.2**
https://github.com/Hullabalo/ComfyUI-Loop/
Thanks to rgthree, chrisgoringe, pythongosssss and many, many many others for their contributions, how-to's, code snippets etc.

## Image Attribution
Icons from `/icons` directory Icons are based on icon set from PAOMedia :
https://www.iconfinder.com/paomedia/icon-sets
and licensed under [Creative Commons Attribution 3.0 Unported] (https://creativecommons.org/licenses/by/3.0/deed.en).

All other images in video and examples are CC0 (wikimedia commons)
