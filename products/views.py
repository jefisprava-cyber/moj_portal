from django.http import HttpResponse

def home(request):
    return HttpResponse("Prebieha údržba. Spusti reset DB.")