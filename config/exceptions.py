from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger("exceptions")

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        logger.warning(f"{exc} in {context['view'].__class__.__name__}")
        
        # Log the full response data for debugging
        logger.debug(f"Response data: {response.data}")
        
        # Return the response as-is, without wrapping in another detail field
        # This preserves validation errors that are already properly structured
        return response

    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return Response(
        {"detail": "Internal server error"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
