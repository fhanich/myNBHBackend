import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
import pandas as pd
import numpy as np
import googlemaps
from datetime import datetime, timedelta
from django.db.models import Min, Max
import json
import wikipediaapi
import re
from bs4 import BeautifulSoup
import polyline
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import matplotlib
import geojsoncontour
from vt2geojson.tools import vt_bytes_to_geojson
import mercantile
import scipy.stats as stats


from ..models import Rentals, Jobs, Cities, Companies
from ..serializers import RentalsSerializer, CityCostSerializer, JobShortSerializer, CitySerializer, JobSerializer, CompanySerializer
from .chatGPT import make_QoL_description, make_aff_description, make_recognition_description, make_security_description, getCompReviews
from turfpy.measurement import boolean_point_in_polygon, distance
from geojson import Point, MultiPolygon, Feature

def tukeys_fences(data, value, multiplier=1.5):
    """
    Detect outliers using Tukey's Fences algorithm.

    Parameters:
    data (pd.Series): The dataset you want to filter.
    multiplier (float): The multiplier for IQR to calculate the fences. Default is 1.5.

    Returns:
    pd.Series: Data without outliers.
    pd.Series: Outliers detected by the algorithm.
    """
    # Calculate the first (Q1) and third quartile (Q3)
    #Q1 = min(data.quantile(0.05), value)
    #Q3 = max(data.quantile(0.95), value)

    Q1 = data.quantile(0.25)
    Q3 = data.quantile(0.75)


    # Calculate the interquartile range (IQR)
    IQR = Q3 - Q1
    
    # Define the lower and upper fences
    lower_fence = Q1 - multiplier * IQR
    upper_fence = Q3 + multiplier * IQR
    
    # Filter out outliers
    data_without_outliers = data[(data >= Q1) & (data <= Q3)]
    outliers = data[(data < Q1) | (data > Q3)]
    
    return data_without_outliers, outliers


def find_decile(value, data, num_quantiles=100):
    """
    Find which quantile a value falls into using pandas qcut.

    Parameters:
    value (float): The value to find the quantile for.
    data (list or pandas series): The dataset.
    num_quantiles (int): The number of quantiles to divide the data into (default is 4 for quartiles).

    Returns:
    int: The quantile the value falls into.
    """
    """

    ranges = data.quantile([0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1])
    quantile = 0
    while ranges[quantile/10] < value and quantile <=10:
        quantile+=1   

    print('quantile',quantile,value,ranges[0],max(ranges))

    """
    if value > max(data):
        quantile = 100
    else:
        # Use qcut to divide data into quantiles and assign labels
        quantile_bins = pd.qcut(data.rank(method='first'), q=num_quantiles, labels=range(1, num_quantiles + 1))
        
        # Find where the value fits in terms of quantiles
        quantile = quantile_bins[data == value].iloc[0]
    #print('quantile', quantile, value, min(data), max(data))

    return quantile

def SendSingleGoogleAPIRequest(external_api_url, header, requestData):
    try:
            # Make a GET request to the external API

        response = requests.post(external_api_url,
                                headers=header, 
                                json=requestData
                                )
            
            # Check if the request was successful
        if response.status_code == 200:
                # Get the JSON data from the response
            data = response.json()
               
                # Return the data to the client
            return data
        else:
            print('Return an error response', external_api_url, response.status_code)
                # Return an error response if the external API request failed
            return {"error": status.HTTP_400_BAD_REQUEST, "status": "NOK", "data": ''}
    except requests.exceptions.RequestException as e:
            # Handle exceptions that occur during the request
        print('Handle exceptions')
        return {"error": str(e), "status": "NOK", "data": ''}

def SendGoogleAPIRequest(external_api_url, header, requestData):
    responseData = []
    nextPageToken = "True"
    nextPageTokens=[]
    while nextPageToken:
        if nextPageToken != "True":
            external_api_url = external_api_url+"&pageToken="+nextPageToken
        data = SendSingleGoogleAPIRequest(external_api_url, header, requestData)
        if 'error' in data: 
            nextPageToken = False
            responseData = data
        else:
            if 'hoursInfo' in data:
                if len(data['hoursInfo'])> 0:
                    i=0
                    arraData = []
                    while i < len(data['hoursInfo']):
                        if 'indexes' in data['hoursInfo'][i]:
                            arraData.extend(data['hoursInfo'][i]['indexes'])
                        i+= 1
                    responseData.extend(arraData)
                    if 'nextPageToken' in data:
                        nextPageToken = data['nextPageToken']
                        nextPageTokens.append(nextPageToken)
                    else:
                        nextPageToken = False
    
    return responseData


def SearchNearby(keyword, gps_lat, gps_lon, radius, type, rentalID):
    # Example external API URL (replace with the actual API endpoint)
    types = {
    "goOut": ["restaurant","bar","cafe","night_club", "movie_theater"], # QoS
    "culture": ["art_gallery","museum","performing_arts_theater"], #QoS
    "shoping": ["grocery_store","discount_store","clothing_store", "supermarket", "market"], #QoS
    "education": ["library","school","university"], #location?
    "entertain": ["cultural_center","community_center","casino", "amusement_park"], #QoS
    "health": ["dentist","doctor","pharmacy", "hospital"], #QoS/location?
    "turism": ["private_guest_room","hotel","hostel", "bed_and_breakfast"], #QoS
    "housing": ["barber_shop","laundry","child_care_agency", "hair_salon", "bakery", "food_store", "store"], #QoS
    "sports": ["athletic_field","sports_complex","gym", "fitness_center","swimming_pool"], #QoS
    "green": ["national_park","park"],
    "travel": ["bus_station","bus_stop","train_station", "taxi_stand"]
    }

    radiuses = {
    "goOut": 100,
    "culture": 1000,
    "shoping": 100,
    "education": 300,
    "entertain": 600,
    "health": 200,
    "turism": 600,
    "housing": 300,
    "sports": 300,
    "green": 300,
    "travel": 200
    }

    groups = ["goOut", "culture", "shoping", "education", "entertain", "health", "turism", "sports", "green", "travel"] # "housing", 
    paramNameMap = {"goOut": "Clubs, bars",
                     "culture": "Cinema, museum, theaters", 
                     "shoping": "Shopping", 
                     "education": "Education", 
                     "entertain": "Entertainment", 
                     "health": "Health services", 
                     "turism": "Turism", 
                     "housing": "Amenities", 
                     "sports": "Sports opportunities", 
                     "green": "Parks, green", 
                     "travel": "Public transportation",
                     "pollution": "Pollution",
                     }
    headers = {
            'Content-Type': 'application/json',  # Set content type
            'Authorization': 'AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0',  # Example header
            'X-Goog-Api-Key': "AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0",
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.types,places.priceLevel,places.primaryType,places.id,places.location,places.allowsDogs,places.curbsidePickup,places.delivery,places.dineIn,places.editorialSummary,places.evChargeOptions,places.fuelOptions,places.goodForChildren,places.goodForGroups,places.goodForWatchingSports,places.liveMusic,places.menuForChildren,places.parkingOptions,places.paymentOptions,places.outdoorSeating,places.reservable,places.restroom,places.servesBeer,places.servesBreakfast,places.servesBrunch,places.servesCocktails,places.servesCoffee,places.servesDessert,places.servesDinner,places.servesLunch,places.servesVegetarianFood,places.servesWine,places.takeout"
        }        


    #external_api_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json??keyword=&radius="+str(radius)+"&type="+type+"&location="+location
    external_api_url = "https://places.googleapis.com/v1/places:searchNearby"
    rentalObject = Rentals.objects.get(id = rentalID)
    response = {}
    sumValues = 0
    normedScores = []
    allPlaces = []
    for param in groups:
        paramRank = str(param)+"Rank"

        requestData = {
                "includedTypes": types[param],
                "maxResultCount": "20",
                "locationRestriction": {
                    "circle": {
                        "center": {
                            "latitude": str(getattr(rentalObject, 'gps_lat') ),
                            "longitude": str(getattr(rentalObject, 'gps_lon') )},
                        "radius": str(radiuses[param])
                        }
                    }
                }
        
        score = getattr(rentalObject, paramRank)
        paramPlaces = getattr(rentalObject, param)
        if not(score) or (score == 0) or (score == "") or (score == None):
            if 'pollution' in param:
                pollutionRank = AirQuality(rentalID)
                setattr(rentalObject, param, pollutionRank['polutants'])
                setattr(rentalObject, paramRank, pollutionRank['rank']) #normalize
                rentalObject.save() 
                #print('pollutionRank', pollutionRank)       
            else:

                response = requests.post(external_api_url,
                                            headers=headers, 
                                            json=requestData
                                            )
                responseJson = response.json()


                if "places" in responseJson:
                    setattr(rentalObject, param, json.dumps(responseJson["places"]))
                    setattr(rentalObject, paramRank, len(responseJson["places"])) #normalize
                    rentalObject.save()   
                    if param == "turism":    
                        score =  20-len(responseJson["places"])
                    else:
                        score =  len(responseJson["places"])
                    paramPlaces = responseJson["places"]  

                else:
                    score =  0
                    paramPlaces = {}
        else:
            try:
                paramPlaces = json.loads(paramPlaces)
            except:
                response = requests.post(external_api_url,
                                            headers=headers, 
                                            json=requestData
                                            )
                responseJson = response.json()

                if "places" in responseJson:
                    setattr(rentalObject, param, json.dumps(responseJson["places"]))
                    setattr(rentalObject, paramRank, len(responseJson["places"])) #normalize
                    rentalObject.save()       
                    if param == "turism":    
                        score =  20-len(responseJson["places"])
                    else:
                        score =  len(responseJson["places"])
                    paramPlaces = responseJson["places"]  

                else:
                    score =  0
                    paramPlaces = {}

        #print('score', paramRank, score)       

        min_max_values = Rentals.objects.aggregate(
            min_value=Min(paramRank),
            max_value=Max(paramRank)
        )
        if min_max_values['min_value'] == "":
            min_max_values['min_value'] = 0
        if min_max_values['max_value'] == "":
            min_max_values['max_value'] = 20    # 20 is the max number of search items the Google API returns with
        #if getattr(rentalObject, paramRank):
        if min_max_values['max_value'] == 0:
            normScore = 0
        else:
            #print('score, sumValues',score, sumValues, float(min_max_values['max_value']))

            normScore = round(float(score/20*100),0)    #Shall be "float(min_max_values['max_value']" in the denominator, if values in DB are real
            normedScores.append({'name': paramNameMap[param], 'value': normScore})
            allPlaces.append({'name': paramNameMap[param], 'value': paramPlaces})
        sumValues += normScore

    #return SendGoogleAPIRequest(external_api_url, headers, requestData)
    if len(normedScores) > 0:
        finalResult = sumValues/len(normedScores)
    else:
        finalResult = 0

    return {'scores': normedScores, 'result': finalResult, 'places':  allPlaces}


