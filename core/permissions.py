# ============================================
# FILE 1: core/permissions.py - RBAC Permissions
# ============================================
from rest_framework import permissions


class IsSystemAdmin(permissions.BasePermission):
    """Allow only system admins"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'system_admin'
        )


class IsClientAdmin(permissions.BasePermission):
    """Allow only client admins"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'client_admin'
        )


class IsClientAdminOrSystemAdmin(permissions.BasePermission):
    """Allow client admins or system admins"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['client_admin', 'system_admin']
        )


class IsClientMember(permissions.BasePermission):
    """Allow any authenticated user who belongs to a client"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # System admin can access everything
        if request.user.role == 'system_admin':
            return True
        
        # Other users must belong to a client
        return request.user.client_id is not None