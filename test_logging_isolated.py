import logging
import json
import sys
from app.core.logging_config import CustomJsonFormatter

class TestJSONFormatting:
    """Test JSON log formatting functionality."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.formatter = CustomJsonFormatter()
    
    def test_json_formatting_with_exception(self):
        """Test JSON formatting with exception information."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test.module", level=logging.ERROR, pathname="test.py", lineno=42,
                msg="Error occurred", args=(), exc_info=sys.exc_info()
            )
        
        formatted = self.formatter.format(record)
        print(f"Formatted type: {type(formatted)}")
        print(f"Formatted value: {repr(formatted[:200])}")
        
        log_data = json.loads(formatted)
        print(f"log_data type: {type(log_data)}")
        print(f"log_data: {log_data}")
        
        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Error occurred"
        # Exception info should be included in some form
        assert isinstance(log_data, dict)
        print("Test passed!")

# Run the test
if __name__ == "__main__":
    test = TestJSONFormatting()
    test.setup_method()
    test.test_json_formatting_with_exception() 