from contextlib import closing
from typing import List, Tuple, Any

from django.core.handlers.wsgi import WSGIRequest
from django.db import connection
from django.shortcuts import redirect, render
from django.contrib import messages

from sprut.views.use_cases import check_priv, execute_sql, get_connector_database, get_schema_name_current_interface, timeit

from sprut.views.params import role_admin_name, role_auditor_name


@timeit
def get_list_reports(connect, request, interface_name):
    try:
        sql_query = """SELECT id
            group_name,
            caption,
            alias,
            case when status = 0 then 'Enable' else 'Disable' end "status_report",
            register_dttm
            FROM """ + get_schema_name_current_interface(interface_name) + """.report_ui_main order by group_name, caption"""
        reports_i = execute_sql(
            connect.cursor(),
            interface_name,
            sql_query,
        ).fetchall()
        reports = connect.cursor().execute(sql_query).fetchall()
        print(reports, reports_i)
    except Exception as e:
        reports = None
        connect.rollback()
        messages.add_message(request, 80, str(e))
    
    return reports


@timeit
def report_settings(request: WSGIRequest, interface_name: str):
    connect = get_connector_database()
    # session_role_all = check_priv(connect, request, role_admin_name, "user", interface_name)
    # admin_flg = 0
    # for i in session_role_all:
    #     if i[0] == 1 or i[0] == 3:
    #         admin_flg = 1
    # if admin_flg == 0:
    #     return redirect('/' + interface_name + '/workpage')
    
    # session_role_auditor = check_priv(connect, request, role_auditor_name, "user", interface_name)
    # for i in session_role_auditor:
    #     if i[0] == 1:
    #         return redirect('/' + interface_name + '/workpage')
        
    # has_permission = True if admin_flg == 1 else False

    reports = get_list_reports(connect, request, interface_name)
    print(reports, connect)
    return render(
        request,
        "page/report_settings.html",
        {
            "reports": reports,
            "interface_name": interface_name,
     #       "has_permission": has_permission
        }
    )


@timeit
def _get_changeable_params_data(connect: connection, interface_name: str, _id: str) -> List[Any]: # type: ignore
    sql_query = (
        """SELECT caption,
            comment,
            table_report_dt,
            table_order_col,
            proc_name,
            status,
            group_name,
            flg_online,
            flg_sequrity,
            flg_useparam,
            url_details,
            use_datefilter,
            user_filter,
            source_flg,
            visible_info,
            visible_search,
            collapse_column,
            collapse_length,
            collapse_flag,
            report_version
            FROM """
        + get_schema_name_current_interface(interface_name)
        + f""".report_ui_main where id = %s"""
    )

    changeable_params_data = execute_sql(
        connect.cursor(),
        interface_name,
        sql_query,
        [_id]
    ).fetchall()

    return changeable_params_data


@timeit
def _get_additional_report_params(connect: connection, interface_name: str, _id: str) -> List[Any]:
    sql_query = (
        """SELECT alias,
            table_schema,
            table_name,
            table_column,
            register_dttm,
            register_user,
            filter_column,
            filter_hint,
            flg_export,
            table_column_export,
            table_report_dt2,
            objtype,
            download_flg,
            id
            FROM """
        + get_schema_name_current_interface(interface_name)
        + f""".report_ui_main where id = %s"""
    )

    additional_params_data = execute_sql(
        connect.cursor(),
        interface_name,
        sql_query,
        [_id]
    ).fetchall()

    return additional_params_data


@timeit
def _get_alias_for_id(connect: connection, interface_name: str, _id: str) -> str:
    alias = ''
    alias_data = execute_sql(
        connect.cursor(),
        interface_name,
        "SELECT alias FROM " + get_schema_name_current_interface(interface_name) + ".report_ui_main where id = %s",
        [_id]
    ).fetchall()
    for i in alias_data:
        alias = i[0] 

    return alias


@timeit
def _get_code_data(connect: connection, interface_name: str, _id: str) -> str:
    alias = _get_alias_for_id(connect, interface_name, _id)
    code_data = execute_sql(
        connect.cursor(),
        interface_name,
        """SELECT id, alias, code, insert_dttm, step_id, page_alias, table_schema, table_name, level FROM """
        + get_schema_name_current_interface(interface_name)
        + ".report_ui_code where code is not null and alias = %s",
        [alias]
    ).fetchall()

    return code_data


