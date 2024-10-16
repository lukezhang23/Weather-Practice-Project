import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse


class Location:
    def __init__(self, latitude, longitude, status):
        self.latitude = latitude
        self.longitude = longitude
        self.status = status


class Weather:
    def __init__(self, dataframe, status):
        self.dataframe = dataframe
        self.status = status


def get_weather_data(latitude, longitude):
    """
    Fetches temperature data for a given location using the National Weather Service API.
    """
    headers = {"User-Agent": st.secrets["email"]}

    try:
        # Get the forecast grid data URL from the initial location response
        location_response = requests.get(
            f'https://api.weather.gov/points/{latitude},{longitude}',
            headers=headers
        )
        location_response.raise_for_status()
        gridpoints_url = location_response.json()["properties"]["forecastGridData"]

        # Get temperature data from the forecast grid
        response = requests.get(gridpoints_url, headers=headers)
        response.raise_for_status()
        temps = response.json()["properties"]["temperature"]["values"]

    except requests.exceptions.RequestException:
        return Weather(None, "weathergov error")

    # Extract times and convert temperatures to Fahrenheit
    time_list = [x["validTime"] for x in temps]
    temp_list = [(x["value"] * 1.8) + 32 for x in temps]  # Convert from Celsius to Fahrenheit

    # Parse ISO8601 time strings into datetime objects
    valid_times = [parse_iso8601_time(t) for t in time_list]

    # Create DataFrame that holds weather data
    weatherdf = pd.DataFrame(temp_list, index=valid_times, columns=["Temperature (°F)"])

    return Weather(weatherdf, "good")


def streamlit_output(coordinates, temps, location_status, weather_status):
    st.title("Weather Forecast")

    # Regular output for good status
    if location_status == "good" and weather_status == "good":
        st.map(coordinates, size=0)
        st.line_chart(temps, x_label="Date", y_label="Temperature")

    # Error outputs for error statuses
    elif location_status == "location not found":
        st.text("Location not found, please try another location. (Geoapify retrieval error)")
    elif location_status == "not in us":
        st.text("Location not in the United States, please select a different location.")
    elif weather_status == "weathergov error":
        st.text("Error, please try another location. (Weather.gov retrieval error)")
    else:
        st.text("Error, please try another location (Uncaught error)")

    # Geoapify attribution
    st.markdown('Powered by [Geoapify](https://www.geoapify.com/)')


def geocode_city(city):
    # Morrill Tower coordinates
    found_latitude = 40.00007409649716
    found_longitude = -83.0219446815833
    status = "good"

    # If not Morrill Tower, find coordinates
    if city.lower() != "morrill tower":

        # Make the request to Geoapify
        parsed_city = urllib.parse.quote(city)
        geoapify_url = (f'https://api.geoapify.com/v1/geocode/search?text={parsed_city}&format=json'
                        f'&apiKey={st.secrets["geoapifyKey"]}')
        geocode_response = requests.get(geoapify_url).json()

        # Check that location was found
        if not geocode_response["results"]:
            status = "location not found"

        else:
            # Check that location is in United States
            if geocode_response["results"][0]["country_code"] != "us":
                status = "not in us"

            else:
                # Extract latitude and longitude from the response
                found_latitude = geocode_response["results"][0]["lat"]
                found_longitude = geocode_response["results"][0]["lon"]

    return Location(found_latitude, found_longitude, status)


# Function to parse the ISO date-time string and ignore the duration part
def parse_iso8601_time(iso_time_str):
    # Split the string by '/' and take the first part (before '/PT1H')
    time_str = iso_time_str.split('/')[0]

    # Parse the time string to a datetime object
    return datetime.fromisoformat(time_str)


# Input field to type a city name
city_input = st.text_input("Location:", value="Morrill Tower")

# Make API calls for data
location = geocode_city(city_input)
weather = get_weather_data(location.latitude, location.longitude)

# Creating dataframe from coordinates
coordinatesdf = pd.DataFrame({
    'lat': [location.latitude],
    'lon': [location.longitude]
})

streamlit_output(coordinatesdf, weather.dataframe, location.status, weather.status)
