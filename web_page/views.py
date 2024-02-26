from django.shortcuts import render


def index(request):
    return render(request, 'create.html',
                  context={
                      "creating_type_name": "Курса",
                      "creating_url": "/"
                  })
