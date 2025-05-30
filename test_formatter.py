import logging
import json
import sys
from app.core.logging_config import CustomJsonFormatter

formatter = CustomJsonFormatter()

# Test with exception
try:
    raise ValueError('Test exception')
except ValueError:
    record = logging.LogRecord(
        name='test.module', 
        level=logging.ERROR, 
        pathname='test.py', 
        lineno=42,
        msg='Error occurred', 
        args=(), 
        exc_info=sys.exc_info()
    )

formatted = formatter.format(record)
print('Type:', type(formatted))
print('Value:', repr(formatted[:200]))

if isinstance(formatted, str):
    try:
        log_data = json.loads(formatted)
        print('JSON parsed successfully:', type(log_data))
        print('Keys:', list(log_data.keys()) if isinstance(log_data, dict) else 'Not a dict')
        if isinstance(log_data, dict):
            print('Level:', log_data.get('level'))
            print('Message:', log_data.get('message'))
    except json.JSONDecodeError as e:
        print('JSON decode error:', e)
else:
    print('Formatter did not return a string!') 