from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("request/", views.create_request, name="create_request"),
    path("match/<int:request_id>/", views.request_detail, name="request_detail"),
    path("tutor/dashboard/", views.tutor_dashboard, name="tutor_dashboard"),
    path("interview/request/", views.create_interview_request, name="create_interview_request"),

]
