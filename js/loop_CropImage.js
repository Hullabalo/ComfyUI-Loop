import { app } from "../../../scripts/app.js";
import { $el } from "../../../scripts/ui.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "loop.clickCrop",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass !== "ImageCropLoop") return;

        const DEFAULT_DIMENSIONS = {
            WIDTH: 200,
            HEIGHT: 200,
            MARGIN: 0,
            TITLE_HEIGHT: 24
        };

        class CoordinateConverter {
            /* Core class that handles coordinate transformations */
            constructor(originalDimensions) {
                this.originalDimensions = originalDimensions;
                this.previewDimensions = { width: 0, height: 0 };
            }
        
            toOriginalCoords(previewX, previewY, frame) {
                /* Converts preview coordinates to original image coordinates */
                if (!this.isValidDimensions()) return [previewX, previewY];
                
                const scaleX = this.originalDimensions.width / frame.width;
                const scaleY = this.originalDimensions.height / frame.height;
                
                return [
                    Math.round(previewX * scaleX),
                    Math.round(previewY * scaleY)
                ];
            }
        
            toPreviewCoords(originalX, originalY, frame) {
                /* Converts original coordinates to preview coordinates */
                if (!this.isValidDimensions()) return [originalX, originalY];
                
                const scaleX = frame.width / this.originalDimensions.width;
                const scaleY = frame.height / this.originalDimensions.height;
                
                return [
                    Math.round(originalX * scaleX),
                    Math.round(originalY * scaleY)
                ];
            }
        
            toOriginalSize(previewSize, frame) {
                /* Converts preview size to original image size */
                if (!this.isValidDimensions()) return previewSize;
                return Math.round(previewSize * (this.originalDimensions.width / frame.width));
            }
        
            toPreviewSize(originalSize, frame) {
                /* Converts original size to preview size */
                if (!this.isValidDimensions()) return originalSize;
                // First, ensure originalSize doesn't exceed original image dimensions
                const maxOriginalSize = Math.min(originalSize, this.originalDimensions.width);
                return Math.round(maxOriginalSize * (frame.width / this.originalDimensions.width));
            }
        
            constrainOriginalCoords(x, y, size) {
                /* Ensures coordinates stay within image bounds */
                if (!this.isValidDimensions()) return [x, y];
                
                // Ensure size doesn't exceed original dimensions
                const constrainedSize = Math.min(size, this.originalDimensions.width);
                
                const maxX = Math.max(0, this.originalDimensions.width - constrainedSize);
                const maxY = Math.max(0, this.originalDimensions.height - constrainedSize);
                
                return [
                    Math.max(0, Math.min(x, maxX)),
                    Math.max(0, Math.min(y, maxY))
                ];
            }
        
            isValidDimensions() {
                return this.originalDimensions?.width && this.originalDimensions?.height;
            }
        
            updateDimensions(originalWidth, originalHeight, previewWidth, previewHeight) {
                this.originalDimensions = { width: originalWidth, height: originalHeight };
                this.previewDimensions = { width: previewWidth, height: previewHeight };
            }
        }

        // Define ClickCropWidget class inside the extension scope
        class ClickCropWidget {
            /* Handles the visual interface */
            constructor(node) {
                this.node = node;
                this.type = "HTML";
                this.name = "clickableFrame";
                this.value = null;

                // this.originalOnMouseEnter = node.onMouseEnter;
                // this.originalOnMouseLeave = node.onMouseLeave;
        
                // node.onMouseEnter = (e, pos) => {
                //     if (this.node) {
                //         this.node.flags = this.node.flags || {};
                //         this.node.flags.pinned = true;
                //         app.graph.setDirtyCanvas(true, false);
                //     }
                //     if (this.originalOnMouseEnter) {
                //         this.originalOnMouseEnter.call(node, e, pos);
                //     }
                // };
        
                // node.onMouseLeave = (e, pos) => {
                //     if (this.node) {
                //         this.node.flags = this.node.flags || {};
                //         this.node.flags.pinned = false;
                //         app.graph.setDirtyCanvas(true, false);
                //     }
                //     if (this.originalOnMouseLeave) {
                //         this.originalOnMouseLeave.call(node, e, pos);
                //     }
                // };
            }

            draw(ctx, node, widget_width, y, widget_height) {
                /* Main rendering function for the widget */
                if (!this.isValidImage(node)) return;

                this.updateOriginalDimensions(node);
                const frame = this.calculateFrame(y, node.size[0], node.size[1]);
                node.frameArea = frame;

                this.drawFrame(ctx, frame);
                this.drawMarker(ctx, node, frame);
            }

            isValidImage(node) {
                return node.imgs?.[0]?.width && node.imgs?.[0]?.height;
            }

            updateOriginalDimensions(node) {
                const img = node.imgs[0];
                const match = img.src.match(/_(\d+)_(\d+)_/);
                if (match) {
                    node.converter.updateDimensions(parseInt(match[1]), parseInt(match[2]));
                    this.updateMarkerPosition(node);
                }
            }

            calculateFrame(y, nodeWidth, nodeHeight) {
                /* Determines the frame dimensions and position */
                const TITLE_HEIGHT = 24;
                const img = this.node.imgs[0];
                
                const availWidth = nodeWidth;
                const availHeight = nodeHeight - TITLE_HEIGHT - y;
                
                const imgRatio = img.naturalWidth / img.naturalHeight;
                const containerRatio = availWidth / availHeight;
                
                let frameWidth, frameHeight;
                if (containerRatio > imgRatio) {
                    frameHeight = availHeight;
                    frameWidth = frameHeight * imgRatio;
                } else {
                    frameWidth = availWidth;
                    frameHeight = frameWidth / imgRatio;
                }
                
                return {
                    left: (availWidth - frameWidth) / 2,
                    top: y + TITLE_HEIGHT + (availHeight - frameHeight) / 2,
                    width: frameWidth,
                    height: frameHeight
                };
            }

            drawFrame(ctx, frame) {
                /* Renders the frame border */
                // ctx.strokeStyle = "#ff7500";
                ctx.strokeStyle = "green";
                ctx.lineWidth = 1;
                ctx.strokeRect(frame.left, frame.top, frame.width, frame.height);
            }

            drawMarker(ctx, node, frame) {
                /* Renders the selection marker */
                if (!node.clickMarker) return;
                
                const previewSize = node.converter.toPreviewSize(
                    node.widgets.find(w => w.name === 'size').value, 
                    frame
                );
                ctx.strokeStyle = "green";
                ctx.lineWidth = 1;
                ctx.strokeRect(
                    node.clickMarker.x,
                    node.clickMarker.y,
                    previewSize,
                    previewSize
                );
            }

            updateMarkerPosition(node) {
                /* Updates marker position when coordinates change */
                const frame = node.frameArea;
                if (!node.clickMarker || !frame) return;

                const xWidget = node.widgets.find(w => w.name === 'x');
                const yWidget = node.widgets.find(w => w.name === 'y');
                
                const [newPreviewX, newPreviewY] = node.converter.toPreviewCoords(
                    xWidget.value, 
                    yWidget.value, 
                    frame
                );
                node.clickMarker.x = frame.left + newPreviewX;
                node.clickMarker.y = frame.top + newPreviewY;
            }
        }

        nodeType.prototype.setupNode = function() {
            /* Initializes the node with default values and widgets */
            this.converter = new CoordinateConverter({ width: 0, height: 0 });
            this.size = [DEFAULT_DIMENSIONS.WIDTH, DEFAULT_DIMENSIONS.HEIGHT];
            
            const widgets = {
                x: this.widgets.find(w => w.name === 'x'),
                y: this.widgets.find(w => w.name === 'y'),
                size: this.widgets.find(w => w.name === 'size')
            };

            this.setupWidgetCallbacks(widgets);
            this.addCustomWidget(new ClickCropWidget(this));
            this.setupMouseHandler(widgets);

            this.serialize_widgets = false;
        };

        nodeType.prototype.initializeMarker = function(frame, widgets) {
            /* Initializes the marker with default values and widgets */
            if (!frame) return;
            const { x: xWidget, y: yWidget, size: sizeWidget } = widgets;
            
            // Apply initial constraints
            const [constrainedX, constrainedY] = this.converter.constrainOriginalCoords(
                xWidget.value,
                yWidget.value,
                sizeWidget.value
            );
            
            // Update widget values
            xWidget.value = constrainedX;
            yWidget.value = constrainedY;
            
            // Convert to preview coordinates
            const [previewX, previewY] = this.converter.toPreviewCoords(
                constrainedX,
                constrainedY,
                frame
            );
            
            // Create marker
            this.clickMarker = {
                x: frame.left + previewX,
                y: frame.top + previewY
            };
            
            this.setDirtyCanvas(true);
        };        

        nodeType.prototype.setupWidgetCallbacks = function(widgets) {
            /* Sets up event handlers for widget value changes */
            const { x: xWidget, y: yWidget, size: sizeWidget } = widgets;
        
            // Size widget callback with dynamic coordinate updates
            sizeWidget.callback = function(value) {
                const frame = this.frameArea;
                if (!frame) return;
        
                // Constrain size to original image dimensions
                const maxSize = Math.min(this.converter.originalDimensions.width, this.converter.originalDimensions.height);

                const constrainedValue = Math.min(value, maxSize);
        
                // Round to nearest multiple of 8
                const roundedValue = Math.round(constrainedValue / 8) * 8;
                if (value !== roundedValue) {
                    sizeWidget.value = roundedValue;
                    this.onSizeChange(roundedValue, frame, widgets);
                    return;
                }
        
                if (!this.clickMarker) {
                    this.initializeMarker(frame, widgets);
                } else {
                    this.onSizeChange(roundedValue, frame, widgets);
                }
            }.bind(this);
        
            // X and Y widget callbacks with floor to ensure integer values
            const createAutoMarkerCallback = (axis) => {
                /* Creates handler for marker changes */
                return function(value) {
                    const frame = this.frameArea;
                    if (!frame) return;
        
                    // Ensure integer values
                    const intValue = Math.floor(value);
                    if (value !== intValue) {
                        if (axis === 'x') {
                            xWidget.value = intValue;
                        } else {
                            yWidget.value = intValue;
                        }
                        value = intValue;
                    }
        
                    if (!this.clickMarker) {
                        this.initializeMarker(frame, widgets);
                    } else {
                        this.createCoordinateCallback(axis, xWidget, yWidget, sizeWidget).call(this, value);
                    }
                }.bind(this);
            };
        
            xWidget.callback = createAutoMarkerCallback('x');
            yWidget.callback = createAutoMarkerCallback('y');
        };

        nodeType.prototype.onSizeChange = function(newSize, frame, widgets) {
            /* Handles size change events */
            const { x: xWidget, y: yWidget, size: sizeWidget } = widgets;
            
            if (!frame || !this.converter.isValidDimensions()) return;
        
            // Get current original coordinates
            let currentX = Math.floor(xWidget.value);
            let currentY = Math.floor(yWidget.value);
        
            // Apply constraints with new size
            const [constrainedX, constrainedY] = this.converter.constrainOriginalCoords(
                currentX,
                currentY,
                newSize
            );
        
            // Update widget values if they were constrained
            if (currentX !== constrainedX || currentY !== constrainedY) {
                xWidget.value = constrainedX;
                yWidget.value = constrainedY;
            }
        
            // Convert to preview coordinates and update marker
            const [previewX, previewY] = this.converter.toPreviewCoords(
                constrainedX,
                constrainedY,
                frame
            );
        
            this.clickMarker = {
                x: frame.left + previewX,
                y: frame.top + previewY
            };
        
            this.setDirtyCanvas(true);
        };

        nodeType.prototype.createCoordinateCallback = function(axis, xWidget, yWidget, sizeWidget) {
            /* Creates handlers for coordinate changes */
            return function(value) {
                const frame = this.frameArea;
                if (!frame || !this.clickMarker) return;

                // Ensure integer values for coordinates
                const currentCoords = axis === 'x' 
                    ? [Math.floor(value), Math.floor(yWidget.value)] 
                    : [Math.floor(xWidget.value), Math.floor(value)];

                const [constrainedX, constrainedY] = this.converter.constrainOriginalCoords(
                    ...currentCoords, 
                    sizeWidget.value
                );

                const updatedValue = axis === 'x' ? constrainedX : constrainedY;
                if (value !== updatedValue) {
                    if (axis === 'x') xWidget.value = updatedValue;
                    else yWidget.value = updatedValue;
                    return;
                }

                const [previewX, previewY] = this.converter.toPreviewCoords(
                    axis === 'x' ? constrainedX : xWidget.value,
                    axis === 'y' ? constrainedY : yWidget.value,
                    frame
                );

                const markerSize = this.converter.toPreviewSize(sizeWidget.value, frame);
                this.clickMarker.x = frame.left + (axis === 'x' ? previewX : this.clickMarker.x - frame.left);
                this.clickMarker.y = frame.top + (axis === 'y' ? previewY : this.clickMarker.y - frame.top);

                this.setDirtyCanvas(true);
            }.bind(this);
        };

        nodeType.prototype.createSizeCallback = function(xWidget, yWidget, sizeWidget) {
            /* Creates handler for size changes */
            return function(value) {
                const frame = this.frameArea;
                if (!frame || !this.clickMarker) return;
        
                // Get current original coordinates
                const [origX, origY] = this.converter.toOriginalCoords(
                    this.clickMarker.x - frame.left,
                    this.clickMarker.y - frame.top,
                    frame
                );
        
                // Constrain coordinates with new size value
                const [constrainedX, constrainedY] = this.converter.constrainOriginalCoords(origX, origY, value);
                
                // Update x and y widgets if they were constrained
                if (xWidget.value !== constrainedX) xWidget.value = constrainedX;
                if (yWidget.value !== constrainedY) yWidget.value = constrainedY;
        
                // Convert back to preview coordinates
                const [previewX, previewY] = this.converter.toPreviewCoords(constrainedX, constrainedY, frame);
                
                // Update marker position
                this.clickMarker.x = frame.left + previewX;
                this.clickMarker.y = frame.top + previewY;
                
                this.setDirtyCanvas(true);
            }.bind(this);
        };

        nodeType.prototype.setupMouseHandler = function(widgets) {
            /* Handles mouse interactions for selection */
            this.onMouseDown = (e, pos) => {
                const frame = this.frameArea;
                if (!frame || 
                    pos[0] < frame.left || pos[0] > frame.left + frame.width ||
                    pos[1] < frame.top || pos[1] > frame.top + frame.height) return;

                const { x: xWidget, y: yWidget, size: sizeWidget } = widgets;
                const relativeX = pos[0] - frame.left;
                const relativeY = pos[1] - frame.top;
                
                const previewSize = this.converter.toPreviewSize(sizeWidget.value, frame);
                const markerX = Math.max(0, Math.min(relativeX - previewSize / 2, frame.width - previewSize));
                const markerY = Math.max(0, Math.min(relativeY - previewSize / 2, frame.height - previewSize));
                
                const [origX, origY] = this.converter.toOriginalCoords(markerX, markerY, frame);
                const [constrainedX, constrainedY] = this.converter.constrainOriginalCoords(origX, origY, sizeWidget.value);
                
                xWidget.value = constrainedX;
                yWidget.value = constrainedY;
                
                const [previewX, previewY] = this.converter.toPreviewCoords(constrainedX, constrainedY, frame);
                this.clickMarker = { x: frame.left + previewX, y: frame.top + previewY };
                this.setDirtyCanvas(true);
            };
        };

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function() {
            onNodeCreated?.apply(this, arguments);
            this.setupNode();
        };
    }
});


