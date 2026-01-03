"""
Secure parser utility using RestrictedPython for safe code execution.
"""
from typing import Any
import signal
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import safe_builtins, guarded_iter_unpack_sequence
from RestrictedPython.Eval import default_guarded_getiter, default_guarded_getitem


class ParserTimeoutError(Exception):
    """Raised when parser code execution times out."""
    pass


class ParserExecutionError(Exception):
    """Raised when parser code execution fails."""
    pass


class ParserSecurityError(Exception):
    """Raised when parser code contains unsafe operations."""
    pass


def timeout_handler(signum, frame):
    raise ParserTimeoutError("Parser code execution timed out")


def _safe_getattr(obj, name, default=None):
    """Safe getattr that blocks access to private attributes."""
    if name.startswith('_'):
        raise ParserSecurityError(f"Access to private attribute '{name}' is not allowed")
    return getattr(obj, name, default)


def _safe_write(obj):
    """Guard for write operations."""
    return obj


def execute_parser(parser_code: str, data: Any, raw_response: str, timeout: int = 10) -> Any:
    """
    Execute user-provided parser code in a secure sandbox.
    
    Args:
        parser_code: Python code containing a `parse(data)` function
        data: Parsed JSON data from API response
        raw_response: Raw response text
        timeout: Maximum execution time in seconds
    
    Returns:
        Parsed result from user code
    
    Example parser_code:
        def parse(data):
            return [item['name'] for item in data['results']]
    """
    if not parser_code or not parser_code.strip():
        return data
    
    # Compile with RestrictedPython
    try:
        byte_code = compile_restricted(
            parser_code,
            filename='<parser>',
            mode='exec'
        )
    except SyntaxError as e:
        raise ParserExecutionError(f"Syntax error in parser code: {e}")
    
    # Check for compilation errors
    if byte_code is None:
        raise ParserSecurityError("Parser code contains disallowed operations")
    
    # Create restricted namespace
    restricted_builtins = dict(safe_builtins)
    restricted_builtins.update({
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'list': list,
        'dict': dict,
        'tuple': tuple,
        'set': set,
        'range': range,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'sorted': sorted,
        'reversed': reversed,
        'sum': sum,
        'min': min,
        'max': max,
        'abs': abs,
        'round': round,
        'isinstance': isinstance,
        'type': type,
        'None': None,
        'True': True,
        'False': False,
    })
    
    namespace = {
        '__builtins__': restricted_builtins,
        '_getattr_': _safe_getattr,
        '_getitem_': default_guarded_getitem,
        '_getiter_': default_guarded_getiter,
        '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
        '_write_': _safe_write,
        'data': data,
        'raw_response': raw_response,
    }
    
    try:
        # Set timeout (Unix only)
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
        except (AttributeError, ValueError):
            pass
        
        # Execute the restricted code
        exec(byte_code, namespace)
        
        # Check if parse function exists
        if 'parse' not in namespace:
            raise ParserExecutionError("Parser code must define a 'parse(data)' function")
        
        # Call the parse function
        result = namespace['parse'](data)
        
        return result
        
    except ParserTimeoutError:
        raise
    except ParserSecurityError:
        raise
    except ParserExecutionError:
        raise
    except Exception as e:
        raise ParserExecutionError(f"Parser execution failed: {str(e)}")
    finally:
        try:
            signal.alarm(0)
        except (AttributeError, ValueError):
            pass


def extract_by_json_path(data: Any, path: str) -> Any:
    """
    Extract data from a JSON structure using a dot-notated path.
    Supports array indexing: data.answer[0].content
    
    Args:
        data: The JSON data to extract from
        path: Dot-notated path string
        
    Returns:
        The extracted value, or None if not found
    """
    if not path or not path.strip():
        return data
        
    import re
    
    # Split by dots, but handle array brackets
    # Example: data.answer[0].content -> ['data', 'answer[0]', 'content']
    parts = path.split('.')
    current = data
    
    try:
        for part in parts:
            # Check for array indexing: name[index]
            match = re.match(r'(.+)\[(\d+)\]', part)
            if match:
                key = match.group(1)
                index = int(match.group(2))
                
                # Access dict or list
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif key == "" and isinstance(current, (list, tuple)):
                    # Handle cases like [0].something (path starting with [0])
                    pass
                else:
                    return None
                    
                # Access list by index
                if isinstance(current, (list, tuple)) and 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                # Regular dict access
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
                    
        return current
    except (IndexError, KeyError, TypeError, ValueError):
        return None
