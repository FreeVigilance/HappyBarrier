from django.core import validators
from django.utils.deconstruct import deconstructible


@deconstructible
class VerificationCodeValidator(validators.RegexValidator):
    """
    Validator for verification codes consisting of exactly 6 digits.
    """

    regex = r"^\d{6}$"
    message = "Enter a valid 6-digit verification code."
    flags = 0


@deconstructible
class VerificationTokenValidator(validators.RegexValidator):
    """
    Validator for verification tokens consisting of exactly 32 ascii letters or digits.
    """

    regex = r"^[a-zA-Z0-9]{32}$"
    message = "Enter a valid 32-character verification token (letters and digits only)."
    flags = 0
