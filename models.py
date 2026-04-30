from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now

# address,area,balcony,bath,bed,built,city,currency,date,desc,features,floor,furnished,garden,gps_lat,gps_lon,gym,id,image,imageList,paid,parking,pets,pool,price,relDate,score,size,size_unit,type,url


class BaseRentalModel(models.Model):
    address = models.TextField(blank=True,null=True)
    age = models.TextField(blank=True,null=True)
    area = models.TextField(blank=True,null=True)
    balcony = models.TextField(blank=True,null=True)
    bath = models.FloatField(blank=True,null=True)
    bed = models.FloatField(blank=True,null=True)
    block_size = models.TextField(blank=True,null=True)
    built = models.TextField(blank=True,null=True)
    city = models.CharField(max_length=50)
    clusterCity = models.CharField(max_length=50, null=True)
    currency = models.CharField(max_length=10, blank=True, default='')
    deposit = models.TextField(blank=True,null=True)
    desc = models.TextField(blank=True,null=True)
    features = models.TextField(blank=True,null=True)
    floor = models.TextField(blank=True,null=True)
    furnished = models.TextField(blank=True,null=True)
    fees = models.TextField(blank=True,null=True)
    garden = models.TextField(blank=True,null=True)
    gps_lat = models.FloatField(blank=True, null=True, db_index=True)
    gps_lon = models.FloatField(blank=True, null=True, db_index=True)
    gym = models.TextField(blank=True,null=True)
    id = models.TextField(editable=False, unique=True, primary_key=True)
    image = models.TextField(null=True, blank=True)
    imageList = models.TextField(null=True, blank=True)
    link = models.TextField(blank=True,null=True)
    location = models.TextField(blank=True,null=True)
    max_floor = models.TextField(blank=True,null=True)
    max_tenant = models.TextField(blank=True,null=True)
    paid = models.TextField(blank=True,null=True)
    parking = models.TextField(blank=True,null=True)
    pets = models.TextField(blank=True,null=True)
    pool = models.TextField(blank=True,null=True)
    price = models.FloatField(blank=True,null=True)
    score = models.TextField(blank=True,null=True)
    size = models.FloatField(blank=True,null=True)
    size_unit = models.TextField(blank=True,null=True)
    type = models.TextField(blank=True,null=True)
    url = models.TextField(blank=True,null=True)
    nearbyRestaurants = models.TextField(blank=True,null=True)
    nearbyRestaurantsUpdated = models.TextField(blank=True,null=True)
    pollution = models.TextField(blank=True,null=True)
    goOut = models.TextField(blank=True,null=True) 
    culture= models.TextField(blank=True,null=True)
    shoping=models.TextField(blank=True,null=True)
    education=models.TextField(blank=True,null=True)
    entertain=models.TextField(blank=True,null=True)
    health=models.TextField(blank=True,null=True)
    turism=models.TextField(blank=True,null=True)
    housing=models.TextField(blank=True,null=True)
    sports=models.TextField(blank=True,null=True)
    travel=models.TextField(blank=True,null=True)
    green=models.TextField(blank=True,null=True)
    locationRank = models.FloatField(blank=True,null=True, default=0)
    goOutRank = models.FloatField(blank=True,null=True, default=0)
    cultureRank= models.FloatField(blank=True,null=True, default=0)
    shopingRank=models.FloatField(blank=True,null=True, default=0)
    educationRank=models.FloatField(blank=True,null=True, default=0)
    entertainRank=models.FloatField(blank=True,null=True, default=0)
    healthRank=models.FloatField(blank=True,null=True, default=0)
    turismRank=models.FloatField(blank=True,null=True, default=0)
    housingRank=models.FloatField(blank=True,null=True, default=0)
    sportsRank=models.FloatField(blank=True,null=True, default=0)
    travelRank=models.FloatField(blank=True,null=True, default=0)
    greenRank=models.FloatField(blank=True,null=True, default=0)
    pollutionRank=models.FloatField(blank=True,null=True, default=0)
    gptDescription = models.TextField(blank=True,null=True)
    affDescription = models.TextField(blank=True,null=True)
    affScore = models.TextField(blank=True,null=True)
    security=models.TextField(blank=True,null=True)
    securityRank = models.FloatField(blank=True,null=True, default=0)
    referenceCircle = models.JSONField(blank=True,null=True) 
    date = models.DateTimeField(default=now,null=True)

    class Meta:
        abstract = True  # This prevents Django from creating a table for this model

