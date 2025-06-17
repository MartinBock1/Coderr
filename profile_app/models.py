from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# --- Helper Functions ---
def user_directory_path(instance, filename):
    """
    Generates a dynamic, user-specific path for file uploads.

    This function ensures that each user's uploaded files are stored in a separate directory named
    after their user ID, preventing filename clashes and organizing the media folder.

    Args:
        instance (Profile): The instance of the Profile model being saved.
        filename (str): The original filename of the uploaded file.

    Returns:
        str: A unique path like 'profiles/1/avatar.jpg'.
    """
    return f'profiles/{instance.user.id}/{filename}'


# --- Models ---
class Profile(models.Model):
    """
    Extends the built-in Django User model with additional, application-specific information.
    
    This model uses a OneToOneField to maintain a strict one-to-one relationship with a User,
    effectively adding custom fields to it without altering the original User model, which is a
    Django best practice.
    """
    # A one-to-one link to Django's built-in User model.
    # on_delete=models.CASCADE: If a User is deleted, their associated Profile is also deleted.
    # related_name='profile': Allows easy reverse access from a User instance (e.g., `user.profile`).
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    class UserType(models.TextChoices):
        """
        An enumeration for the user's role within the application. Using TextChoices provides a
        readable and robust way to manage a fixed set of options for the 'type' field.
        """
        CUSTOMER = 'customer', 'Kunde'
        BUSINESS = 'business', 'Geschäft'

    # --- Profile-specific Fields ---

    # An optional profile picture.
    # upload_to: Specifies the function that generates the upload path.
    # null=True: Allows the database column to be NULL (no file uploaded).
    # blank=True: Allows the field to be empty in forms (e.g., the Django admin).
    # verbose_name: A human-readable name for the field, used in forms and the admin.
    file = models.ImageField(upload_to=user_directory_path, null=True,
                             blank=True, verbose_name="Profilbild")
    
    # Optional text fields. The pattern `blank=True, default=''` is used to store an empty string
    # in the database instead of NULL, which can simplify form and template logic.
    location = models.CharField(max_length=100, blank=True, default='', verbose_name="Standort")
    tel = models.CharField(max_length=20, blank=True, default='', verbose_name="Telefonnummer")
    description = models.TextField(blank=True, default='', verbose_name="Beschreibung")
    working_hours = models.CharField(max_length=50, blank=True,
                                     default='', verbose_name="Öffnungszeiten")
    
    # The type of user, chosen from the UserType enumeration.
    # choices: Restricts the field's value to the options defined in UserType.
    # default: Sets a default value for new profiles.
    type = models.CharField(max_length=10, choices=UserType.choices,
                            default=UserType.CUSTOMER, verbose_name="Benutzertyp")
    
    # A timestamp for when the profile was created.
    # auto_now_add=True: Automatically sets the value to the current time when the object
    # is first created. This field is non-editable and is set only once.
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Methods ---
    def __str__(self):
        """
        Returns a human-readable string representation of the profile object. This is primarily used in
        the Django admin interface for a clear object display.
        """
        return f"Profil von {self.user.username}"

    @property
    def file_url(self):
        """
        A read-only property to safely get the URL of the profile picture.
        
        This method checks if a file has been uploaded and has a URL attribute before attempting
        to access it, thus preventing an AttributeError if no file is set.
        
        Returns:
            str: The full URL of the uploaded file, or None if no file exists.
        """
        if self.file and hasattr(self.file, 'url'):
            return self.file.url
        return None
