from functools import wraps
import time
from django.shortcuts import redirect, render
import psycopg2

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

from sprut import settings
from sprut.views.params import role_auditor_name
import logging

logger = logging.getLogger(__name__)
logger.setLevel(level="INFO")


# декоратор для логов
def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        res = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        logger.info(f"Function {func.__name__}. Took {total_time:.4f} seconds")
        # connect = get_connector_database()
        # execute_sql(
        #     connect.commit,
        #     f"""insert into sprut_prom.logs(function_name, time) values({func.__name__}, {total_time:.4f})"""
        # )
        # connect.commit()
        return res

    return wrapper


@timeit
def get_schema_name_current_interface(interface_name: str):
    return "sprut_prom"


def login_required(request, interface_name: str):
    form = AuthenticationForm(request=request)

    if request.method == "POST":
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            request.session["all_flg"] = "0"

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                connect = get_connector_database()
                check_role = check_priv(
                    connect, request, role_auditor_name, request.user.username
                )

                # Проверяем роль пользователя и перенаправляем на соответствующую страницу
                for row in check_role:
                    if row[0] == 1:
                        return redirect(f"/{interface_name}/audit")

                return redirect(f"/{interface_name}/workpage")
            else:
                messages.error(request, "Неверное имя пользователя или пароль.")
                print("Invalid username or password during authentication.")
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
            print("Form is not valid:", form.errors)

    return render(request, "registration/login.html", {"form": form})


@timeit
def execute_sql(connect, sql_query, params=None):
    if params is None:
        params = []
    connect.execute(sql_query, params)
    return connect


@timeit
def get_connector_database():
    connect_str = f"dbname={settings.PG_DBNAME} user={settings.PG_USER} password={settings.PG_PASS} host={settings.PG_HOST} port={settings.PG_PORT}"
    try:
        return psycopg2.connect(connect_str)
    except Exception as e:
        print(f"Ошибка подключения: {e}")


def get_current_user(request):
    return request.user.username


def check_priv(connect, request, role_name, user_name):
    try:
        check_role = execute_sql(
            connect.cursor(),
            """select sprut_prom.check_priv_report(%s, %s)""",
            [role_name, user_name],
        )
        res = check_role.fetchall()

    except Exception as e:
        res = None
        connect.rollback()
        messages.add_message(request, 80, str(e))

    return res
