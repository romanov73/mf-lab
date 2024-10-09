import os
import django


if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
    django.setup()

    from web_page.logic.users_syncronisation import synchronise
    from base.settings import LDAP_ADMIN_DATA

    synchronise(LDAP_ADMIN_DATA["USER"],
                LDAP_ADMIN_DATA["PASSWORD"])
