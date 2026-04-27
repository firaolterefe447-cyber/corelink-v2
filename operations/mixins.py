# operations/mixins.py
from django.apps import apps


class SecurityAuditMixin:
    """
    Automatic Surveillance System.
    Attaching this to any Admin class forces it to record:
    1. Who made the change (Admin)
    2. What changed (The Fields)
    3. The IP Address
    """

    def _get_audit_model(self):
        # We fetch the model dynamically to prevent Circular Import Errors
        return apps.get_model('operations', 'AuditLog')

    def _get_target_user(self, obj):
        """Finds the human associated with the record"""
        if hasattr(obj, 'user'): return obj.user
        if hasattr(obj, 'username'): return obj  # If the object IS a user
        return None

    def save_model(self, request, obj, form, change):
        AuditLog = self._get_audit_model()
        action_type = "UPDATE" if change else "CREATE"
        model_name = obj._meta.verbose_name.title()

        # Capture specific changes
        changes = {}
        if change and form.changed_data:
            for field in form.changed_data:
                # Convert value to string to ensure JSON compatibility
                changes[field] = str(form.cleaned_data.get(field, ''))
        elif not change:
            changes = "New Record Created"

        # Write to Blackbox
        AuditLog.objects.create(
            admin=request.user,
            target_user=self._get_target_user(obj),
            action=f"{action_type} {model_name}",
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                "object_id": str(obj.pk),
                "object_repr": str(obj),
                "changes": changes
            }
        )

        # PROCEED WITH NORMAL SAVE
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        AuditLog = self._get_audit_model()
        model_name = obj._meta.verbose_name.title()

        AuditLog.objects.create(
            admin=request.user,
            target_user=self._get_target_user(obj),
            action=f"DELETE {model_name}",
            ip_address=request.META.get('REMOTE_ADDR'),
            details={"object_id": str(obj.pk), "object_repr": str(obj)}
        )

        # PROCEED WITH NORMAL DELETE
        super().delete_model(request, obj)