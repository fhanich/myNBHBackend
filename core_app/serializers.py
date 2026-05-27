from rest_framework import serializers
from django.contrib.auth.models import User
from . import models
import requests
from django.http import JsonResponse
from .models import UserProfile

class RoundedFloatField(serializers.FloatField):
    def to_representation(self, value):
        return round(super().to_representation(float(value)), 0)

    def to_internal_value(self, data):
        return round(super().to_internal_value(float(data)), 0)

class RentalsCoordsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Rentals
        fields = ["gps_lat","gps_lon", "id" ,"clusterCity"]

class RentalsShortSerializer(serializers.ModelSerializer): # serializer for API data
    class Meta:
        model = models.Rentals
        fields = ["address","age","area","balcony","bath","bed","block_size","built","city","currency","deposit","features","floor","furnished","fees","garden","gps_lat","gps_lon","gym","id","image","imageList","link","location","max_floor","max_tenant","paid","parking","pets","pool","price","score","size","size_unit","type","url","clusterCity"]

    def to_internal_value(self, data):
        # Convert empty strings to None
        for key, value in data.items():
            if value == '':
                data[key] = 0
        return super().to_internal_value(data)

    def validate(self, data):
        bed = data.get('bed')
        price = data.get('price')
        gps_lat = data.get('gps_lat')
        gps_lon = data.get('gps_lon')
        size = data.get('size')
        imageList = data.get('imageList')    

        try:
            data['imageList'] = imageList.replace("[","").replace(']',"")
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['imageList'] = imageList  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string
       

        try:
            data['bed'] = round(float(bed),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['bed'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['price'] = round(float(price),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['price'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['gps_lat'] = float(gps_lat)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['gps_lat'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['gps_lon'] = float(gps_lon)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['gps_lon'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['size'] = round(float(size),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['size'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string


        return data



class RentalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Rentals
        fields = '__all__'
    
    def validate(self, data):
        bed = data.get('bed')
        price = data.get('price')
        gps_lat = data.get('gps_lat')
        gps_lon = data.get('gps_lon')
        size = data.get('size')
        goOutRank = data.get('goOutRank')
        cultureRank= data.get('cultureRank')
        shopingRank=data.get('shopingRank')
        educationRank=data.get('educationRank')
        entertainRank=data.get('entertainRank')
        healthRank=data.get('healthRank')
        turismRank=data.get('turismRank')
        housingRank=data.get('housingRank')
        sportsRank=data.get('sportsRank')
        travelRank=data.get('travelRank')
        greenRank=data.get('greenRank')
        pollutionRank=data.get('pollutionRank')
        affScore = data.get('affScore')        
        clusterCity = data.get('clusterCity')    
        locationRank = data.get('locationRank')    
        imageList = data.get('imageList')    

        try:
            data['imageList'] = imageList.replace("[","").replace(']',"")
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['imageList'] = imageList  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['bed'] = round(float(bed),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['bed'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['price'] = round(float(price),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['price'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['gps_lat'] = float(gps_lat)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['gps_lat'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['gps_lon'] = float(gps_lon)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['gps_lon'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['size'] = round(float(size),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['size'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['goOutRank'] = round(float(goOutRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['goOutRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['cultureRank'] = round(float(cultureRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['cultureRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['shopingRank'] = round(float(shopingRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['shopingRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['educationRank'] = round(float(educationRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['educationRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['entertainRank'] = round(float(entertainRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['entertainRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['healthRank'] = round(float(healthRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['healthRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['turismRank'] = round(float(turismRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['turismRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['housingRank'] = round(float(housingRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['housingRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['sportsRank'] = round(float(sportsRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['sportsRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['travelRank'] = round(float(travelRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['travelRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['greenRank'] = round(float(greenRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['greenRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['pollutionRank'] = round(float(pollutionRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['pollutionRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['affScore'] = round(float(affScore),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['affScore'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['locationRank'] = round(float(locationRank),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['locationRank'] = 0  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string


        return data
    
class RentalsContourSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Rentals
        fields = ["gps_lat","gps_lon","price"]

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Cities
        fields = '__all__'
    
class CityShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Cities
        fields = ["gps_lat","gps_lon","name"]
    def validate(self, data):
        gps_lat = data.get('gps_lat')
        gps_lon = data.get('gps_lon')
        

        try:
            data['gps_lat'] = float(gps_lat)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['gps_lat'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['gps_lon'] = float(gps_lon)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['gps_lon'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

    

class CityCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Cities
        fields = ["rentalFee", "markets", "transportation", "school", "sportsnLeisure", "utilities", "clothing", "restaurants"]
    def to_representation(self, instance):
        # Get the original representation of the instance
        representation = super().to_representation(instance)
        
        # Remap fields to include spaces
        representation['Rental Fee'] = round(representation.pop('rentalFee'),0)
        representation['Food'] = round(representation.pop('markets'),0)
        representation['Transportation'] = round(representation.pop('transportation'),0)
        representation['Education'] = round(representation.pop('school'),0)
        representation['Clothing'] = round(representation.pop('clothing'),0)
        representation['SportsnLeisure'] = round(representation.pop('sportsnLeisure'),0)
        representation['Utilities'] = round(representation.pop('utilities'),0)
        representation['Restaurants'] = round(representation.pop('restaurants'),0)
        return representation



class JobShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Jobs
        fields = ["id","city","company","currency","salary","name", "industry","sector", "gps_lon", "gps_lat","clusterCity"]
    def to_internal_value(self, data):
        # Convert empty strings to None
        for key, value in data.items():
            if value == '':
                data[key] = None
        return super().to_internal_value(data)
    def validate(self, data):
        salary = data.get('salary')
        gps_lat = data.get('gps_lat')
        gps_lon = data.get('gps_lon')

        try:
            data['salary'] = round(float(salary),0)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['salary'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['gps_lat'] = float(gps_lat)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['gps_lat'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string

        try:
            data['gps_lon'] = float(gps_lon)
        except ValueError:
            # Skip the ValueError and set a default or keep original data
            data['gps_lon'] = None  # You can handle it however you want (e.g., set to None)
            # Or you can completely skip this field or just keep the original string
def validate_float_or_none(value):
    if value == '':
        return None
    return value

class JobSerializer(serializers.ModelSerializer):
    gps_lat = serializers.FloatField(validators=[validate_float_or_none])
    gps_lon = serializers.FloatField(validators=[validate_float_or_none])

    class Meta:
        model = models.Jobs
        fields = '__all__'
    def to_internal_value(self, data):
        # Convert empty strings to None
        for key, value in data.items():
            if value == '':
                data[key] = None
        return super().to_internal_value(data)
    
class UserRegistrationSerializer(serializers.ModelSerializer):
    # Confirm password field
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        # Ensure the two password fields match
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        # Remove the password2 field before saving
        validated_data.pop('password2')
        
        # Create the user with the provided data
        user = User.objects.create_user(**validated_data)
        return user

# User login serializer
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

def call_external_api(request):
    # Define the API endpoint URL
    api_url = "https://api.example.com/data"

    # Make a GET request to the external API
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()  # Assuming the response is in JSON format
        
        # Return the API response data as JSON to the client
        return JsonResponse(data, status=200)

    except requests.exceptions.RequestException as e:
        # Handle exceptions (e.g., network issues, invalid responses)
        return JsonResponse({"error": str(e)}, status=500)


class AppSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AppData
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['preferredRentals', 'bookedRental','preferredJobs','bookedJob']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = '__all__'

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update profile
        profile, created = UserProfile.objects.get_or_create(user=instance)
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        return instance

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Companies
        fields = '__all__'