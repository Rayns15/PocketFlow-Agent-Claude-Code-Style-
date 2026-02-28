import requests

API_KEY = 'YOUR_API_KEY'

url = 'https://api.openweathermap.org/data/2.5/weather?q=London&appid={}'

response = requests.get(url)

weather_data = response.json()

print(weather_data['main']['temp'])