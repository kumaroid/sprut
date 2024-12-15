import datetime
from contextlib import closing
from typing import List, Any


from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import redirect, render
from django.contrib import messages

from sprut.views.use_cases import (
    execute_sql,
    get_connector_database,
    get_schema_name_current_interface,
    timeit,
)


@timeit
def get_list_reports(request, interface_name, connect):
    try:
        sql_query = (
            """SELECT id
            group_name,
            caption,
            alias,
            case when status = 0 then 'Enable' else 'Disable' end "status_report",
            register_dttm
            FROM """
            + get_schema_name_current_interface(interface_name)
            + """.report_ui_main order by group_name, caption"""
        )
        reports = execute_sql(connect.cursor(), sql_query).fetchall()
    except Exception as e:
        reports = None
        connect.rollback()
        messages.add_message(request, 80, str(e))

    return reports


@timeit
def archivate_report(connect, interface_name, alias):
    sql_query = f"""select {get_schema_name_current_interface(interface_name)}.archive_report(%s)"""
    execute_sql(connect.cursor(), sql_query, [alias])
    connect.commit()


@timeit
def report_settings(request: WSGIRequest, interface_name: str):
    try:
        connect = get_connector_database()
        if request.method == "POST":
            if "archive_report" in request.POST:
                alias = request.POST["alias"]
                archivate_report(connect, interface_name, alias)
                return redirect("/" + interface_name + "/report_data/archive_reports")

        reports = get_list_reports(request, interface_name, connect)
        return render(
            request,
            "page/report_settings.html",
            {
                "reports": reports,
                "interface_name": interface_name,
            },
        )
    except Exception as e:
        print(str(e))
        return render(request, "page/500.html")


@timeit
def _get_changeable_params_data(connect, interface_name: str, _id: str) -> List[Any]:  # type: ignore
    sql_query = (
        """SELECT caption,
            comment,
            proc_name,
            status,
            group_name,
            url_details,
            report_version
            FROM """
        + get_schema_name_current_interface(interface_name)
        + """.report_ui_main WHERE id = %s"""
    )

    changeable_params_data = execute_sql(connect.cursor(), sql_query, [_id]).fetchall()

    return changeable_params_data


@timeit
def _get_additional_report_params(connect, interface_name: str, _id: str) -> List[Any]:
    sql_query = (
        """SELECT alias,
            table_schema,
            table_name,
            register_dttm,
            register_user,
            id
            FROM """
        + get_schema_name_current_interface(interface_name)
        + """.report_ui_main where id = %s"""
    )

    additional_params_data = execute_sql(connect.cursor(), sql_query, [_id]).fetchall()

    return additional_params_data


@timeit
def _get_alias_for_id(connect, interface_name: str, _id: str) -> str:
    alias = ""
    alias_data = execute_sql(
        connect.cursor(),
        "SELECT alias FROM "
        + get_schema_name_current_interface(interface_name)
        + ".report_ui_main where id = %s",
        [_id],
    ).fetchall()
    for i in alias_data:
        alias = i[0]

    return alias


@timeit
def _get_code_data(connect, interface_name: str, _id: str) -> str:
    alias = _get_alias_for_id(connect, interface_name, _id)
    code_data = execute_sql(
        connect.cursor(),
        """SELECT id, alias, code, insert_dttm, table_schema, table_name FROM """
        + get_schema_name_current_interface(interface_name)
        + ".report_ui_code where code is not null and alias = %s",
        [alias],
    ).fetchall()

    return code_data


@timeit
def _get_last_report_id(connect, interface_name: str) -> str:
    _id = ""
    id_data = execute_sql(
        connect.cursor(),
        "SELECT MAX(id) FROM "
        + get_schema_name_current_interface(interface_name)
        + ".report_ui_main",
    ).fetchall()

    for i in id_data:
        _id = i[0]

    return _id


@timeit
def _get_report_filters(connect, interface_name: str, alias: str) -> List[Any]:
    sql_query = (
        """SELECT id,
                    alias,
                    username,
                    profile_name,
                    operator,
                    column_name,
                    column_type,
                    operand,
                    insert_dttm,
                    group_id
                    FROM """
        + get_schema_name_current_interface(interface_name)
        + """.report_ui_filters where alias = %s"""
    )

    filters_data = execute_sql(connect.cursor(), sql_query, [alias]).fetchall()

    return filters_data


