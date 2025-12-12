# website/urls.py
from django.urls import path
from .views import (
    RoleBasedLoginView,
    admin_dashboard,
    manager_dashboard,
    agent_dashboard,
    cashier_dashboard,
    home
)
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', home, name='home'),
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('admin-dashboard/', admin_dashboard, name='admin-dashboard'),
    path('manager-dashboard/', manager_dashboard, name='manager-dashboard'),
    path('agent-dashboard/', agent_dashboard, name='agent-dashboard'),
    path('cashier-dashboard/', cashier_dashboard, name='cashier-dashboard'),
]
