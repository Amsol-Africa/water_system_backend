# ============================================
# FILE 9: core/health_views.py
# ============================================
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import connection
from django.core.cache import cache
import redis


class HealthCheckView(APIView):
    """Basic health check"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'amsol-backend',
            'version': '1.0.0'
        })


class ReadinessCheckView(APIView):
    """Readiness check for dependencies"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        checks = {
            'database': False,
            'cache': False
        }
        
        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks['database'] = True
        except Exception:
            pass
        
        # Check Redis/Cache
        try:
            cache.set('health_check', 'ok', 10)
            checks['cache'] = cache.get('health_check') == 'ok'
        except Exception:
            pass
        
        all_ready = all(checks.values())
        
        return Response({
            'ready': all_ready,
            'checks': checks
        }, status=200 if all_ready else 503)
