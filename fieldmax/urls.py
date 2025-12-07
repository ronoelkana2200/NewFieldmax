from django.contrib import admin
from django.urls import path, include
from website.views import RoleBasedLoginView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('accounts/login/', RoleBasedLoginView.as_view()),  
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),

    # HTML ROUTES (Django Template Views)
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('users/', include('users.urls')),

    # Main site
    path('', include('website.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]
