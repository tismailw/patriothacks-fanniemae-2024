from flask import Flask, render_template, request
from datetime import datetime, timedelta
import requests
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# flask instance
scraping = Flask(__name__)

GOOGLE_API_KEY = 'AIzaSyCuiU5o34o8fmb_IwrcxADz-QS8ZWRm22k'



@scraping.route('/schools', methods=['POST'])
def schools_page():
    # values + default values if values fail to load in 
    owner = request.form.get('owner', 'N/A')
    mailing_address = request.form.get('mailing_address', 'N/A')
    total_due = request.form.get('total_due', 'N/A')
    calculated_value = request.form.get('calculated_value', 'N/A')
    map_url = request.form.get('map_url', 'N/A')
    street_view_url = request.form.get('street_view_url', 'N/A')
    lat_lng = request.form.get('lat_lng', '0,0')

    lat, lng = lat_lng.split(',')

    # calling funcktion 
    schools = get_nearby_schools(lat, lng)
    

    return render_template('schools.html', 
                           schools=schools, 
                           owner=owner,
                           mailing_address=mailing_address,
                           total_due=total_due,
                           calculated_value=calculated_value,
                           map_url=map_url,
                           street_view_url=street_view_url,
                           lat_lng=lat_lng)





# find nearby schools
def get_nearby_schools(lat, lon, radius=7000):
    places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius={radius}&type=school&key={GOOGLE_API_KEY}"
    places_response = requests.get(places_url)
    places_results = places_response.json().get('results', [])

    # Debugging line: print the entire API response to inspect what data we receive
    print(places_results)

    schools = {
        'elementary': [],
        'middle': [],
        'high': []
    }
    
    for place in places_results:
        school_name = place['name']
        school_address = place.get('vicinity', 'N/A')
        school_rating = place.get('rating', 'No rating available')
        types = place.get('types', [])

        print(f"School: {school_name}, Types: {types}")  # Debugging: Check what types are associated with each school
        
        # Determine the school level based on types (Google Places API may use different type strings)
        if 'primary_school' in types or 'elementary_school' in types:
            schools['elementary'].append({'name': school_name, 'address': school_address, 'rating': school_rating})
        if 'middle' in school_name.lower():
            schools['middle'].append({'name': school_name, 'address': school_address, 'rating': school_rating})
        elif 'high_school' in types or ('secondary_school' in types and 'high' in school_name.lower()):
            # Treat secondary schools with 'high' in their name as high schools
            schools['high'].append({'name': school_name, 'address': school_address, 'rating': school_rating})
    
    return schools


def get_monthly_weather(lat, lon):
    weather_data = {}
    current_date = datetime.now()

    for i in range(12):
        # Get the first day of each month by subtracting i months from the current date
        first_day_of_month = current_date.replace(day=1) - timedelta(days=30 * i)
        month_year = first_day_of_month.strftime("%B %Y")  # Set month and year string
        start_date = first_day_of_month.strftime("%Y-%m-%d")  # Date in required format


        # Call the Visual Crossing Weather API for historical weather data
        weather_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}/{start_date}?unitGroup=metric&key=35HRWZKGLNXCZYT2QSGLG5543&include=obs"
        
        response = requests.get(weather_url)

        if response.status_code == 200:
            monthly_data = response.json()
            # Assuming the response contains 'days' with temperature and other weather data
            avg_temp_celsius = monthly_data['days'][0].get('temp', 0)  # Default to 0 if missing
            avg_temp_fahrenheit = round((avg_temp_celsius * 9/5) + 32, 1)  # Convert to Fahrenheit
            
            # Extract other weather details (adjust according to the API response format)
            avg_rain_mm = monthly_data['days'][0].get('precip', 0)  # Default to 0 if missing
            avg_cloud_cover = monthly_data['days'][0].get('cloudcover', 0)  # Default to 0 if missing

            avg_rain_in = round(avg_rain_mm * 0.0393701, 2)  # Correct conversion from mm to inches

            cloud_cover_meaning = ""
            if avg_cloud_cover is not None:
                if 0 <= avg_cloud_cover <= 25:
                    cloud_cover_meaning = "Pretty Sunny"
                elif 26 <= avg_cloud_cover <= 50:
                    cloud_cover_meaning = "Partly Cloudy"
                elif 51 <= avg_cloud_cover <= 75:
                    cloud_cover_meaning = "Mostly Cloudy"
                else:
                    cloud_cover_meaning = "Very Cloudy"
            else:
                cloud_cover_meaning = "No Data"

            # Store weather stats in the dictionary
            weather_data[month_year] = {
                'temp': avg_temp_fahrenheit,
                'rain': avg_rain_in,
                'cloud_cover': cloud_cover_meaning,
            }
        else:
            weather_data[month_year] = {
                'temp': "No Data Available",
                'rain': "No Data Available",
                'cloud_cover': "No Data Available",
            }
    
    return weather_data


