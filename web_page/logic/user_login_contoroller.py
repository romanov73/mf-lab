import django.contrib.auth
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from ldap3 import Connection, SUBTREE, LEVEL
from ldap3.core.exceptions import LDAPException

from web_page.models import User

LDAP_HOST_NAME: str = "ldap://lk.ustu:389"  # Адрес ldap сервера. Да, это IP ноута в моей локалке.
LDAP_BASE_DOMAIN: str = 'ams,dc=ulstu,dc=ru'  # Базовый домен организации. В политехе, очевидно, другой
LDAP_OU_TEXT: str = "accounts"


def _find_user(request, username: str, password: str) -> User | None:
    """
    Приватный метод получения пользователя с учётом Ldap. Предполагается, что именно его мы будем расширять
    """
    try:
        # Подключаемся к LDAP под доменом LDAP_BASE_DOMAIN и именем пользователя username
        with Connection(LDAP_HOST_NAME,
                        user=f'uid={username},ou={LDAP_OU_TEXT},dc={LDAP_BASE_DOMAIN}',
                        password=password) as conn:

            # Смотрим, что всё хорошо и мы подключились
            if conn.result["description"] == "success":
                user = User.objects.filter(username=username).first()
                if user is None:
                    pass
                    # todo Как насчёт того, чтобы в случае, если авторизация прошла,
                    #  но при этом в локальной БД ничего нет, запускать синхронизацию
                return user
    except LDAPException as e:
        print(e)
    # Если ldap не смог - то используем внутреннюю БД. По многочисленным заявкам трудящихся.
    return authenticate(request, username=username, password=password)


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
