import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from django.shortcuts import render


def _fetch_json(url: str) -> dict | list:
	with urlopen(url, timeout=12) as response:
		return json.loads(response.read().decode("utf-8"))


def weather_home(request):
	context = {}

	if request.method == "POST":
		city = request.POST.get("city", "").strip()
		context["city"] = city

		if not city:
			context["error"] = "Please enter a city name."
			return render(request, "weather/index.html", context)

		api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
		if not api_key:
			context["error"] = "Missing OPENWEATHER_API_KEY. Add it in your terminal first."
			return render(request, "weather/index.html", context)

		try:
			geo_url = (
				"https://api.openweathermap.org/geo/1.0/direct"
				f"?q={quote(city)}&limit=1&appid={api_key}"
			)
			locations = _fetch_json(geo_url)

			if not locations:
				context["error"] = "City not found. Try another spelling or include country code."
				return render(request, "weather/index.html", context)

			location = locations[0]
			weather_url = (
				"https://api.openweathermap.org/data/2.5/weather"
				f"?lat={location['lat']}&lon={location['lon']}&units=metric&appid={api_key}"
			)
			payload = _fetch_json(weather_url)

			location_parts = [location.get("name", "")]
			if location.get("state"):
				location_parts.append(location["state"])
			if location.get("country"):
				location_parts.append(location["country"])

			context["weather"] = {
				"location": ", ".join([part for part in location_parts if part]),
				"temperature": round(payload["main"]["temp"]),
				"feels_like": round(payload["main"]["feels_like"]),
				"description": payload["weather"][0]["description"],
				"icon": payload["weather"][0]["icon"],
				"humidity": payload["main"]["humidity"],
				"pressure": payload["main"]["pressure"],
				"visibility": round(payload.get("visibility", 0) / 1000, 1),
				"wind": round(payload["wind"]["speed"] * 3.6, 1),
			}
		except HTTPError as err:
			if err.code in (401, 403):
				context["error"] = "API key is invalid or not active yet. Recheck the key and try again in a few minutes."
			else:
				context["error"] = "Weather service returned an error. Please try again shortly."
		except (URLError, TimeoutError):
			context["error"] = "Cannot reach weather service right now. Try again shortly."
		except (KeyError, ValueError, json.JSONDecodeError):
			context["error"] = "Unexpected weather response. Please try another city."

	return render(request, "weather/index.html", context)
