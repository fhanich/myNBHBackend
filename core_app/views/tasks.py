from celery import shared_task
import pandas as pd

from .utils import SearchNearby, calculateAffordability, AirQuality, calculateRecognition, calculateSalary, calculateSecurity, calculateNeighborhoods, get_commute_route
from .chatGPT import make_QoL_description
from ..models import Rentals, Cities, Jobs
from ..serializers import RentalsSerializer, CityCostSerializer, JobSerializer, JobShortSerializer

@shared_task
def evaluate_scenario_task(rentalID, jobID):
    """
    Celery task to evaluate a scenario in the background.
    """
    rental_property_query = Rentals.objects.filter(id__iexact=rentalID)
    job_property_query = Jobs.objects.filter(id__iexact=jobID)
    rental_properties = RentalsSerializer(rental_property_query, many=True).data
    job_properties = JobShortSerializer(job_property_query, many=True).data

    if not rental_properties or not job_properties:
        return {'error': 'Invalid rental or job ID.'}

    if rental_properties[0]['clusterCity'] != job_properties[0]['clusterCity']:
        return {'error': 'Cross city evaluation is not yet available'}

    # The entire logic from the original view goes here.
    cityProps = Cities.objects.filter(name__iexact=job_properties[0]['clusterCity'])
    cityData = CityCostSerializer(cityProps, many=True).data
    
    # --- Reference Response Calculation ---
    city_job_property_query = Jobs.objects.filter(name__iexact=job_properties[0]['name'], city__iexact=job_properties[0]['city'])
    city_positions = JobSerializer(city_job_property_query, many=True).data
    for item in city_positions:
        item['salary'] = calculateSalary(item)
    df_pos = pd.DataFrame(city_positions)
    city_positions_median = {}
    if not df_pos.empty:
        city_positions_median = {
            'range': [*df_pos['salary'].quantile([0, .25, .5, .75, 1]), df_pos['salary'].mean()],
            'period': '', 'bonus': '', 'title': ''
        }

    city_job_industry_property_query = city_job_property_query.filter(industry__iexact=job_properties[0]['industry'])
    city_industry_positions = JobSerializer(city_job_industry_property_query, many=True).data
    for item in city_industry_positions:
        item['salary'] = calculateSalary(item)
    df_ind = pd.DataFrame(city_industry_positions)
    city_industry_positions_median = {}
    if not df_ind.empty:
        city_industry_positions_median = {
            'range': [*df_ind['salary'].quantile([0, .25, .5, .75, 1]), df_ind['salary'].mean()],
            'period': '', 'bonus': '', 'title': ''
        }

    referenceResponse = {
        'expenditure': {'family': '', 'children': '', 'area': '', 'costs': cityData[0] if cityData else {}},
        'income': {
            'salary': [city_positions_median, city_industry_positions_median],
            'industry': job_properties[0]['industry'],
            'sector': job_properties[0]['sector'],
            'job': job_properties[0]['name'],
        }
    }

    # --- Evaluation Response Calculation ---
    nearbyRestaurants = SearchNearby("", rental_properties[0]["gps_lat"], rental_properties[0]["gps_lon"], 500, "restaurant", rentalID)
    if 'error' in nearbyRestaurants:
        return {'error': 'Failed to get Quality of Life data.', 'details': nearbyRestaurants['error']}

    try:
        qolDescription = make_QoL_description(rentalID)
    except Exception as e:
        qolDescription = f"Quality of Life analysis not yet available here. Error: {e}"
    try:
        affordabilityScores = calculateAffordability(rentalID, jobID)
    except Exception as e:
        affordabilityScores = {'result': 0, "scores": [], "desc": f"Affordability analysis not yet available here. Error: {e}"}
    try:
        recognition = calculateRecognition(jobID)
    except Exception as e:
        recognition = {"scores": [], "desc": "", "result": 0, "error": str(e)}
    try:
        securityScores = calculateSecurity(rentalID)
    except Exception as e:
        securityScores = {"result": 0, "scores": {}, "desc": f"Security analysis not yet available here. Error: {e}"}
    try:
        neighborhoodsScores = calculateNeighborhoods(rentalID)
    except Exception as e:
        neighborhoodsScores = {'score': 0, 'desc': f"Neighborhoods analysis not yet available here. Error: {e}"}

    try:
        commuteScores = get_commute_route({'lat': rental_properties[0]["gps_lat"], 'lng': rental_properties[0]["gps_lon"]}, {'lat': job_properties[0]["gps_lat"], 'lng': job_properties[0]["gps_lon"]})
        morning_duration = commuteScores.get("A_to_B", {}).get("duration", "N/A")
        evening_duration = commuteScores.get("B_to_A", {}).get("duration", "N/A")
        commute_evaluation = [
            f"{morning_duration} estimated morning commute",
            f"{evening_duration} estimated evening commute"
        ]
        try:
            commute_time = int(morning_duration.split()[0])
        except (ValueError, AttributeError, IndexError):
            commute_time = 10
    except Exception as e:
        commuteScores = {'score': 0, 'desc': f"Commute analysis not yet available here. Error: {e}"}
        commute_evaluation = ["Commute analysis not yet available here"]
        commute_time = 10

    evaluationResponse = {
        "affordability": affordabilityScores,
        "recognition": recognition,
        "qualityoflife": {"scores": nearbyRestaurants['scores'], "desc": qolDescription},
        "commute": commuteScores,
        "security": securityScores,
        "neighborhoods": neighborhoodsScores.get("score"),
    }

    # --- Score Calculation ---
    overallScore = 0
    total = 0
    scores_to_check = [
        securityScores.get('result'), affordabilityScores.get('result'),
        recognition.get('result'), neighborhoodsScores.get('score'),
        nearbyRestaurants.get('result')
    ]
    for score in scores_to_check:
        if isinstance(score, (int, float)) and score > 0:
            overallScore += score
            total += 1

    scoreResponse = {
        "Overall Score": round(overallScore / total, 0) if total > 0 else 0,
        "Affordability": affordabilityScores.get('result', 0),
        "Recognition": recognition.get('result', 0),
        "Quality of life": nearbyRestaurants.get('result', 0),
        "Commute Time": commute_time,
        "Security": securityScores.get('result', 0),
        "Neighborhoods": neighborhoodsScores.get('score', 0)
    }

    return {
        'scores': scoreResponse,
        'reference': referenceResponse,
        'evaluation': evaluationResponse,
        'id': [rentalID, jobID]
    }