def AirQuality(rentalID):
    rental_property_query = Rentals.objects.filter(id__iexact = rentalID)
    rentalData = RentalsSerializer(rental_property_query, many=True).data
    pollutionRank={'pollutionRank': 2}

    if rentalData[0]['pollutionRank']:
        pollution = rentalData[0]['pollution']
        pollutionRank = analizeAirQuality(pollution)
    else:
        pollution = sendAirQuality("",rentalData[0]["gps_lat"], rentalData[0]["gps_lon"])
        if not('error' in pollution):
            rentalObject = Rentals.objects.get(id = rentalID)
            pollutionRank = analizeAirQuality(pollution)
            print('type(pollutionRank)',str(type(pollutionRank['rank'])))
            if 'float' in str(type(pollutionRank['rank'])):
                setattr(rentalObject, 'pollutionRank', pollutionRank['rank'])
            setattr(rentalObject, 'pollution', pollution)
            rentalObject.save()
            return Response(pollutionRank, status=status.HTTP_200_OK)
        #else:
                # interpolate in case data is not found in DB and API call is unsuccessful
            '''queryset = Rentals.objects.values('gps_lat', 'gps_lon', 'pollutionRank')  # Use `only()` to limit the fields retrieved
                pollutionRankSeries = RentalsSerializer(queryset)
                print('pollutionRankSeries', pollutionRankSeries)
                df = pd.DataFrame(pollutionRankSeries)
                points = df[['gps_lat', 'gps_lon']].values  # Known points (latitude, longitude)
                values = df['pollutionRank'].values  # Known parameter values
                target_point = np.array([rentalData[0]["gps_lat"], rentalData[0]["gps_lon"]])  # Example: Latitude 35.0, Longitude -120.0
                interpolated_pollutionRank = griddata(points, values, target_point, method='linear')

                print('interpolated_pollutionRank', interpolated_pollutionRank)'''

    return pollutionRank

def sendAirQuality(keyword, gps_lat, gps_lon):
    # Example external API URL (replace with the actual API endpoint)
      
    headers = {
            'Content-Type': 'application/json'  # Set content type
        }      
    requestData = {
            "period": {
                "startTime":"2024-08-17T12:00:00Z",
                "endTime":"2024-08-25T12:00:00Z"
            },
            "pageSize": "3",
            "pageToken":"",
            "location": {
                "latitude": str(gps_lat),
                "longitude": str(gps_lon)
            }
            }

    external_api_url = "https://airquality.googleapis.com/v1/history:lookup?key=AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0"
   
    return SendGoogleAPIRequest(external_api_url, headers, requestData)


def analizeAirQuality(pollution):
    rangeNames = ["Excellent",
        "Good",
        "Moderate",
        "Low",
        "Poor"]
    #for hourData in pollution['hoursInfo']:
    df = pd.DataFrame(pollution)
    if 1:
        #print('df', df['aqi'].mean(), df['aqi'].quantile([0, .25, .5, .75, 1])) #hourData['indexes'][0]['aqi'].mean()
        #ranges = [(100,80),(80,60),(60,40),(40,20),(20,0)]
        ranges = [100, 80, 60, 40, 20, 0]
        q1 = df['aqi'].quantile(.25)
        q0 = df['aqi'].min()
        q3 = df['aqi'].quantile(.25)
        q4 = df['aqi'].max()
        q1I = 0
        while ranges[q1I]:
            if ranges[q1I] < q1:
                break
            q1I+=1
        q3I = 0
        while ranges[q3I]:
            if ranges[q3I] < q3:
                break
            q3I+=1

        q0I = 0
        while ranges[q0I]:
            if ranges[q0I] < q0:
                break
            q0I+=1
        q4I = 0
        while ranges[q4I]:
            if ranges[q4I] < q4:
                break
            q4I+=1

        #returnResult = {'min': rangeNames[q0I-1], 'q1': rangeNames[q1I-1], 'q2': rangeNames[q3I-1], 'max': rangeNames[q4I-1], 'rank': df['aqi'].quantile(.5)}
        returnResult = {'rank': df['aqi'].quantile(.5), 'polutants': df['dominantPollutant'].unique()}

    else:
        returnResult={'error': 'No entry'}

    
    return returnResult

