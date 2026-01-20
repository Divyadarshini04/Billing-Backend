"""
Custom DRF exception handler for consistent error response formatting.
"""

from rest_framework.views import exception_handler
from rest_framework import status

def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error format.
    
    Format:
    {
        "errors": [
            {
                "detail": "Error message",
                "code": "error_code"
            }
        ]
    }
    
    Or for single errors:
    {
        "detail": "Error message",
        "code": "error_code"
    }
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the response
        if isinstance(response.data, dict):
            # Handle validation errors that come as dictionaries
            if 'detail' in response.data:
                # Simple detail error
                return response
            else:
                # Field-level validation errors
                errors = []
                for field, messages in response.data.items():
                    if isinstance(messages, list):
                        for message in messages:
                            errors.append({
                                "field": field,
                                "detail": str(message),
                                "code": str(message.code) if hasattr(message, 'code') else "invalid"
                            })
                    else:
                        errors.append({
                            "field": field,
                            "detail": str(messages),
                            "code": "invalid"
                        })
                
                response.data = {
                    "errors": errors,
                    "status": response.status_code
                }
        
        # Ensure proper error format for detail errors
        if 'detail' in response.data and isinstance(response.data['detail'], str):
            response.data = {
                "detail": response.data['detail'],
                "code": response.status_code
            }
        
        return response
    
    # Return None if no response (this shouldn't happen in normal cases)
    return None
