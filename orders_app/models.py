from django.db import models
from django.conf import settings
from django.db.models import JSONField

# Create your models here.


class Order(models.Model):
    """
    This model captures the details of a transaction, including the parties involved,
    the scope of work (title, features), financial details (price), and its
    current status and timeline. It acts as a snapshot of the agreement at the
    time of purchase.

    Attributes:
        customer_user (ForeignKey): The user who is buying the service.
        business_user (ForeignKey): The user who is selling the service.
        title (CharField): A descriptive title for the order.
        status (CharField): The current state of the order (e.g., 'in_progress').
        price (DecimalField): The total price for the order.
        revisions (IntegerField): The number of revisions included.
        delivery_time_in_days (IntegerField): The agreed-upon delivery time.
        features (JSONField): A list of features included in the order.
        offer_type (CharField): The type of package the order is based on.
        created_at (DateTimeField): Timestamp of when the order was created.
        updated_at (DateTimeField): Timestamp of the last update.
    """
    # --- Enumerations ---
    class OrderStatus(models.TextChoices):
        """
        Provides a controlled, readable, and robust set of choices for the status field.

        Using TextChoices prevents typos and "magic strings" in the code, ensuring
        data integrity. Each choice is a tuple: (`database_value`, `human_readable_label`).
        """
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    # --- Relationships ---
    customer_user = models.ForeignKey(
        # Best practice: link to the user model defined in settings, not directly to `User`.
        # This makes the app more reusable.
        settings.AUTH_USER_MODEL,
        # Defines the name for the reverse relationship from a User instance.
        # e.g., `user.customer_orders.all()` will get all orders for a user as a customer.
        related_name='customer_orders',
        # If the customer user is deleted, their orders are also deleted.
        on_delete=models.CASCADE,
        help_text="The user who is buying the service/product (the customer)."
    )
    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # e.g., `user.business_orders.all()` will get all orders for a user as a business.
        related_name='business_orders',
        # If the business user is deleted, all their associated orders are also deleted.
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
        # Restricts the field's value to the options defined in `OrderStatus`.
        # This is enforced at the database and form/serializer level.
        choices=OrderStatus.choices,
        # Sets the default value for new orders using the enumeration for clarity.
        default=OrderStatus.IN_PROGRESS,
        help_text="The current status of the order (e.g., 'in_progress', 'completed', 'cancelled')."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        # Using DecimalField is crucial for financial calculations to avoid floating-point
        # rounding errors that can occur with the standard `FloatField`.
        help_text="The total price for the order. Using DecimalField to avoid floating-point inaccuracies with currency."
    )

    # --- Offer Specifications ---
    # These fields capture the specific terms of the service at the time of purchase,
    # making the Order a self-contained record of the agreement.
    revisions = models.IntegerField(
        default=3,
        help_text="The number of revisions included in the offer."
    )
    delivery_time_in_days = models.IntegerField(
        default=5,
        help_text="The agreed-upon delivery time in days."
    )
    features = JSONField(
        # Initializes the field with an empty list, preventing errors if no features are provided.
        default=list,
        # Stores a list of features (e.g., ["Logo Design", "Source File"]) as structured JSON,
        # which is more flexible than a simple text field.
        help_text="A list of features or specific items included in the order, stored as JSON."
    )

    offer_type = models.CharField(
        max_length=50,
        default='basic',
        help_text="The type of package or offer this order is based on (e.g., 'basic', 'premium')."
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(
        # Automatically sets the timestamp to the current time *only when the object is first created*.
        # This field is non-editable after creation.
        auto_now_add=True,
        help_text="Timestamp for when the record was first created. Automatically set on creation."
    )
    updated_at = models.DateTimeField(
        # Automatically updates the timestamp to the current time *every time the object is saved*.
        auto_now=True,
        help_text="Timestamp for when the record was last updated. Automatically set on every save."
    )

    class Meta:
        """Inner class to configure model-level options."""
        # Sets the human-readable name for the model, used in the Django admin interface.
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        """
        Provides a human-readable string representation of the Order instance.
        
        This method is called by Django in various places, most notably in the admin
        interface, to display a clear and identifiable name for the object.
        """
        return f"Order {self.id}: {self.title}"