def calculateSalary(job_properties):
    cityRanges = {'New York': [{'ranges': [0,100], 'paid': 'hourly'},
                         {'ranges': [101,1000], 'paid': 'daily'},
                         {'ranges': [1001,20000], 'paid': 'monthly'},
                         {'ranges': [20001,2000000], 'paid': 'yearly'},
                         
                         ]}

    if not 'paid' in job_properties:
        for salRange in cityRanges['New York']:
            if (job_properties['salary'] > salRange['ranges'][0]) & (job_properties['salary'] < salRange['ranges'][1]):
                job_properties['paid'] = salRange['paid']
                print('Salary range',salRange, job_properties['salary'], job_properties['paid'])


    paidMultiplier = 1

    if 'paid' in job_properties:
        if job_properties['paid'] == 'hourly':
            paidMultiplier = 8*22
        elif job_properties['paid'] == 'daily':
            paidMultiplier = 22
        elif job_properties['paid'] == 'yearly':
            paidMultiplier = 1/12
        elif job_properties['paid'] == 'weekly':
            paidMultiplier = 4
        elif job_properties['paid'] == 'monthly':
            paidMultiplier = 1

    if job_properties['currency'] == 'USD':
        currencyMultiplier = 1
    else:
        currencyMultiplier = 1        

    return round(float(job_properties["salary"]) * paidMultiplier * currencyMultiplier,0)


def calculateSecurity(rentalID):
    rental_property = Rentals.objects.get(id = rentalID)
    rental_properties = RentalsSerializer(rental_property).data
    securityRank = rental_properties["securityRank"]
    cityObj = Cities.objects.get(name = rental_properties["clusterCity"] )

    secuParams = {'CRMCYPROC': 'Property crime',
                'CRMCYASST': 'Assault',
                'CRMCYMURD': 'Murder',
                'CRMCYMVEH': 'Motor Vehicle Theft',
                'CRMCYRAPE': 'Rape',
                'CRMCYPERC': 'Personal crime',
                #'CRMCYTOTC': 'Total',
                'CRMCYROBB': 'Robbery',
                'CRMCYLARC': 'Larceny',
                'CRMCYBURG': 'Burhlary'
                }

    paramsEval = {}
    total = 0
    for item,value in json.loads(getattr(cityObj, 'Secirity').replace("'",'"')).items():
        if item in secuParams:
            paramsEval[secuParams[item]] = round((json.loads(rental_properties["security"].replace("'",'"'))[item]/value)*100)
            total += paramsEval[secuParams[item]]
        #else:
        #    total = round((1-json.loads(rental_properties["security"].replace("'",'"'))[item]/value)*100)


    secDescription = '' #make_security_description(rental_properties)
    return {"result": round((1-total/len(paramsEval)/100)*100,0), "scores": paramsEval , "desc": secDescription} 


def calculateAffordability(rentalID, jobID):
    rental_property = Rentals.objects.get(id = rentalID)
    job_property = Jobs.objects.get(id = jobID)
    rental_properties = RentalsSerializer(rental_property).data
    job_properties = JobSerializer(job_property).data
    city = rental_properties["clusterCity"]
    cityProps = Cities.objects.get(name = city)
    cityCostData = CityCostSerializer(cityProps).data
    cityDataData = CitySerializer(cityProps).data
    salary = calculateSalary(job_properties) #float(job_properties["salary"])


    """
    # Rental properties
    area = rental_properties["area"]



    #print('cityData sum: ', sum(cityCostData.values()))


    # Job properties
    industry = job_properties["industry"]
    sector = job_properties["sector"]
    jobName = job_properties["name"]
    #print('salary',salary)

    rentals_property_query = Rentals.objects.filter(clusterCity__iexact = city, size__isnull=False, price__isnull=False)
    city_rentals = RentalsSerializer(rentals_property_query, many=True).data 
    rentals_property_query = Rentals.objects.filter(clusterCity__iexact = city, area__iexact = area, size__isnull=False, price__isnull=False)
    city_area_rentals = RentalsSerializer(rentals_property_query, many=True).data


    jobs_property_query = Jobs.objects.filter(clusterCity__iexact = city, salary__isnull=False)
    city_jobs = JobSerializer(jobs_property_query, many=True).data 
    for item in city_jobs:
        item['salary'] = calculateSalary(item)


    df_city_rentals = pd.DataFrame(city_rentals)
    df_city_jobs = pd.DataFrame(city_jobs)
    #df_city_area_rentals = pd.DataFrame(city_area_rentals)


    df_city_jobs['usdSalary'] = pd.to_numeric(df_city_jobs['salary']) #* pd.to_numeric(df_city_jobs["currency"])
    df_city_rentals['sqmCityPrice'] = pd.to_numeric(df_city_rentals['price']) / pd.to_numeric(df_city_rentals['bed'])

    #sqmPrice = float(rental_properties['price'])/float(rental_properties['bed'])

    #filteredJobs, outliersJobs = tukeys_fences(df_city_jobs['usdSalary'], salary)
    #filteredRental, outliersRental = tukeys_fences(df_city_rentals['sqmCityPrice'], sqmPrice)



    df_city_area_rentals = df_city_rentals[df_city_rentals['area'] == area]

    #KPIs
    #   1) compare total spending to the city average
    #   2) compare rental to the average rental spending in city
    #   3) Compare rental share from the total spending
    #   4) Rental price is higher than average in city

    # salary vs city average
    # total costs vs city average
    # 
    # Affordability score:
    #   - 20% stretch on total living costs is 0% affordability
    #   - 
    try:
        cityRentalToSalary = float(cityDataData['rentalFee'])/1.5/float(cityDataData['avgNetSalary'])
    except:
        cityRentalToSalary = 0

    try:
        ownRentalToSalary = float(rental_properties["price"])/(salary/12)
    except:
        ownRentalToSalary = 0

    try:
        rentalToCosts = float(rental_properties["price"]) / sum(cityCostData.values()),
    except:
        rentalToCosts = 0

    scores = {
            'cityRentalToSalary': cityRentalToSalary,
            'ownRentalToSalary': ownRentalToSalary,
            'cityAverageCosts': sum(cityCostData.values()),
            'ownCosts': sum(cityCostData.values()) -  float(cityDataData['rentalFee']) + float(rental_properties["price"]),
            'rentalToCosts': rentalToCosts,
        }
    
    affordabilityResultFactor = ((salary/scores['ownCosts'] - 1)-0.5)*2.5
    affordabilityResult = pow(2, affordabilityResultFactor )/(1+pow(2,affordabilityResultFactor))*100 # sigmoid function
    print('affordabilityResult', affordabilityResult)

    affDescription = ""
    #if not(getattr(rental_property, 'affDescription')):
    #    affDescription = make_aff_description(scores)
    #    setattr(rental_property, 'affDescription', affDescription)
    #    setattr(rental_property, 'affScore', scores)
    #    rental_property.save()
    #else:
    #    affDescription = getattr(rental_property, 'affDescription')
    """

    # Affordability categories
    #   Savings = 0% --> Affordability = 10% 
    #   safety buffer = 
    #   bonus = 20%
    #         fields = ["rentalFee", "markets", "transportation", "school", "sportsnLeisure", "utilities", "clothing", "restaurants"]
    # costs doesn't cover health costs, that can be upsell

    userEssentialCosts = 0
    userGoodToHaveCosts = 0
    cityCostData.pop("Education")   # check from user personal data

    costs = (sum(cityCostData.values()) - cityCostData['Rental Fee'] + rental_properties['price']) + userEssentialCosts
    riskBudget = costs * 0.2
    recreationBudget = costs * 0.1

    bareMinCost = costs - cityCostData['SportsnLeisure'] - cityCostData['Restaurants']
    stretchedCost = costs
    affordableCost = costs + riskBudget
    comfortableCost = affordableCost + recreationBudget
    relaxingCost = comfortableCost + userGoodToHaveCosts
    forwardLookingCost = relaxingCost
    balance = round(salary - costs,0)

    personalCosts = cityCostData
    personalCosts['Rental Fee'] = rental_properties['price']



    # Affordability categories: 
    #   Unaffordable: salary doesn't cover minCosts --> 0%
    #   Stretched: salary between minCosts and costs, little going out and entertainment, no risk budget for unexpected expenses --> 0-20%
    #   Affordable: salary higher than costs, but smaller than all cost+20% risk budget --> 40-60%
    #   Comfortable: salary higher than costs+20% risk budget, but smaller than costs+20% risk budget+10% holiday --> 60-70%
    #   Relaxing: higher than costs+20% risk budget+10% holiday --> 70-85%
    #   Forward-looking: higher than costs+20% risk budget+10% holiday --> 85-100%
    
    affordabilityCategory = 'Unaffordable'
    if salary > bareMinCost:
        affordabilityCategory = 'Stretched'
        personalCosts.pop("SportsnLeisure")
        personalCosts.pop("Restaurants")
        balance = round(salary - bareMinCost,0)
    elif salary > stretchedCost:
        affordabilityCategory = 'Affordable'
        personalCosts.pop("SportsnLeisure")
        personalCosts.pop("Restaurants")
        balance = round(salary - stretchedCost,0)

    elif salary > affordableCost:
        affordabilityCategory = 'Comfortable'
        personalCosts['Risks'] = riskBudget
        balance = round(salary - affordableCost,0)
    elif salary > comfortableCost:
        affordabilityCategory = 'Relaxing'
        personalCosts['Risks'] = riskBudget
        personalCosts['Recreation'] = recreationBudget
        balance = round(salary - comfortableCost,0)
    elif salary > relaxingCost:
        affordabilityCategory = 'Forward-looking'
        personalCosts['Risks'] = riskBudget
        personalCosts['Recreation'] = recreationBudget
        balance = round(salary - relaxingCost,0)
    savingRate = balance/salary


    # Option 1: saturation function
    affordabilityResult = round(100/(1+pow(2,(0.4 - savingRate)*7.5)),0)

    # Option 2: hyperbolic function
    #affordabilityResult = 1-1/(savingRate+1)

    response = {'result': affordabilityResult, 'category': affordabilityCategory, "scores": {'salary': salary, 'balance':  balance, 'savingRate': round(savingRate*100,0), 'totalCost': costs}, 'costs': personalCosts }

    return response

