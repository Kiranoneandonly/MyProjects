from django.contrib import admin
from holidays.models import Holiday


class HolidayAdmin(admin.ModelAdmin):
    list_display = ['holiday_name', 'holiday_date', 'description', 'is_deleted']
    readonly_fields = ('created', 'modified')
    search_fields = ('holiday_name', 'holiday_date', 'description', )
    ordering = ('holiday_date', )

admin.site.register(Holiday, HolidayAdmin)
