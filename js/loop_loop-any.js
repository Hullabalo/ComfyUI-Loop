/* A simple image loop for your workflow. MIT License. version 0.2
https://github.com/Hullabalo/ComfyUI-Loop/
Thanks to rgthree, chrisgoringe, pythongosssss and many, many many others for their contributions, how-to's, code snippets etc.
 */

import { app } from "../../../scripts/app.js";

const NODES_LIST = ["LoopAny", "SaveAny"];
const FIXED_INPUTS = ["mask"];
const FIXED_OUTPUTS = ["path", "width", "height", "mask"];

app.registerExtension({
    name: "loop.LoopAny.InputOutput",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (!NODES_LIST.includes(nodeData.name)) return;

        // ============================================
        // 'any' input and output helper methods
        // ============================================

        nodeType.prototype.getDefaultLabelForType = type => type === "*" ? "any" : type;

        nodeType.prototype.updateInputTypeAndLabel = function(input, type, label) {
            input.type = type;
            input.label = label ?? this.getDefaultLabelForType(type);
            if (app.canvas?.default_connection_color_byType) {
                input.color_on = app.canvas.default_connection_color_byType[type];
            }
        };

        nodeType.prototype.updateOutputTypeAndLabel = function(output, type, label) {
            output.type = type;
            output.label = label ?? this.getDefaultLabelForType(output.type);
        };

        // Check if two types are incompatible (neither is wildcard and they differ)
        nodeType.prototype.areTypesIncompatible = (type1, type2) => 
            type1 !== type2 && type1 !== "*" && type2 !== "*";

        // Disconnect a target node's input if types are incompatible
        nodeType.prototype.disconnectIfIncompatible = function(targetNode, targetSlot, newType) {
            if (!targetNode?.inputs?.[targetSlot]) return false;
            
            const targetInput = targetNode.inputs[targetSlot];
            if (this.areTypesIncompatible(targetInput.type, newType)) {
                targetNode.disconnectInput(targetSlot);
                return true;
            }
            return false;
        };

        // ============================================
        // Widget Management (Proper disable/hide)
        // ============================================

        nodeType.prototype.manageLoopMaskWidget = function() {
            // Only manage widgets for LoopAny node
            if (this.type !== "LoopAny") return;
            
            const anyInput = this.inputs?.find(i => i.name === "input");
            if (!anyInput || !this.widgets) return;

            const hasConnection = anyInput.link != null;
            const shouldShowLoopMask = hasConnection && anyInput.label?.toUpperCase() === "IMAGE";
            
            const loopMaskWidget = this.widgets?.find(w => w.name === "loop_mask");
            const loopMaskInput = this.inputs?.find(i => i.name === "loop_mask");
            
            if (loopMaskWidget) {
                loopMaskWidget.hidden = !shouldShowLoopMask;
                
                // Handle the input connection point
                if (!shouldShowLoopMask && loopMaskInput) {
                    const index = this.inputs.findIndex(i => i.name === "loop_mask");
                    if (index !== -1) {
                        this.removeInput(index);
                    }
                }
                const size = this.computeSize();
                size[1] += 17;
                this.setSize(size);
            }
        };

        // ============================================
        // Dynamic Input/Output Management
        // ============================================

        nodeType.prototype.removeByName = function(collection, names, removeFn) {
            names.forEach(name => {
                const index = collection.findIndex(o => o.name === name);
                if (index !== -1) {
                    removeFn.call(this, index);
                }
            });
        };

        nodeType.prototype.manageInputOutputVisibility = function() {
            const anyInput = this.inputs?.find(i => i.name === "input");
            if (!anyInput) return;

            const hasConnection = anyInput.link != null;
            const hasOutputs = this.outputs?.length > 0;
            const hasMaskInput = this.inputs?.some(o => o.name === "mask");
            const shouldShowMask = hasConnection && anyInput.label?.toUpperCase() === "IMAGE";
            
            // Add/remove mask input according to 'guessed' type
            if (shouldShowMask && !hasMaskInput) {
                this.addInput("mask", "MASK");
            } else if (!shouldShowMask && hasMaskInput) {
                this.removeByName(this.inputs, ["mask"], this.removeInput);
            }
            
            // Only manage outputs if the node has them
            if (hasOutputs) {
                const hasMaskOutput = this.outputs?.some(o => o.name === "mask");
                const hasWidthOutput = this.outputs?.some(o => o.name === "width");
                const hasHeightOutput = this.outputs?.some(o => o.name === "height");

                const shouldShowDimensions = hasConnection && 
                    ["IMAGE", "MASK", "LATENT"].includes(anyInput.label?.toUpperCase());

                // Mask output (only for nodes with outputs)
                if (shouldShowMask && !hasMaskOutput) {
                    this.addOutput("mask", "MASK");
                } else if (!shouldShowMask && hasMaskOutput) {
                    this.removeByName(this.outputs, ["mask"], this.removeOutput);
                }

                // Width and height outputs
                if (shouldShowDimensions && !hasWidthOutput && !hasHeightOutput) {
                    if (!hasWidthOutput) this.addOutput("width", "INT");
                    if (!hasHeightOutput) this.addOutput("height", "INT");
                } else if (!shouldShowDimensions && (hasWidthOutput || hasHeightOutput)) {
                    this.removeByName(this.outputs, ["width", "height"], this.removeOutput);
                }

                // Force output order
                const orderMap = new Map(
                    ["output", ...FIXED_OUTPUTS].map((name, i) => [name, i])
                );
                this.outputs.sort((a, b) => 
                    (orderMap.get(a.name) ?? 999) - (orderMap.get(b.name) ?? 999)
                );
            }

            this.setSize?.(this.computeSize());
            this.manageLoopMaskWidget?.();
            
            // update visual connections
            if (app.canvas) {
                app.canvas.setDirty(true);
                app.canvas.draw(true, true);
            }
        };

        // ============================================
        // Reroute Node Handling (pysssss, rgthree and native reroute)
        // ============================================

        nodeType.prototype.updateRerouteNode = function(rerouteNode, slot, type, label) {
            const input = rerouteNode.inputs?.[slot];
            const output = rerouteNode.outputs?.[slot];
            
            if (!input || !output) return;

            // Update input and output types
            if (input.type !== type) {
                this.updateInputTypeAndLabel(input, type, label);
            }
            
            if (output.type !== type) {
                this.updateOutputTypeAndLabel(output, type, label);
                
                // Disconnect incompatible outputs
                const outputLinks = output.links ?? [];
                for (const outputLinkId of [...outputLinks]) {
                    const outputLink = app.graph.links?.[outputLinkId];
                    if (!outputLink) continue;
                    
                    const targetNode = app.graph.getNodeById(outputLink.target_id);
                    this.disconnectIfIncompatible(targetNode, outputLink.target_slot, type);
                }
            }
            
            rerouteNode.setDirtyCanvas(true, true);
        };

        // ============================================
        // Type Propagation
        // ============================================

        nodeType.prototype.propagateTypeToConnectedNode = function(linkId, type, label, visited, depth, maxDepth) {
            try {
                const graph = app.graph;
                if (!graph?.links) return;

                const link = graph.links[linkId];
                if (!link) return;

                const node = graph.getNodeById(link.target_id);
                if (!node) return;

                const targetSlot = link.target_slot;
                
                // Handle Reroute nodes
                if (node.type.includes("Reroute")) {
                    this.updateRerouteNode(node, targetSlot, type, label);
                    return;
                }

                // Handle nodes with updateChainType capability
                if (node.updateChainType) {
                    const targetInput = node.inputs?.[targetSlot];
                    if (targetInput) {
                        const typeChanged = targetInput.type !== type;
                        this.updateInputTypeAndLabel(targetInput, type, label);
                        
                        if (typeChanged && node.outputs?.[targetSlot]) {
                            node.updateChainType(targetSlot, type, label, visited, depth + 1, maxDepth);
                        }
                        node.setDirtyCanvas(true, true);
                        
                        // Trigger input/output visibility management for the downstream node
                        setTimeout(() => {
                            node.manageInputOutputVisibility?.();
                        }, 10);
                    }
                } else {
                    // Handle standard nodes --> disconnect if incompatible
                    this.disconnectIfIncompatible(node, targetSlot, type);
                }
            } catch (linkError) {
                console.warn('Error processing link in propagateTypeToConnectedNode:', linkError);
            }
        };

        nodeType.prototype.updateChainType = function(slot, type, label, visited = new Set(), depth = 0, maxDepth = 50) {
            try {
                if (depth > maxDepth) {
                    console.warn('Recursion depth exceeded in updateChainType');
                    return;
                }

                if (!this?.outputs?.length) return;
                
                if (visited.has(this.id)) return;
                visited.add(this.id);

                const output = this.outputs[slot];
                if (!output) return;
                
                // Do not relabel the fixed output if exists
                if (["mask", "width", "height"].includes(output.name)) return;

                // Update output type and label
                this.updateOutputTypeAndLabel(output, type, label);

                const graph = app?.graph;
                if (!graph?.links) return;

                const links = output.links ?? [];
                for (const linkId of [...links]) {
                    const link = graph.links?.[linkId];
                    if (!link) continue;
                    
                    const targetNode = graph.getNodeById(link.target_id);
                    
                    // Disconnect if incompatible, otherwise propagate
                    if (!this.disconnectIfIncompatible(targetNode, link.target_slot, type)) {
                        this.propagateTypeToConnectedNode(linkId, type, label, visited, depth, maxDepth);
                    }
                }
            } catch (e) {
                console.warn('Error in updateChainType:', e);
            }
        };

        // ============================================
        // Lifecycle Methods
        // ============================================

        const Configure = nodeType.prototype.configure ?? LGraphNode.prototype.configure;
        nodeType.prototype.configure = function() {
            this.configuring = true;
            const r = Configure?.apply(this, arguments);
            this.configuring = false;
            
            setTimeout(() => {
                this.inputs?.forEach((input, slot) => {
                    // Ignore fixed inputs
                    if (this.fixedInputs?.includes(input.name)) return;
                    
                    // If input is connected, simulate a connection change
                    if (input.link != null) {
                        const graph = app?.graph;
                        if (!graph?.links) return;
                        
                        const link = graph.links[input.link];
                        if (!link) return;
                        
                        const originNode = graph._nodes_by_id?.[link.origin_id];
                        const connectedType = originNode?.outputs?.[link.origin_slot]?.type;
                        
                        if (connectedType) {
                            const label = this.getDefaultLabelForType(connectedType);
                            
                            // input update (we don't change the type)
                            input.label = label;
                            if (app.canvas?.default_connection_color_byType) {
                                input.color_on = app.canvas.default_connection_color_byType[connectedType];
                            }
                            
                            // propagate the type to the node connected forward
                            if (this.outputs?.length && this.outputs[slot]) {
                                this.updateChainType(slot, connectedType, label, new Set(), 0, 50);
                            }
                        }
                    }
                });
                
                this.manageInputOutputVisibility?.();
            }, 10);
            
            return r;
        };

        // Init types from existing connections
        nodeType.prototype.initializeTypesFromConnections = function() {
            this.inputs?.forEach((input, inputSlot) => {
                // Ignore fixed inputs
                if (this.fixedInputs?.includes(input.name)) return;
                
                // if input is connected
                if (input.link != null) {
                    const graph = app?.graph;
                    if (!graph?.links) return;
                    
                    const link = graph.links[input.link];
                    if (!link) return;
                    
                    const originNode = graph._nodes_by_id?.[link.origin_id];
                    const connectedType = originNode?.outputs?.[link.origin_slot]?.type;
                    
                    if (connectedType) {
                        const label = this.getDefaultLabelForType(connectedType);
                        
                        // ONLY update the 'any' type in init (type === "*")
                        // allow further reconnections with different types
                        if (input.type === "*") {
                            input.type = connectedType;
                        }
                        
                        // ALWAYS update label and color
                        input.label = label;
                        if (app.canvas?.default_connection_color_byType) {
                            input.color_on = app.canvas.default_connection_color_byType[connectedType];
                        }
                        
                        // Propagate the type on node forward
                        if (this.outputs?.length && this.outputs[inputSlot]) {
                            this.updateChainType(inputSlot, connectedType, label, new Set(), 0, 50);
                        }
                    }
                }
            });
        };

        const OnConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function(side, slot, connect, link_info) {
            if (this.configuring) return;

            // Don't do anything to the fixed inputs
            if (FIXED_INPUTS.includes(this.inputs[slot]?.name)) {
                return OnConnectionsChange?.apply(this, arguments);
            }

            // Change only the 'any' input
            if (side === 1 && this.inputs) {
                const input = this.inputs[slot];
                
                if (connect && link_info) {
                    const connectedType = this.getConnectedOutputType(link_info);
                    
                    if (connectedType) {
                        // CRITICAL: we don't change input.type to allow reconnection with different node input types
                        // updating label and color only
                        input.label = this.getDefaultLabelForType(connectedType);
                        if (app.canvas?.default_connection_color_byType) {
                            input.color_on = app.canvas.default_connection_color_byType[connectedType];
                        }
                        
                        const label = this.getDefaultLabelForType(connectedType);
                        
                        // Only call updateChainType if the node has outputs
                        if (this.outputs?.length && this.outputs[slot]) {
                            this.updateChainType(slot, connectedType, label, new Set(), 0, 50);
                        }
                    }
                } else {
                    // Reset if disconnected
                    input.type = "*";
                    input.label = this.getDefaultLabelForType("*");
                    input.color_on = undefined;
                    
                    const label = this.getDefaultLabelForType("*");
                    
                    // Only call updateChainType if the node has outputs
                    if (this.outputs?.length && this.outputs[slot]) {
                        this.updateChainType(slot, "*", label, new Set(), 0, 50);
                    }
                }
                
                this.setDirtyCanvas(true, true);
            }

            const result = OnConnectionsChange?.apply(this, arguments);
            
            // inputs/outputs visibility after connection change
            if (side === 1) { // INPUT change
                setTimeout(() => {
                    this.manageInputOutputVisibility?.();
                }, 10);
            }
            return result;
        };

        // Helper to get the connected output type
        nodeType.prototype.getConnectedOutputType = link_info => {
            const graph = app?.graph;
            if (!graph?._nodes_by_id || !link_info.origin_id) return null;
            
            return graph._nodes_by_id[link_info.origin_id]?.outputs?.[link_info.origin_slot]?.type ?? null;
        };

        const OnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const r = OnNodeCreated ? OnNodeCreated.apply(this, arguments) : undefined;
            
            this.configuring = false;
            this.fixedInputs = this.fixedInputs ?? FIXED_INPUTS;
            this.fixedOutputs = this.fixedOutputs ?? FIXED_OUTPUTS;
            
            // Initialize inputs
            this.inputs?.forEach(input => {
                if (input.type === "*" && !input.label) {
                    input.label = this.getDefaultLabelForType(input.type);
                }
            });
            
            // Initialize outputs
            this.outputs?.forEach(output => {
                if (output.type === "*" && !output.label) {
                    output.label = this.getDefaultLabelForType(output.type);
                }
            });
            
            // Init inputs/outputs visibility
            setTimeout(() => {
                this.manageInputOutputVisibility?.();
            }, 10);
            
            return r;
        };

        const OnRemoved = nodeType.prototype.onRemoved ?? LGraphNode.prototype.onRemoved;
        nodeType.prototype.onRemoved = function() {
            delete this.configuring;
            return OnRemoved?.apply(this, arguments);
        };
    }
});