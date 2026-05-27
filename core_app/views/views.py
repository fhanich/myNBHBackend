from rest_framework import status
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, ListAPIView
import pandas as pd
#import pysupercluster
from .utils import SearchNearby, AirQuality, analizeAirQuality, calculateRecognition, calculateAffordability, calculateSecurity, getCoords, calculateSalary, getCompanyParams, getJobAddress, make_hdi_description, get_rental_price_contours  # Import the function from utils
import numpy as np
from scipy.interpolate import griddata
try:
    import matplotlib.pyplot as plt
    import matplotlib
except Exception:
    plt = None
    matplotlib = None
import geojsoncontour
from .chatGPT import make_QoL_description
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
import uuid
from sklearn.cluster import DBSCAN
from sklearn.utils import shuffle
from django.http import StreamingHttpResponse


import geopandas as gpd
from vt2geojson.tools import vt_bytes_to_geojson

from ..models import Rentals, Cities, Jobs, AppData, Companies
from ..serializers import RentalsSerializer, CitySerializer, JobSerializer, UserRegistrationSerializer, LoginSerializer, RentalsContourSerializer, CityShortSerializer, AppSetupSerializer, RentalsShortSerializer, JobShortSerializer, UserSerializer, RentalsCoordsSerializer
import json
from  geojson import FeatureCollection, Feature, Point
from turfpy import measurement
from django.db.models import Min, Max
import pandas as pd
from datetime import datetime
from numerize import numerize 


# Get the basic app details.
class AppSetup(APIView):
    def get(self, request):
        appKeys = AppData.objects.all()

        keyList = AppSetupSerializer(appKeys, many=True).data
        
        return Response({keyList[0]['name']:keyList[0]['key'], keyList[1]['name']:keyList[1]['key']}, status=status.HTTP_200_OK)
        #return Response(keyList, status=status.HTTP_200_OK)

