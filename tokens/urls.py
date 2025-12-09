# ============================================
#     tokens/urls.py
# ============================================
from django.urls import path
from . import views

app_name = 'tokens'

urlpatterns = [
    path('', views.TokenListView.as_view(), name='token_list'),
    path('<uuid:pk>/', views.TokenRetrieveView.as_view(), name='token_detail'),
    path('issue/', views.IssueTokenView.as_view(), name='issue_token'),
    path('clear-credit/', views.ClearCreditView.as_view(), name='clear_credit'),
    path('clear-tamper/', views.ClearTamperView.as_view(), name='clear_tamper'),
    #path('revoke/', views.RevokeTokenView.as_view(), name='revoke_token'),
    path('<uuid:pk>/resend-sms/', views.TokenResendSmsView.as_view(), name='resend_token_sms'),
]