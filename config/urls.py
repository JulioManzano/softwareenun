"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.views.decorators.csrf import csrf_exempt
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
import graphene
from channel.scheme import  Query as ChannelQuery
from core.scheme import Query as CoreQuery
from graphene_django_extras import all_directives
from graphene_file_upload.django import FileUploadGraphQLView

class Query(ChannelQuery, CoreQuery,graphene.ObjectType):
    pass

#class Mutation(graphene.ObjectType):
#    pass

#schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False, directives=all_directives)
schema = graphene.Schema(
    query=Query,
    auto_camelcase=False,
    directives=all_directives,
)

class DebugView(FileUploadGraphQLView):
    def dispatch(self, request, *args, **kwargs):       
        return super().dispatch(request, *args, **kwargs)
    

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path(
        "graphql/",
        csrf_exempt(DebugView.as_view(graphiql=True, schema=schema)),
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )