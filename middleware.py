# core_app/middleware.py
import json
from django.utils.deprecation import MiddlewareMixin
from .models import UserHistory
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.authentication import JWTAuthentication

class RentalLoggingMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        response = self.get_response(request)
        return response
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Check if the request is to the 'rental' API
        if request.path.startswith('/api/core/rental/') and request.method in ['POST', 'PUT', 'PATCH']:
            user, _ = self.jwt_auth.authenticate(request)
            try:
                # Parse the request body
                body = json.loads(request.body.decode('utf-8'))
                rentalID = body.get('rentalID')
                if rentalID:
                    UserHistory.objects.create(
                        user=user,
                        rentals=rentalID
                    )
            except json.JSONDecodeError:
                pass  

        return None

class JobLoggingMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        response = self.get_response(request)
        return response
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Check if the request is to the 'jobs' API
        if request.path.startswith('/api/core/jobs/') and request.method in ['POST', 'PUT', 'PATCH']:
            user, _ = self.jwt_auth.authenticate(request)
            try:
                # Parse the request body
                body = json.loads(request.body.decode('utf-8'))
                jobID = body.get('jobID')
                if jobID:
                    UserHistory.objects.create(
                        user=user,
                        jobs=jobID
                    )
            except json.JSONDecodeError:
                print('error with user authentication')
                pass  

        return None

class ScenarioLoggingMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Check if the request is to the 'scenarios' API
        if request.path.startswith('/api/core/scenarios/') and request.method in ['POST', 'PUT', 'PATCH']:
            user, _ = self.jwt_auth.authenticate(request)
            try:
                # Parse the request body
                body = json.loads(request.body.decode('utf-8'))
                rental = body.get('rental')
                job = body.get('job')
                if rental and job:
                    UserHistory.objects.create(
                        user=user,
                        jobs=job,
                        rentals=rental,
                    )
            except json.JSONDecodeError:
                pass  
        return None
