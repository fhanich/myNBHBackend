from django.urls import path, include
from .views import views
from .views.views import GetAll, Pager, Zoomin, Init, Register, UserRegistrationView, LoginView, JobsProps, RentalProps, PollutionProps, CallGPT, GetRecognition, GetAffordability, GetSecurity, AppSetup, GetCoords, RegisterNewRental, RegisterNewJob, UserDetailView, GetCrime, GetHDI, GetCompParams, Align, RentalClusterCities, allJobCoords, RentalPriceContours
from .views.scenarios_views import Scenarios
#from .views.scenarios_views import make_QoL_description
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
  path('get-city/<str:city>/', views.GetCity.as_view() , name='city'),
  path('listall/', GetAll.as_view(), name='GetAll'),
  path('scenarios/', Scenarios.as_view(), name='Scenarios'),
  path('jobs/', JobsProps.as_view(), name='JobsProps'),
  path('rental/', RentalProps.as_view(), name='RentalProps'),
  path('recognition/', GetRecognition.as_view(), name='GetRecognition'),
  path('affordability/', GetAffordability.as_view(), name='GetAffordability'),
  path('pollution/', PollutionProps.as_view(), name='PollutionProps'),
  path('security/', GetSecurity.as_view(), name='GetSecurity'),
  #path('contours/', Contours.as_view(), name='Contours'),
  path('testGPT/', CallGPT.as_view(), name='Pager'),
  path('pager/', Pager.as_view(), name='Pager'),
  path('zoomin/', Zoomin.as_view(), name='Zoomin'),
  path('init/', Init.as_view(), name='Init'),
  #path('connect/', Register.as_view(), name='Register'),
  path('signup/', UserRegistrationView.as_view(), name='user-registration'),
  path('login/', LoginView.as_view(), name='login'),
  path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
  path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
  path('appsetup/', AppSetup.as_view(), name='AppSetup'),
  path('getcoords/', GetCoords.as_view(), name='GetCoords'),
  path('newrental/', RegisterNewRental.as_view(), name='RegisterNewRental'),
  path('newjob/', RegisterNewJob.as_view(), name='RegisterNewJob'),
  path('company/', GetCompParams.as_view(), name='GetCompParams'),

  path('align/', Align.as_view(), name='Align'),


  path('api/auth/', include('dj_rest_auth.urls')),
  path('api/auth/registration/', include('dj_rest_auth.registration.urls')),


  path('getUser/', UserDetailView.as_view(), name='UserDetailView'),
  path('getCrime/', GetCrime.as_view(), name='GetCrime'),

  path('getHDI/', GetHDI.as_view(), name='GetHDI'),
  path('rentalClusterCities/', RentalClusterCities.as_view(), name='RentalClusterCities'),
  path('allJobCoords/', allJobCoords.as_view(), name='allJobCoords'),
  path('rentalPriceContours/', RentalPriceContours.as_view(), name='RentalPriceContours'),


]
