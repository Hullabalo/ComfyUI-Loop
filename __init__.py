from .nodes import *
from .utils.loop_path_utils import LoopPathUtils

# copy preview icons
LoopPathUtils.copy_tree("custom_nodes/ComfyUI-CustomPreviewOnNode/icons", "temp")

WEB_DIRECTORY = "js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