# Create your models here.
class Rentals(BaseRentalModel):
    pass

# Create your models here.
class OwnRentals(BaseRentalModel):
    pass

class Cities(models.Model):
    name = models.TextField(editable=False, unique=True, primary_key=True, default="none")
    gps_lon = models.FloatField(blank=True, null=True, db_index=True)
    gps_lat = models.FloatField(blank=True, null=True, db_index=True)
    clusterCount = models.FloatField(blank=True,null=True)
    bbox = models.TextField(blank=True,null=True)
    rentalPriceContours = models.JSONField(blank=True, null=True)
    rentalAverage = models.FloatField(blank=True,null=True)
    incomeAverage = models.FloatField(blank=True,null=True)
    QoL = models.FloatField(blank=True,null=True)
    PP = models.FloatField(blank=True,null=True)
    rentalFee = models.FloatField(blank=True,null=True)
    dailyFood = models.FloatField(blank=True,null=True)
    travel = models.FloatField(blank=True,null=True)
    school = models.FloatField(blank=True,null=True)
    entert = models.FloatField(blank=True,null=True)
    utilities = models.FloatField(blank=True,null=True)
    Climate = models.TextField(blank=True,null=True)
    Temperatures = models.JSONField(blank=True,null=True)
    Inhabitants = models.FloatField(blank=True,null=True)
    Secirity = models.TextField(blank=True,null=True)
    CoL = models.FloatField(blank=True,null=True)
    timezone = models.TextField(blank=True,null=True)

    ppi  = models.FloatField(blank=True,null=True)
    safety = models.FloatField(blank=True,null=True)
    health = models.FloatField(blank=True,null=True)
    property2Income = models.FloatField(blank=True,null=True)
    commuteTime = models.FloatField(blank=True,null=True)
    pollution = models.FloatField(blank=True,null=True)

    price2Income = models.FloatField(blank=True,null=True)
    mortgage2Income = models.FloatField(blank=True,null=True)
    loanAffordability = models.FloatField(blank=True,null=True)
    price2RentCentre = models.FloatField(blank=True,null=True)
    price2RentOutside = models.FloatField(blank=True,null=True)
    grossRentalYield = models.FloatField(blank=True,null=True)
    grossRentalYield = models.FloatField(blank=True,null=True)
    apartmentPrice = models.FloatField(blank=True,null=True)
    transportation = models.FloatField(blank=True,null=True)
    clothing = models.FloatField(blank=True,null=True)
    sportsnLeisure = models.FloatField(blank=True,null=True)
    markets = models.FloatField(blank=True,null=True)
    restaurants = models.FloatField(blank=True,null=True)
    avgNetSalary = models.FloatField(blank=True,null=True)

class Companies(models.Model):
    #id = models.TextField(editable=False, unique=True, primary_key=True)
    name = models.TextField(blank=True,null=True)
    gps_lat = models.TextField(blank=True,null=True)
    gps_lon = models.TextField(blank=True,null=True)
    size = models.TextField(blank=True,null=True)
    industry = models.TextField(blank=True,null=True)
    sector = models.TextField(blank=True,null=True)
    admin = models.TextField(blank=True,null=True)
    HQAddr = models.TextField(blank=True,null=True)
    locAddr = models.TextField(blank=True,null=True)
    reviews = models.TextField(blank=True,null=True)
    city = models.TextField(blank=True,null=True)
    subsidiaries = models.TextField(blank=True,null=True)