@timeit
def advanced_report_settings(request, interface_name, _id):
    try:
        is_new_data_in_report = False
        if request.method == "POST":
            if "btn_save_filters" in request.POST:
                connect = get_connector_database()
                alias = _get_alias_for_id(connect, interface_name, _id)

                group_id = request.POST["group_id"]
                column_name = request.POST["column_name"]

                try:
                    with closing(connect.cursor()) as cc:
                        cc.execute(
                            """UPDATE """
                            + get_schema_name_current_interface(interface_name)
                            + """.report_ui_filters """
                            + """SET group_id = %s,
                                column_name = %s
                                WHERE alias = %s""",
                            [group_id, column_name, alias],
                        )
                    connect.commit()
                    messages.add_message(
                        request, 80, f"Фильтры отчета обновлены id: {_id}"
                    )
                    return redirect("/" + interface_name + "/report_settings")
                except Exception as e:
                    print(str(e))
                    connect.rollback()
                    messages.add_message(request, 80, str(e))

            if "bt_save_sql" in request.POST:
                connect = get_connector_database()
                alias = _get_alias_for_id(connect, interface_name, _id)

                report_sql = request.POST["report_sql"]
                report_sql_table_schema = request.POST["report_sql_table_schema"]
                report_sql_table_name = request.POST["report_sql_table_name"]

                if report_sql is not None and report_sql.split() != []:
                    try:
                        with closing(connect.cursor()) as cc:
                            cc.execute(
                                """UPDATE """
                                + get_schema_name_current_interface(interface_name)
                                + """.report_ui_code
                                    SET code = %s,
                                    table_schema = %s,
                                    table_name = %s, 
                                    insert_dttm = now(),
                                    WHERE alias = %s and id = %s""",
                                [
                                    report_sql,
                                    report_sql_table_schema,
                                    report_sql_table_name,
                                    alias,
                                    _id,
                                ],
                            )
                        connect.commit()
                        messages.add_message(
                            request, 80, f"Код сборки отчета обновлен id: {_id}"
                        )
                        return redirect(
                            "/"
                            + interface_name
                            + "/report_settings/advanced_report_settings/"
                            + _id
                        )
                    except Exception as e:
                        connect.rollback()
                        messages.add_message(request, 80, str(e))
                else:
                    messages.add_message(
                        request, 80, f"Код сборки отчета не может быть пустым id: {_id}"
                    )

            if "bt_save" in request.POST:
                connect = get_connector_database()
                report_caption = request.POST["report_caption"]
                report_comment = request.POST["report_comment"]
                report_proc_name = request.POST["report_proc_name"]
                report_status = request.POST["report_status"]
                report_group_name = request.POST["report_group_name"]
                report_url_details = request.POST["report_url_details"]
                report_version = request.POST["report_version"]
                try:
                    with closing(connect.cursor()) as cc:
                        sql_query = (
                            """UPDATE """
                            + get_schema_name_current_interface(interface_name)
                            + """.report_ui_main
                                SET caption = %s,
                                    comment = %s,
                                    proc_name = %s,
                                    status = %s,
                                    group_name = %s,
                                    url_details = %s,
                                    report_version  = %s
                                WHERE id = %s """
                        )
                        cc.execute(
                            sql_query,
                            [
                                report_caption,
                                report_comment,
                                report_proc_name,
                                report_status or 0,
                                report_group_name,
                                report_url_details,
                                report_version or 1,
                                _id,
                            ],
                        )
                    is_new_data_in_report = True
                    connect.commit()
                    messages.add_message(
                        request, 80, f"Параметры отчета обновлены id: {_id}"
                    )
                    return redirect("/" + interface_name + "/report_settings")
                except Exception as e:
                    print(str(e))
                    connect.rollback()
                    messages.add_message(request, 80, str(e))

        connect = get_connector_database()
        page_name = "Редактор параметров отчета"

        alias = _get_alias_for_id(connect, interface_name, _id)
        report_sql = _get_code_data(connect, interface_name, _id)
        report_filters = _get_report_filters(connect, interface_name, alias)
        changeable_params = _get_changeable_params_data(connect, interface_name, _id)
        additional_params = _get_additional_report_params(connect, interface_name, _id)
        return render(
            request,
            "page/advanced_report_settings.html",
            {
                "id": _id,
                "alias": alias,
                "page_name": page_name,
                "report_sql_data": report_sql,
                "report_filters": report_filters,
                "interface_name": interface_name,
                "changeable_params": changeable_params,
                "additional_params": additional_params,
                "is_new_data_in_report": is_new_data_in_report,
            },
        )
    except Exception as e:
        print(str(e))
        return render(request, "page/500.html")


