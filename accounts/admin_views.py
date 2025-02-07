# accounts/admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import CustomUser, UserProfile, LoginHistory, PasswordReset
from .forms import AdminUserCreationForm, AdminUserEditForm


@staff_member_required
def user_list(request):
    users = CustomUser.objects.select_related('profile').all()

    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(company_name__icontains=search)
        )

    status = request.GET.get('status')
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    elif status == 'locked':
        users = users.filter(account_locked_until__gt=timezone.now())

    paginator = Paginator(users.order_by('-date_joined'), 20)
    page = request.GET.get('page')
    users = paginator.get_page(page)

    return render(request, 'admin/accounts/user_list.html', {
        'users': users,
        'search': search,
        'status': status
    })


@staff_member_required
def user_detail(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    login_history = LoginHistory.objects.filter(user=user).order_by('-login_datetime')[:10]

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'activate':
            user.is_active = True
            user.save()
            messages.success(request, 'User activated successfully.')

        elif action == 'deactivate':
            user.is_active = False
            user.save()
            messages.success(request, 'User deactivated successfully.')

        elif action == 'unlock':
            user.unlock_account()
            messages.success(request, 'Account unlocked successfully.')

        elif action == 'verify_email':
            user.is_email_verified = True
            user.save()
            messages.success(request, 'Email verified successfully.')

    return render(request, 'admin/accounts/user_detail.html', {
        'user_obj': user,
        'login_history': login_history
    })


@staff_member_required
def user_edit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('accounts:admin_user_detail', user_id=user.id)
    else:
        form = AdminUserEditForm(instance=user)

    return render(request, 'admin/accounts/user_edit.html', {'form': form})


@staff_member_required
def user_create(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'User created successfully.')
            return redirect('accounts:admin_user_detail', user_id=user.id)
    else:
        form = AdminUserCreationForm()

    return render(request, 'admin/accounts/user_create.html', {'form': form})


@staff_member_required
def login_history(request):
    history = LoginHistory.objects.select_related('user').all()

    status = request.GET.get('status')
    if status == 'success':
        history = history.filter(is_successful=True)
    elif status == 'failure':
        history = history.filter(is_successful=False)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        history = history.filter(login_datetime__gte=start_date)
    if end_date:
        history = history.filter(login_datetime__lte=end_date)

    paginator = Paginator(history.order_by('-login_datetime'), 50)
    page = request.GET.get('page')
    history = paginator.get_page(page)

    return render(request, 'admin/accounts/login_history.html', {
        'history': history,
        'status': status,
        'start_date': start_date,
        'end_date': end_date
    })