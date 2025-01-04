# ComfyUI-Loop
A pair of nodes to create a simple loop in your workflows. The operating principle is quite straightforward: the image saved by the 'Save Image (LOOP)' node overwrites the image specified in the 'image path' field, allowing it to be automatically reloaded in the next iteration.

![alt text](https://github.com/Hullabalo/ComfyUI-Loop/blob/main/snappy_snap.png?raw=true)

The code is fairly basic, but special care was taken to protect the image data to prevent degradation. Visually, there is no loss in quality after 150 iterations. Theoretically, the same result should hold even after a thousand successive saves.

**Usage**
- feed image path with a full /path/to/image.png in 'Load Image (Loop)' Node
- Connect path output to 'Save Image (Loop)' image_path input
- 'mask' input is optional in 'Save Image (LOOP)' node
- Set 'save steps' to true if you want to keep a copy of the saved file at each iteration.

**Limitations**

- No support for image lists as input for 'Save Image (LOOP)'. If provided, only the first image will be saved and displayed.
- If a mask is present, it must match the image format to be saved in the alpha channel of the output image. Otherwise, an error message will appear in the console, and your image will be returned in RGB mode instead of RGBA.
- No preview available in the 'Load Image' node (theoretically, you know what you’ve loaded, right? :) )
- No preview in the 'Save Image' node if the image is located outside the output folder.
- Huge file size, because of uncompressed file and quality
- No jpeg files in the loop at the moment. Use png instead.

**Install**
- No additional dependencies. Copy the ComfyUI-Loop folder into Custom Nodes and that's it.

**Future plans**

This is an alpha version put together in one evening. I will revisit the code later, but for now, it works as expected.
