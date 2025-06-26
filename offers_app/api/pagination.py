from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class to allow clients to set page size.
    """
    # The default number of results to return per page.
    page_size = 10

    # The query parameter that allows the client to set the page size.
    # For example: /api/offers/?page_size=5
    page_size_query_param = 'page_size'

    # The maximum page size that a client can request.
    # This prevents clients from requesting a huge number of items at once.
    max_page_size = 100
