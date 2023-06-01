from rest_framework import permissions

'''
This custom Permission Class decorated in use for Premium Only User views (Analytics unlocked)
'''

class UserHaveUnlockedAnalytics(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.user.is_authenticated and request.user.has_analysis_unlocked:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated and request.user.has_analysis_unlocked:
            return True
        return False

