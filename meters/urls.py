from django.urls import path
from .views import (
    MeterListCreateView,
    MeterRetrieveUpdateDestroyView,
    MeterQueryView,
    MeterAssignmentListView,
    MeterSuspendView,   
    MeterResumeView,
)

app_name = "meters"

urlpatterns = [
    path('', MeterListCreateView.as_view(), name='meter_list'),
    # important: non-pk routes before the '<uuid:pk>/' route
    path('query/', MeterQueryView.as_view(), name='meter_query'),
    path('<uuid:pk>/assignments/', MeterAssignmentListView.as_view(), name='meter_assignments'),
    path('<uuid:pk>/suspend/', MeterSuspendView.as_view(), name='meter_suspend'),  
    path('<uuid:pk>/resume/', MeterResumeView.as_view(), name='meter_resume'),
    path('<uuid:pk>/', MeterRetrieveUpdateDestroyView.as_view(), name='meter_detail'),
]
