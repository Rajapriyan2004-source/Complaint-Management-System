
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # STUDENT
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('complaint/new/', views.submit_complaint, name='submit_complaint'),

    # ADMIN DASHBOARD
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # UPDATE COMPLAINT STATUS
    path(
        'update-status/<int:complaint_id>/',
        views.update_status,
        name='update_status'
    ),

    # STUDENT ACCOUNT APPROVAL
    path(
        'review-student-request/<int:request_id>/',
        views.review_student_request,
        name='review_student_request'
    ),

    # ADMIN ACCOUNT APPROVAL
    path(
        'review-admin-request/<int:request_id>/',
        views.review_admin_request,
        name='review_admin_request'
    ),

    # CREATE ADMIN ACCOUNT
    path(
        'create-admin/',
        views.create_admin,
        name='create_admin'
    ),

    # ADMIN ACCESS REQUEST
    path(
        'request-admin-access/',
        views.request_admin_access,
        name='request_admin_access'
    ),
]
