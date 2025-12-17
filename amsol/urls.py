from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema')
    ,
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # APIs
    path('api/auth/', include('accounts.urls')),
    path('api/clients/', include('clients.urls')),
    path('api/meters/', include('meters.urls')),
    path('api/customers/', include('customers.urls')),
    path('api/tokens/', include('tokens.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/alerts/', include('alerts.urls')),
    path('api/dashboard/', include('core.dashboard_urls')),
    path('api/reports/', include('core.reports_urls')),

    # Webhooks & health
    path('api/payments/', include('payments.urls', namespace='payments')),
   # path('api/webhooks/c2b/', include('payments.webhook_urls')),
    path('health/', include('core.health_urls')),

    # Root → docs (pick what you prefer here)
    path('', RedirectView.as_view(pattern_name='swagger-ui', permanent=False)),
]

# Serve static/media in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
