from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render



def main_page(request):
    # tasks = Task.objects.order_by('-create_time').all()
    # new_time = calc_last_update(tasks)
    # all(task.__str__() for task in tasks)
    return render(request, 'index.html', {})

def create_new_task(request):
    # new_task = Task(create_time=timezone.now())
    # new_task.save()
    # this_module.public_queue.put({"status":0, "message":"wake up"})
    return JsonResponse({'status':'ok'})