def amendStartEnd(cityCounts, posCounts, industryCounts, bin_edges):
    start = bin_edges[0]
    end = bin_edges[-1]
    steps = bin_edges[1] - bin_edges[0]
    extendedEdges = np.append(bin_edges, end+steps)#.insert(0,start-steps)
    extendedEdges = np.insert(extendedEdges, 0, start-steps)#.insert(0,start-steps)

    extendedCityCounts = np.append(cityCounts,0)
    extendedCityCounts = np.insert(extendedCityCounts, 0, 0)

    extendedPosCounts = np.append(posCounts,0)
    extendedPosCounts = np.insert(extendedPosCounts, 0, 0)

    extendedIndustryCounts = np.append(industryCounts,0)
    extendedIndustryCounts = np.insert(extendedIndustryCounts, 0, 0)

    return {'cityCounts': extendedCityCounts.tolist(),'posCounts': extendedPosCounts.tolist(), 'industryCounts': extendedIndustryCounts.tolist(), 'edges': extendedEdges.tolist()}


def calculateRecognition(jobID):
    job_property = Jobs.objects.get(id = jobID)
    job_properties = JobSerializer(job_property).data
    city = job_properties['city']

    # Job properties
    industry = job_properties["industry"]
    sector = job_properties["sector"]
    jobName = job_properties["name"]
    salary = calculateSalary(job_properties)
    print('industry, sector, jobName, salary', industry, sector, jobName, salary)

    cityProps = Cities.objects.get(name = city)
    cityDataData = CitySerializer(cityProps).data

    jobs_property_query = Jobs.objects.filter(city__iexact = city, salary__isnull=False)
    city_jobs = JobSerializer(jobs_property_query, many=True).data 
    for item in city_jobs:
        item['salary'] = calculateSalary(item)

    jobs_property_query = Jobs.objects.filter(city__iexact = city, name__iexact = jobName, salary__isnull=False)
    cityPositionJobs = JobSerializer(jobs_property_query, many=True).data 
    for item in cityPositionJobs:
        item['salary'] = calculateSalary(item)


    jobs_property_query = Jobs.objects.filter(city__iexact = city, name__iexact = jobName, salary__isnull=False, industry__iexact = industry)
    cityIndustryJobs = JobSerializer(jobs_property_query, many=True).data 
    for item in cityIndustryJobs:
        item['salary'] = calculateSalary(item)


    dfCityJobs = pd.DataFrame(city_jobs)
    dfCityJobs['usdSalary'] = pd.to_numeric(dfCityJobs['salary']) 
    dfCityPositionJobs = pd.DataFrame(cityPositionJobs)
    dfCityPositionJobs['usdSalary'] = pd.to_numeric(dfCityPositionJobs['salary']) 
    dfIndustryJobs = pd.DataFrame(cityIndustryJobs)
    dfIndustryJobs['usdSalary'] = pd.to_numeric(dfIndustryJobs['salary']) 


    filteredJobs, outliersJobs = tukeys_fences(dfCityJobs['usdSalary'], salary)
    filteredPositionJobs, outliersJobs = tukeys_fences(dfCityPositionJobs['usdSalary'], salary)
    filteredIndustryJobs, outliersIndustryJobs = tukeys_fences(dfIndustryJobs['usdSalary'], salary)


    counts, bin_edges = np.histogram(filteredJobs, bins=10)
    posCounts, posEdges = np.histogram(filteredPositionJobs, bins=bin_edges)
    industryCounts, industryEdges = np.histogram(filteredIndustryJobs, bins=bin_edges)

    cityResult = amendStartEnd(counts, posCounts, industryCounts, bin_edges)

        # Calculate key statistics
    quantiles = np.percentile(filteredJobs, [10, 25, 50, 75, 90])
    salaryDecile = find_decile(salary, filteredJobs) #(salary-min(filteredJobs))/(max(filteredJobs)-min(filteredJobs))*100
    salaryPositionDecile = find_decile(salary, filteredJobs) #filteredPositionJobs) #(salary-min(filteredJobs))/(max(filteredJobs)-min(filteredJobs))*100
    salaryIndustryDecile = find_decile(salary, filteredJobs) #filteredIndustryJobs) #(salary-min(filteredJobs))/(max(filteredJobs)-min(filteredJobs))*100
    salarySectorDecile = find_decile(salary, filteredJobs) #filteredSectorJobs) #(salary-min(filteredJobs))/(max(filteredJobs)-min(filteredJobs))*100


    jobs_property_query = Jobs.objects.filter(name__iexact = jobName, salary__isnull=False)
    PositionJobs = JobSerializer(jobs_property_query, many=True).data 
    for item in PositionJobs:
        item['salary'] = calculateSalary(item)

    jobs_property_query = Jobs.objects.filter(name__iexact = jobName, city__iexact = city, salary__isnull=False)
    positionCityjobs = JobSerializer(jobs_property_query, many=True).data 
    for item in positionCityjobs:
        item['salary'] = calculateSalary(item)

    jobs_property_query = Jobs.objects.filter(name__iexact = jobName, city__iexact = city, salary__isnull=False, industry__iexact = industry)
    positionIndustryJobs = JobSerializer(jobs_property_query, many=True).data 
    for item in positionIndustryJobs:
        item['salary'] = calculateSalary(item)


    dfPositionJobs = pd.DataFrame(PositionJobs)
    dfPositionJobs['usdSalary'] = pd.to_numeric(dfPositionJobs['salary']) 
    dfPositionCityJobs = pd.DataFrame(positionCityjobs)
    dfPositionCityJobs['usdSalary'] = pd.to_numeric(dfPositionCityJobs['salary']) 
    dfPositionIndustryJobs = pd.DataFrame(positionIndustryJobs)
    dfPositionIndustryJobs['usdSalary'] = pd.to_numeric(dfPositionIndustryJobs['salary']) 

    filteredJobs, outliersJobs = tukeys_fences(dfPositionJobs['usdSalary'], salary)
    filteredPositionJobs, outliersJobs = tukeys_fences(dfPositionCityJobs['usdSalary'], salary)
    filteredIndustryJobs, outliersIndustryJobs = tukeys_fences(dfPositionIndustryJobs['usdSalary'], salary)


    counts, bin__edges = np.histogram(filteredJobs, bins=bin_edges)
    posCounts, posEdges = np.histogram(filteredPositionJobs, bins=bin_edges)
    industryCounts, industryEdges = np.histogram(filteredIndustryJobs, bins=bin_edges)
    posResult = amendStartEnd(counts, posCounts, industryCounts, bin_edges)


    scores = {
            'inCity': cityResult,
            'inPosition': posResult,
            'quantiles': quantiles.tolist(),
            'salaryDecile': salaryDecile,
            'salaryPositionDecile': salaryPositionDecile,
            'salaryIndustryDecile': salaryIndustryDecile, 
            'salarySectorDecile': salarySectorDecile, 
            'salary': salary,
            'position': jobName,
        }

    overallResult = round((salaryPositionDecile*6 + salaryIndustryDecile + salarySectorDecile + salaryDecile)/9,0)

    '''violin = []
    for i in range(len(bin_edges.tolist())-1):
        violin.append({'name': (bin_edges.tolist()[i]+bin_edges.tolist()[i+1])/2,'city': counts.tolist()[i], 'industry': counts.tolist()[1], 'segment': counts.tolist()[1]})'''
    """if not(getattr(job_property, 'recDescription')):
        recDescription = make_recognition_description(scores)
        setattr(job_property, 'recDescription', recDescription)
        #setattr(job_property, 'recScore', scores)
        job_property.save()
    else:
        recDescription = getattr(job_property, 'recDescription')"""

    response = {"scores": scores , "result": overallResult}

    return response

