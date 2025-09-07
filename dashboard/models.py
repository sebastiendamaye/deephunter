from django.db import models

class DashboardPermission(models.Model):
    # This is a dummy model to define a custom permission (dashboard.view_dashboard)
    # Notice that irrelevant permissions will be added automatically (no way to get rid of them):
    # dashboard.add_dashboardpermission
    # dashboard.change_dashboardpermission
    # dashboard.delete_dashboardpermission
    # dashboard.view_dashboardpermission
    class Meta:
        managed = False  # No database table will be created
        permissions = [
            ("view_dashboard", "Can view dashboard"),
        ]