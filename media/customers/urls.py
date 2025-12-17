# ============================================
# FILE 5: customers/urls.py
# ============================================
from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.CustomerListCreateView.as_view(), name='customer_list'),
    path('<uuid:pk>/', views.CustomerRetrieveUpdateDestroyView.as_view(), name='customer_detail'),
    path('<uuid:pk>/assign-meter/', views.CustomerAssignMeterView.as_view(), name='assign_meter'),
    path('<uuid:pk>/unassign-meter/', views.CustomerUnassignMeterView.as_view(), name='unassign_meter'),
]