"""
Mobile-api extensions django models.
"""
import logging
import uuid
from django.contrib.auth import get_user_model
from django.db import IntegrityError, models, transaction

log = logging.getLogger(__name__)
User = get_user_model()


class MobileUserAuth(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mobile_user_auth')
    authorization_code = models.CharField(unique=True, null=True, blank=True, max_length=32)

    class Meta:
        verbose_name = 'Mobile User Auth'
        verbose_name_plural = 'Mobile Users Auth'

    @staticmethod
    def _generate_authorization_code():
        """
        Create a new auth code.
        """
        return uuid.uuid4().hex

    def set_authorization_code(self):
        """
        Generate and store authorization code.

        Overwrite the existing auth code.
        """
        if not self.authorization_code:
            token = self._generate_authorization_code()
            self.authorization_code = token
            try:
                with transaction.atomic():
                    self.save()
            except IntegrityError:
                # Violated uniqueness constraint.
                # It's quite improbable to run into this case: https://stackoverflow.com/a/1155027
                log.info(f"Generated duplicate authorization_code {token} for user {self.user.id}. Re-generating.")
                return self.set_authorization_code()

        return self.authorization_code
