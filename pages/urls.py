from django.urls import path
from django.views.generic.base import TemplateView
from pages.views import HomePageView

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="pages/robots.txt",
            content_type="text/plain",
        ),
        name="robots",
    ),
]
