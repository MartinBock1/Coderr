from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.


class Review(models.Model):
    """
    Represents a review given by one user (reviewer) to another (business_user).
    """
    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='reviews_received',
        on_delete=models.CASCADE,
        help_text="The user (business) who is being reviewed."
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='reviews_given',
        on_delete=models.CASCADE,
        help_text="The user who wrote the review."
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="The rating given, from 1 to 5."
    )
    description = models.TextField(
        blank=True,
        help_text="The text content of the review."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        # Ensures a user can only review a business once.
        unique_together = ('business_user', 'reviewer')
        verbose_name = "Review"
        verbose_name_plural = "Reviews"

    def __str__(self):
        return f"Review by {self.reviewer.username} for {self.business_user.username} ({self.rating} stars)"