def fillRentalSecurity(rentalID):
    rental_property = Rentals.objects.get(id = rentalID)
    rental_properties = RentalsSerializer(rental_property).data

    if rental_properties['securityRank'] == 0:
        point = Feature(geometry=Point([rental_properties['gps_lon'], rental_properties['gps_lat']]))

        with open('data/security/adt_geoData1.json') as f:
            d = json.load(f)
            for features in d["features"]:
                if boolean_point_in_polygon(point, features):
                    foundState = features

        if foundState:
            print('inside',foundState["properties"]['STATEABBR'])
            with open('data/security/'+foundState["properties"]['STATEABBR']+'.json') as f:
                d = json.load(f)
                for features in d["features"]:
                    if boolean_point_in_polygon(point, features):
                        foundCounty = features

        if foundCounty:
            print('inside',foundCounty["properties"]['COUNTYNAME'])
            with open('data/security/'+foundCounty["properties"]['COUNTYNAME'].replace(' ', '')+'.json') as f:
                d = json.load(f)
                for features in d["features"]:
                    if boolean_point_in_polygon(point, features):
                        foundArea = features
                        setattr(rental_property, 'securityRank', foundArea["properties"]['CRMCYTOTC'])
                        setattr(rental_property, 'security', foundArea["properties"])
                        rental_property.save()
                print('inside',foundArea["properties"])

    print('rental_properties',rental_properties['security'].replace("'",'"'))
    secProperties = json.loads(rental_properties['security'].replace("'",'"'))

    secDescription = '' #make_security_description(rental_properties)
    return {"scores": secProperties , "desc": secDescription, "result": rental_properties['securityRank']} 


def averSecurity(rentalID):
    # rental_property = Rentals.objects.get(id = rentalID)
    # rental_properties = RentalsSerializer(rental_property).data
    secuParams = ['CRMCYPROC',
                'CRMCYASST',
                'CRMCYMURD',
                'CRMCYMVEH',
                'CRMCYRAPE',
                'CRMCYPERC',
                'CRMCYTOTC',
                'CRMCYROBB',
                'CRMCYLARC',
                'CRMCYBURG']

    rental_property_query = Rentals.objects.all()
    cityObj = Cities.objects.get(name = getattr(rental_property_query[0], 'city') )
    print('Secirity old', getattr(cityObj, 'Secirity'))

    params = {}
    for rental_properties in rental_property_query:
        if getattr(rental_properties, 'security'):
            for item,value in json.loads(getattr(rental_properties, 'security').replace("'",'"')).items():
                if item in params:
                    if value > params[item]:
                        params[item] = value
                else:
                    if item in secuParams:
                        params[item] = value
    setattr(cityObj, 'Secirity', params)
    cityObj.save()
    print('Secirity', getattr(cityObj, 'Secirity'))



def allSecurity(rentalID):
    # rental_property = Rentals.objects.get(id = rentalID)
    # rental_properties = RentalsSerializer(rental_property).data

    rental_property_query = Rentals.objects.all()

    rental_property = RentalsSerializer(rental_property_query, many=True).data

    
    for rental_properties in rental_property_query:


        if not getattr(rental_properties, 'securityRank'):
            #point = Feature(geometry=Point([rental_properties['gps_lon'], rental_properties['gps_lat']]))
            point = Feature(geometry=Point([getattr(rental_properties, 'gps_lon'), getattr(rental_properties, 'gps_lat')]))

            with open('data/security/adt_geoData1.json') as f:
                d = json.load(f)
                for features in d["features"]:
                    if boolean_point_in_polygon(point, features):
                        foundState = features

            if foundState:
                print('inside',foundState["properties"]['STATEABBR'])
                with open('data/security/'+foundState["properties"]['STATEABBR']+'.json') as f:
                    d = json.load(f)
                    for features in d["features"]:
                        if boolean_point_in_polygon(point, features):
                            foundCounty = features

            if foundCounty:
                print('inside',foundCounty["properties"]['COUNTYNAME'])
                with open('data/security/'+foundCounty["properties"]['COUNTYNAME'].replace(' ', '')+'.json') as f:
                    d = json.load(f)
                    for features in d["features"]:
                        if boolean_point_in_polygon(point, features):
                            foundArea = features
                            setattr(rental_properties, 'securityRank', foundArea["properties"]['CRMCYTOTC'])
                            setattr(rental_properties, 'security', foundArea["properties"])
                            rental_properties.save()
                    print('inside',foundArea["properties"])

    secDescription = '' #make_security_description(rental_properties)
    return {"scores": foundArea["properties"] , "desc": secDescription, "result": foundArea["properties"]['CRMCYTOTC']} 

def getCoords(address):
    #gmaps = googlemaps.Client(key='AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0')

    # Geocoding an address
    #geocode_result = gmaps.geocode(address)

    #geocode_result[0]['geometry']['location']
    headers = {
            'Content-Type': 'application/json'  # Set content type
        }      
    data = {address}

    external_api_url = "https://maps.googleapis.com/maps/api/place/textsearch/json?key=AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0&query="+address
   
    result = SendSingleGoogleAPIRequest(external_api_url, headers,"")

    if len(result['results'])> 0 :
        return result['results'][0]['geometry']['location']
    else:
        return {'error': result}

def getJobAddress(company, city):
    #gmaps = googlemaps.Client(key='AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0')

    # Geocoding an address
    #geocode_result = gmaps.geocode(address)

    #geocode_result[0]['geometry']['location']

    data = {"textQuery" : company+' offices in '+city}

    headers = {
            'Content-Type': 'application/json',  # Set content type
            'Authorization': 'AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0',  # Example header
            'X-Goog-Api-Key': "AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0",
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.primaryType,places.id,places.location"
        }   

    external_api_url = "https://places.googleapis.com/v1/places:searchText"
   
    result = SendSingleGoogleAPIRequest(external_api_url, headers, data)

    if 'places' in result:
        if len(result['places']) > 0:
            return {'location': result['places'][0]['location'], 'address': result['places'][0]['formattedAddress']}
    else:
        return {'error': result}
    