# Function to get nearby places using Google Places API with a custom radius
def get_nearby_places(location, place_type, user_address, radius):
    places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={location}&radius={radius}&type={place_type}&key={GOOGLE_API_KEY}"
    places_response = requests.get(places_url)
    places_results = places_response.json().get('results', [])

    places = []
    for place in places_results:
        name = place['name']
        address = place.get('vicinity', 'N/A')
        place_location = f"{place['geometry']['location']['lat']},{place['geometry']['location']['lng']}"
        types = place.get('types', [])  # Get the types of the place

        # Calculate distance using Distance Matrix API
        distance_matrix_url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={user_address}&destinations={place_location}&key={GOOGLE_API_KEY}"
        distance_response = requests.get(distance_matrix_url)
        distance_data = distance_response.json()
        distance = distance_data['rows'][0]['elements'][0]['distance']['text']  # Get distance in a readable format
        
        # Convert distance from km to miles if applicable
        if ' km' in distance:
            distance_km = float(distance.replace(' km', ''))
            distance_miles = distance_km * 0.621371  # Convert km to miles
            distance = f"{distance_miles:.2f} miles"
        else:
            distance = distance

        places.append({
            'name': name,
            'address': address,
            'distance': distance,
            'types': types  # Add types to the place data
        })
    return places



# Function to get public transportation (buses, trains, airports) with a 30,000-meter radius
def get_public_transportation(location, user_address):
    transport_modes = ['bus_station', 'train_station', 'airport']  # Focus on bus stops, trains, and airports
    all_transport_stations = []

    for mode in transport_modes:
        stations = get_nearby_places(location, mode, user_address, radius=30000)  # Public transport within 30,000 meters
        all_transport_stations.extend(stations)

    return all_transport_stations



# calculates mortgage 
def calculate_mortgage(loan_amount, interest_rate, loan_term_years):
    monthly_interest_rate = interest_rate / 100 / 12
    number_of_payments = loan_term_years * 12

    if monthly_interest_rate == 0:

        monthly_payment = loan_amount / number_of_payments
    else:
        monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** number_of_payments) / ((1 + monthly_interest_rate) ** number_of_payments - 1)
    
    return monthly_payment


@scraping.route('/')
def index():
    return render_template('index.html')

