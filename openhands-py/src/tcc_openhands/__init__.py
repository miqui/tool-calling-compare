"""Placeholder package; real OpenHands SDK wiring comes later."""


def mock_get_weather(city: str) -> dict[str, object]:
    return {"city": city, "temp_c": 18, "conditions": "cloudy"}
