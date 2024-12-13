from functools import wraps
import time
from django.shortcuts import redirect, render
import psycopg2

from django.core.handlers.wsgi import WSGIRequest
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

from sprut import settings

#декоратор для логов
def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        res = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Function {func.__name__}. Took {total_time:.4f} seconds')
        return res
    return wrapper


def get_schema_name_current_interface(interface_name: str):
    return "sprut_prom"


def login_required(request: WSGIRequest, interface_name: str):
    if request.method == "POST":
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            request.session['all_flg'] = '0'
            user = authenticate(username=username, password=password)
            # if user is not None:
            #     login(request, user)
            #     connect = get_connector_database()
            #     check_role = check_priv(connect, request, role_auditor, request.user.username, interface_name)
            #     for row in check_role:
            #         if row[0] == 1:
            #             return redirect('/' + interface_name + '/audit')
        return redirect('/' + interface_name + '/workpage')
            # else:
            #     messages.add_message(request, 80, "Invalid username or password")
        # else:
        #     messages.add_message(request, 80, "Invalid username or password")

    form = AuthenticationForm()

    return render(
        request,
        "registration/login.html",
        {
            "form": form
        }
    )


@timeit
def execute_sql(connect, sql_query, params=None) :
    if params is None:
        params = []
    connect.execute(sql_query, params)
    return connect


@timeit
def get_connector_database():
    connect_str = f"dbname={settings.PG_DBNAME} user={settings.PG_USER} password={settings.PG_PASS} host={settings.PG_HOST} port={settings.PG_PORT}"
    try:
        print(connect_str)
        return psycopg2.connect(connect_str)
    except Exception as e:
        print(f"Ошибка подключения: {e}")


def check_priv(connect, request, role_name, user_name, interface_name):
    try:
        check_role = execute_sql(
            connect.cursor(),
            interface_name,
            'check_priv_function',
            f'''select ''' + '''sprut_prom.check_proc_priv(%s, %s)''',
            [role_name, user_name]
        )
        res = check_role.fetchall()

    except Exception as e:
        res = None
        connect.rollback()
        messages.add_message(request, 80, str(e))
    
    return res