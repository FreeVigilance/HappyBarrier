from django.core import validators
from django.utils.deconstruct import deconstructible


@deconstructible
class PhoneNumberValidator(validators.RegexValidator):
    """Validator for phone numbers in the format +7XXXXXXXXXX (Russian numbers)."""

    regex = r"^\+7\d{10}$"
    message = "Enter a valid phone number in the format +7XXXXXXXXXX."
    flags = 0
