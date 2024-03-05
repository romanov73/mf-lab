from django.shortcuts import render




def index(request):
    return render(request, 'index.html')



def course_list(request):
    return render(request, 'course_list.html')
