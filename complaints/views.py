
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Complaint, AdminRequest, StudentRequest
from .forms import RegisterForm, ComplaintForm


def is_admin(user):
    return user.is_authenticated and user.is_staff


def is_main_admin(user):
    return user.is_authenticated and user.is_superuser


def home(request):
    return render(request, 'home.html')


# STUDENT REGISTRATION
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.is_staff = False
            new_user.is_superuser = False
            new_user.save()

            StudentRequest.objects.create(
                user=new_user,
                status='Pending'
            )

            messages.success(
                request,
                'Registration submitted. Wait for Admin approval.'
            )
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


# LOGIN
def login_view(request):
    is_admin_login = (
        request.GET.get('next') == '/admin-dashboard/'
        or request.POST.get('login_type') == 'admin'
    )

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()

            # MAIN ADMIN LOGIN
            if user.is_superuser:
                if is_admin_login:
                    login(request, user)
                    return redirect('admin_dashboard')

                messages.error(
                    request,
                    'Please use Admin Login.'
                )

            # ADMIN LOGIN
            elif user.is_staff:
                try:
                    admin_request = AdminRequest.objects.get(user=user)

                    if admin_request.status == 'Pending':
                        messages.error(
                            request,
                            'Your Admin account is waiting for Main Admin approval.'
                        )
                    elif admin_request.status == 'Rejected':
                        messages.error(
                            request,
                            'Your Admin account request was rejected.'
                        )
                    elif admin_request.status == 'Approved':
                        if is_admin_login:
                            login(request, user)
                            return redirect('admin_dashboard')

                        messages.error(
                            request,
                            'Please use Admin Login.'
                        )

                except AdminRequest.DoesNotExist:
                    if is_admin_login:
                        login(request, user)
                        return redirect('admin_dashboard')

                    messages.error(
                        request,
                        'Please use Admin Login.'
                    )

            # STUDENT LOGIN
            else:
                try:
                    student_request = StudentRequest.objects.get(user=user)

                    if student_request.status == 'Pending':
                        messages.error(
                            request,
                            'Your Student account is waiting for Admin approval.'
                        )

                    elif student_request.status == 'Rejected':
                        messages.error(
                            request,
                            'Your Student account request was rejected.'
                        )

                    elif student_request.status == 'Approved':
                        if is_admin_login:
                            messages.error(
                                request,
                                'You are not authorized as an Admin.'
                            )
                        else:
                            login(request, user)
                            return redirect('dashboard')

                except StudentRequest.DoesNotExist:
                    # EXISTING STUDENT ACCOUNT
                    if is_admin_login:
                        messages.error(
                            request,
                            'You are not authorized as an Admin.'
                        )
                    else:
                        login(request, user)
                        return redirect('dashboard')

        else:
            messages.error(
                request,
                'Invalid username or password.'
            )

    else:
        form = AuthenticationForm(request)

    return render(request, 'login.html', {
        'form': form,
        'is_admin_login': is_admin_login,
    })


# STUDENT DASHBOARD
@login_required(login_url='/login/')
def dashboard(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')

    # Prevent pending/rejected students from accessing dashboard
    try:
        student_request = StudentRequest.objects.get(user=request.user)

        if student_request.status != 'Approved':
            logout(request)
            messages.error(
                request,
                'Your student account is not approved.'
            )
            return redirect('login')

    except StudentRequest.DoesNotExist:
        pass

    complaints = Complaint.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'dashboard.html',
        {'complaints': complaints}
    )


