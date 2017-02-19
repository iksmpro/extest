from django.db import models

class NewsInstance(models.Model):
    time = models.DateTimeField('Creation time')
    title = models.CharField(max_length=128)
    category = models.CharField(max_length=256)
    description = models.CharField(max_length=1024)

