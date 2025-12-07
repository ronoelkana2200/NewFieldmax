def dashboard_url(request):
    if not request.user.is_authenticated:
        return {'dashboard_url': None}

    try:
        role = request.user.profile.role
    except AttributeError:
        role = None

    if role == 'admin':
        url = '/admin-dashboard/'
    elif role == 'manager':
        url = '/manager-dashboard/'
    elif role == 'agent':
        url = '/agent-dashboard/'
    else:
        url = '/'

    return {'dashboard_url': url}

