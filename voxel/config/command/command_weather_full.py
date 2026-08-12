import json
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


class CommandWeatherFull:
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
            locations = json.load(response).get("results", [])
        if not locations:
            raise LookupError("Localização não encontrada para a consulta meteorológica.")

        location = locations[0]
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={location['latitude']}&longitude={location['longitude']}"
            "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
            "weather_code,wind_speed_10m,wind_direction_10m,uv_index,visibility"
            "&daily=temperature_2m_min,temperature_2m_max,sunrise,sunset"
            "&wind_speed_unit=kmh&timezone=auto&forecast_days=1"
        )
        with urlopen(weather_url, timeout=15) as response:
            data = json.load(response)

        current = data["current"]
        daily = data["daily"]
        return {
            "temperature": current["temperature_2m"],
            "temperature_feels": current["apparent_temperature"],
            "temperature_min": daily["temperature_2m_min"][0],
            "temperature_max": daily["temperature_2m_max"][0],
            "weather_condition": self._weather_condition(current["weather_code"]),
            "humidity": current["relative_humidity_2m"],
            "wind_speed": current["wind_speed_10m"],
            "wind_direction": self._wind_direction(current["wind_direction_10m"]),
            "uv_index": current["uv_index"],
            "visibility": round(float(current["visibility"]) / 1000, 1),
            "sunrise": daily["sunrise"][0].split("T")[-1],
            "sunset": daily["sunset"][0].split("T")[-1],
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
    def _wind_direction(degrees):
        directions = ("Norte", "Nordeste", "Leste", "Sudeste", "Sul", "Sudoeste", "Oeste", "Noroeste")
        return directions[int((float(degrees) + 22.5) // 45) % 8]

    @staticmethod
    def _format_number(value):
        return f"{float(value):g}"

    def build_response(self, user, weather, now=None):
        salutation, first_name, city, state = user
        now = now or datetime.now()
        weekdays = (
            "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sábado", "domingo"
        )
        date = f"{weekdays[now.weekday()]}, {now:%d/%m/%Y}"
        message = (
            f"Bom dia {salutation} {first_name}! Agora são {now:%H:%M:%S} do dia {date}.\n"
            f"Boletim meteorológico para {city}-{state}:\n\n"
            f"O dia está {weather['weather_condition']}, com temperatura atual de "
            f"{self._format_number(weather['temperature'])}°C.\n"
            f"A sensação térmica é de {self._format_number(weather['temperature_feels'])}°C.\n"
            f"A máxima hoje chega a {self._format_number(weather['temperature_max'])}°C e a mínima foi de "
            f"{self._format_number(weather['temperature_min'])}°C.\n"
            f"Umidade do ar em {self._format_number(weather['humidity'])}%, com ventos de "
            f"{self._format_number(weather['wind_speed'])} km/h na direção {weather['wind_direction']}.\n"
            f"Índice UV está em {self._format_number(weather['uv_index'])} e visibilidade de "
            f"{self._format_number(weather['visibility'])} km.\n"
            f"O sol nasceu às {weather['sunrise']} e vai se pôr às {weather['sunset']}."
        )

        alerts = []
        if float(weather["humidity"]) < 30:
            alerts.append("Atenção: Umidade do ar está baixa, beba bastante água!")
        if float(weather["uv_index"]) > 8:
            alerts.append("Cuidado: Índice UV está alto, use protetor solar!")
        if float(weather["temperature"]) > 35:
            alerts.append("Alerta de calor intenso, evite exposição ao sol entre 10h e 16h!")
        if alerts:
            message += "\n\n" + "\n".join(alerts)

        return {
            "status": "SUCCESS",
            "message": message,
            "date": date,
            "weather": weather,
            "alerts": alerts,
        }

    def execute(self):
        user = self.get_user()
        if user is None:
            return {"status": "USER_NOT_FOUND", "message": "Usuário não encontrado."}
        try:
            weather = self.weather_provider(user[2], user[3])
        except Exception as error:
            return {"status": "WEATHER_NOT_AVAILABLE", "message": str(error)}
        return self.build_response(user, weather)

    def run(self):
        return self.execute()
