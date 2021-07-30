from django.utils import timezone


class TimezoneMiddleware(object):
    def process_request(self, request):
        if request.user.id:
            tzname = request.user.user_timezone
            if tzname:
                timezone.activate(tzname)
            else:
                timezone.deactivate()
