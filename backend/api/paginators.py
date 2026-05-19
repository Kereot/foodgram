from rest_framework.pagination import PageNumberPagination


class LimitOnlyPagination(PageNumberPagination):
    page_size_query_param = 'limit'
