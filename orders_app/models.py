from django.db import models
from django.conf import settings
from django.db.models import JSONField

# Create your models here.


class Order(models.Model):
    """
    Represents an order placed by a customer to a business or service provider.

    This model captures the details of a transaction, including the parties involved, the scope of
    work (title, features), financial details (price), and its current status and timeline.
    """
    # --- Relationships ---
    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='customer_orders',
        on_delete=models.CASCADE,
        help_text="The user who is buying the service/product (the customer)."
    )
    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='business_orders',
        on_delete=models.CASCADE,
        help_text="The user who is selling the service/product (the business/freelancer)."
    )

    # --- Order Details ---
    title = models.CharField(
        max_length=255,
        help_text="A descriptive title for the order."
    )
    status = models.CharField(
        max_length=50,
        default='in_progress',
        help_text="The current status of the order (e.g., 'in_progress', 'completed', 'cancelled')."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The total price for the order. Using DecimalField to avoid floating-point inaccuracies with currency."
    )

    # --- Offer Specifications ---
    revisions = models.IntegerField(
        default=3,
        help_text="The number of revisions included in the offer."
    )
    delivery_time_in_days = models.IntegerField(
        default=5,
        help_text="The agreed-upon delivery time in days."
    )
    features = JSONField(
        default=list,
        help_text="A list of features or specific items included in the order, stored as JSON."
    )

    offer_type = models.CharField(
        max_length=50,
        default='basic',
        help_text="The type of package or offer this order is based on (e.g., 'basic', 'premium')."
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp for when the record was first created. Automatically set on creation."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp for when the record was last updated. Automatically set on every save."
    )

    class Meta:
        """Metadata options for the Order model."""
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        """
        Returns a human-readable string representation of the order.
        
        This is used in the Django admin interface and when printing the object.
        """
        return f"Order {self.id}: {self.title}"