@timeit
def _get_last_report_id(connect, interface_name):
    _id = ""
    id_data = execute_sql(
        connect.cursor(),
        """select MAX(id) from """
        + get_schema_name_current_interface(interface_name)
        + ".report_ui_main",
    ).fetchall()
    for nn in id_data:
        _id = nn[0]

    return _id


@timeit
def _get_data_from_report(connect, request, interfce_name, _id):
    try:
        sql_query = f"""SELECT caption, alias, comment, table_schema, table_name, proc_name, status, register_dttm, register_user, group_name, url_details, report_version, download_flg
	        FROM {get_schema_name_current_interface(interfce_name)}.report_ui_main where id = %s"""

        data = execute_sql(connect.cursor(), sql_query, [_id]).fetchall()
    except Exception as e:
        data = None
        connect.rollback()
        messages.add_message(request, 80, str(e))
    return data


@timeit
def create_report(request, interface_name):
    try:
        sql_query = ""
        connect = get_connector_database()
        _id = str(int(_get_last_report_id(connect, interface_name)) + 1)
        request.method = "POST"
        if request.method == "POST":
            if "bt_save_new_report" in request.POST:
                report_caption = request.POST["report_caption"]
                report_comment = request.POST["report_comment"]
                report_proc_name = request.POST["report_proc_name"]
                report_status = request.POST["report_status"]
                report_group_name = request.POST["report_group_name"]
                report_url_details = request.POST["report_url_details"]
                report_alias = request.POST["report_alias"]
                report_table_schema = request.POST["report_table_schema"]
                report_table_name = request.POST["report_table_name"]
                report_register_user = request.POST["report_register_user"]
                report_version = request.POST["report_version"]
                report_download_flg = request.POST["report_download_flg"]
                try:
                    sql_query = (
                        """INSERT INTO """
                        + get_schema_name_current_interface(interface_name)
                        + """.report_ui_main(caption, alias, comment, table_schema, table_name,
                                        proc_name, status, register_dttm, register_user, group_name,
                                         url_details, report_version, download_flg, id) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                                %s, %s, %s) """
                    )
                    with closing(connect.cursor()) as cc:
                        cc.execute(
                            sql_query,
                            [
                                report_caption,
                                report_alias,
                                report_comment,
                                report_table_schema,
                                report_table_name,
                                report_proc_name,
                                report_status or 0,
                                datetime.datetime.now(),
                                report_register_user,
                                report_group_name,
                                report_url_details or 0,
                                report_version or 1,
                                report_download_flg or 1,
                                _id,
                            ],
                        )
                    connect.commit()
                    messages.add_message(request, 80, "Создан отчет [id: " + _id + "]")
                    return redirect("/" + interface_name + "/report_settings/")
                except Exception as e:
                    print(f"Ошибка выполнения SQL-запроса: {str(e)}")
                    connect.rollback()
                    messages.add_message(request, 80, str(e))

        connect = get_connector_database()

        page_name = "Создание отчета"

        data_from_report = _get_data_from_report(connect, request, interface_name, _id)

        return render(
            request,
            "page/report_create.html",
            {
                "new_report_id": _id,
                "page_name": page_name,
                "sql_query": sql_query,
                "interface_name": interface_name,
                "data_from_report": data_from_report,
            },
        )
    except Exception:
        return render(request, "page/500.html")


@timeit
def _get_archive_reports(connect, interface_name):
    sql_query = f"""SELECT hist_id, caption, alias, comment, table_schema, table_name,
         proc_name, status, register_dttm, register_user, group_name, url_details, report_version, download_flg
	FROM {get_schema_name_current_interface(interface_name)}.report_ui_main_arch"""

    data = execute_sql(connect.cursor(), sql_query).fetchall()

    return data


@timeit
def unarchive_report(connect, interface_name, _id):
    sql_query = f"""SELECT {get_schema_name_current_interface(interface_name)}.recovery_report(%s)"""
    execute_sql(connect.cursor(), sql_query, [_id])
    connect.commit()


@timeit
def archive_reports(request, interface_name):
    try:
        connect = get_connector_database()
        archive_reports = _get_archive_reports(connect, interface_name)
        if request.method == "POST":
            if "recovery_report" in request.POST:
                _id = request.POST["report_id"]
                unarchive_report(connect, interface_name, _id)
                return redirect("/" + interface_name + "/report_settings")
        return render(
            request,
            "page/archive_reports.html",
            {"interface_name": interface_name, "archive_reports": archive_reports},
        )
    except Exception as e:
        print(str(e))
        return render(request, "page/500.html")