@scraping.route('/search', methods=['POST'])
def search():
    # gets user input
    number = request.form['number']
    street_name = request.form['street_name']

    '''
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Runs Chrome in headless mode
    chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
    chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    chrome_options.add_argument('--disable-gpu')  # Applicable for Windows, GPU process will not be started
    chrome_options.add_argument('--window-size=1920,1080')  # Set a default window size for rendering
    chrome_options.add_argument('--log-level=3')  # Suppress logs


    '''








    # initializes selenium wiht the chrome driver(with head )
    options = webdriver.ChromeOptions()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # opens website and inserts value
    driver.get('https://reparcelasmt.loudoun.gov/pt/search/commonsearch.aspx?mode=address')
    driver.implicitly_wait(5)

    # adds values 
    number_input = driver.find_element(By.NAME, 'inpNumber')
    number_input.send_keys(number)

    street_name_input = driver.find_element(By.NAME, 'inpStreet')
    street_name_input.send_keys(street_name)

    # Submit the form
    search_button = driver.find_element(By.ID, 'btSearch')
    search_button.click()

    # Wait for the results page to load
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "//td[contains(text(), 'Name')]"))
    )

    try:
        # Scrape the "Owner" field
        owner_element = driver.find_element(By.XPATH, "//td[contains(text(), 'Name')]/following-sibling::td[@class='DataletData']")
        owner = owner_element.text

        # Scrape the "Mailing Address" field (first row)
        mailing_address_element_1 = driver.find_element(By.XPATH, "//td[contains(text(), 'Mailing Address')]/following-sibling::td[@class='DataletData']")
        mailing_address_1 = mailing_address_element_1.text

        # Scrape the second row of the mailing address (e.g., city, state, and zip)
        additional_info_element = driver.find_element(By.XPATH, "//*[@id='Owner']/tbody/tr[5]/td[2]")
        additional_info = additional_info_element.text

        # Combine both parts of the mailing address
        full_mailing_address = f"{mailing_address_1} {additional_info}"




        # Scrape the "Tax History / Payment" link using XPath targeting the correct link
        tax_history_link_element = driver.find_element(By.XPATH, "//a[contains(@href, 'taxes')]")
        tax_history_link = tax_history_link_element.get_attribute('href')

        # Navigate to the tax history page
        driver.get(tax_history_link)

        # Wait for the "Total Due" element to appear using the specific XPath you provided
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="ctl00_cphMainContent_SkeletonCtrl_3_lblAccountSumTotalDue"]'))
        )

        # Scrape the "Total Due" value
        total_due_element = driver.find_element(By.XPATH, '//*[@id="ctl00_cphMainContent_SkeletonCtrl_3_lblAccountSumTotalDue"]')
        total_due = total_due_element.text

        # Remove dollar signs and commas, convert to float, and perform the calculation
        total_due_numeric = float(total_due.replace('$', '').replace(',', ''))
        calculated_value = f"${(total_due_numeric * 1000 / 4.15):,.2f}"


        # Get the latitude and longitude of the address using Google Geocoding API
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={full_mailing_address.replace(' ', '+')}&key={GOOGLE_API_KEY}"
        geocode_response = requests.get(geocode_url)
        geocode_data = geocode_response.json()
        print(geocode_data)  # Add this to debug
        location = geocode_data['results'][0]['geometry']['location']
        lat_lng = f"{location['lat']},{location['lng']}"

        # Get nearby grocery stores within a 10,000-meter radius using Google Places API
        grocery_stores = get_nearby_places(lat_lng, 'grocery_or_supermarket', full_mailing_address, radius=10000)

        # Get nearby public transportation within a 30,000-meter radius using Google Places API
        public_transportation = get_public_transportation(lat_lng, full_mailing_address)





        # Generate Google Maps Embed API URL for the address
        map_url = f"https://www.google.com/maps/embed/v1/place?key={GOOGLE_API_KEY}&q={full_mailing_address.replace(' ', '+')}"
        # Generate Google Street View Static API URL for the address
        street_view_url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={full_mailing_address.replace(' ', '+')}&key={GOOGLE_API_KEY}"


    except Exception as e:
        owner = "N/A"
        full_mailing_address = "N/A"
        tax_history_link = "N/A"
        total_due = "N/A"
        calculated_value = "N/A"  # Handle the case where the calculation fails
        map_url = "N/A"  # Handle the case where map cannot be displayed
        street_view_url = "N/A"  # Handle case where street view cannot be displayed
        grocery_stores = []
        public_transportation = []
        lat_lng = "0,0"

        print(f"Error: {e}")

    # Close the browser
    driver.quit()

    # Pass the extracted data and the calculated value to the results page
    return render_template('general_info.html', 
                           owner=owner, 
                           mailing_address=full_mailing_address, 
                           total_due=total_due, 
                           calculated_value=calculated_value, 
                           map_url=map_url, 
                           street_view_url=street_view_url,
                           grocery_stores=grocery_stores, 
                           public_transportation=public_transportation,
                           lat_lng=lat_lng)  # Make sure lat_lng is passed


# Mortgage Calculator Page Route
@scraping.route('/mortgage_page', methods=['POST'])
def mortgage_page():
    # Extract data from form submission
    owner = request.form['owner']
    mailing_address = request.form['mailing_address']
    total_due = request.form['total_due']
    calculated_value = request.form['calculated_value']
    map_url = request.form['map_url']
    street_view_url = request.form['street_view_url']

    return render_template('mortgage_calculator.html',
                           owner=owner,
                           mailing_address=mailing_address,
                           total_due=total_due,
                           calculated_value=calculated_value,
                           map_url=map_url,
                           street_view_url=street_view_url)

