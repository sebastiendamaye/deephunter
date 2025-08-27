from django.urls import path
from . import views

urlpatterns = [
    path('vthashchecker/', views.vthashchecker, name='vthashchecker'),
    path('vtipchecker/', views.vtipchecker, name='vtipchecker'),
    path('loldriverhashchecker/', views.loldriverhashchecker, name='loldriverhashchecker'),
    path('malwarebazaarhashchecker/', views.malwarebazaarhashchecker, name='malwarebazaarhashchecker'),
    path('whois/', views.whois, name='whois'),
]
