from django.db import models
from django.core.exceptions import ValidationError

class Repo(models.Model):
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField(unique=True)
    is_private = models.BooleanField(default=False)
    token = models.CharField(max_length=200, blank=True, null=True, help_text="Only for private repos. Token (GitHub) or App password (Bitbucket).")
    last_check_date = models.DateTimeField(null=True, blank=True, editable=False)
    last_import_date = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        # Only support github and bitbucket repos
        if not ("github.com/" in self.url or "bitbucket.org/" in self.url):
            raise ValidationError({'url': 'Only GitHub and Bitbucket repos are currently supported.'})
        # If private repo, token is mandatory
        if self.is_private and not self.token:
            raise ValidationError({'token': 'Token is mandatory for private repos.'})


class RepoAnalytic(models.Model):
    repo = models.ForeignKey(Repo, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    url = models.URLField()
    report = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.repo.name}:{self.name}"
