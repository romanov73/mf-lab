from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied


def for_teacher():
    def is_teacher(user):
        if user.is_teacher:
            return True
        raise PermissionDenied

    return user_passes_test(is_teacher)


def for_student():
    def is_student(user):
        if not user.is_teacher:
            return True
        raise PermissionDenied

    return user_passes_test(is_student)
