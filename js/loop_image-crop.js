/* A simple image loop for your workflow. MIT License. version 0.2
https://github.com/Hullabalo/ComfyUI-Loop/
Thanks to rgthree, chrisgoringe, pythongosssss and many, many many others for their contributions, how-to's, code snippets etc.
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Constants
const CONSTANTS = {
    NODE_NAME: "ImageCropLoop",
    EXTENSION_NAME: "Comfy.ImagePreviewNode",
    EVENT_NAME: "crop-bridge-proxy",
    API_ENDPOINT: "/api/bridge/response",
    WIDGET_NAMES: ["x", "y", "size", "color"],
    MIN_NODE_SIZE: 300,
    PREVIEW_HEIGHT: 300,
    MARGIN: 10,
    SIZE_INCREMENT: 8,
    DEFAULT_VALUES: {
        minSize: 256,
        maxSize: 2048
    }
};

// Utility functions
const Utils = {
    clamp: (val, min, max) => Math.min(Math.max(val, min), max),

    getImageBounds(img) {
        if (!img?.complete || img?.naturalWidth <= 0) return null;
        return { w: img.naturalWidth, h: img.naturalHeight };
    },

    calculateImageDimensions(img, availableWidth, availableHeight) {
        const imgW = img.naturalWidth;
        const imgH = img.naturalHeight;
        const scale = Math.min(availableWidth / imgW, availableHeight / imgH, 1);
        const scaledW = imgW * scale;
        const scaledH = imgH * scale;

        return { imgW, imgH, scale, scaledW, scaledH };
    },

    calculateMarkerBounds(widgetRefs, displayScale, scaledW, scaledH, previewScale) {
        const x = widgetRefs.x?.value ?? 0;
        const y = widgetRefs.y?.value ?? 0;
        const size = widgetRefs.size?.value ?? CONSTANTS.DEFAULT_VALUES.minSize;

        const markerSize = Math.min(size * displayScale, scaledW, scaledH);
        const markerX = Utils.clamp(x * displayScale, 0, scaledW - markerSize);
        const markerY = Utils.clamp(y * displayScale, 0, scaledH - markerSize);

        return { markerX, markerY, markerSize };
    },

    constructImageURL(filename) {
        return api.apiURL(
            `/view?filename=${encodeURIComponent(filename)}&type=temp&subfolder=`
        );
    },

    colorNameToRgba(colorName, alpha) {
        const colors = {
            red: "255, 0, 0",
            green: "0, 255, 0",
            blue: "0, 0, 255",
            black: "0, 0, 0",
            grey: "125, 125, 125"
        };
        const rgb = colors[colorName] ?? colors.red;
        return `rgba(${rgb}, ${alpha})`;
    },

    hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
};

// Event handler for crop bridge proxy
api.addEventListener(CONSTANTS.EVENT_NAME, (event) => {
    console.log('Image Crop - Received event:', event.detail);

    const { detail: data } = event;
    const nodeId = parseInt(data.id);
    const targetNode = app.graph.getNodeById(nodeId);

    targetNode?.updatePreview?.({
        filename: data.name,
        maskFilename: data.mask,
        scale: data.scale,
        original_width: data.original_width,
        original_height: data.original_height
    });
    // // Send a response to backend (commented out for now)
    // const reply = {
    //     id: data.id,
    //     modified_params: {
    //         x: targetNode?.widgetRefs?.x?.value ?? 128,
    //         y: targetNode?.widgetRefs?.y?.value ?? 64,
    //         size: targetNode?.widgetRefs?.size?.value ?? 512
    //     }
    // };

    // try {
    //     const response = await api.fetchApi(CONSTANTS.API_ENDPOINT, {
    //         method: "POST",
    //         headers: { "Content-Type": "application/json" },
    //         body: JSON.stringify(reply)
    //     });
        
    //     if (!response.ok) {
    //         console.error("Failed to send response to backend:", response.status);
    //     }
    // } catch (error) {
    //     console.error("Error sending response to backend:", error);
    // }
});

// Preview widget factory
const createPreviewWidget = (node) => ({
    name: "preview",
    type: "image_preview",
    value: "",
    height: CONSTANTS.PREVIEW_HEIGHT,
    serializeValue: () => undefined,

    draw(ctx, node, widgetWidth, y) {
        const img = this.previewImage;
        const availableWidth = widgetWidth - CONSTANTS.MARGIN * 2;
        const availableHeight = node.size[1] - y - CONSTANTS.MARGIN * 2;

        if (!img?.complete || img?.naturalWidth <= 0) {
            drawPlaceholder(ctx, widgetWidth, y);
            return;
        }

        drawImageWithMarker(ctx, node, img, availableWidth, availableHeight, y);
    }
});

const drawPlaceholder = (ctx, widgetWidth, y) => {
    ctx.fillStyle = "#666";
    ctx.font = "14px Arial";
    ctx.textAlign = "center";
    ctx.fillText("Waiting for image...", widgetWidth / 2, y + 40);
};

const drawImageWithMarker = (ctx, node, img, availableWidth, availableHeight, y) => {
    const dims = Utils.calculateImageDimensions(img, availableWidth, availableHeight);
    const imgX = CONSTANTS.MARGIN + (availableWidth - dims.scaledW) / 2;
    const imgY = y + CONSTANTS.MARGIN + (availableHeight - dims.scaledH) / 2;
    const colorValue = node.widgetRefs.color?.value ?? "black";
    const overlayColor = Utils.colorNameToRgba(colorValue, 0.5);

    const previewScale = node.previewData?.scale ?? 1.0;
    const displayScale = previewScale * dims.scale;

    node.imageArea = {
        x: imgX,
        y: imgY,
        width: dims.scaledW,
        height: dims.scaledH,
        scale: dims.scale,
        displayScale: displayScale,
        previewScale: previewScale
    };

    // Draw main image
    ctx.drawImage(img, imgX, imgY, dims.scaledW, dims.scaledH);

    // Draw mask overlay if available and show_mask is true
    const showMask = node.widgetRefs.show_mask?.value ?? false;
    if (showMask && node.previewWidget.previewMask) {
        drawMaskOverlay(ctx, node.previewWidget.previewMask, imgX, imgY, dims.scaledW, dims.scaledH);
    }

    // Draw crop rectangle marker
    const marker = Utils.calculateMarkerBounds(
        node.widgetRefs,
        displayScale,
        dims.scaledW,
        dims.scaledH,
        dims.scale
    );

    const markerAbsX = imgX + marker.markerX;
    const markerAbsY = imgY + marker.markerY;

    ctx.save();
    
    ctx.beginPath();
    ctx.rect(imgX, imgY, dims.scaledW, dims.scaledH);
    ctx.rect(markerAbsX + marker.markerSize, markerAbsY, -marker.markerSize, marker.markerSize);
    ctx.closePath();
    
    ctx.fillStyle = overlayColor;
    ctx.fill();
    
    ctx.restore();
};

const drawMaskOverlay = (ctx, maskImg, imgX, imgY, width, height) => {
    ctx.save();
    // ctx.globalAlpha = 0.8; // changing preview mask opacity made easy
    ctx.drawImage(maskImg, imgX, imgY, width, height);
    ctx.restore();
};

// Widget constraint handler
const setupWidgetConstraints = (node) => {
    const redraw = () => node.previewWidget?.parent?.graph?.setDirtyCanvas(true);

    CONSTANTS.WIDGET_NAMES.forEach(name => {
        const widget = node.widgetRefs[name];
        if (!widget) return;

        const originalCallback = widget.callback;
        let isUpdating = false;

        widget.callback = (val) => {
            if (isUpdating) return;
            isUpdating = true;

            try {
                const bounds = {
                    w: node.previewData?.original_width ?? node.previewWidget?.previewImage?.naturalWidth,
                    h: node.previewData?.original_height ?? node.previewWidget?.previewImage?.naturalHeight
                };
                
                const values = updateWidgetValues(node.widgetRefs, name, val, bounds);
                applyWidgetValues(node.widgetRefs, values);

                originalCallback?.call(widget, values[name]);

                redraw();
            } catch (err) {
                console.warn(`Error in widget ${name} callback:`, err);
            } finally {
                isUpdating = false;
            }
        };
    });

    // Setup show_mask widget observer
    const showMaskWidget = node.widgetRefs.show_mask;
    if (showMaskWidget) {
        const originalShowMaskCallback = showMaskWidget.callback;
        showMaskWidget.callback = (val) => {
            originalShowMaskCallback?.call(showMaskWidget, val);
            redraw();
        };
    }
};

const updateWidgetValues = (widgetRefs, changedWidget, newValue, bounds) => {
    const values = {
        x: widgetRefs.x?.value ?? 0,
        y: widgetRefs.y?.value ?? 0,
        size: widgetRefs.size?.value ?? CONSTANTS.DEFAULT_VALUES.minSize,
        [changedWidget]: newValue
    };

    if (bounds && bounds.w && bounds.h) {
        const { w: imgW, h: imgH } = bounds;

        values.size = Utils.clamp(
            values.size,
            CONSTANTS.DEFAULT_VALUES.minSize,
            Math.min(CONSTANTS.DEFAULT_VALUES.maxSize, imgW, imgH)
        );

        const maxX = imgW - values.size;
        const maxY = imgH - values.size;
        values.x = Utils.clamp(values.x, 0, maxX);
        values.y = Utils.clamp(values.y, 0, maxY);
    }

    return values;
};

const applyWidgetValues = (widgetRefs, values) => {
    widgetRefs.x && (widgetRefs.x.value = values.x);
    widgetRefs.y && (widgetRefs.y.value = values.y);
    widgetRefs.size && (widgetRefs.size.value = values.size);
};

const setupMouseHandler = (nodeType) => {
    const originalOnMouseDown = nodeType.prototype.onMouseDown;
    const originalOnMouseMove = nodeType.prototype.onMouseMove;
    const originalOnMouseUp = nodeType.prototype.onMouseUp;
    const originalOnMouseLeave = nodeType.prototype.onMouseLeave;

    nodeType.prototype.onMouseDown = function(e, localPos, graphCanvas) {
        const area = this.imageArea;
        const { x: xWidget, y: yWidget, size: sizeWidget } = this.widgetRefs ?? {};

        if (!isClickInImageArea(area, xWidget, yWidget, sizeWidget, localPos)) {
            return originalOnMouseDown?.call(this, e, localPos, graphCanvas);
        }

        if (e.button !== 0) {
            return originalOnMouseDown?.call(this, e, localPos, graphCanvas);
        }

        e.stopPropagation();
        e.preventDefault();

        this.isDraggingMarker = true;
        updateMarkerPosition(area, localPos, xWidget, yWidget, sizeWidget);
        return true;
    };

    nodeType.prototype.onMouseMove = function(e, localPos, graphCanvas) {
        if (this.isDraggingMarker && !(e.buttons & 1)) {
            this.isDraggingMarker = false;
        }

        if (this.isDraggingMarker) {
            const area = this.imageArea;
            const { x: xWidget, y: yWidget, size: sizeWidget } = this.widgetRefs ?? {};

            if (area && xWidget && yWidget && sizeWidget) {
                e.stopPropagation();
                e.preventDefault();
                
                updateMarkerPosition(area, localPos, xWidget, yWidget, sizeWidget);
                return true;
            }
        }

        const area = this.imageArea;
        if (area && localPos) {
            this.isMouseOverImage = isClickInImageArea(area, null, null, null, localPos);
        }

        return originalOnMouseMove?.call(this, e, localPos, graphCanvas);
    };

    nodeType.prototype.onMouseUp = function(e, localPos, graphCanvas) {
        if (this.isDraggingMarker) {
            this.isDraggingMarker = false;
            e.stopPropagation();
            e.preventDefault();
            return true;
        }

        return originalOnMouseUp?.call(this, e, localPos, graphCanvas);
    };

    nodeType.prototype.onMouseLeave = function(e, graphCanvas) {
        this.isDraggingMarker = false;
        this.isMouseOverImage = false;

        return originalOnMouseLeave?.call(this, e, graphCanvas);
    };
};

const isClickInImageArea = (area, xWidget, yWidget, sizeWidget, localPos) => {
    if (!area) return false;

    return localPos[0] >= area.x &&
           localPos[0] <= area.x + area.width &&
           localPos[1] >= area.y &&
           localPos[1] <= area.y + area.height;
};

const updateMarkerPosition = (area, localPos, xWidget, yWidget, sizeWidget) => {
    const relativeX = localPos[0] - area.x;
    const relativeY = localPos[1] - area.y;
    const markerSize = sizeWidget.value * area.displayScale;

    let markerX = relativeX - markerSize / 2;
    let markerY = relativeY - markerSize / 2;
    markerX = Utils.clamp(markerX, 0, area.width - markerSize);
    markerY = Utils.clamp(markerY, 0, area.height - markerSize);

    const origX = Math.round(markerX / area.displayScale);
    const origY = Math.round(markerY / area.displayScale);

    xWidget.value = origX;
    yWidget.value = origY;
    xWidget.callback?.(origX);
    yWidget.callback?.(origY);
};

const adjustSizeForNode = (node, delta) => {
    const sizeWidget = node.widgetRefs?.size;
    if (!sizeWidget) return;

    const bounds = {
        w: node.previewData?.original_width,
        h: node.previewData?.original_height
    };
    
    if (!bounds.w || !bounds.h) return;

    const maxSize = Math.min(CONSTANTS.DEFAULT_VALUES.maxSize, bounds.w, bounds.h);
    const newSize = Utils.clamp(sizeWidget.value + delta, CONSTANTS.DEFAULT_VALUES.minSize, maxSize);

    sizeWidget.value = newSize;
    sizeWidget.callback?.(newSize);

    app.graph.setDirtyCanvas(true, true);
};

const setupUpdatePreview = (nodeType) => {
    nodeType.prototype.updatePreview = function(imageInfo) {
        if (!this.previewWidget) {
            console.warn("Preview widget not found on node");
            return;
        }

        this.previewData = {
            scale: imageInfo.scale ?? 1,
            original_width: imageInfo.original_width,
            original_height: imageInfo.original_height
        };

        const url = Utils.constructImageURL(imageInfo.filename);
        console.log("Loading image from:", url);
        console.log("Preview data:", this.previewData);

        const img = new Image();

        img.onload = () => {
            this.previewWidget.previewImage = img;
            adjustNodeSize(this, img);
            refreshCanvas(this);
        };

        img.onerror = (e) => {
            console.error("Failed to load preview image:", url, e);
            this.previewWidget.previewImage = null;
            refreshCanvas(this);
        };

        img.src = url;

        if (imageInfo.maskFilename) {
            const maskUrl = Utils.constructImageURL(imageInfo.maskFilename);
            console.log("Loading mask from:", maskUrl);

            const maskImg = new Image();

            maskImg.onload = () => {
                this.previewWidget.previewMask = maskImg;
                console.log("Mask loaded successfully");
                refreshCanvas(this);
            };

            maskImg.onerror = (e) => {
                console.error("Failed to load mask image:", maskUrl, e);
                this.previewWidget.previewMask = null;
                refreshCanvas(this);
            };

            maskImg.src = maskUrl;
        } else {
            this.previewWidget.previewMask = null;
        }
    };
};

const adjustNodeSize = (node, img) => {
    if (!img?.naturalWidth || !img?.naturalHeight) return;

    if (node.defaultSize && 
        (node.size[0] !== node.defaultSize[0] || node.size[1] !== node.defaultSize[1])) {
        return;
    }

    const widgetWidth = node.size[0] - CONSTANTS.MARGIN * 2;
    const headerHeight = node.widgets_start_y ?? 0;
    const totalHeight = headerHeight + 512 + CONSTANTS.MARGIN * 3;
    const newHeight = Math.max(totalHeight, CONSTANTS.MIN_NODE_SIZE);

    if (Math.abs(node.size[1] - newHeight) > 2) {
        node.setSize([node.size[0], newHeight]);
        node.graph?.setDirtyCanvas(true, true);
    }
};

const refreshCanvas = (node) => {
    node?.graph?.setDirtyCanvas(true, true);
};

const setupNodeCreation = (nodeType) => {
    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

    nodeType.prototype.onNodeCreated = function() {
        const result = originalOnNodeCreated?.apply(this, arguments);

        this.widgetRefs = {
            x: this.widgets.find(w => w.name === "x"),
            y: this.widgets.find(w => w.name === "y"),
            size: this.widgets.find(w => w.name === "size"),
            color: this.widgets.find(w => w.name === "color"),
            show_mask: this.widgets.find(w => w.name === "show_mask")
        };

        this.previewWidget = this.addCustomWidget(createPreviewWidget(this));
        this.previewData = {
            scale: 1,
            original_width: 0,
            original_height: 0
        };

        this.setSize([
            Math.max(this.size[0], CONSTANTS.MIN_NODE_SIZE),
            Math.max(this.size[1], CONSTANTS.MIN_NODE_SIZE)
        ]);
        
        this.defaultSize = [...this.size];
        setupWidgetConstraints(this);
        this.isMouseOverImage = false;

        return result;
    };
};

app.registerExtension({
    name: CONSTANTS.EXTENSION_NAME,

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== CONSTANTS.NODE_NAME) return;

        setupNodeCreation(nodeType);
        setupMouseHandler(nodeType);
        setupUpdatePreview(nodeType);

        const originalOnRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function() {
            return originalOnRemoved?.apply(this, arguments);
        };
    },

    commands: [
        {
            id: "ImageCropLoop.increaseSize",
            label: "Increase Marker Size",
            function: () => {
                const node = app.graph._nodes.find(n => 
                    n.type === CONSTANTS.NODE_NAME && n.isMouseOverImage
                );
                node && adjustSizeForNode(node, CONSTANTS.SIZE_INCREMENT);
            }
        },
        {
            id: "ImageCropLoop.decreaseSize",
            label: "Decrease Marker Size",
            function: () => {
                const node = app.graph._nodes.find(n => 
                    n.type === CONSTANTS.NODE_NAME && n.isMouseOverImage
                );
                node && adjustSizeForNode(node, -CONSTANTS.SIZE_INCREMENT);
            }
        }
    ],

    keybindings: [
        {
            combo: { key: "PageUp" },
            commandId: "ImageCropLoop.increaseSize"
        },
        {
            combo: { key: "PageDown" },
            commandId: "ImageCropLoop.decreaseSize"
        }
    ]
});