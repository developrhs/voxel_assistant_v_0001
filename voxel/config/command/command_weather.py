import json
import sqlite3
from datetime import datetime
from urllib.parse import quote
from urllib.request import urlopen
from pathlib import Path


class CommandWeather:
    def __init__(self, project_root=None, weather_provider=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.database_path = self.project_root / "config" / "database" / "db" / "db_virtual_assistant.db"
        self.weather_provider = weather_provider or self._fetch_current_weather

    def get_user(self):
        with sqlite3.connect(self.database_path) as connection:
            return connection.execute(
                """
                SELECT tb_user_salutation, tb_user_first_name,
                       tb_user_city, tb_user_state
                FROM tb_user
                ORDER BY tb_user_id
                LIMIT 1
                """
            ).fetchone()

    def _fetch_current_weather(self, city, state):
        location_query = quote(f"{city}, {state}")
        geocoding_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={location_query}&count=1&language=pt&format=json"
        )
        with urlopen(geocoding_url, timeout=15) as response:
            location_data = json.load(response)

        locations = location_data.get("results", [])
        if not locations:
            raise LookupError("Localização não encontrada para a consulta meteorológica.")

        location = locations[0]
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={location['latitude']}&longitude={location['longitude']}"
            "&current=temperature_2m,weather_code,wind_speed_10m"
            "&wind_speed_unit=kmh&timezone=auto"
        )
        with urlopen(weather_url, timeout=15) as response:
            weather_data = json.load(response)

        current = weather_data["current"]
        return {
            "temperature": current["temperature_2m"],
            "weather_condition": self._weather_condition(current["weather_code"]),
            "wind_speed": current["wind_speed_10m"],
        }

    @staticmethod
    def _weather_condition(weather_code):
        code = int(weather_code)
        if code == 0:
            return "ensolarado"
        if code in {1, 2, 3}:
            return "nublado"
        if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
            return "chuvoso"
        return "variável"

    @staticmethod
    def _format_temperature(temperature):
        value = float(temperature)
        return f"{value:g}"

    def build_response(self, user, weather, now=None):
        salutation, first_name, city, state = user
        temperature = self._format_temperature(weather["temperature"])
        condition = str(weather["weather_condition"]).strip().lower()
        wind_speed = float(weather["wind_speed"])

        if condition == "ensolarado":
            response = (
                f"Hoje está um dia muito bom de sol com temperatura de {temperature}°C, "
                "muito bom para um passeio!"
            )
        elif condition == "nublado":
            response = (
                f"Hoje o dia está nublado com temperatura de {temperature}°C, "
                "tempo agradável para fazer algo tranquilo!"
            )
        elif condition == "chuvoso":
            response = (
                f"Hoje está chovendo e a temperatura é de {temperature}°C, "
                "melhor ficar em casa e relaxar!"
            )
        else:
            response = f"Hoje o tempo está {condition} com temperatura de {temperature}°C"

        if wind_speed > 20:
            wind_comment = "O vento está um pouco forte hoje, cuidado!"
        else:
            wind_comment = "O vento está bem tranquilo, dá até para sentir a brisa!"

        now = now or datetime.now()
        return {
            "status": "SUCCESS",
            "message": f"{salutation} {first_name}, {response} {wind_comment}",
            "hour": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "city": city,
            "state": state,
            "temperature": weather["temperature"],
            "weather_condition": weather["weather_condition"],
            "wind_speed": weather["wind_speed"],
        }

    def execute(self):
        user = self.get_user()
        if user is None:
            return {
                "status": "USER_NOT_FOUND",
                "message": "Usuário não encontrado.",
            }

        try:
            weather = self.weather_provider(user[2], user[3])
        except Exception as error:
            return {
                "status": "WEATHER_NOT_AVAILABLE",
                "message": str(error),
            }

        return self.build_response(user, weather)

    def run(self):
        return self.execute()
