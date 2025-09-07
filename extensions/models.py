from django.db import models

class ExtensionsPermission(models.Model):
    # This is a dummy model to define a custom permission (extensions.view_extensions)
    # Notice that irrelevant permissions will be added automatically (no way to get rid of them):
    # extensions.add_extensionspermission
    # extensions.change_extensionspermission
    # extensions.delete_extensionspermission
    # extensions.view_extensionspermission
    class Meta:
        managed = False  # No database table will be created
        permissions = [
            ("view_extensions", "Can view extensions"),
        ]