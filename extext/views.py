from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render



def main_page(request):
    return render(request, 'index.html', {})

def create_new_task(request):
    print(request.POST.keys())
    return JsonResponse({'status':'ok','message':'Your request has been accepted! Now expect email!'})
    # return JsonResponse({'status':'error','message':'Your have some problems'})