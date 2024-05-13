from ldap3 import Connection, SUBTREE
from ldap3.core.exceptions import LDAPException

from web_page.models import User

LDAP_HOST_NAME: str = "ldap://lk.ustu:389"  # Адрес ldap сервера. Да, это IP ноута в моей локалке.
LDAP_BASE_DOMAIN: str = 'ams,dc=ulstu,dc=ru'  # Базовый домен организации. В политехе, очевидно, другой
LDAP_ACCOUNT_OU: str = "accounts"
LDAP_ACCOUNT_NAME_TYPE: str = "uid"
LDAP_GROUP_OU: str = "groups"
LDAP_GROUP_NAME_TYPE: str = "cn"
LDAP_STUDENTS_GROUP_NAME: str = "LEARNING"
LDAP_TEACHERS_GROUP_NAME: str = "WORKING"


def _prepare_database():
    """
    Метод служит для подготвки БД к работе. По большому счёту он просто ставит флаг в false,
     чтобы потом можно было почистить базу от тех, кото на LDAP больше нет
    """
    User.objects.filter(is_superuser=0).update(is_present=False)  # todo Возможно тут нужен промежуточный метод get_all


def _database_after_clear():
    """
    Непосредственно чистит БД от тех, котого больше с нами нет. Работает в паре с _prepare_database и ОБЯЗАТЕЛЬНО
    должен быть запущен после всех операций чтения с LDAP и записи в БД. По факту, просто удаляет из локальной БД
    всех, у которых флаг в false(то есть их нет на LDAP)
    """
    User.objects.filter(is_present=False).delete()


def _load_students_from_LDAP_group(conn: Connection) -> list[str] | None:
    """
    Метод для получения из LDAP списка логинов всех пользователей, которые являются студентами. Возвращает None,
    если что-то пошло не так
    """
    # todo Возвращаем список всех студентов (по полю uid из группы LDAP_STUDENTS_GROUP_NAME)
    res = conn.search(
        search_base="cn=LEARNING,ou=groups,dc=ams,dc=ulstu,dc=ru",
        search_filter="(memberUid=*)",
        search_scope=SUBTREE,
        attributes=['memberUid']
    )

    return conn.entries[0].memberUid


def _load_teachers_from_LDAP_group(conn: Connection) -> list[str] | None:
    """
    Метод для получения из LDAP списка логинов всех пользователей, которые являются преподавателями. Возвращает None,
    если что-то пошло не так
    """
    # todo Возвращаем список всех препожавателей (по полю uid из группы LDAP_TEACHERS_GROUP_NAME)
    res = conn.search(
        search_base="cn=WORKING,ou=groups,dc=ams,dc=ulstu,dc=ru",
        search_filter="(memberUid=*)",
        search_scope=SUBTREE,
        attributes=['memberUid']
    )

    return conn.entries[0].memberUid


def _load_full_name_from_LDAP(conn: Connection, username: str) -> str | None:
    """
    Получает полное имя пользователя(студент/преподаватель) по его логину.
    Реализация примерная, на основе теоретических знаний.
    Если имени не удалось получить - возвращаем None
    """
    # todo Может быть сюда try -expect ???
    conn.search(
        search_base=f'uid={username},ou={LDAP_ACCOUNT_OU},dc={LDAP_BASE_DOMAIN}',
        search_filter='(objectClass=*)',
        search_scope=SUBTREE,
        attributes=["cn"]
    )
    # todo Проверить, что мы получили ответ и что он успешный... Если нет - return None
    name: str = conn.entries[0].cn  # todo Получить имя из ответа(я не знаю, как конкретно это сделать, ибо не вижу структуры.
    if name is not None and name != "":
        return name
    return None


def _synch_single_user(conn: Connection, username: str, is_teacher: bool) -> str | None:
    """
    Метод синхронизации одного студента с LDAP. Получает логин, и флаг: преподаватель или нет.
    Если ошибок по ходу нет, и при этом пользователь не отличается от того, что в БД - возвращаем None
    Если есть ошибки - возвращаем её текстом
    Если данные в БД различаются - возвращаем текстом, что мы поменяли для пользоавтеля такое-то поле на значение
    """
    try:
        full_user_name: str = _load_full_name_from_LDAP(conn, username)
        if full_user_name is None:
            return f"cannot load full name for user {username}"

        user = User.objects.filter(username=username).first()

        if user is not None:
            res = ""
            if user.full_name != full_user_name:
                user.full_name = full_user_name
                res += f"full name changed to {full_user_name} "

            if user.is_teacher != is_teacher:
                user.is_teacher = is_teacher
                res += f"is teacher changed to {is_teacher} "

            user.is_present = True
            user.save()
            if res != "":
                return f"{username}:{res}"
            else:
                return None
        else:
            user = User(
                username=username,
                full_name=full_user_name,
                is_teacher=is_teacher
            )
            user.save()
            return f"new {username}"
    except Exception as e:
        return f"ERROR on {username}: {e}"


def _synch_user(conn: Connection, users: list[str], is_teacher: bool) -> str:
    """
    Просто обёртка, чтобы было удобнее. По факту получает список пользователей и последовательно их синхронизирует.
    Возвращает 'Логи': если что-то поменяли у пользователя - это тут будет,
    так же если с каким-то пользователем что-то не вышло - тоже будет отражено
    """
    if users is None or len(users) == 0:
        return "loaded list is null or empty"

    res: str = ""
    for user in users:
        try:
            tmp = _synch_single_user(conn, user, is_teacher)
            if tmp is not None:
                res += f"{tmp}\n"
        except Exception as e:
            res = f"ERROR for {user}: {e}"

    return res


def synchronise(admin_login: str, admin_password: str) -> str:
    """
    Основной метод синхронизации. Он требует на вход креды админа в LDAP, но использует его только для чтения.
    Возвращает "Логи" работы, чтобы можно было понимать, что и как пошло, во время синхронизации.
    """
    try:
        # Подключаемся к LDAP под доменом LDAP_BASE_DOMAIN и именем пользователя username
        with Connection(LDAP_HOST_NAME,
                        user=f'{admin_login}',
                        password=admin_password, check_names=True) as conn:

            # Смотрим, что всё хорошо и мы подключились
            if conn.result["description"] == "success":
                _prepare_database()

                res: str = ""
                res += f"Students:\n{_synch_user(conn, _load_students_from_LDAP_group(conn), False)}"
                res += f"Teachers:\n{_synch_user(conn, _load_teachers_from_LDAP_group(conn), True)}"

                _database_after_clear()
                return res
            else:
                return "Cannot connect ot LDAP"

    except LDAPException as e:
        return f"ERROR on connection to LDAP: {e}"
    except Exception as e:
        return f"SOME ERROR: {e}"


if __name__ == '__main__':
    with Connection(LDAP_HOST_NAME,
                    user=f'',
                    password='', check_names=True) as conn:
        _load_students_from_LDAP_group(conn)