@timeit
def _get_last_report_id(connect: connection, interface_name: str) -> str:
    _id = ''
    id_data = execute_sql(
        connect.cursor(),
        interface_name,
        "SELECT MAX(id) FROM " + get_schema_name_current_interface(interface_name) + ".report_ui_main"
    ).fetchall()

    for i in id_data:
        _id = i[0]

    return _id


@timeit
def _get_report_filters(connect: connection, interface_name: str, alias: str) -> List[Any]:
    sql_query = """SELECT id,
                    alias,
                    username,
                    profile_name,
                    operator,
                    column_name,
                    column_type,
                    operand,
                    insert_dttm,
                    "grouping",
                    param_alias,
                    column_default,
                    column_default_flg,
                    readonly_flg,
                    group_id
                    FROM """ + get_schema_name_current_interface(interface_name) + """.report_ui_filters where alias = %s"""
    
    filters_data = execute_sql(
        connect.cursor(),
        interface_name,
        sql_query,
        [alias]
    ).fetchall()

    return filters_data


@timeit
def advanced_report_settings(request, interface_name, _id):
    is_new_data_in_report = False

    if request.method == "POST":
        if "btn_save_filters" in request.POST:
            connect = get_connector_database()
            alias = _get_alias_for_id(connect, interface_name, _id)

            group_name = request.POST["group_name"]
            column_name = request.POST["column_name"]
            column_data = request.POST["column_data"]
            column_caption = request.POST["column_caption"]
            position = request.POST["position"]

            try:
                with closing(connect.cursor()) as cc:
                    cc.execute(
                        """UPDATE """
                        + get_schema_name_current_interface(interface_name)
                        + """.report_ui_filters"""
                        + """SET group_name = %s,
                            column_name = %s,
                            column_data = %s,
                            column_caption = %s,
                            postion = %s
                            WHERE alias = %s""",
                            [
                                group_name,
                                column_name,
                                column_data,
                                column_caption,
                                position,
                                alias
                            ]
                    )
                connect.commit()
                messages.add_message(request, 80, f"Фильтры отчета обновлены id: {_id}")
                return redirect('/' + interface_name + '/report_settings/advanced_report_settings/' + _id)    
            except Exception as e:
                connect.rollback()
                messages.add_message(request, 80, str(e))
        
        query_id = list(request.POST.keys())[-1].split('_')[-1]
        if f"bt_save_sql_{query_id}" in request.POST:
            connect = get_connector_database()
            alias = _get_alias_for_id(connect, interface_name, _id)

            report_sql = request.POST[f"report_sql_{query_id}"]
            report_sql_step_id = request.POST[f"report_sql_{query_id}"]
            report_sql_table_schema = request.POST[f"report_sql_table_schema_{query_id}"]
            report_sql_table_name = request.POST[f"report_sql_table_name_{query_id}"]
            report_sql_level = request.POST[f"report_sql_level_{query_id}"]

            if report_sql is not None and report_sql.split() != []:
                try:
                    with closing(connect.cursor()) as cc:
                        cc.execute(
                            """UPDATE """
                            + get_schema_name_current_interface(interface_name)
                            + """.report_ui_code
                                SET code = %s,
                                step_id = %s,
                                table_schema = %s,
                                table_name = %s, 
                                insert_dttm = now(),
                                level = %s
                                WHERE alias = %s and id = %s""",
                                
                                [
                                    report_sql,
                                    report_sql_step_id,
                                    report_sql_table_schema,
                                    report_sql_table_name,
                                    report_sql_level,
                                    alias,
                                    query_id
                                ]
                        )
                    connect.commit()
                    messages.add_message(request, 80, f"Код сборки отчета обновлен id: {_id}")
                    return redirect('/' + interface_name + '/report_settings/advanced_report_settings/' + _id)
                except Exception as e:
                    connect.rollback()
                    messages.add_message(request, 80, str(e))
            else:
                messages.add_message(request, 80, f"Код сборки отчета не может быть пустым id: {_id}")

        if "bt_save" in request.POST:
            connect = get_connector_database()

            report_caption = request.POST["report_caption"]
            report_comment = request.POST["report_comment"]
            report_table_dt = request.POST["report_table_dt"]
            report_table_order_col = request.POST["report_table_order_col"]
            report_proc_name = request.POST["report_proc_name"]
            report_status = request.POST["report_status"]
            report_group_name = request.POST["report_group_name"]
            report_flg_online = request.POST["report_flg_online"]
            report_flg_security = request.POST["report_flg_security"]
            report_flg_useparam = request.POST["report_flg_useparam"]
            report_url_details = request.POST["report_url_details"]
            report_use_datefilter = request.POST["report_use_datefilter"]
            report_user_filter = request.POST["report_user_filter"]
            report_source_flg = request.POST["report_source_flg"]
            report_visible_info = request.POST["report_visible_info"]
            report_visible_search = request.POST["report_visible_search"]
            report_collapse_column = request.POST["report_collapse_column"]
            report_collapse_length = request.POST["report_collapse_length"]
            report_collapse_flag = request.POST["report_collapse_flag"]
            report_version = request.POST["report_version"]

            try:
                with closing(connect.cursor()) as cc:
                    cc.execute(
                        """UPDATE """
                        + get_schema_name_current_interface(interface_name)
                        + """.report_ui_main
                            SET caption = %s,
                            "comment" = %s,
                            table_report_dt = %s,
                            table_order_col = %s,
                            proc_name = %s,
                            status = %s, 
                            register_dttm = now(),
                            group_name = %s,
                            flg_online = %s,
                            flg_sequrity = %s,
                            flg_useparam = %s,
                            url_details = %s,
                            use_datefilter = %s,
                            user_filter = %s,
                            source_flg = %s,
                            visible_info = %s,
                            visible_search = %s,
                            collapse_column = %s,
                            collapse_length = %s,
                            collapse_flag = %s,
                            report_version = %s
                            WHERE id = %s """,
                            [
                                report_caption,
                                report_comment,
                                report_table_dt,
                                report_table_order_col,
                                report_proc_name,
                                report_status,
                                report_group_name,
                                report_flg_online,
                                report_flg_security,
                                report_flg_useparam,
                                report_url_details,
                                report_use_datefilter,
                                report_user_filter,
                                report_source_flg,
                                report_visible_info,
                                report_visible_search,
                                report_collapse_column,
                                report_collapse_length,
                                report_collapse_flag,
                                report_version,
                                _id
                            ]
                    )
                is_new_data_in_report = True
                connect.commit()
                messages.add_message(request, 80, f"Параметры отчета обновлены id: {_id}")
                return redirect('/' + interface_name + '/report_settings/advanced_report_settings/' + _id)
            except Exception as e:
                connect.rollback()
                messages.add_message(request, 80, str(e))
        
    connect  = get_connector_database()
    page_name = 'Редактор параметров отчета'
    session_role_all = check_priv(connect, request, role_admin_name, "user", interface_name)
    admin_flg = 0
    for i in session_role_all:
        if i[0] == 1 or i[0] == 3:
            admin_flg = 1
    if admin_flg == 0:
        return redirect('/' + interface_name + '/workpage')
    
    session_role_auditor = check_priv(connect, request, role_auditor_name, "user", interface_name)
    for i in session_role_auditor:
        if i[0] == 1:
            return redirect('/' + interface_name + '/workpage')
        
    has_permission = True if admin_flg == 1 else False

    alias = _get_alias_for_id(connect, interface_name, _id)
    report_sql = _get_code_data(connect, interface_name, _id)
    report_filters = _get_report_filters(connect, interface_name, alias)
    changeable_params = _get_changeable_params_data(connect, interface_name, _id)
    additional_params = _get_additional_report_params(connect, interface_name, _id)

    return render(
        request,
        'page/advanced_report_settings.html',
        {
            "id": _id,
            "alias": alias,
            "page_name": page_name,
            "sql_query": report_sql,
            "report_filters": report_filters,
            "interface_name": interface_name,
            "changeable_params": changeable_params,
            "additional_params": additional_params,
            "is_new_data_in_report": is_new_data_in_report
        }
    )

    
