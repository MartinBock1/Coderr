from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.
class Review(models.Model):
    """
    Represents a review given by a customer to a business user.

    This model establishes a relationship between a reviewing user ('reviewer') and a user being
    reviewed ('business_user'). It includes a numeric rating, a text description, and timestamps. A
    key constraint is that a specific reviewer can only leave one review for a specific
    business_user, enforced by a unique constraint on the database level.

    Attributes:
        business_user (ForeignKey): A link to the User instance being reviewed.
            This is typically a user with a 'business' profile.
        reviewer (ForeignKey): A link to the User instance who wrote the review.
            This is typically a user with a 'customer' profile.
        rating (PositiveIntegerField): A star rating from 1 to 5, enforced
            by validators.
        description (TextField): The optional, detailed text content of the review.
        created_at (DateTimeField): Timestamp automatically set when the review
            is first created.
        updated_at (DateTimeField): Timestamp automatically updated every time
            the review is saved.
    """
    # The user (typically a business) who is being reviewed.
    # If the business user is deleted, all reviews they received are also deleted due to
    # on_delete=models.CASCADE.
    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='reviews_received',
        on_delete=models.CASCADE,
        help_text="The user (business) who is being reviewed."
    )
    
    # The user (typically a customer) who wrote the review.
    # If the reviewer is deleted, all reviews they have written are also deleted.
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='reviews_given',
        on_delete=models.CASCADE,
        help_text="The user who wrote the review."
    )
    
    # The numeric rating, validated to be between 1 and 5 (inclusive).
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="The rating given, from 1 to 5."
    )
    
    # The free-form text of the review. Can be left blank.
    description = models.TextField(
        blank=True,
        help_text="The text content of the review."
    )
    
    # Timestamp for when the review was created. Set once and is not editable.
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Timestamp for the last update. Automatically set on every save operation.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the Review model."""
        
        # Default ordering for querysets: newest reviews first.
        ordering = ['-updated_at']
       
        # Enforces that a reviewer can only submit one review per business_user.
        # This database-level constraint prevents duplicate reviews.
        unique_together = ('business_user', 'reviewer')
        
        # Human-readable names for the model in the Django admin interface.
        verbose_name = "Review"
        verbose_name_plural = "Reviews"

    def __str__(self):
        """
        Returns a human-readable string representation of the review.

        This is used in the Django admin interface and for debugging purposes to easily identify
        a review instance.
        """
        return f"Review by {self.reviewer.username} for {self.business_user.username} ({self.rating} stars)"