# Nearby Places Page Route
@scraping.route('/stuff_near_me', methods=['POST'])
def stuff_near_me_page():
    # Get the data from the hidden fields in general_info.html
    owner = request.form['owner']
    mailing_address = request.form['mailing_address']
    total_due = request.form['total_due']
    calculated_value = request.form['calculated_value']
    map_url = request.form['map_url']
    street_view_url = request.form['street_view_url']
    lat_lng = request.form['lat_lng']  # Capture lat_lng here

    # Use Google Geocoding API to get latitude and longitude
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={mailing_address.replace(' ', '+')}&key={GOOGLE_API_KEY}"
    geocode_response = requests.get(geocode_url)
    geocode_data = geocode_response.json()

    if geocode_data['status'] == 'OK':
        location = geocode_data['results'][0]['geometry']['location']
        lat_lng = f"{location['lat']},{location['lng']}"
    else:
        lat_lng = "0,0"  # Fallback to a default value in case of failure

    # Use the function to get nearby grocery stores and transportation
    grocery_stores = get_nearby_places(lat_lng, 'grocery_or_supermarket', mailing_address, radius=10000)
    public_transportation = get_public_transportation(lat_lng, mailing_address)

    # Render the stuff_near_me.html with the data
    return render_template('stuff_near_me.html', 
                           owner=owner, 
                           mailing_address=mailing_address, 
                           total_due=total_due, 
                           calculated_value=calculated_value, 
                           map_url=map_url, 
                           street_view_url=street_view_url, 
                           grocery_stores=grocery_stores, 
                           public_transportation=public_transportation,
                           lat_lng=lat_lng)  # Make sure lat_lng is passed back


@scraping.route('/mortgage', methods=['POST'])
def calculate_mortgage_payments():
    try:
        # Get the down payment and interest rate from the form
        down_payment = float(request.form['down_payment'])  # Dollar amount for the down payment
        interest_rate = float(request.form.get('interest_rate', 7))  # Default to 7% if left empty

        # Get the calculated home value from the hidden form field
        home_value = float(request.form['calculated_value'].replace('$', '').replace(',', ''))

        # Get other hidden form fields
        owner = request.form['owner']
        mailing_address = request.form['mailing_address']
        total_due = request.form['total_due']
        map_url = request.form['map_url']
        street_view_url = request.form['street_view_url']

        # Calculate the loan amount
        loan_amount = home_value - down_payment

        # Calculate mortgage payments
        mortgage_30_year = calculate_mortgage(loan_amount, interest_rate, 30)  # 30-year fixed
        mortgage_15_year = calculate_mortgage(loan_amount, interest_rate, 15)  # 15-year fixed

        # For 5/1 ARM, assume the rate is fixed for 5 years at the given interest rate, then adjusts
        mortgage_arm = calculate_mortgage(loan_amount, interest_rate, 30)  # Simplified 5/1 ARM calculation

        # Pass the calculated values back to the results page
        return render_template('mortgage_calculator.html',
                               mortgage_30_year=f"${mortgage_30_year:.2f}",
                               mortgage_15_year=f"${mortgage_15_year:.2f}",
                               mortgage_arm=f"${mortgage_arm:.2f}",
                               owner=owner,
                               mailing_address=mailing_address,
                               total_due=total_due,
                               calculated_value=f"${home_value:,.2f}",
                               map_url=map_url,
                               interest_rate=f"{interest_rate:.2f}%",

                               down_payment=f"${down_payment:,.2f}",

                               street_view_url=street_view_url)

    except KeyError as e:
        # Handle the error if the form field is missing
        print(f"Error: {e}")
        return f"Error: {e}", 500

@scraping.route('/weather', methods=['POST'])
def weather_page():
    # Get latitude and longitude from the hidden form field
    lat_lng = request.form.get('lat_lng', '0,0')  # Default to "0,0" if not present

    try:
        lat, lon = lat_lng.split(',')
    except ValueError:
        # Handle the case where lat_lng is not in the correct format
        return "Invalid latitude/longitude value", 400

    # Fetch the average weather data for the past year, month by month
    weather_data = get_monthly_weather(lat, lon)

    # Render the weather.html page with the weather data
    return render_template('weather.html', weather_data=weather_data, lat_lng=lat_lng)





















@scraping.route('/general_info', methods=['POST'])
def general_info():
    try:
        # Extract the form data that was passed back
        owner = request.form['owner']
        mailing_address = request.form['mailing_address']
        total_due = request.form['total_due']
        calculated_value = request.form['calculated_value']
        map_url = request.form['map_url']
        street_view_url = request.form['street_view_url']
        lat_lng = request.form.get('lat_lng', '0,0')  # Default to '0,0' if missing
        print(f"lat_lng received: {lat_lng}")  # Add this line to debug

        
        # Render the general_info.html template with the extracted data
        return render_template('general_info.html', 
                               owner=owner, 
                               mailing_address=mailing_address, 
                               total_due=total_due, 
                               calculated_value=calculated_value, 
                               map_url=map_url, 
                               street_view_url=street_view_url,
                               lat_lng=lat_lng)  # Ensure lat_lng is passed back

    except Exception as e:
        return f"Error: {e}", 500







if __name__ == '__main__':
    scraping.run(debug=True, port=8060)
