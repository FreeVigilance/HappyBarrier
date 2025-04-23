from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from core.utils import success_response

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


class CustomPageNumberPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE


class BasePaginatedListView(ListAPIView):
    """Base view to add pagination metadata"""

    pagination_class = CustomPageNumberPagination
    pagination_response_key = "results"

    def list(self, request, *args, **kwargs):
        """Add total_count, current_page, and page_size to the response"""

        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def get_paginated_response(self, data):
        """Format the response with pagination details"""

        paginator = self.pagination_class()
        paginator.page = self.paginator.page

        return success_response(
            {
                "total_count": paginator.page.paginator.count,
                "current_page": paginator.page.number,
                "page_size": paginator.get_page_size(self.request),
                self.pagination_response_key: data,
            }
        )
