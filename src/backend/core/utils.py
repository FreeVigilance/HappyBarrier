from rest_framework import status
from rest_framework.response import Response


def error_response(message, status_code, *, headers=None, **extra):
    return Response({"error": message, **extra}, status=status_code, headers=headers)


def success_response(data, status_code=status.HTTP_200_OK):
    return Response(data, status=status_code)


def validation_error_response(errors):
    return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)


def created_response(data):
    return Response(data, status=status.HTTP_201_CREATED)


def deleted_response(data=None):
    return Response(data, status=status.HTTP_204_NO_CONTENT)
