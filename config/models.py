from django.db import models

class Module(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class ModulePermission(models.Model):
    """
    Permissions associated with modules.
    IMPORTANT: this table does not store groups permissions, but only lists permissions used in DeepHunter.
    """
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    permission = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.module.name}:{self.action}"
    
    class Meta:
        unique_together = ('module', 'action')
        ordering = ['module__name', 'action']
