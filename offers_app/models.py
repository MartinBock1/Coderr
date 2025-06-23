from django.db import models
from django.conf import settings

# Create your models here.


class Offer(models.Model):
    """
    Represents a main service or product offer created by a user.

    This model holds the core information for an offer, such as its title,
    description, and the user who created it. The actual pricing and delivery
    options are defined in the related 'OfferDetail' model.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offers")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='offers/images/',
        blank=True,
        null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Offer"
        verbose_name_plural = "Offers"

    def __str__(self):
        """String representation of the Offer model."""
        return self.title


class OfferDetail(models.Model):
    """
    Represents a specific pricing tier or package for an Offer.

    An offer can have multiple detail packages (e.g., Basic, Standard, Premium).
    Each detail defines a specific price and delivery time. The API will use
    this model to calculate the 'min_price' and 'min_delivery_time' for the
    parent Offer.
    """
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="details")
    title = models.CharField(max_length=150, default="Standard Package")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time_days = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='offers/images/',
        blank=True,
        null=True)

    class Meta:
        ordering = ['price']
        verbose_name = "Offer Detail"
        verbose_name_plural = "Offer Details"

    def __str__(self):
        """String representation of the OfferDetail model."""
        return f"{self.offer.title} - {self.title} (${self.price})"
