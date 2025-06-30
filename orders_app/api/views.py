from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView

# Local application imports
from ..models import Order
from .serializers import OrderSerializer, CreateOrderSerializer, OrderStatusUpdateSerializer
from .permissions import IsBusinessUserAndOwner
from offers_app.models import OfferDetail
from reviews_app.api.permissions import IsCustomerUser


class OrderViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing, creating, and updating Order instances.

    This ViewSet provides the primary CRUD (Create, Retrieve, Update, Delete) functionality for
    Orders. It uses dynamic permissions and serializers based on the specific action being
    performed to ensure security and proper data handling.

    - 'list' and 'retrieve': Authenticated users can see their own orders.
    - 'create': Authenticated users can create new orders from an offer.
    - 'update'/'partial_update': Only the business user who owns the order can update its status.
    - 'destroy': Only admin users can delete an order.
    """
    # Pagination is disabled for this ViewSet. All results will be returned in a single response.
    pagination_class = None

    def get_permissions(self):
        """
        Dynamically sets permissions based on the request action.

        This method ensures that the appropriate level of authorization is required for each type
        of operation.
        """
        if self.action == 'destroy':
            # Only administrators can delete orders.
            self.permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            # To update, a user must be authenticated and be the business owner of the order.
            self.permission_classes = [IsAuthenticated, IsBusinessUserAndOwner]
        elif self.action == 'create':
            # Nur eingeloggte Kunden dürfen Bestellungen erstellen
            self.permission_classes = [IsAuthenticated, IsCustomerUser]
        else:
            # For all other actions (list, retrieve, create), the user just needs to be
            # authenticated.
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        """
        Filters the queryset to ensure regular users only see orders they are
        involved in. Admins still need special handling for detail/delete views.
        """
        user = self.request.user

        if user.is_authenticated:
            # Für die Listenansicht filtern wir immer
            return Order.objects.filter(
                Q(customer_user=user) | Q(business_user=user)
            )
        # Für nicht eingeloggte User einen leeren QuerySet zurückgeben.
        return Order.objects.none()
    
    def get_object(self):
        """
        Overrides the default get_object to allow admins to access any order
        by its ID for detail/update/delete actions, while regular users are still
        restricted to their own orders.
        """
        queryset = self.get_queryset() # Holt den Standard-QuerySet
        obj = None

        # Für Admins erweitern wir die Suche auf ALLE Objekte
        if self.request.user.is_staff:
            # Wir durchsuchen alle Objekte, nicht nur den gefilterten QuerySet
            obj = generics.get_object_or_404(Order.objects.all(), pk=self.kwargs['pk'])
        else:
            # Normale User suchen nur in ihrem gefilterten QuerySet
            obj = generics.get_object_or_404(queryset, pk=self.kwargs['pk'])

        # Permissions für das spezifische Objekt prüfen
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        """
        Selects the appropriate serializer class based on the request action.
        """
        if self.action in ['update', 'partial_update']:
            # For updates, use the specialized serializer that only allows 'status' changes.
            return OrderStatusUpdateSerializer
        if self.action == 'create':
            # For creating an order, use the serializer that expects an 'offer_detail_id'.
            return CreateOrderSerializer
        # For all other actions (e.g., 'list', 'retrieve'), use the full Order serializer.
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        """
        Custom logic to create an Order from an OfferDetail ID.

        This method overrides the default `create` behavior. It takes an 'offer_detail_id',
        validates it, and then creates a new Order by copying the relevant details from the
        specified OfferDetail.
        """
        # 1. Validate the incoming request using the specialized CreateOrderSerializer.
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        offer_detail_id = input_serializer.validated_data['offer_detail_id']

        try:
            # 2. Retrieve the full OfferDetail object, pre-fetching the related user for efficiency
            offer_detail = OfferDetail.objects.select_related(
                'offer__user').get(pk=offer_detail_id)
        except OfferDetail.DoesNotExist:
            return Response({"detail": "Offer detail not found."}, status=status.HTTP_404_NOT_FOUND)

        # 3. Business logic check: A user cannot create an order for their own offer.
        business_user = offer_detail.offer.user
        if business_user == request.user:
            return Response(
                {"detail": "You cannot create an order for your own offer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Create the new Order instance using data from the request user and the offer detail.
        order = Order.objects.create(
            customer_user=request.user,
            business_user=business_user,
            title=offer_detail.title,
            price=offer_detail.price,
            revisions=offer_detail.revisions,
            delivery_time_in_days=offer_detail.delivery_time_in_days,
            features=offer_detail.features,
            offer_type=offer_detail.offer_type
        )

        # 5. Serialize the complete new order object for the response.
        output_serializer = OrderSerializer(order)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """
        Custom logic to update an Order's status.

        This method uses the `OrderStatusUpdateSerializer` to validate that only the 'status' field
        is being modified. It then returns the full, updated order object.
        """
        instance = self.get_object()
        # Use the specialized serializer to validate that ONLY the status field is provided.
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Perform the update using the validated data.
        self.perform_update(serializer)

        # For the response, serialize the full, updated instance using the main serializer.
        output_serializer = OrderSerializer(instance)

        return Response(output_serializer.data)


class OrderCountView(APIView):
    """
    An API view that returns the count of 'in_progress' orders for a specific business user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id, format=None):
        """
        Handles GET requests to count in-progress orders.

        Args:
            business_user_id (int): The primary key of the business user whose orders are to be
            counted.

        Returns:
            Response: A JSON response containing the order count or a 404 if the user doesn't
            exist.
        """
        try:
            # First, verify that the user ID corresponds to an existing user.
            User.objects.get(pk=business_user_id)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Filter orders by the business user and 'in_progress' status, then count them efficiently.
        count = Order.objects.filter(
            business_user_id=business_user_id,
            status='in_progress'
        ).count()

        return Response({'order_count': count}, status=status.HTTP_200_OK)


class CompletedOrderCountView(APIView):
    """
    An API view that returns the count of 'completed' orders for a specific business user.
    
    Note: This is very similar to OrderCountView and could be combined into a single view that
    accepts an optional 'status' query parameter for more flexibility.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id, format=None):
        """
        Handles GET requests to count completed orders.
        
        Args:
            business_user_id (int): The primary key of the business user whose orders are to be
            counted.
            
        Returns:
            Response: A JSON response containing the completed order count or a 404 if the user
            doesn't exist.
        """
        try:
            # Verify the user exists.
            User.objects.get(pk=business_user_id)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Filter orders by the business user and 'completed' status, then count them.
        count = Order.objects.filter(
            business_user_id=business_user_id,
            status='completed'
        ).count()

        return Response({'completed_order_count': count}, status=status.HTTP_200_OK)
