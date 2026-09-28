"""Minimal Jev (typesafe.ai System One) client: the device has requests, not the SDK."""
URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
TIMEOUT_S = 1.5


def ask(session, api_key: str, state: dict, questions: dict, name: str, timeout: float = TIMEOUT_S) -> str | None:
  """The chosen label for question `name`, or None on any failure (the caller falls back to DEC)."""
  try:
    response = session.post(URL, json={"state": state, "model": MODEL, "questions": questions},
                            headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)
    response.raise_for_status()
    answer = response.json()["answers"][name]
    return str(answer["choice"]) if answer.get("type") == "choice" else None
  except Exception:  # network, HTTP, JSON or schema problems: no opinion this second
    return None
