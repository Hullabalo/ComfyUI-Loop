import os

class LoopStringUtils:
    """Utility class for string and text files management"""

    @staticmethod
    def load_or_create_text_file(input: str | int |float, path: str, load: bool = True) -> str:
        """
        Load an existing text file or create it.
        """
        if os.path.exists(path) and load:
            return LoopStringUtils.load_text_file(path)
        else:
            if input is None:
                input = ""
            LoopStringUtils.save_text_file(input, path)
            return input

    @staticmethod
    def load_text_file(path: str) -> str | None:
        """
        Load an existing text file and return its content.
        """
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content

    @staticmethod
    def save_text_file(input: str | int | float, path: str) -> str:
        """
        Save a text file and return input path.
        """
        if isinstance(input, (int, float)):
            input = str(input)
        with open(path, "w", encoding="utf-8") as f:
            f.write(input)
        return path
