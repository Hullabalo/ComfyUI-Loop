# ComfyUI-Loop
ComfyUI-Loop is essentially a pair of nodes designed to create a simple image loop within your workflows. The operating principle is straightforward: the Save Image (LOOP) node saves an image by overwriting the file specified in the 'image path' field, making it automatically available for the next iteration. This functionality is primarily intended for inpainting workflows.

![alt text](https://github.com/Hullabalo/ComfyUI-Loop/blob/main/inpainting_loop(no_workflow).png?raw=true)

The current code is relatively basic, but special care has been taken to preserve image data quality and prevent degradation. Visually, there is no noticeable loss in quality even after 150 iterations, and ~~theoretically, this should~~(a) remain true after a thousand consecutive loops and saves.

01/07/25: Tired of writing paths? I added a browser button to the Image Loader (Be aware that for now it only load picture hosted in the 'output' folder). recreate the node in your graph if you run into problems.

01/05/25 update : The day after releasing the initial version on GitHub, I added two more nodes from my toolkit: Cut Image (LOOP) and Paste Image (LOOP). These nodes facilitate working with large images by cutting a specific part of an image, sending it to your inpainting workflow, KSampler, or other processes, and then pasting it back in place afterward. You can find an example workflow in the example_workflow folder.

![alt text](https://github.com/Hullabalo/ComfyUI-Loop/blob/main/cut_and_paste_example(no_workflow).png?raw=true)

**Install**

No additional dependencies are required. Search for 'Loop' in the ComfyUI Custom Nodes Manager or copy the ComfyUI-Loop folder into the Custom Nodes directory — and you're ready to go!

**Usage**
- in  Load Image (LOOP) node browse for an image from **output folder** (or feed the field with its name e.g. 'image.png'). **Always** work on a copy of your source file (if you don't want it to be overwritten).
- Connect the path output from Load Image (LOOP) to the image_path input of Save Image (LOOP).
- The mask input in Save Image (LOOP) is optional.
- Enable save steps if you want to keep a copy of the file at each iteration.

**Limitations**
- No support for image lists or batch inputs in 'Save Image (LOOP)'. If a list is provided, only the first image will be saved and displayed repeatedly.
- Mask format compatibility: If a mask is used, it must match the image format to be saved in the alpha channel. Otherwise, the output will be saved in RGB mode instead of RGBA.
- No preview in the 'Load Image (LOOP)' node (But you know what you’ve loaded, right? :) ). This design choice prevents ComfyUI from hanging when loading large 64Mpixels images :).
- Large file sizes due to uncompressed output for maximum quality preservation.

**Troubleshoot**

With KJNodes Resize Mask. If you get an error 'Cannot handle this data type: (1, 1, 1), |u1', do a Convert Mask to Image > KJNodes Resize Image > Convert Image to Mask as a workaround.

**Future plans**

This is an alpha version created in one evening. I plan to revisit the code later but it works well for basic use (I’m currently working on something else, smarter... but don't judge a fish by its ability to climb a tree, I will just do my best :D). If you encounter issues or have suggestions, ask on the repo ! :)

If you enjoy this project and want to help its development, leave a star or consider [buying me a coffee](https://buymeacoffee.com/hullabaloo) . your support makes a difference! ♥️

---
(a) Finally tested on 1000 loops, so you don’t have to wear out your SSD for proofing. A diff returns a perfectly black image in GIMP.

