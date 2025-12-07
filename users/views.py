# users/views.py
from rest_framework import viewsets
from django.contrib.auth.models import User
from .serializers import UserSerializer  # Make sure you have this
from .models import Role
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.models import User

class GetUsersJSONView(View):
    def get(self, request):
        users = User.objects.all().values("id", "username")
        return JsonResponse({"users": list(users)}, safe=False)



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

# List all users
class UserListView(ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'

# Detail view for a single user
class UserDetailView(DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user'

# Create a new user
class UserCreateView(CreateView):
    model = User
    template_name = 'users/user_form.html'
    fields = ['username', 'email', 'is_staff', 'is_active', 'password']
    success_url = reverse_lazy('user-list')

    def form_valid(self, form):
        # Hash the password before saving
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        return super().form_valid(form)
    
    def add_user(request):
        roles = Role.objects.all()
        return render(request, 'template.html', {'roles': roles})


# Update an existing user
class UserUpdateView(UpdateView):
    model = User
    template_name = 'users/user_form.html'
    fields = ['username', 'email', 'is_staff', 'is_active']
    success_url = reverse_lazy('user-list')

# Delete a user
class UserDeleteView(DeleteView):
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('user-list')





# ================================
# GET USERS 
# ================================
from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()

def get_users_as_json(request):
    """
    Returns a JSON list of all users for transfer dropdown.
    """
    users = User.objects.all()
    user_list = [{"id": user.id, "name": user.get_full_name() or user.username} for user in users]
    return JsonResponse({"users": user_list})


from django.http import JsonResponse
from django.views import View
from django.contrib.auth.models import User

class GetUsersJSONView(View):
    def get(self, request):
        users = User.objects.all().values("id", "username")
        return JsonResponse({"users": list(users)}, safe=False)
