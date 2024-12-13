"""
URL configuration for sprut project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, re_path

from sprut.views import (
    use_cases,
    views_dashboard,
    views_report,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(
        r"^(?P<interface_name>\w+)/login/$", use_cases.login_required
    ),
    re_path(
        r"^(?P<interface_name>\w+)/workpage/$", views_dashboard.workpage
    ),
    re_path(
        r"^(?P<interface_name>\w+)/report_settings/$", views_report.report_settings
    ),
    re_path(
        r"^(?P<interface_name>\w+)/report_settings/advanced_report_setiings/(?P<_id>\w+)/$", views_report.advanced_report_settings
    )
]
