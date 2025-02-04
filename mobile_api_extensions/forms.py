"""Mobile-api extensions form."""
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from oauth2_provider.models import Application

User = get_user_model()


class AuthorizationCodeExchangeForm(forms.Form):
    """
    Form for access authorization code exchange endpoint.
    """
    authorization_code = forms.CharField(max_length=32)
    client_id = forms.CharField()

    def __init__(self, request, oauth2_adapter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.oauth2_adapter = oauth2_adapter

    def clean(self):
        cleaned_data = super().clean()
        if 'client_id' not in self.errors:
            client_id = cleaned_data.get('client_id', '')
            try:
                self.cleaned_data['client'] = self.oauth2_adapter.get_client(client_id=client_id)
            except Application.DoesNotExist:
                self.add_error("client_id", _("Client id [{client_id}] does not exist.").format(client_id=client_id))

        if 'authorization_code' not in self.errors:
            authorization_code = cleaned_data.get('authorization_code', '')
            try:
                self.cleaned_data['user'] = User.objects.get(mobile_user_auth__authorization_code=authorization_code)
            except User.DoesNotExist:
                self.add_error(
                    "authorization_code",
                    _("Can't find user associated with [{auth_code}] authorization code.").format(
                        auth_code=authorization_code
                    )
                )

