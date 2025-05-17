from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response


def error_response(message, status_code, *, headers=None, **extra):
    return Response({"detail": message, **extra}, status=status_code, headers=headers)


def success_response(data, status_code=status.HTTP_200_OK):
    return Response(data, status=status_code)


def created_response(data):
    return Response(data, status=status.HTTP_201_CREATED)


def deleted_response(data=None):
    return Response(data, status=status.HTTP_204_NO_CONTENT)


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Already exists."
    default_code = "conflict"
