from django.urls import path, include
from . import views
from .views import GetUsersJSONView
from .views import get_users_as_json
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from .views import  UserListView, UserDetailView, UserCreateView, UserUpdateView, UserDeleteView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),

    path('user/', UserListView.as_view(), name='user-list'),
    path('user/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('user/add/', UserCreateView.as_view(), name='user-add'),
    path('user/<int:pk>/edit/', UserUpdateView.as_view(), name='user-edit'),
    path('user/<int:pk>/delete/', UserDeleteView.as_view(), name='user-delete'),
   
    path('get-users/', GetUsersJSONView.as_view(), name='get-users-json'),
    path('users/', get_users_as_json, name='get-users-json'),
    
]
