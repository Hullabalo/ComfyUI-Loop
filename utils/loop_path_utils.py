from pathlib import Path
import shutil

class LoopPathUtils:
    """Utility class for files and path management"""

    @staticmethod
    def parse_path(full_path: str, base_dir: str) -> tuple[str | None, str | None, str | None]:
        """
        Given a full path, returns filename, relative_subfolders, base_path.
        """
        try:
            full_path = Path(full_path)
            filename = full_path.name
            parent_dir = full_path.parent

            parts = parent_dir.parts
            if base_dir in parts:
                base_index = parts.index(base_dir)
                base_path = Path(*parts[:base_index + 1])
                relative = parent_dir.relative_to(base_path)
            else:
                base_path = parent_dir
                relative = Path("")

            return filename, str(relative) if str(relative) != '.' else '', str(base_path)
        except Exception:
            return None, None, None

    @staticmethod
    def copy_tree(source: str, dest: str) :
        """
        Copy relative source folder content to relative dest folder. I.E. ComfyUI folder as base folder
        """
        source = Path.cwd() / source
        dest = Path.cwd() /dest

        try:
            shutil.copytree(source, dest, dirs_exist_ok=True)
        except FileNotFoundError:
            print(f"Error: Cannot find source directory")
        except Exception as e:
            print(f"Error while copying: {e}")