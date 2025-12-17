# ============================================
# FILE 2: core/exceptions.py - Custom Exception Handler
# ============================================
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom exception handler for DRF"""
    
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    # Log the exception
    logger.error(
        f"API Exception: {exc}",
        extra={
            'exception_type': type(exc).__name__,
            'view': context.get('view'),
            'request': context.get('request')
        }
    )
    
    # Customize response format
    if response is not None:
        custom_response_data = {
            'error': True,
            'message': str(exc),
            'details': response.data
        }
        response.data = custom_response_data
    
    return response