import openai
from ..models import Rentals, Jobs
from ..serializers import RentalsSerializer, JobSerializer
# Set up the API key (replace with your actual API key)
openai.api_key = "sk-g-61rzbTus78FDQVW7lBhXiGAK5kWiGKzlHWz9XUZPT3BlbkFJvQGjoLEM4XnO95sBSlw97v9AjDH1zDRwxT5_AqD1MA"

def call_openai_api(prompt, systemRole, model):
    '''response = openai.Completion.create(
        engine="GPT-3.5-turbo",  # Specify the model (e.g., text-davinci-003, gpt-4)
        prompt=prompt,
        max_tokens=150,  # Max length of the response
        n=1,  # Number of responses to return
        stop=None,  # What should stop the response
        temperature=0.7,  # Creativity level
    )'''


    response = openai.ChatCompletion.create(
        model=model,  # Free-tier available model
        messages=[
            {"role": "system", "content": systemRole},
            {"role": "user", "content": prompt},
        ],
        max_tokens=150,
        temperature=0.7,     # Creativity level
        presence_penalty=0.3, # Encourage new ideas
        frequency_penalty=0.3 # Discourage repetition
    )

    return response.choices[0].message.content

def paramMedians(params):
    prmList =[
        'entertainRank',
        'cultureRank',
        'greenRank',
        'shopingRank',
        'sportsRank',
        'pollutionRank',
        'healthRank',
        'entertainRank',
              ]
    return


def make_QoL_description(rentalID):
    rental_property_query = Rentals.objects.filter(id__iexact = rentalID)
    rental_property = RentalsSerializer(rental_property_query, many=True).data
    params = rental_property[0]

    # Example usage
    #medianParams = paramMedians(params)

    if not(params['gptDescription']):
        question = "I have defined a scale of 5 ranking system of locations with 50 as average in all parameters. Please make a description in 3-4 sentences of a location with the following ranks with positive emotional considerations: "
        question += "entertainment possibilities: "+str(params['entertainRank'])
        question += ", cultureal places: "+str(params['cultureRank'] ) + ", where median is 40"
        question += ", green and parks: "+str(params['greenRank']) + ", where median is 44"
        question += ", shoping possibilities: "+str(params['shopingRank']) + ", where median is 50"
        question += ", sports possibilities: "+str(params['sportsRank']) + ", where median is 50"
        question += ", air cleanness: "+str(params['pollutionRank']) + ", where median is 30"
        question += ", healthcare availability: " +str(params['healthRank']) + ", where median is 60"
        result = call_openai_api(question, "You are an expert of the location.", "gpt-3.5-turbo")

        rentalObject = Rentals.objects.get(id = rentalID)
        setattr(rentalObject, 'gptDescription', result)
        rentalObject.save()
    else:
        result = params['gptDescription']

    return result

def make_aff_description(scores):
    question = "How would you evaluate in 2-3 sentences from financial aspect the affordability of an apartment rental with emotional considerations, where the city level average rental fee is "
    question += str(scores['cityRentalToSalary']*100) + "% of the average disposable income and this appartment's rental fee is "
    question += str(scores['ownRentalToSalary']*100) + "% of the salary of the position. The average household cost is "
    question += str(scores['cityAverageCosts']) + "$ in the city and with this apartment it would have been "
    question += str(scores['ownCosts']) + "$. The rental fee to total cost ratio in this case is "
    question += str(scores['rentalToCosts']*100) + "%, while on average it's consifered to be healthy around 30% of the total costs"
    result = call_openai_api(question, "You are an expert of economics.", "gpt-3.5-turbo")
    return result

def make_recognition_description(scores):

    question = "How would you evaluate a potential "
    question += scores['position'] + " position in 2-3 sentences with positive emotional considerations that I think of applying, where the salary is in the"
    question += str(scores['salaryPositionDecile']) + " decile of all salaries paid in a similar position, in the "
    question += str(scores['salaryDecile']) + " decile of all salaries paid in the city, in the "
    question += str(scores['salaryIndustryDecile']) + " decile of all salaries paid in the industry and in the "
    question += str(scores['salarySectorDecile']) + " decile of all salaries paid in the sector?"
    result = call_openai_api(question, "You are an expert of economics.", "gpt-3.5-turbo")

    return result

def make_security_description(rental):

    question = "I'm considering to move to " + rental['address'] + ", " + rental['area'] + ", " + rental['city'] + " from abroad. What are the latest security statistics of the place and the surrounding from burglaries, thefts and violent crimes aspects in 2-3 sentences? How strong security awareness is required?"
    result = call_openai_api(question, "You are a helpful assistant that provides concise and accurate answers", "gpt-4-turbo")

    return {'question': question,'result': result}

def getCompReviews(company, city):
    question = "Please create a consolidated summary of "+company+" reviews of the employees with pros and cons from indeed.com, glassdoor.com and linkedin.com, if there are any local "+city+" specifics, without mentioning where the reviews are from"
    result = call_openai_api(question, "You are an HR expert.", "gpt-3.5-turbo")
    return result