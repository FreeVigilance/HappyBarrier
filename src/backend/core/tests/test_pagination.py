import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from barriers.models import Barrier
from users.models import User


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(phone="+79991112233", role=User.Role.ADMIN, is_staff=True)


@pytest.fixture
def client_admin(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    return client


@pytest.fixture
def create_barriers(admin_user):
    return [
        Barrier.objects.create(
            address=f"st. Test {i}",
            owner=admin_user,
            device_phone=f"+7999000000{i}",
            device_model=Barrier.Model.RTU5025,
            device_phones_amount=1,
            device_password="1234",
            additional_info="test",
            is_public=True,
        )
        for i in range(15)
    ]


@pytest.mark.django_db
class TestBasePaginatedListView:
    endpoint = "admin_my_barriers"

    def test_default_pagination(self, client_admin, create_barriers):
        url = reverse(self.endpoint)
        response = client_admin.get(url)
        data = response.json()

        assert response.status_code == 200
        assert data["total_count"] == 15
        assert data["current_page"] == 1
        assert data["page_size"] == 10
        assert len(data["barriers"]) == 10

    def test_custom_page_size(self, client_admin, create_barriers):
        url = reverse(self.endpoint)
        response = client_admin.get(url, {"page_size": 5})
        data = response.json()

        assert response.status_code == 200
        assert data["page_size"] == 5
        assert len(data["barriers"]) == 5

    def test_max_page_size(self, client_admin, create_barriers):
        url = reverse(self.endpoint)
        response = client_admin.get(url, {"page_size": 999})
        data = response.json()

        assert response.status_code == 200
        assert data["page_size"] == 100  # MAX_PAGE_SIZE
        assert len(data["barriers"]) == 15

    def test_invalid_page(self, client_admin, create_barriers):
        url = reverse(self.endpoint)
        response = client_admin.get(url, {"page": 999})
        assert response.status_code == 404