def getCompanyParams(jobID):
    print('jobID', jobID)
    jobObj = Jobs.objects.get(id = jobID)
    jobData = JobSerializer(jobObj).data
    print('company', jobData['company'])

    try:
        companyObj = Companies.objects.get(name = jobData['company'])
    except:
        companyObj = False

    #companyObj = CompanySerializer(company_property_query)

        lat = "Not found"
        lon = "Not found"
        descr = "Not found"
        industry = "Not found"
        sector = "Not found"
        reviews = "Not found"

    print('companyObj', companyObj)

    if companyObj:
        if not getattr(companyObj, 'gps_lat'):
            coords = getJobAddress(jobData['company'], jobData['city'])
            setattr(companyObj, 'gps_lat', coords['location']['latitude'])
            setattr(companyObj, 'gps_lon', coords['location']['longitude'])
        if getattr(companyObj, 'reviews') == "Not found":
            try:
                #reviews = getCompReviews(jobData['company'], jobData['city']) #create a summary of Ralph Lauren company reviewed at indeed.com
                reviews = {'chatGPT': company_summary(jobData['company']), 'gemini': get_company_summary_and_employee_reviews(jobData['company'])}
                print('company reviews: ', reviews)
                setattr(companyObj, 'reviews', reviews)
            except:
                print('No reviews found')
                reviews = "No review is available"
        else:
            print(getattr('Existing company reviews: ', companyObj, 'reviews'))

        if not getattr(companyObj, 'industry'):
            indSec = getIndustry(jobData['company'], jobData['city'])
            setattr(companyObj, 'industry', indSec['industry'])
            setattr(companyObj, 'sector', indSec['sector'])
            setattr(companyObj, 'admin', indSec['admin'])

        companyObj.save()
        

        if not getattr(jobObj, 'industry'):
            setattr(jobObj, 'industry', getattr(companyObj, 'industry'))
            setattr(jobObj, 'sector', getattr(companyObj, 'sector'))
        jobObj.save()

        lat = getattr(companyObj, 'gps_lat')
        lon = getattr(companyObj, 'gps_lon')
        descr = getattr(companyObj, 'admin')
        industry = getattr(companyObj, 'industry')
        sector = getattr(companyObj, 'sector')
        reviews = getattr(companyObj, 'reviews')
    else:
        """if not getattr(companyObj, 'gps_lat'):
            coords = getJobAddress(jobData['company'], jobData['city'])
            setattr(companyObj, 'gps_lat', coords['location']['latitude'])
            setattr(companyObj, 'gps_lon', coords['location']['longitude'])"""
        try:
            #reviews = getCompReviews(jobData['company'], jobData['city']) #create a summary of Ralph Lauren company reviewed at indeed.com
            reviews = {'chatGPT': company_summary(jobData['company']), 'gemini': get_company_summary_and_reviews(jobData['company'])}
            print('company reviews: ', reviews)
            setattr(companyObj, 'reviews', reviews)
        except:
            print('No reviews found')
            reviews = "No review is available"
        """else:
            print(getattr('Existing company reviews: ', companyObj, 'reviews'))

        if not getattr(companyObj, 'industry'):
            indSec = getIndustry(jobData['company'], jobData['city'])
            setattr(companyObj, 'industry', indSec['industry'])
            setattr(companyObj, 'sector', indSec['sector'])
            setattr(companyObj, 'admin', indSec['admin'])

        companyObj.save()
        

        if not getattr(jobObj, 'industry'):
            setattr(jobObj, 'industry', getattr(companyObj, 'industry'))
            setattr(jobObj, 'sector', getattr(companyObj, 'sector'))
        jobObj.save()

        lat = getattr(companyObj, 'gps_lat')
        lon = getattr(companyObj, 'gps_lon')
        descr = getattr(companyObj, 'admin')
        industry = getattr(companyObj, 'industry')
        sector = getattr(companyObj, 'sector')
        reviews = getattr(companyObj, 'reviews')"""

    return {'gps_lat': lat, 'gps_lon': lon, 'compDescription': descr, 'industry': industry, 'sector': sector, 'reviews': reviews}

def getIndustry(company, city):
    data = {"query" : company}

    headers = {
            'Content-Type': 'application/json',  # Set content type
            'Authorization': '3ed6d266a81891891306b59f27d86dcc10a3e72d3f251162fd595594d08847d1',  # Example header
        }   

    external_api_url = "https://api.sec-api.io/full-text-search"
   
    result = SendSingleGoogleAPIRequest(external_api_url, headers, data)
    if len(result['filings'])>0:
        external_api_url = "https://api.sec-api.io/mapping/cik/"+result['filings'][0]['cik']

        result = requests.get(external_api_url,
                                headers=headers
                                )


        return {'sector': result.json()[0]['sicSector'], 'industry': result.json()[0]['sicIndustry'], 'admin': result.json()[0]}
    else:
        return {'sector': '', 'industry': '', 'admin': ''}


def make_hdi_description(point, features):
    params = {}
    for feature in features:
        if boolean_point_in_polygon(point, feature):
            params['adjusted_hdi'] = round(feature['properties']['adjusted_hdi']*100)
            if 'adjusted_income_index' in feature['properties']:
                params['Income'] = round(feature['properties']['adjusted_income_index']*100)
            if 'final_edu_index' in feature['properties']:
                params['Education'] = round(feature['properties']['final_edu_index']*100)
            if 'le_index' in feature['properties']:
                params['Life Expectancy'] = round(feature['properties']['le_index']*100)

    result = ''
    adjusted_hdi = 0
    if 'Income' in params:
        result = "The income is "+str(params['Income']) + "%, " \
        "Education level is "+str(params['Education']) + "%, "\
        "Life Expectancy is "+str(params['Life Expectancy']) + "% of the city averages"
        adjusted_hdi = params['adjusted_hdi']


    return params
            

def calculateNeighborhoods(rentalID):
    rental_property = Rentals.objects.get(id = rentalID)
    rental_properties = RentalsSerializer(rental_property).data

    HDIScore = calculateHDI(rental_property, rental_properties['gps_lon'], rental_properties['gps_lat'])
    try:
        priceContour = get_rental_price_contours(rental_properties['gps_lon'], rental_properties['gps_lat'],rental_properties['clusterCity'], 'ft', 10, 20)
    except:
        priceContour = []
    priceScore = 0
    priceHistogram, priceScore   = get_rental_price_histogram(rental_properties, rental_properties['size_unit'], rental_properties['clusterCity'])

    return {'HDI': HDIScore, 'score': HDIScore['score'], 'contour': priceContour, 'priceScore': priceScore, 'priceHistogram': priceHistogram }

def calculateHDI(rentalObj, lng, lat, zoom=10):
    tile = mercantile.tile(lng, lat, zoom)
    z = tile.z
    x = tile.x
    y = tile.y
    # Sources:  https://github.com/mansueto-institute/hdi-map/blob/main/build/index.js#L64
    #           https://github.com/mansueto-institute/local-hdi/blob/master/README.md
    #           https://communityhdi.org/#4.25/37.04/-90.34


    #print('features', features)
    #gdf = gpd.GeoDataFrame.from_features(features)
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

    if not location:
        setattr(rentalObj, 'location', location)
        setattr(rentalObj, 'locationRank', location['adjusted_hdi'])
        rentalObj.save()

    return {'features': features, 'evaluation': location, 'score': round(location['adjusted_hdi']/105*100,0)}

