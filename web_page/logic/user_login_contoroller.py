import django.contrib.auth
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from ldap3 import Connection, SUBTREE
from ldap3.core.exceptions import LDAPException

from web_page.models import User

LDAP_HOST_NAME: str = "ldap://192.168.1.120:389"  # Адрес ldap сервера. Да, это IP ноута в моей локалке.
LDAP_BASE_DOMAIN: str = 'ramhlocal,dc=com'  # Базовый домен организации. В политехе, очевидно, другой


def _find_user(request, username: str, password: str) -> User | None:
    """
    Приватный метод получения пользователя с учётом Ldap. Предполагается, что именно его мы будем расширять
    """
    try:
        # Подключаемся к LDAP под доменом LDAP_BASE_DOMAIN и именем пользователя username
        with Connection(LDAP_HOST_NAME,
                        user=f'cn={username},dc={LDAP_BASE_DOMAIN}',
                        password=password) as conn:

            # Смотрим, что всё хорошо и мы подключились
            if conn.result["description"] == "success":
                # Тут нужна более сложная логика. Надо будет извлечь из ldap данные пользователя(в том числе группу) и
                # проверить, что они соответсвуют тем, что в БД. Если нет - поправить БД и дальше уже выдать сущность
                # кстати, в ldap есть вроде как userID, так что можно будет по нему привязываться
                # results = conn.search(f"dc={LDAP_BASE_DOMAIN}",
                #                          search_scope= SUBTREE,
                #                          search_filter = "objectClass=posixAccount"
                # )

                return authenticate(request, username=username, password=password)
    except LDAPException:
        pass
    # Если ldap не смог - то значит и авторизация не успешная. Печально...
    return None


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_page = request.GET.get('next')

        user = _find_user(request, username, password)

        if user is not None:
            django.contrib.auth.login(request, user)
            if next_page:
                return redirect(next_page)
            return redirect(reverse('main'))
        else:
            return render(request, 'login.html', {'message': 'Неверный логин или пароль'})
    return render(request, 'login.html')


@login_required
def logout(request):
    django.contrib.auth.logout(request)
    return redirect(reverse('login'))
