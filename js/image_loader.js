import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "ImageLoader.FileButton",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass === "LoadImageSimple") {
            const onAdded = nodeType.prototype.onAdded;
            nodeType.prototype.onAdded = function() {
                const result = onAdded?.apply(this, arguments);

                const fileInput = document.createElement("input");
                fileInput.type = "file";
                fileInput.accept = "image/*";
                fileInput.style.display = "none";
                document.body.appendChild(fileInput);

                const widget = this.addWidget("button", "Browse output folder", "browse", () => {
                    fileInput.click();
                });

                fileInput.addEventListener("change", (event) => {
                    const file = event.target.files[0];
                    if (file) {
                        // Update the image widget with the name of the file
                        const widgets = this.widgets.filter(w => w.name === "image");
                        if (widgets.length > 0) {
                            widgets[0].value = file.name;
                            this.setDirtyCanvas(true, true);

                        }
                    }
                });
                return result;
            };
        }
    }
});