class UserRegistrationView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Login View
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            if user:
                token, created = Token.objects.get_or_create(user=user)
                return Response({'token': token.key}, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterNewRental(APIView):
    def post(self, request):
        rentalData = request.data
        if 'gps_lat' not in rentalData:
            coords = getCoords(rentalData['address'])
            rentalData['gps_lat'] = coords["lat"]
            rentalData['gps_lon'] = coords["lng"]

        rentalData['id']=str(uuid.uuid1())
        print('rentalData',rentalData)
        serializer = RentalsSerializer(data=rentalData)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class RegisterNewJob(APIView):
    def post(self, request):
        jobData = request.data
        if 'gps_lat' not in request.data:
            coords = getCoords(request.data['address'])
            request.data['gps_lat'] = coords["lat"]
            request.data['gps_lon'] = coords["lng"]

        request.data['id']=str(uuid.uuid1())
        print('jobData',request.data)
        serializer = JobSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

# Create your views here.
class GetCity(APIView):
    def get(self, request, city):
        rental_property_query = Rentals.objects.filter(city__iexact = city)

        if(not rental_property_query):
            return Response({'errorMessage': f'Rental property not found in the {city.capitalize()}. Please make sure you searched for correct city.'}, status=status.HTTP_404_NOT_FOUND)

        rental_property = RentalsShortSerializer(rental_property_query, many=True).data
        
        return Response({'rentalData':rental_property}, status=status.HTTP_200_OK)


# Create your views here.
class CallGPT(APIView):
    def get(self, request):
        rentalID = request.query_params.get('rental', None) 
        '''rental_property_query = Rentals.objects.filter(id__iexact = rentalID)
        rental_property = RentalsSerializer(rental_property_query, many=True).data

        rentalObject = Rentals.objects.get(id = rentalID)
        setattr(rentalObject, 'gptDescription', description) #normalize
        rentalObject.save()   '''     
        description = make_QoL_description(rentalID)

        
        return Response({'description':description}, status=status.HTTP_200_OK)

# Jobs API.
class JobsProps(APIView):
    def post(self, request):
        jobID = request.data['jobID']
        job_property_query = Jobs.objects.get(id = jobID)
        jobData = JobSerializer(job_property_query).data
        jobData['salary'] = calculateSalary(jobData)

        result = getCompanyParams(jobID)


        return Response({'jobData': jobData, 'companyData': result}, status=status.HTTP_200_OK)

# Rental API.
class RentalProps(APIView):
    def post(self, request):
        rentalID = request.data['rentalID']
        rental_property_query = Rentals.objects.get(id = rentalID)
        rentalData = RentalsSerializer(rental_property_query).data

        """if rentalData['nearbyRestaurants']:
            nearbyRests = rentalData['nearbyRestaurants']
        else:
            nearbyRests = SearchNearby("",rentalData["gps_lat"], rentalData["gps_lon"], 500, "restaurant", rentalID)
            if 'error' in nearbyRests:
                return Response(nearbyRests, status=status.HTTP_400_BAD_REQUEST)"""
        return Response({'rentalData': rentalData}, status=status.HTTP_200_OK)

       


# Jobs API.
class PollutionProps(APIView):
    def get(self, request):
        rentalID = request.query_params.get('rental', None) 
        pollutionRank = AirQuality(rentalID)

        return Response( pollutionRank, status=status.HTTP_200_OK)


class Register(APIView):
    def get(self, request):
        job = request.query_params.get('job', None) 
        family = request.query_params.get('family', None) 
        motiv = request.query_params.get('motiv', None) 
        
        request.session['job'] = 'job'
        request.session['family'] = 'family'
        request.session['motiv'] = 'motiv'
     
        return Response({{"message": "Session data saved!"}}, status=status.HTTP_200_OK)


class GetAll(APIView):
    def get(self, request):
        props = ['bed', 'bath', 'city', 'price'];
        rjs = request.query_params.get('rjs', None) 


        cityList = Rentals.objects.values('clusterCity').distinct()
        clusterCityList = cityList.values_list('clusterCity', flat=True)
# !!!!!!!!!!!!!! Next step: convert cityList from dict to array!!!!!!!!!!!!!!!!!!
        citiesObj = Cities.objects.filter(name__in = clusterCityList )
        citiesSerializer = CitySerializer(citiesObj, many=True).data
        #print('getall',citiesSerializer) 


        df = pd.DataFrame(citiesSerializer)


        rent_min_lat = min(df['gps_lat'])
        rent_min_lon = min(df['gps_lon'])
        rent_max_lat = max(df['gps_lat'])
        rent_max_lon = max(df['gps_lon'])


        rentalList_property=[];
        jobList_property=[];
        rentalFeaturesColl=[];

        if rjs == 'r':
            respType = "Rentals"
            allRentalCount = Rentals.objects.all().count()
        if rjs == 'j':
            respType = "Jobs"
            allRentalCount = Jobs.objects.all().count()
        rentalCount = []
        for citiProp in citiesSerializer:
            if rjs == 'r':
                rentalObjs = Rentals.objects.filter(clusterCity__iexact = citiProp['name'])
                rentalCount = rentalObjs.count()+1
                rental_property_query = rentalObjs[:int(rentalCount/allRentalCount*100)]
                rental_property = RentalsShortSerializer(rental_property_query, many=True).data
            if rjs == 'j':
                rentalObjs = Jobs.objects.filter(clusterCity__iexact = citiProp['name'])
                rentalCount = rentalObjs.count()+1
                rental_property_query = rentalObjs[:int(rentalCount/allRentalCount*100)]
                rental_property = JobShortSerializer(rental_property_query, many=True).data

            if len(rental_property) > 0:
                dfCity = pd.DataFrame(rental_property)
                cityRent_min_lat = min(dfCity['gps_lat'])
                cityRent_min_lon = min(dfCity['gps_lon'])
                cityRent_max_lat = max(dfCity['gps_lat'])
                cityRent_max_lon = max(dfCity['gps_lon'])

                count = numerize.numerize(round(rentalObjs.count(),-len(str(rentalObjs.count()))+1))

                rentalList_property.append(Feature(
                    geometry=Point((citiProp['gps_lon'], citiProp['gps_lat'])), 
                    properties={
                                'city':citiProp['name'],
                                'count': rentalObjs.count(), 
                                'countText': count+'+', 
                                'bbox':[{'lng': cityRent_max_lon,'lat': cityRent_max_lat},{'lng': cityRent_min_lon, 'lat': cityRent_min_lat}], 
                                }))

                for property in rental_property:
                    rentalFeaturesColl.append(Feature(
                            geometry=Point((float(property['gps_lon']), float(property['gps_lat']))), 
                            properties=property
                            ));

        finalResponse = {respType: {
                    'list': rentalFeaturesColl, 
                    'overview':rentalList_property, 
                    'bbox':[[rent_min_lon,rent_min_lat],[rent_max_lon,rent_max_lat]], 
                    'pageing': {'start': 0, 'end': 20, 'max': 100} }}
        return Response(finalResponse, 
                         status=status.HTTP_200_OK)

"""
        if rjs == 'j':
            job_property_query = Jobs.objects.all()[:100]
            job_property = JobSerializer(job_property_query, many=True).data

            jobFeaturesColl=[];
            for property in job_property:
                #cityProps = Cities.objects.get(name = property['city'])
                #cityData = CityShortSerializer(cityProps).data
                #if len(cityData):
                if (not property['gps_lon']):

                    #jobCoords = getCoords(property['company']+" "+property['city'])
                    jobCoords = getJobAddress(property['id'])
                    if not('error' in jobCoords):
                        jobObj = Jobs.objects.get(id = property['id'])
                        setattr(jobObj, 'gps_lat', jobCoords["gps_lat"])
                        setattr(jobObj, 'gps_lon', jobCoords["gps_lon"])
                        setattr(jobObj, 'industry', jobCoords['industry'])
                        setattr(jobObj, 'companyRating', jobCoords['compDescription'])
                        jobObj.save()        
                        jobFeaturesColl.append(Feature(
                                    geometry=Point((float(jobCoords['gps_lon']), float(jobCoords['gps_lat']))), 
                                    properties=property
                                    ));
                else :
                    jobCoords = {"gps_lat":float(property['gps_lat']),"gps_lon":float(property['gps_lon'])}

                    jobFeaturesColl.append(Feature(
                                geometry=Point((float(jobCoords['gps_lon']), float(jobCoords['gps_lat']))), 
                                properties=property
                                ));

            jobCount = Jobs.objects.filter(city__iexact = citiProp['city']).order_by('gps_lat')
            job_property = JobSerializer(jobCount, many=True).data
    #min_max_values = Jobs.objects.aggregate(
    #    job_min_lat=Min('gps_lat'),
    #    job_max_lat=Max('gps_lat'),
    #    job_min_lon=Min('gps_lon'),
    #    job_max_lon=Max('gps_lon'),
    #    )

            job_min_lat = float(job_property[0]['gps_lat'])
            job_max_lat = float(job_property[-1]['gps_lat'])

            jobCount = Jobs.objects.filter(city__iexact = citiProp['city']).order_by('gps_lon')
            job_property = JobSerializer(jobCount, many=True).data
            job_min_lon = float(job_property[0]['gps_lon'])
            job_max_lon = float(job_property[-1]['gps_lon'])
            jobList_property.append(Feature(
                #geometry=Point((float((job_min_lon+job_max_lon)/2), float((job_min_lat+job_max_lat)/2))), 
                geometry=Point((float(cityCoords['gps_lon']), float(cityCoords['gps_lat']))), 
                properties={'city':citiProp['city'],'count': jobCount.count()}))

            finalResponse = {'Jobs': {
                        'list': jobFeaturesColl, 
                        'overview':jobList_property, 
                        'bbox':[[job_min_lon,job_min_lat],[job_max_lon,job_max_lat]], 
                        'pageing': {'start': 0, 'end': 20, 'max': 100}}}
"""
                
    



class Pager(APIView):
    def get(self, request):
        rjs = request.query_params.get('rjs', None)  
        city = request.query_params.get('city', None)  
        start = request.query_params.get('start', None)  
        steps = request.query_params.get('steps', None)

        if rjs == "r":
            if city:
                rental_property_query = Rentals.objects.filter(city__iexact = city)[start:start+steps]
            else:
                rental_property_query = Rentals.objects.all()[start:start+steps]
            pagedProperties = RentalsSerializer(rental_property_query, many=True).data
        elif rjs == "j":
            if city:
                job_property_query = Jobs.objects.filter(city__iexact = city)[start:start+steps]
            else:
                job_property_query = Jobs.objects.all()[start:start+steps]
            pagedProperties = JobSerializer(job_property_query, many=True).data

        return Response({rjs: pagedProperties}, status=status.HTTP_200_OK)

def bounding_box(iterable):
    min_x, min_y = np.min(iterable, axis=0)
    max_x, max_y = np.max(iterable, axis=0)
    return [[min_x, min_y], [max_x, max_y]]

class Init(APIView):
    def post(self, request):
        print('Init starter', request.data['rjs'] )
        rjs = request.data['rjs']

        clusters=[]

        allCityList = Cities.objects.filter(clusterCount__gt=0)
        for cityProps in allCityList:
            clusters.append(Feature(
                    geometry=Point((float(getattr(cityProps,'gps_lon')), float(getattr(cityProps,'gps_lat')))), 
                    properties={'city':getattr(cityProps,'name'),'count': getattr(cityProps,'clusterCount'), 'bbox': json.loads(getattr(cityProps,'bbox'))}
                    ));

        response = Response({rjs: {'clusters': clusters}}, status=status.HTTP_200_OK)
        return response


class Zoomin(ListAPIView):
    def post(self, request):
        print('zoomin starter', request.data['rjs'] )
        rjs = request.data['rjs']
        bounds = request.data['bounds']
        rentalList_property=[]

        def generate(rjs, bounds):   #streaming response
            print('generate',bounds)
            allRentalCount = 0
            maxCount = 100
            if bounds: #
                #print('bounds',bounds)
                #cityProps = Cities.objects.filter(gps_lon__range=(bounds[0], bounds[2]), gps_lat__range=(bounds[1], bounds[3]))
                #cityData = CitySerializer(cityProps, many=True).data
                downlonrange = min(bounds[0][0], bounds[1][0])
                uplonrange = max(bounds[0][0], bounds[1][0])
                downlatrange = min(bounds[0][1], bounds[1][1])
                uplatrange = max(bounds[0][1], bounds[1][1])

                if rjs == 'r':
                    rentalObj = Rentals.objects.filter(gps_lat__range=(downlatrange, uplatrange),  gps_lon__range=(downlonrange, uplonrange))
                    #rental_propertyAll = RentalsShortSerializer(rentalObj, many=True).data

                if rjs == 'j':
                    rentalObj = Jobs.objects.filter(gps_lat__range=(downlatrange, uplatrange),  gps_lon__range=(downlonrange, uplonrange))
                    #rental_propertyAll = JobShortSerializer(rentalObj, many=True).data

                allRentalCount = rentalObj.count()
                cityList = rentalObj.values('clusterCity').distinct()


                #print('up/down lat/lon, cityList',downlatrange, uplatrange,downlonrange, uplonrange, allRentalCount)
                if (maxCount > allRentalCount):
                    maxCount = allRentalCount
                if allRentalCount > 0:
                    print('cityList', cityList)        

                    for citiProp in cityList:
                        #rentalList_property=[]  # to be included for windowing
                        rentalObjs = rentalObj.filter(clusterCity__iexact = citiProp['clusterCity'])
                        rentalCount = rentalObjs.count()+1
                        rental_property_query = rentalObjs[:int(rentalCount/allRentalCount*maxCount)]
                        if rjs == 'r':
                            rental_property = RentalsShortSerializer(rental_property_query, many=True).data
                        if rjs == 'j':
                            rental_property = JobShortSerializer(rental_property_query, many=True).data

                        if len(rental_property) > 0:
                            for property in rental_property:
                                if rjs == 'j':
                                    property['salary'] = calculateSalary(property)
                                if property['gps_lon']:
                                    rentalList_property.append(Feature(
                                            geometry=Point((float(property['gps_lon']), float(property['gps_lat']))), 
                                            properties=property
                                            ));
                        #print('rentalList_property', len(rentalList_property))        

                        #if len(rentalList_property) > 0:   # to be included for windowing
                        #    yield {rjs: {'points': shuffle(rentalList_property)}}  # to be included for windowing
                yield {rjs: {'points': shuffle(rentalList_property)}}

        #response = StreamingHttpResponse(generate(rjs, bounds), content_type="application/json")
        #response["Cache-Control"] = "no-cache"
        response = Response(generate(rjs, bounds), status=status.HTTP_200_OK)
        return response


"""
            index = pysupercluster.SuperCluster(
                    np.array([(rental['gps_lon'], rental['gps_lat']) for rental in rental_propertyAll]),
                    min_zoom=0,
                    max_zoom=16,
                    radius=40,
                    extent=512)

            superclusters = index.getClusters(
                    top_left=(-180, 90),
                    bottom_right=(180, -90),
                    zoom=4)
            newClusters=[]
            for cluster in superclusters:
                newClusters.append(Feature(
                        geometry=Point((float(cluster['longitude']), float(cluster['latitude']))), 
                        properties={'count': cluster['count']}
                        ));


            if rjs == 'r':

                rental_property_query = Rentals.objects.filter(gps_lat__range=(downlatrange, uplatrange),  gps_lon__range=(downlonrange, uplonrange))[:200]#.exclude(image__isnull=True).exclude(image__exact='')[:200]
                rentalProperties = RentalsShortSerializer(rental_property_query, many=True).data
                for feature in rentalProperties:
                    rentalList_property.append(Feature(
                        geometry=Point((float(feature['gps_lon']), float(feature['gps_lat']))), 
                        properties=feature))
                print('rentalList_property',len(rentalList_property))

            if rjs == 'j':

                job_property_query = Jobs.objects.filter(gps_lat__range=(downlatrange, uplatrange),  gps_lon__range=(downlonrange, uplonrange))[:200]
                jobProperties = JobSerializer(job_property_query, many=True).data
                print('jobProperties', jobProperties)


                for feature in jobProperties:
                    feature['salary'] = calculateSalary(feature)

                    if feature['gps_lon']:
                        #feature['gps_lon'] = cityData[0]['gps_lon']
                        #feature['gps_lat'] = cityData[0]['gps_lat']

                        jobList_property.append(Feature(
                            geometry=Point((float(feature['gps_lon']), float(feature['gps_lat']))), 
                            properties=feature))
"""        
    
class Contours(APIView): # too long process, even with small grid, not to be used
    def get(self, request):
        rental_property_query = Rentals.objects.all()
        rental_property = RentalsContourSerializer(rental_property_query, many=True).data
        matplotlib.use('Agg')


        latArray=[]
        lonArray=[]
        priceArray=[]
        for prop in rental_property:
            latArray.append(prop['gps_lat'])
            lonArray.append(prop['gps_lon'])
            priceArray.append(prop['price'])

        lats = np.array(latArray)
        lons = np.array(lonArray)
        prices = np.array(priceArray)

        levels = 10
        print('grid_size')

        grid_size = 10  # Change this value based on the resolution you want
        lat_grid = np.linspace(min(lats), max(lats), grid_size)
        lon_grid = np.linspace(min(lons), max(lons), grid_size)

        # Create a meshgrid for interpolation
        lon_grid_mesh, lat_grid_mesh = np.meshgrid(lon_grid, lat_grid)
        print('price_grid')

        # Interpolate height data onto the grid
        price_grid = griddata(
            (lons, lats), prices, (lon_grid_mesh, lat_grid_mesh), method='cubic'
        )

        contour_levels = np.arange(min(prices), max(prices), levels)  # Example: every 10 units
        print('contour = plt.contour')

        # Create a contour plot without displaying it
        contour = plt.contour(lon_grid_mesh, lat_grid_mesh, price_grid, levels=contour_levels)
        print('geojson_isobands')
        geojson_isobands = geojsoncontour.contour_to_geojson(
            contour=contour,
            ndigits=2  # Decimal precision for the coordinates
        )

        plt.close()

        # Print the resulting GeoJSON isobands
        print(geojson_isobands)
        return Response(geojson_isobands, status=status.HTTP_200_OK)


class RentalPriceContours(APIView):
    def get(self, request):
        rentalID = request.query_params.get('rentalID', None)
        size_unit = request.query_params.get('size_unit', 'sqm')

        if not rentalID:
            return Response({"error": "rentalID parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        rentalObj = Rentals.objects.get(id = rentalID)
        rental_properties = RentalsSerializer(rentalObj).data
        print('rental_properties', rental_properties['clusterCity'])

        try:
            grid_size = int(request.query_params.get('grid_size', 20))
        except ValueError:
            grid_size = 20
            
        try:
            num_levels = int(request.query_params.get('num_levels', 10))
        except ValueError:
            num_levels = 10

        if not rental_properties['clusterCity']:
            return Response({"error": "No city found"}, status=status.HTTP_400_BAD_REQUEST)


        contours = get_rental_price_contours(
            rental_properties['gps_lon'],
            rental_properties['gps_lat'],
            rental_properties['clusterCity'],
            size_unit,
            grid_size,
            num_levels,
        )
        if "error" in contours:
            return Response(contours, status=status.HTTP_400_BAD_REQUEST)
        return Response(contours, status=status.HTTP_200_OK)
    

class GetRecognition(APIView):
    def get(self, request):
        jobID = request.query_params.get('job', None) 
        recognition = calculateRecognition(jobID)
        return Response(recognition, status=status.HTTP_200_OK)
    
class GetAffordability(APIView):
    def get(self, request):
        jobID = request.query_params.get('job', None) 
        rentalID = request.query_params.get('rental', None) 
        recognition = calculateAffordability(rentalID, jobID)
        return Response(recognition, status=status.HTTP_200_OK)
    
class GetSecurity(APIView):
    def get(self, request):
        rentalID = request.query_params.get('rental', None) 
        recognition = calculateSecurity(rentalID)
        return Response(recognition, status=status.HTTP_200_OK)
    

class GetCoords(APIView):
    def get(self, request):
        address = request.query_params.get('address', None) 
        coords = getCoords(address)
        return Response(coords, status=status.HTTP_200_OK)

    
class UserDetailView(RetrieveUpdateAPIView):
    """
    Retrieve and update the authenticated user's data (including profile).
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Get the currently authenticated user
        print(self.request.user)

        return self.request.user
    
class GetCrime(APIView):
    def get(self, request):
        headers = {
                'Content-Type': 'application/json',  # Set content type
                'x-api-key': 'k3RAzKN1Ag14xTPlculT39RZb38LGgsG8n27ZycG'
                }      
        external_api_url = "https://api.crimeometer.com/v2/crime-incidents?lat=40.7375388&lon=-74.0619489&datetime_ini=2023-01-10 10:00:00&datetime_end=2023-01-11 10:00:00&distance=1km"

        response = requests.get(external_api_url,
                                 headers=headers
                                 )
        
        print('response', response)
        return Response(response, status=status.HTTP_200_OK)
    

class GetHDI(APIView):
    def post(self, request):
        z = int(request.data['z'])
        x = int(request.data['x'])
        y = int(request.data['y'])
        rentalID = request.data['rentalID']

        # Sources:  https://github.com/mansueto-institute/hdi-map/blob/main/build/index.js#L64
        #           https://github.com/mansueto-institute/local-hdi/blob/master/README.md
        #           https://communityhdi.org/#4.25/37.04/-90.34

        headers = {
                'Content-Type': 'application/json',  # Set content type
                'x-api-key': 'k3RAzKN1Ag14xTPlculT39RZb38LGgsG8n27ZycG'
                }      


        #print('features', features)
        #gdf = gpd.GeoDataFrame.from_features(features)
        rentalObj = Rentals.objects.get(id = rentalID)
        coords = [getattr(rentalObj, 'gps_lon'), getattr(rentalObj, 'gps_lat')]
        location = getattr(rentalObj, 'location')
        locationRank = getattr(rentalObj, 'locationRank')

        features={}

        external_api_url = f"https://api.mapbox.com/v4/mapbox.mapbox-terrain-v2,mapbox.mapbox-streets-v8,nmarchi0.test-tile-size,nmarchi0.0ypc4257,nmarchi0.us-hdi-lores/{z}/{x}/{y}.vector.pbf?sku=101VOjAihcHPe&access_token=pk.eyJ1Ijoibm1hcmNoaTAiLCJhIjoiY2p6dTljeDhiMGRwcjNubnl2aXI0OThhYyJ9.4FdGkBJlOXMPRugyqiXrjg"
        response = requests.get(external_api_url)
        assert response.status_code == 200, response.content
        vt_content = response.content

        features = vt_bytes_to_geojson(vt_content, x, y, z)
        filteredFeatures = [p for p in features['features'] if 'adjusted_hdi' in p['properties'] ]
        features['features'] = filteredFeatures

        location = make_hdi_description(coords, features['features'])
        print('GetHDI location', location )

        if not location:
            setattr(rentalObj, 'location', location)
            setattr(rentalObj, 'locationRank', location['adjusted_hdi'])
            rentalObj.save()

        return Response({'features': features, 'evaluation': location}, status=status.HTTP_200_OK)

class GetCompParams(APIView):
    def post(self, request):
        jobID = request.query_params.get('jobID', None) 

        result = getCompanyParams(jobID)

        return Response(result, status=status.HTTP_200_OK)


class Align(APIView):
    def get(self, request):
        job_property_query = Jobs.objects.filter(city__iexact = "New York")
        for item in job_property_query:
            compObj = Companies.objects.get(name = getattr(item,'company'))
            setattr(item,'industry', getattr(compObj,'industry'))
            setattr(item,'sector', getattr(compObj,'sector'))
            print('position', getattr(item,'name'), getattr(item,'company'))
            item.save()

        return Response("ok", status=status.HTTP_200_OK)


class allJobCoords(APIView):
    def get(self, request):
            jobID = request.query_params.get('id', None) 
            if jobID:
                job_property_query = Jobs.objects.filter(id__iexact = jobID)
            else:
                job_property_query = Jobs.objects.all()
            if(not job_property_query):
                return Response({'errorMessage': f'Job property not found in the . Please make sure you searched for correct city.'}, status=status.HTTP_404_NOT_FOUND)

            print('job_property_query', job_property_query)

            job_property = JobSerializer(job_property_query, many=True).data

            jobFeaturesColl=[];
            for property in job_property:
                #cityProps = Cities.objects.get(name = property['city'])
                #cityData = CityShortSerializer(cityProps).data
                #if len(cityData):
                if (property['gps_lon']<-180):

                    #jobCoords = getCoords(property['company']+" "+property['city'])
                    jobCoords = getJobAddress(property['company'], property['city'])
                    print('jobCoords', jobCoords)

                    if not('error' in jobCoords):
                        jobObj = Jobs.objects.get(id = property['id'])
                        setattr(jobObj, 'gps_lat', jobCoords['location']["latitude"])
                        setattr(jobObj, 'gps_lon', jobCoords['location']["longitude"])
                        setattr(jobObj, 'address', jobCoords['address'])
                        setattr(jobObj, 'date', datetime.today())
                        jobObj.save()        
                        jobFeaturesColl.append(Feature(
                                    geometry=Point((float(jobCoords['location']["longitude"]), float(jobCoords['location']["latitude"]))), 
                                    properties=property
                                    ));
            return Response(jobFeaturesColl, status=status.HTTP_200_OK)



class RentalClusterCities(APIView):
    def get(self, request):
        rjs = request.query_params.get('rjs', None) 
        itemId = request.query_params.get('id', None) 

        if rjs == 'r':
            if itemId:
                rental_property_query = Rentals.objects.filter(id__iexact = itemId)
            else:
                rental_property_query = Rentals.objects.all()

            rentalSerializer = RentalsCoordsSerializer(rental_property_query, many=True).data
        else:
            if itemId:
                rental_property_query = Jobs.objects.filter(id__iexact = itemId)
            else:
                rental_property_query = Jobs.objects.all()

            rentalSerializer = JobSerializer(rental_property_query, many=True).data


        city_property_query = Cities.objects.all()
        citySerializer = CitySerializer(city_property_query, many=True).data

        cityList = [p['name'] for p in citySerializer]


        for rental in rentalSerializer:
            if not rental['clusterCity']:
                distancefrom=[]
                rentalPoint = Feature(geometry=Point((rental['gps_lon'], rental['gps_lat'])))
                for city in citySerializer:
                    cityCenter = Feature(geometry=Point((city['gps_lon'], city['gps_lat'])))
                    distancefrom.append(measurement.distance(rentalPoint,cityCenter))

                shortest = distancefrom.index(np.min(distancefrom))
                closestCity = citySerializer[shortest]
                print('closestCity', closestCity)
                rental_property = Rentals.objects.get(id=rental['id'])
                #rental_property = Jobs.objects.get(id=rental['id'])
                setattr(rental_property, 'clusterCity', closestCity['name'])
                setattr(rental_property, 'date', datetime.today())

                rental_property.save()

        for city in citySerializer:
            clusterCount = Rentals.objects.filter(clusterCity__iexact = city['name'])
            rentals = RentalsSerializer(clusterCount, many=True).data
            rentalcoords = [[c['gps_lon'], c['gps_lat']] for c in rentals if c['gps_lon'] and c['gps_lat']]

            #clusterCount = Jobs.objects.filter(clusterCity__iexact = city['name']).count()
            city_property = Cities.objects.get(name=city['name'])
            setattr(city_property, 'clusterCount', clusterCount.count())
            if len(rentalcoords)>0:
                setattr(city_property, 'bbox', json.dumps(bounding_box(rentalcoords)))
            city_property.save()

        return Response("ok", status=status.HTTP_200_OK)
