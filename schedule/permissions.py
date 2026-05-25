from rest_framework import permissions

class IsAdminUserRole(permissions.BasePermission):
    """ Дозволяє доступ лише адміністраторам. """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'ADMIN')

class IsDeputyOrAdmin(permissions.BasePermission):
    """ Дозволяє доступ заступникам директора та адміністраторам. """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['ADMIN', 'DEPUTY'])

class IsTeacher(permissions.BasePermission):
    """ Дозволяє доступ лише вчителям (наприклад, для заповнення доступності). """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'TEACHER')

class IsPublicReadOnly(permissions.BasePermission):
    """ Дозволяє читання всім (учням/батькам), а запис - лише адмінам/заступникам. """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True # Читати можуть всі (або IsAuthenticated, якщо розклад закритий)
        return bool(request.user and request.user.is_authenticated and request.user.role in ['ADMIN', 'DEPUTY'])