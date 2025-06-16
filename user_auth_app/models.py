from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    """
    Extends the built-in Django User model to store additional profile information.

    This model uses a one-to-one relationship to the `User` model, a common
    pattern in Django for adding application-specific fields without creating a
    fully custom user model. It is primarily used to store the role or "type"
    of a user within the system.

    Attributes:
        user (OneToOneField): A required link to an instance of the `auth.User`
            model. Deleting the User will also delete the associated UserProfile
            due to `on_delete=models.CASCADE`.
        type (CharField): A string field to categorize the user, for example,
            as a 'customer' or a 'business'.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        help_text="The user this profile belongs to."
    )
    type = models.CharField(
        max_length=15,
        help_text="The role or type of the user (e.g., customer, business)."
    )

    def __str__(self):
        """
        Returns the username of the associated User.

        This provides a human-readable representation of the UserProfile instance,
        which is particularly useful in the Django admin interface and for debugging.
        """
        return self.user.username