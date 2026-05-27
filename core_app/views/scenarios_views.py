from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework.generics import CreateAPIView
import pandas as pd
import requests
from .utils import SearchNearby, calculateAffordability, AirQuality, calculateRecognition, calculateSalary, calculateSecurity, calculateNeighborhoods, get_commute_route  # Import the function from utils
from .chatGPT import make_QoL_description, make_aff_description
from turfpy.transformation import circle
from turfpy.measurement import boolean_point_in_polygon

from ..models import Rentals, Cities, Jobs
from ..serializers import RentalsSerializer, CitySerializer, JobSerializer, UserRegistrationSerializer, CityCostSerializer, JobShortSerializer
import json
from  geojson import FeatureCollection, Feature, Point


class Scenarios(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        rentalID = request.data['rental']
        jobID = request.data['job']
        user = request.user
        print('Scenarios user', user)
        rental_property_query = Rentals.objects.filter(id__iexact = rentalID)
        job_property_query = Jobs.objects.filter(id__iexact = jobID)
        rental_properties = RentalsSerializer(rental_property_query, many=True).data
        job_properties = JobShortSerializer(job_property_query, many=True).data

        scoreResponse = [];
        titleResponse = "This scenario is not supported yet";
        referenceResponse = [];
        evaluationResponse = [];
        if rental_properties[0]['clusterCity'] == job_properties[0]['clusterCity']: # evaluate the scenario
            cityProps = Cities.objects.filter(name__iexact = job_properties[0]['clusterCity'])
            cityData = CityCostSerializer(cityProps, many=True).data
            # referenceResponse: compare to numbeo average references
            #   city salaries in same profession
            city_job_property_query = Jobs.objects.filter(name__iexact = job_properties[0]['name'], city__iexact = job_properties[0]['city'])
            city_positions = JobSerializer(city_job_property_query, many=True).data
            for item in city_positions:
                item['salary'] = calculateSalary(item)
            df = pd.DataFrame(city_positions)
            city_positions_median = {'range': [*df['salary'].quantile([0, .25, .5, .75, 1]), df['salary'].mean()],
                                     'period': '',
                                     'bonus': '',
                                     'title': ''
                                     }                                     

            #   city salaries in same profession and sector
            city_job_industry_property_query = city_job_property_query.filter(industry__iexact = job_properties[0]['industry'])
            city_industry_positions = JobSerializer(city_job_industry_property_query, many=True).data
            for item in city_industry_positions:
                item['salary'] = calculateSalary(item)

            df = pd.DataFrame(city_industry_positions)
            city_industry_positions_median = {'range': [*df['salary'].quantile([0, .25, .5, .75, 1]),df['salary'].mean()],
                                               'period': '',
                                               'bonus': '',
                                               'title': ''
                                            }
            referenceResponse = {'expenditure': {
                                    'family': '' ,
                                    'children': '' ,
                                    'area': '' ,
                                    'costs': cityData[0] ,
                                     },
                                'income': {
                                    'salary': [city_positions_median, city_industry_positions_median],
                                    'industry': job_properties[0]['industry'],
                                    'sector': job_properties[0]['sector'],
                                    'job': job_properties[0]['name'],
                                    }
                                }

            # evaluationResponse: 
            #   affordability
            #   recognition
            #   QoL
            #   commute
            #   
            """
            if not rental_properties[0]["referenceCircle"]:
                center = Feature(geometry=Point((rental_properties[0]["gps_lon"], rental_properties[0]["gps_lat"])))
                referenceCircle = circle(center, radius=0.5, steps=10, units='km')

                rentalObject = Rentals.objects.filter(city__iexact = rental_properties[0]['city'])
                points = RentalsSerializer(rentalObject, many=True).data

                pointsInReference = []
                for point in points:
                    pointCoords = Feature(geometry=Point([point['gps_lon'] , point['gps_lat']]))
                    if boolean_point_in_polygon(pointCoords, referenceCircle):
                        pointsInReference.append(point['id'])
                rentalObject = Rentals.objects.get(id = rentalID)
                setattr(rentalObject,'referenceCircle', pointsInReference)
                rentalObject.save()
            else:
                if not rental_properties[0]['locationRank']:
                    if rental_properties[0]['referenceCircle']:
                        rentalObj = Rentals.objects.filter(id__in=rental_properties['referenceCircle'])
                        neibourRentals = RentalsSerializer(rentalObj, many=True).data
                        meanNegibours = pd.DataFrame(neibourRentals)
                        print('meannegibours', meanNegibours['locationRank'].mean())"""


            nearbyRestaurants = SearchNearby("",rental_properties[0]["gps_lat"], rental_properties[0]["gps_lon"], 500, "restaurant", rentalID)
            if not('error' in nearbyRestaurants):

                #qolDescription = make_QoL_description(nearbyRestaurants)
                try:
                    qolDescription = make_QoL_description(rentalID)
                except:
                    qolDescription = "Quality of Life analysis not yet available here"
                try:
                    affordabilityScores = calculateAffordability(rentalID, jobID)
                except:
                    affordabilityScores = {'result': 0, "scores": [] , "desc": "Affordability analysis not yet available here"}

                try:
                    recognition = calculateRecognition(jobID)
                except:
                    recognition = {"scores": [] , "desc": "", "result": 0}
                #affordabilityDescription = make_aff_description(affordabilityScores)
                try:
                    securityScores = calculateSecurity(rentalID)
                except:
                    securityScores = {"result": 0, "scores": {} , "desc": "Security analysis not yet available here"}

                try:
                    neighborhoodsScores = calculateNeighborhoods(rentalID)
                except:
                    neighborhoodsScores = {'score': 0, 'desc': "Neighborhoods analysis not yet available here"}

                modes = ['driving', 'transit', 'bicycling'];
                commuteScores = {}
                averageCommute = 0
                for travelMode in modes:
                    try:
                        commuteScores[travelMode] = get_commute_route({'lat': rental_properties[0]["gps_lat"], 'lng': rental_properties[0]["gps_lon"]}, {'lat': job_properties[0]["gps_lat"], 'lng': job_properties[0]["gps_lon"]}, travelMode)
                        morning_duration = commuteScores[travelMode].get("out", {}).get("duration", "N/A")
                        evening_duration = commuteScores[travelMode].get("back", {}).get("duration", "N/A")
                        averageCommute += (morning_duration + evening_duration) / 6
                        print('averageCommute:', travelMode, averageCommute)
                        try:
                            commute_time = int(morning_duration.split()[0])
                        except (ValueError, AttributeError, IndexError):
                            commute_time = 10
                    except Exception as e:
                        print('Commute Error:', e)
                        commuteScores[travelMode] = {'score': 0, 'desc': "Commute analysis not yet available here"}
                        commute_time = 10

                commuteScore = round(100*pow(averageCommute, -2.5)/(pow(averageCommute, -2.5) + pow(45, -2.5)),0)
                print('commuteScore:', commuteScore)

                evaluationResponse = {
                    "affordability": affordabilityScores,
                    "recognition":  recognition,
                    "qualityoflife": nearbyRestaurants,
                    "commute": commuteScores,
                    "security": securityScores,
                    "neighborhoods": neighborhoodsScores,
                    
                    }
                overallScore=0
                total = 0

                if isinstance(securityScores['result'],(int, float)) & (securityScores['result']>0):
                    overallScore += (securityScores['result'])
                    total+=1
                if isinstance(affordabilityScores['result'],(int, float)) :
                    overallScore += (affordabilityScores['result'])
                    total+=1
                if isinstance(recognition['result'],(int, float)):
                    overallScore += (recognition['result'])
                    total+=1
                if isinstance(neighborhoodsScores['score'],(int, float)) :
                    overallScore += (neighborhoodsScores['score'])
                    total+=1
                if isinstance(nearbyRestaurants['result'],(int, float)) :
                    overallScore += (nearbyRestaurants['result'])
                    total+=1

                if isinstance(commuteScore,(int, float)) :
                    overallScore += commuteScore
                    total+=1

                scoreResponse = {
                    "Oveall Score": round(overallScore/total,0),
                    "Affordability": affordabilityScores['result'],
                    "Recognition": recognition['result'],
                    "Quality of life": nearbyRestaurants['result'],
                    "Commute Time": commuteScore,
                    "Security": securityScores['result'],
                    "Neighborhoods": neighborhoodsScores['score']
                }


            # titleResponse
            response = {'scores': scoreResponse,
                         'reference': referenceResponse,
                         'evaluation': evaluationResponse,
                         'id': [rentalID, jobID]
                         }

        else:
            response = {'error': 'Cross city evaluation is not yet available'}

        return Response(response, status=status.HTTP_200_OK)
    
