# ComfyUI-Loop
A pair of nodes to create a simple loop in your workflows. The operating principle is quite straightforward: the image saved by the 'Save Image (LOOP)' node overwrites the image specified in the 'image path' field, allowing it to be automatically reloaded in the next iteration. Aimed essentially for inpainting.

![alt text](https://github.com/Hullabalo/ComfyUI-Loop/blob/main/inpainting_loop.png?raw=true)

The code is fairly basic, but special care was taken to protect the image data to prevent degradation. Visually, there is no loss in quality after 150 iterations. Theoretically, the same result should hold even after a thousand successive loops/saves.

**Usage**
- feed image path with /path/to/image.ext (png, jpg, gif, tiff... :)) in 'Load Image (Loop)' Node
- Connect path output to 'Save Image (Loop)' image_path input
- 'mask' input is optional in 'Save Image (LOOP)' node
- Set 'save steps' to true if you want to keep a copy of the saved file at each iteration.

**Limitations**
- No support for image lists or batch as input for 'Save Image (LOOP)'. If a list is provided, only the first image will be saved and displayed n times
- If a mask is present, it must match the image format to be saved in the alpha channel of the output image. Otherwise, your image will be saved in RGB mode instead of RGBA.
- No preview available in the 'Load Image' node (Incidentally, you know what you’ve loaded, right? :) )
- No preview in the 'Save Image' node if the image is located outside the output folder.
- Huge file size, because of uncompressed file and quality

**Install**
- No additional dependencies.  Search 'Loop' in Comfy custom nodes Manager, or copy the ComfyUI-Loop folder into Custom Nodes and that's it.

**Future plans**

This is an alpha version put together in one evening. I will revisit the code later, for now, it works as expected at least for my usage. But if you need something more, feel free to ask :)