# SUBMIT COMPLAINT
@login_required(login_url='/login/')
def submit_complaint(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')

    try:
        student_request = StudentRequest.objects.get(user=request.user)

        if student_request.status != 'Approved':
            logout(request)
            messages.error(
                request,
                'Your student account is not approved.'
            )
            return redirect('login')

    except StudentRequest.DoesNotExist:
        pass

    if request.method == 'POST':
        form = ComplaintForm(request.POST)

        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.user = request.user
            complaint.save()

            messages.success(
                request,
                'Complaint submitted successfully.'
            )
            return redirect('dashboard')
    else:
        form = ComplaintForm()

    return render(request, 'submit_complaint.html', {'form': form})


# LOGOUT
def logout_view(request):
    logout(request)
    return redirect('home')


# ADMIN DASHBOARD
@user_passes_test(is_admin, login_url='/login/')
def admin_dashboard(request):
    complaints = Complaint.objects.all().order_by('-created_at')

    pending_students = StudentRequest.objects.filter(
        status='Pending'
    ).select_related('user')

    pending_requests = []

    if request.user.is_superuser:
        pending_requests = AdminRequest.objects.filter(
            status='Pending'
        ).select_related('user')

    return render(
        request,
        'admin_dashboard.html',
        {
            'complaints': complaints,
            'pending_students': pending_students,
            'pending_requests': pending_requests,
            'is_main_admin': request.user.is_superuser,
        }
    )


# UPDATE COMPLAINT STATUS
@user_passes_test(is_admin, login_url='/login/')
@require_POST
def update_status(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)

    new_status = request.POST.get('status')
    allowed_statuses = [
        'Pending',
        'In Progress',
        'Resolved'
    ]

    if new_status in allowed_statuses:
        complaint.status = new_status
        complaint.save(update_fields=['status'])
        messages.success(request, 'Complaint status updated.')
    else:
        messages.error(request, 'Invalid complaint status.')

    return redirect('admin_dashboard')


# STUDENT ACCOUNT APPROVAL - APPROVED ADMINS
@user_passes_test(is_admin, login_url='/login/')
@require_POST
def review_student_request(request, request_id):
    student_request = get_object_or_404(
        StudentRequest,
        id=request_id
    )

    action = request.POST.get('action')

    if action == 'approve':
        student_request.status = 'Approved'
        student_request.save()

        messages.success(
            request,
            'Student account approved.'
        )

    elif action == 'reject':
        student_request.status = 'Rejected'
        student_request.save()

        messages.success(
            request,
            'Student account rejected.'
        )

    else:
        messages.error(request, 'Invalid action.')

    return redirect('admin_dashboard')


# ADMIN ACCOUNT APPROVAL - MAIN ADMIN ONLY
@user_passes_test(is_main_admin, login_url='/login/')
@require_POST
def review_admin_request(request, request_id):
    admin_request = get_object_or_404(
        AdminRequest,
        id=request_id
    )

    action = request.POST.get('action')

    if action == 'approve':
        admin_user = admin_request.user
        admin_user.is_staff = True
        admin_user.is_superuser = False
        admin_user.save()

        admin_request.status = 'Approved'
        admin_request.save()

        messages.success(
            request,
            'Admin account approved.'
        )

    elif action == 'reject':
        admin_user = admin_request.user
        admin_user.is_staff = False
        admin_user.is_superuser = False
        admin_user.save()

        admin_request.status = 'Rejected'
        admin_request.save()

        messages.success(
            request,
            'Admin account rejected.'
        )

    else:
        messages.error(request, 'Invalid action.')

    return redirect('admin_dashboard')


# CREATE ADMIN ACCOUNT - MAIN ADMIN ONLY
@user_passes_test(is_main_admin, login_url='/login/')
def create_admin(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            new_admin = form.save(commit=False)
            new_admin.is_staff = False
            new_admin.is_superuser = False
            new_admin.save()

            AdminRequest.objects.create(
                user=new_admin,
                status='Pending'
            )

            messages.success(
                request,
                'Admin account created. Waiting for Main Admin approval.'
            )
            return redirect('admin_dashboard')
    else:
        form = UserCreationForm()

    return render(
        request,
        'create_admin.html',
        {'form': form}
    )


# ADMIN ACCESS REQUEST DISABLED
@login_required(login_url='/login/')
def request_admin_access(request):
    messages.error(
        request,
        'Admin access requests are disabled. Contact the Main Admin.'
    )
    return redirect('dashboard')
