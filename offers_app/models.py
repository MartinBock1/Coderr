from django.db import models
from django.conf import settings

# Create your models here.


class Offer(models.Model):
    """
    Represents a main service or product offer created by a user.

    This model holds the core information for an offer, such as its title, description, and the
    user who created it. It serves as a container for the specific pricing tiers, which are defined
    in the related 'OfferDetail' model.

    Attributes:
        user (ForeignKey): The user who owns this offer.
        title (CharField): The main, customer-facing title of the offer.
        description (TextField): A detailed description of the overall service.
        image (ImageField): An optional primary image for the offer.
        created_at (DateTimeField): Timestamp of when the offer was created.
        updated_at (DateTimeField): Timestamp of the last update.
    """
    # The user who created and owns this offer.
    # on_delete=CASCADE means if the user is deleted, their offers are deleted too.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offers")

    # The main title of the offer, e.g., "Professional Logo Design".
    title = models.CharField(max_length=255)

    # A more detailed description of the service being offered.
    description = models.TextField(blank=True)

    # An optional representative image for the offer.
    image = models.ImageField(
        upload_to='offers/images/',
        blank=True,
        null=True)

    # Timestamp for when the offer was first created. Automatically set on creation.
    created_at = models.DateTimeField(auto_now_add=True)

    # Timestamp for the last update. Automatically set on every save.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Default ordering for querysets: most recently updated offers first.
        ordering = ['-updated_at']

        # Human-readable names for the Django admin interface.
        verbose_name = "Offer"
        verbose_name_plural = "Offers"

    def __str__(self):
        """Returns the string representation of the Offer model."""
        return self.title


class OfferDetail(models.Model):
    """
    Represents a specific pricing tier or package for an Offer.

    An offer typically has multiple detail packages (e.g., Basic, Standard, Premium).
    Each detail defines a specific price, delivery time, and set of features.
    The API uses this model to calculate aggregated values like 'min_price' for the parent Offer.

    Attributes:
        offer (ForeignKey): The parent Offer this package belongs to.
        title (CharField): The title of this specific package (e.g., "Basic Package").
        price (DecimalField): The price for this package.
        delivery_time_in_days (PositiveIntegerField): Delivery time in whole days.
        description (TextField): A specific description for this package.
        image (ImageField): An optional image specific to this package.
        revisions (PositiveIntegerField): The number of revision rounds included.
        features (JSONField): A list of features included in the package.
        offer_type (CharField): The type of the package (e.g., 'basic', 'standard').
    """
    class OfferType(models.TextChoices):
        """Enumeration for the different types of offer packages."""
        BASIC = 'basic', 'Basic'
        STANDARD = 'standard', 'Standard'
        PREMIUM = 'premium', 'Premium'

    # Link to the parent Offer. `related_name="details"` allows accessing these from an offer instance
    # (e.g., offer.details.all()).
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="details")

    # The title for this specific tier, e.g., "Standard Package".
    title = models.CharField(max_length=150)

    # The price for this package.
    # DecimalField is used to avoid floating-point inaccuracies with currency.
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # The estimated delivery time, in whole days.
    # Renamed from `delivery_time_days` for API consistency.
    delivery_time_in_days = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='offers/images/',
        blank=True,
        null=True)
    revisions = models.IntegerField(default=0)
    features = models.JSONField(default=list)  # Beste Wahl für eine Liste von Strings
    offer_type = models.CharField(
        max_length=20,
        choices=OfferType.choices,
        default=OfferType.STANDARD
    )

    class Meta:
        ordering = ['price']
        verbose_name = "Offer Detail"
        verbose_name_plural = "Offer Details"

    def __str__(self):
        """String representation of the OfferDetail model."""
        return f"{self.offer.title} - {self.title} (${self.price})"
