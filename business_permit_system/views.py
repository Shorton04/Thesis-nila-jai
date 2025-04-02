from django.shortcuts import render
from applications.models import BusinessApplication  # Import your application model


def home(request):
    """
    Render the homepage.
    Includes stats if the user is authenticated.
    """
    context = {}

    if request.user.is_authenticated:
        # Get some basic stats for the user if they're logged in
        try:
            user_applications = BusinessApplication.objects.filter(applicant=request.user)
            context['applications_count'] = user_applications.count()
            context['pending_count'] = user_applications.filter(status='submitted').count()
            context['approved_count'] = user_applications.filter(status='approved').count()
        except:
            # In case the application model isn't available or there's an error
            pass

    return render(request, 'Home.html', context)

def offline(request):
    return render(request, 'offline.html')