class BaseJobModel(models.Model):
    skills = models.TextField(blank=True,null=True)
    education = models.TextField(blank=True,null=True)
    certification = models.TextField(blank=True,null=True)
    jobType = models.TextField(blank=True,null=True)
    city = models.TextField(blank=True,null=True)
    clusterCity = models.TextField(blank=True,null=True)
    area = models.TextField(blank=True,null=True)
    loceJobTagModel = models.TextField(blank=True,null=True)
    station = models.TextField(blank=True,null=True)
    normTitle = models.TextField(blank=True,null=True)
    companyRating = models.TextField(blank=True,null=True)
    id = models.TextField(editable=False, unique=True, primary_key=True)
    name = models.TextField(blank=True,null=True)
    company = models.TextField(blank=True,null=True)
    industry = models.TextField(blank=True,null=True)
    sector = models.TextField(blank=True,null=True)
    salary = models.FloatField(blank=True,null=True)
    paid = models.TextField(blank=True,null=True)
    gps_lat = models.FloatField(blank=True, null=True, db_index=True)
    gps_lon = models.FloatField(blank=True, null=True, db_index=True)
    address = models.TextField(blank=True,null=True)
    currency = models.TextField(blank=True,null=True)
    date = models.DateTimeField(default=now)
    amount = models.TextField(blank=True,null=True)
    desc = models.TextField(blank=True,null=True)
    recScore = models.TextField(blank=True,null=True)
    recDescription = models.TextField(blank=True,null=True)
    postcode = models.TextField(blank=True,null=True)
    state = models.TextField(blank=True,null=True)
    url = models.TextField(blank=True,null=True)
    companyLogoUrl = models.TextField(blank=True,null=True)
    class Meta:
        abstract = True  # This prevents Django from creating a table for this model


#"id","city","company","paid","currency","salary","amount in USD","name","Date"
class Jobs(BaseJobModel):
    pass

class OwnJobs(BaseJobModel):
    pass

'''
class Hexagon(models.Model):
    # Unique identifier for the hexagon (could be generated via H3 or another geospatial indexing system)
    hex_id = models.CharField(max_length=64, unique=True)

    # Polygon representing the boundary of the hexagon
    boundary = models.PolygonField()

    # Resolution level (higher values indicate finer resolution)
    resolution = models.IntegerField()

    # Parent hexagon at a lower resolution (for future higher resolution)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    # Store additional metadata if needed
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        # Spatial index for efficient geospatial queries
        indexes = [
            models.Index(fields=['resolution']),
            models.Index(fields=['hex_id']),
        ]

    def __str__(self):
        return f"Hexagon {self.hex_id} at resolution {self.resolution}"
    '''
class AppData(models.Model):
    key = models.TextField(editable=False)
    name = models.TextField(editable=False)
    
    
class UserProfile(User):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', null=True)
    rentalHistory = models.JSONField(blank=True,null=True) 
    jobHistory = models.JSONField(blank=True,null=True) 
    #preferredRentals = models.TextField(blank=True, null=True)
    #bookedRental = models.TextField(blank=True, null=True)
    #preferredJobs = models.TextField(blank=True, null=True)
    #bookedJob = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.user.username

class UserHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    rentals = models.TextField(blank=True,null=True) 
    jobs = models.TextField(blank=True,null=True) 
    scenarios = models.JSONField(blank=True,null=True) 
    #preferredRentals = models.TextField(blank=True, null=True)
    #bookedRental = models.TextField(blank=True, null=True)
    #preferredJobs = models.TextField(blank=True, null=True)
    #bookedJob = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=now)
    def __str__(self):
        return self.user.username

class Security(models.Model):
    country = models.TextField(editable=False)
    county = models.TextField(editable=False)
    state = models.TextField(editable=False)
    city = models.TextField(editable=False)
    geometry = models.TextField(editable=False)
    properties = models.TextField(editable=False)
