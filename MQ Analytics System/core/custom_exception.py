# =====================================================
# ✅ CUSTOM EXCEPTION HANDLING
# =====================================================
import traceback
import sys

class CustomException(Exception):

    def __init__(self, error_message, error_detail: sys):
        super().__init__(error_message)
        self.error_message = self.get_detailed_error_message(error_message, error_detail)

    @staticmethod
    def get_detailed_error_message(error_message, error_detail: sys):
        _, _, exc_tb = error_detail.exc_info()
        
        # Guard against None traceback in cases where exception wasn't actually raised
        if exc_tb is None:
            return f"Error: {error_message}"
            
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno

        return f"Error in {file_name}, line {line_number}: {error_message}"
    
    def __str__(self):
        return self.error_message
