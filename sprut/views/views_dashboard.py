from django.shortcuts import render

from sprut.views.use_cases import timeit


@timeit
def workpage(request, interface_name):
    return render(request, "page/workpage.html", {"interface_name": interface_name})
