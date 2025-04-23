from rest_framework import status

from verifications.utils import apply_checks


class TestApplyChecks:
    def test_returns_first_error(self):
        def fail_check():
            from core.utils import error_response

            return error_response("failure", status.HTTP_400_BAD_REQUEST)

        def success_check():
            return None

        assert apply_checks(success_check, fail_check, success_check).status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_none_if_all_pass(self):
        def ok():
            return None

        assert apply_checks(ok, ok) is None
