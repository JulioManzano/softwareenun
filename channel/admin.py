from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from .models import CategoryMovie, Channel, Movie
from .services.iptv_importer import import_m3u

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    change_list_template = "admin/channel_changelist.html"

    list_display = ("id","name", "country", "category",)
    list_filter = ("country", "category", )
    search_fields = ("name",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-iptv/", self.admin_site.admin_view(self.import_iptv))
        ]
        return custom_urls + urls

    def import_iptv(self, request):
        urls = [
            "https://iptv-org.github.io/iptv/countries/ar.m3u",
            "https://iptv-org.github.io/iptv/countries/cl.m3u",
        ]

        for url in urls:
            import_m3u(url)

        self.message_user(request, "Canales importados correctamente", messages.SUCCESS)
        return redirect("../")
    
admin.site.register(Movie)
admin.site.register(CategoryMovie)