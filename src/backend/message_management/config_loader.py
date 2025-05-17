import json
import logging
import os

from rest_framework.exceptions import NotFound, ValidationError

from message_management.enums import PhoneCommand

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PHONE_COMMANDS_PATH = os.path.join(BASE_DIR, "configs", "phone_commands.json")
SETTINGS_PATH = os.path.join(BASE_DIR, "configs", "barrier_settings.json")

logger = logging.getLogger(__name__)


def load_phone_commands():
    with open(PHONE_COMMANDS_PATH) as f:
        return json.load(f)


def get_phone_command(device_model: str, command: PhoneCommand) -> dict:
    commands = load_phone_commands()
    model_commands = commands.get(device_model)
    if not model_commands:
        raise NotFound(f"No phone commands defined for device model: '{device_model}'")

    cmd = model_commands.get(command.value)
    if not cmd:
        raise NotFound(f"Command '{command.value}' not found for model '{device_model}'")
    if "response_pattern" not in cmd:
        raise ValidationError(f"Missing 'response_pattern' for command '{command.value}' of model '{device_model}'")

    return cmd


def load_barrier_settings():
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def get_setting(device_model: str, key: str) -> dict:
    settings = load_barrier_settings()

    if not settings:
        raise NotFound("No settings defined.")
    model_settings = settings.get(device_model)
    if not model_settings:
        raise NotFound(f"No settings available for device model: '{device_model}'.")

    setting = model_settings.get(key)
    if not setting:
        raise NotFound(f"Setting '{key}' not found for model '{device_model}'")

    return setting


def build_message(template: str, params: dict) -> str:
    try:
        message = template.format(**params)
        logger.debug(f"Built SMS message: {message}")
        return message
    except KeyError as e:
        msg = f"Missing required parameter '{e.args[0]}' for template: {e.args[0]}"
        logger.warning(msg)
        raise ValidationError({"detail": msg})
