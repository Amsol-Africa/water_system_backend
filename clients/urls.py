# ============================================
# FILE 3: clients/urls.py
# ============================================
from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.ClientListCreateView.as_view(), name='client_list'),
    path('<uuid:pk>/', views.ClientRetrieveUpdateDestroyView.as_view(), name='client_detail'),
    path('<uuid:pk>/stats/', views.ClientStatsView.as_view(), name='client_stats'),
]