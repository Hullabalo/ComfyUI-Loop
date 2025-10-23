import logging

logger = logging.getLogger(__name__)

class ErrorHandler:
    @staticmethod
    def handle_communication_error(error: Exception, context: str = ""):
        """
        Handle communication errors with proper logging
        """
        error_msg = f"Communication error in {context}: {str(error)}"
        logger.error(error_msg)        
        return error_msg