def get_company_summary_and_employee_reviews(company_name):
    """
    Összefoglalót, szektort/iparágat és alkalmazotti értékeléseket ad vissza a cég nevére,
    ingyenes/nyilvános forrásokból.
    
    FONTOS MEGJEGYZÉS: A kód web scraping technikákat használ (Glassdoor), amelyek
    könnyen blokkolhatók vagy hibásan működhetnek az oldal szerkezetének változásakor.
    A pénzügyi API-k (pl. Finnhub) ingyenes tier-je általában API kulcsot és korlátozott kéréseket igényel.
    """
    summary = {}
    reviews = {}
    
    # --- 1. Cég összefoglaló és Iparág/Szektor (Pénzügyi API) ---
    try:
        # Ehhez a lépéshez éles környezetben szükség van egy ingyenes Finnhub API kulcsra
        # Cseréld ki ezt a saját kulcsodra
        FINNHUB_API_KEY = "d4tg5rhr01qnn6lko020d4tg5rhr01qnn6lko02g"
        
        # A cég tőzsdei szimbólumát kell megkeresni (ez a lépés bonyolult, itt egy példát használunk)
        # Egy összetettebb rendszerben először egy 'symbol lookup' API-t kellene használni.
        TICKER_SYMBOL = "AAPL" # Példa: Apple Inc.
        
        # Cégprofil lekérése
        url_profile = f"https://finnhub.io/api/v1/stock/profile2?symbol={TICKER_SYMBOL}&token={FINNHUB_API_KEY}"
        response = requests.get(url_profile)
        data = response.json()
        
        if response.status_code == 200 and data and data.get('name'):
            summary['Company_Profile'] = {
                'Name': data.get('name'),
                'Country': data.get('country'),
                'Exchange': data.get('exchange'),
                'Industry': data.get('industry', 'N/A'), # A Finnhub ezt a mezőt használja
                'Sector': data.get('finnhubIndustry', 'N/A'), # A Finnhub ezt használja szélesebb szektorként
                'IPO_Date': data.get('ipo')
            }
        else:
            summary['Company_Profile'] = "Cég pénzügyi adatok, szektor és iparág nem találhatók (vagy API korlát elérve)."

    except Exception as e:
        summary['Company_Profile'] = f"Hiba a Finnhub API-nál: {e}"


    # --- 2. Alkalmazotti Értékelések (Web Scraping Glassdoor-ról) ---
    # A Glassdoor a legnépszerűbb az alkalmazotti véleményekhez az USA-ban és sok globális cégnél.
    try:
        # A cég nevét URL-barát formára kell alakítani (pl. "Google" -> "google")
        search_query = company_name.lower().replace(" ", "")
        glassdoor_url = f"https://www.glassdoor.com/Reviews/{search_query}-Reviews-E{TICKER_SYMBOL}.htm" # Példa URL, a Glassdoor URL-struktúrája változhat!
        
        # Figyelem: A Glassdoor erősen blokkolja az automatikus kéréseket és megkövetelhet bejelentkezést.
        # Ez a kísérlet valószínűleg csak az előlapot tölti be, a tényleges értékelések nélkül.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(glassdoor_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Próbáljuk meg kinyerni az általános értékelési statisztikákat (ez a rész rendkívül sebezhető)
            overall_rating_element = soup.find('div', {'data-test': 'overall-rating'})
            review_count_element = soup.find('div', {'data-test': 'review-count'})
            
            # Egyéb alkalmazotti metrikák (pl. kultúra, karrier, fizetés, stb.)
            culture_rating = soup.find('div', text=re.compile(r'Culture & Values')).find_next('div').text.strip() if soup.find('div', text=re.compile(r'Culture & Values')) else 'N/A'
            
            reviews['Employee_Reviews_Glassdoor'] = {
                'Note': 'Web scraping kísérlet. Eredményei korlátozottak lehetnek anti-bot védelem miatt.',
                'URL': glassdoor_url,
                'Overall_Employee_Rating': overall_rating_element.text.strip() if overall_rating_element else 'N/A',
                'Total_Review_Count': review_count_element.text.strip() if review_count_element else 'N/A',
                'Culture_and_Values_Rating': culture_rating
            }
        else:
            reviews['Employee_Reviews_Glassdoor'] = f"Értékelések nem találhatók a Glassdoor oldalon ({response.status_code})"

    except Exception as e:
        reviews['Employee_Reviews_Glassdoor'] = f"Hiba a Glassdoor scraping-nél: {e}"


    # --- 3. Végső Összefoglaló összeállítása ---
    final_summary = {
        'Company_Name': company_name,
        'US_EU_Data_Source_Note': 'A szektor és iparág pénzügyi API-ból (tőzsdén jegyzett cégekre), az alkalmazotti értékelések web scrapinggel (Glassdoor) kísérelve (lásd a korlátozásokat).',
        'Summary_Data': summary,
        'Review_Data': reviews
    }
    
    return final_summary


def get_wikipedia_summary_and_industry(company_name):
    """Fetch a short summary and industry info of the company from Wikipedia/Wikidata."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{company_name.replace(' ', '_')}"
    r = requests.get(url)
    if r.status_code != 200:
        return "No Wikipedia data found.", "Unknown", "Unknown"

    data = r.json()
    summary = data.get("extract", "No summary found.")
    page_title = data.get("title", company_name)

    # Try to extract industry from Wikidata
    wikidata_search = requests.get(f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={page_title}&language=en&format=json")
    print('Wiki result: ', wikidata_search)
    if wikidata_search.status_code == 200 and wikidata_search.json().get("search"):
        entity_id = wikidata_search.json()["search"][0]["id"]
        entity_data = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json").json()
        entities = entity_data.get("entities", {})
        if entity_id in entities:
            claims = entities[entity_id].get("claims", {})
            industry = "Unknown"
            sector = "Unknown"
            if "P452" in claims:  # Industry property
                ind_label = claims["P452"][0]["mainsnak"]["datavalue"]["value"]
                if "id" in ind_label:
                    # Fetch label for industry
                    id_label = ind_label["id"]
                    ind_res = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{id_label}.json").json()
                    industry = list(ind_res["entities"][id_label]["labels"].values())[0]["value"]
            if "P199" in claims:  # Sector or parent industry
                sector = claims["P199"][0]["mainsnak"]["datavalue"]["value"]["id"]
            return summary, industry, sector

    return summary, "Unknown", "Unknown"


def get_opencorporates_data(company_name):
    """Fetch company records from OpenCorporates API with jurisdiction data."""
    api_url = f"https://api.opencorporates.com/v0.4/companies/search?q={company_name}"
    r = requests.get(api_url)
    if r.status_code != 200:
        return ["Error fetching data from OpenCorporates."]
    
    results = r.json().get("results", {}).get("companies", [])
    summary = []
    for comp in results[:3]:
        c = comp["company"]
        name = c.get("name")
        jurisdiction = c.get("jurisdiction_code", "Unknown")
        address = c.get("registered_address_in_full", "No address listed")
        industry = c.get("industry_codes", [{}])[0].get("description", "Unknown")
        summary.append(f"{name} ({jurisdiction.upper()}): {address} | Industry: {industry}")
    return summary if summary else ["No company records found."]


def get_employee_reviews(company_name):
    """Estimate employee reviews from public Glassdoor/Indeed search results."""
    reviews = []
    
    # Glassdoor Search
    gd_url = f"https://www.glassdoor.com/Reviews/{company_name.replace(' ', '-')}-Reviews-EI_IE.htm"
    gd_search = requests.get(f"https://www.google.com/search?q={company_name.replace(' ', '+')}+site:glassdoor.com")
    if gd_search.status_code == 200:
        gd_match = re.search(r'([0-9]\.[0-9])\s+out of 5', gd_search.text)
        if gd_match:
            reviews.append(f"Glassdoor average rating: {gd_match.group(1)}/5")
    
    # Indeed Search
    indeed_search = requests.get(f"https://www.google.com/search?q={company_name.replace(' ', '+')}+site:indeed.com+reviews")
    if indeed_search.status_code == 200:
        indeed_match = re.search(r'([0-9]\.[0-9])\s+stars', indeed_search.text)
        if indeed_match:
            reviews.append(f"Indeed average rating: {indeed_match.group(1)}/5")
    
    return reviews if reviews else ["No employee reviews found (Glassdoor/Indeed)."]


def company_summary(company_name):
    print(f"🔍 Gathering data for: {company_name}\n")

    wiki_summary, industry, sector = get_wikipedia_summary_and_industry(company_name)
    print("📘 Wikipedia Summary:")
    print(wiki_summary, "\n")

    print(f"🏭 Industry: {industry}")
    print(f"🌍 Sector: {sector}\n")

    corp_data = get_opencorporates_data(company_name)
    print("🏢 OpenCorporates Records (US/EU examples):")
    for item in corp_data:
        print("-", item)
    print()

    review_summary = get_employee_reviews(company_name)
    print("👥 Employee Reviews Summary:")
    for r in review_summary:
        print("-", r)
    print("\n✅ Done.")


def get_next_weekday_timestamp(weekday, hour):
    """
    Get the Unix timestamp for the next specified weekday and hour.
    weekday: 0 for Monday, 3 for Thursday
    """
    now = datetime.now()
    days_ahead = weekday - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    target_date = now + timedelta(days=days_ahead)
    target_time = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    return int(target_time.timestamp())

def format_location(loc):
    if isinstance(loc, dict):
        if 'lat' in loc and 'lng' in loc:
            return f"{loc['lat']},{loc['lng']}"
        if 'latitude' in loc and 'longitude' in loc:
            return f"{loc['latitude']},{loc['longitude']}"
    elif isinstance(loc, (list, tuple)) and len(loc) == 2:
        return f"{loc[0]},{loc[1]}"
    return str(loc)

def get_commute_route(origin, destination, mode):
    """
    Returns the route points and duration between point A (origin) to B (destination) 
    at 8:00 Monday morning local time, and back from B to A at 17:00 Thursday local time.
    Optional modes: 'driving' (1), 'transit' (2), 'bicycling' (3)
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    api_key = "AIzaSyDenC1k5H6mYqbnFnn87qd-p2MqZQc4Wn0"
    
    origin_str = format_location(origin)
    dest_str = format_location(destination)

    response_a_b = requests.get(url, params={"origin": origin_str, "destination": dest_str, "departure_time": get_next_weekday_timestamp(0, 8), "mode": mode, "key": api_key}).json()
    response_b_a = requests.get(url, params={"origin": dest_str, "destination": origin_str, "departure_time": get_next_weekday_timestamp(3, 17), "mode": mode, "key": api_key}).json()
    
    def parse_directions(data):
        if data.get("status") == "OK" and data.get("routes"):
            route = data["routes"][0]
            leg = route["legs"][0]
            encoded_points = route["overview_polyline"]["points"]
            decoded_coords = polyline.decode(encoded_points, geojson=True)
            return {
                "duration": int(leg.get("duration_in_traffic", leg.get("duration", {})).get("value", "N/A")/60),
                "geojson": {
                    "type": "LineString",
                    "coordinates": decoded_coords
                }
            }
        return {"error": data.get("status", "No routes found"), "message": data.get("error_message", "")}

    return {"out": parse_directions(response_a_b), "back": parse_directions(response_b_a)}


