import json

import pytest
from rest_framework.exceptions import NotFound, ValidationError

from barriers.models import Barrier
from message_management.config_loader import (
    build_message,
    get_phone_command,
    get_setting,
    load_barrier_settings,
    load_phone_commands,
)
from message_management.enums import PhoneCommand


@pytest.fixture
def wrong_command_phone_config(tmp_path, monkeypatch):
    path = tmp_path / "phone_commands.json"
    content = {
        Barrier.Model.RTU5025.label: {
            "some_other_command": {"template": "OTHER {phone}"},
        }
    }
    path.write_text(json.dumps(content))
    monkeypatch.setattr("message_management.config_loader.PHONE_COMMANDS_PATH", str(path))
    return content


@pytest.mark.django_db
class TestLoadPhoneCommands:
    def test_success(self):
        commands = load_phone_commands()

        assert Barrier.Model.RTU5025 in commands
        assert Barrier.Model.TELEMETRICA in commands

        assert PhoneCommand.ADD.value in commands[Barrier.Model.RTU5025]
        assert PhoneCommand.ADD.value in commands[Barrier.Model.TELEMETRICA]

    def test_invalid_json(self, tmp_path, monkeypatch):
        broken_file = tmp_path / "broken.json"
        broken_file.write_text("{invalid json")
        monkeypatch.setattr("message_management.config_loader.PHONE_COMMANDS_PATH", str(broken_file))

        with pytest.raises(json.JSONDecodeError):
            load_phone_commands()


@pytest.mark.django_db
class TestGetPhoneCommand:
    def test_success_rtu5025(self):
        cmd = get_phone_command(Barrier.Model.RTU5025, PhoneCommand.ADD)
        assert cmd["template"] == "{pwd}A{index}#0007{phone}#"

    def test_success_telemetrica(self):
        cmd = get_phone_command(Barrier.Model.TELEMETRICA, PhoneCommand.ADD)
        assert cmd["template"] == "#60#+7{phone}#"

    def test_command_not_found(self, wrong_command_phone_config):
        with pytest.raises(
            NotFound, match=f"Command '{PhoneCommand.ADD.value}' not found for model '{Barrier.Model.RTU5025}'"
        ):
            get_phone_command(Barrier.Model.RTU5025, PhoneCommand.ADD)

    def test_model_not_found(self):
        with pytest.raises(NotFound, match="No phone commands defined for device model: 'UnknownModel'"):
            get_phone_command("UnknownModel", PhoneCommand.ADD)

    def test_command_missing_response_pattern(self, tmp_path, monkeypatch):
        config = {
            Barrier.Model.RTU5025: {
                PhoneCommand.ADD.value: {
                    "template": "{pwd}A{index}#0007{phone}#"
                    # no response_pattern
                }
            }
        }
        config_path = tmp_path / "phone_commands.json"
        config_path.write_text(json.dumps(config))
        monkeypatch.setattr("message_management.config_loader.PHONE_COMMANDS_PATH", str(config_path))

        with pytest.raises(ValidationError, match="Missing 'response_pattern' for command 'add_phone'"):
            get_phone_command(Barrier.Model.RTU5025, PhoneCommand.ADD)


@pytest.mark.django_db
class TestLoadBarrierSettings:
    def test_success(self):
        settings = load_barrier_settings()

        assert Barrier.Model.RTU5025 in settings
        assert Barrier.Model.TELEMETRICA in settings

        assert "start" in settings[Barrier.Model.RTU5025]
        assert "start" in settings[Barrier.Model.TELEMETRICA]


@pytest.mark.django_db
class TestGetSetting:
    def test_success_rtu5025(self):
        setting = get_setting(Barrier.Model.RTU5025, "start")
        assert setting["template"] == "{pwd}TEL0007{local_phone}"

    def test_success_telemetrica(self):
        setting = get_setting(Barrier.Model.TELEMETRICA, "start")
        assert setting["template"] == "#0#"

    def test_setting_not_found(self):
        with pytest.raises(NotFound, match=f"Setting 'none' not found for model '{Barrier.Model.RTU5025}'"):
            get_setting(Barrier.Model.RTU5025, "none")

    def test_model_not_found(self):
        with pytest.raises(NotFound, match="No settings available for device model: 'UnknownModel'."):
            get_setting("UnknownModel", "open_time")

    def test_get_setting_without_params(self, monkeypatch):
        setting_data = {
            Barrier.Model.RTU5025: {
                "simple": {
                    "template": "TEST",
                }
            }
        }

        monkeypatch.setattr("message_management.config_loader.load_barrier_settings", lambda: setting_data)

        setting = get_setting(Barrier.Model.RTU5025, "simple")
        assert setting["template"] == "TEST"


class TestBuildMessage:
    def test_success(self):
        template = "Hello {name}"
        params = {"name": "Alice"}
        result = build_message(template, params)
        assert result == "Hello Alice"

    def test_success_phone(self):
        template = "{pwd}A{index}#0007{phone}#"
        params = {"pwd": "1234", "index": "10", "phone": "9187058794"}
        result = build_message(template, params)
        assert result == "1234A10#00079187058794#"

    def test_missing_param(self):
        template = "Hello {name}"
        params = {}
        with pytest.raises(ValidationError, match="Missing required parameter 'name' for template:"):
            build_message(template, params)
