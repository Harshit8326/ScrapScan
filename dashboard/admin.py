from django.contrib import admin
from .models import DigitalPassport

@admin.register(DigitalPassport)
class DigitalPassportAdmin(admin.ModelAdmin):
    list_display = ('item_id', 'primary_material', 'status', 'timestamp')
    list_filter = ('status', 'primary_material')
    search_fields = ('item_id', 'primary_material')