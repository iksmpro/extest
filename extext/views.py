from re import match

from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render

from .longjobs import extend_database, std_en_category_set


# std_en_category_set = frozenset((
#     "russia","world","ussr","economics","business",
#     "forces","science","sport","culture","media",
#     "style","travel","life","motor","realty"
# ))

def main_page(request):
    return render(request, 'index.html', {})

def create_new_task(request):
    email = request.POST.get('email')
    s_date = request.POST.get('startdate')
    e_date = request.POST.get('enddate')
    try:
        if not email or not match("[^@]+@[^@]+\.[^@]+", email):
            raise Exception('You dont specify email')
        elif not s_date:
            raise Exception('You dont specify start date')
        elif not e_date:
            raise Exception('You dont specify end date')
        s_date = timezone.datetime.strptime(s_date,'%d %B, %Y')
        e_date = timezone.datetime.strptime(e_date,'%d %B, %Y')
        if s_date > e_date:
            raise Exception('End date are smaller than start date')
        elif s_date > timezone.datetime.now():
            raise Exception('We cannot get news from the future')
        if request.POST.get('all'):
            category_set = ['']
        else:
            category_set = list(request.POST.keys() & std_en_category_set)
            if not len(category_set):
                raise Exception('You have not specify any category')
            elif len(category_set) == len(std_en_category_set):
                category_set = ['']
        extend_database.delay(s_date, min(e_date, timezone.datetime.now()), category_set, email)  # okay, here we go
    except Exception as e:
        return JsonResponse({'status':'error','message':str(e)})
    else:
        return JsonResponse({'status':'ok','message':'Your request has been accepted! Now expect email!'})