def get_rental_price_histogram(rental, size_unit='sqm', cluster_city=None):
    """
    Calculates the histogram of the rental price per square meter or square feet
    using Numpy on a 10-edge scale.
    """
    filters = {
        'size_unit__iexact': size_unit,
        'price__isnull': False,
        'size__isnull': False,
    }
    if cluster_city:
        filters['clusterCity__iexact'] = cluster_city

    rentals = Rentals.objects.filter(**filters).values('price', 'size')

    prices_per_unit = [r['price'] / r['size'] for r in rentals if r['price'] is not None and r['size'] is not None and r['size'] > 0]

    if not prices_per_unit:
        return {'counts': [], 'bin_edges': []}

    counts, bin_edges = np.histogram(prices_per_unit, bins=10)
    unitPricePercentileRank = 0
    if rental['size']>0:
        unitPrice = rental['price'] / rental['size']

        unitPricePercentileRank = round(stats.percentileofscore(prices_per_unit, unitPrice))

    return {
        'counts': counts.tolist(),
        'bin_edges': bin_edges.tolist()
    }, unitPricePercentileRank


def get_rental_price_contours(lng, lat, cluster_city, size_unit='m', grid_size=30, num_levels=20):
    """
    Generates contour lines as GeoJSON polygons representing areas with similar 
    per-square-meter rental price levels within a given clusterCity.
    """

    city_obj, _ = Cities.objects.get_or_create(name=cluster_city)
    cache_key = f"{size_unit}:{grid_size}:{num_levels}"
    cached_contours = city_obj.rentalPriceContours

    if isinstance(cached_contours, str):
        try:
            cached_contours = json.loads(cached_contours)
        except (TypeError, ValueError):
            cached_contours = None

    if isinstance(cached_contours, dict):
        if 'type' in cached_contours and 'features' in cached_contours:
            return cached_contours
        if cache_key in cached_contours:
            return cached_contours[cache_key]

    lat = float(lat)
    lng = float(lng)
    
    # 1 degree of latitude is approx 111 km
    lat_delta = 10 / 111.0
    lon_delta = 10 / (111.0 * np.cos(np.radians(lat)))

    filters = {
        'clusterCity__iexact': cluster_city,
        'size_unit__iexact': size_unit,
        'price__isnull': False,
        'size__isnull': False,
        'gps_lat__isnull': False,
        'gps_lon__isnull': False,
        #'gps_lat__gte': lat - lat_delta,
        #'gps_lat__lte': lat + lat_delta,
        #'gps_lon__gte': lng - lon_delta,
        #'gps_lon__lte': lng + lon_delta,
    }

    rentals = Rentals.objects.filter(**filters).values('price', 'size', 'gps_lat', 'gps_lon')
    
    center_point = Feature(geometry=Point((lng, lat)))
    filtered_rentals = []
    for r in rentals:
        if r['price'] is not None and r['size'] is not None and r['size'] > 0:
            rental_point = Feature(geometry=Point((r['gps_lon'], r['gps_lat'])))
            #if distance(center_point, rental_point, units='km') <= 10:
            filtered_rentals.append(r)

    lats = [r['gps_lat'] for r in filtered_rentals]
    lons = [r['gps_lon'] for r in filtered_rentals]
    prices_per_unit = [r['price'] / r['size'] for r in filtered_rentals]

    if len(lats) < 4:
        return {"error": "Not enough data points to generate contours"}

    df = pd.DataFrame({'lat': lats, 'lon': lons, 'price': prices_per_unit})
    filtered_prices, _ = tukeys_fences(df['price'], 0, 2)
    df_filtered = df.loc[filtered_prices.index]

    if len(df_filtered) < 4:
        return {"error": "Not enough data points to generate contours"}

    lats = df_filtered['lat'].values
    lons = df_filtered['lon'].values
    prices = df_filtered['price'].values

    lat_grid = np.linspace(min(lats), max(lats), grid_size)
    lon_grid = np.linspace(min(lons), max(lons), grid_size)
    lon_grid_mesh, lat_grid_mesh = np.meshgrid(lon_grid, lat_grid)

    price_grid = griddata((lons, lats), prices, (lon_grid_mesh, lat_grid_mesh), method='linear')

    matplotlib.use('Agg')
    contour = plt.contourf(lon_grid_mesh, lat_grid_mesh, price_grid, levels=num_levels)
    geojson_isobands = geojsoncontour.contourf_to_geojson(contourf=contour, ndigits=5)
    plt.close()

    contour_geojson = json.loads(geojson_isobands)

    if not isinstance(cached_contours, dict) or ('type' in cached_contours and 'features' in cached_contours):
        cached_contours = {}

    cached_contours[cache_key] = contour_geojson
    city_obj.rentalPriceContours = cached_contours
    city_obj.save(update_fields=['rentalPriceContours'])

    return contour_geojson
