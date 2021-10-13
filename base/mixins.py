from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse


class DeleteMessagesMixin:
    message_deleted = None
    message_protected = None

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        try:
            self.object.delete()
            if self.message_deleted is not None:
                messages.add_message(request, messages.SUCCESS, self.message_deleted.format(self.object))
        except ProtectedError:
            if self.message_protected is not None:
                messages.add_message(request, messages.ERROR, self.message_protected.format(self.object))

        return HttpResponseRedirect(success_url)
