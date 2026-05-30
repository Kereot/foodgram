from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from common.constants import PAGE_SIZE


class LimitOnlyPagination(PageNumberPagination):
    page_size_query_param = 'limit'


class RecipePagination(PageNumberPagination):
    page_size = PAGE_SIZE
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'total': self.page.paginator.count,  # вместо count
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
