import requests

from app.config import settings

GITHUB_API_URL = "https://api.github.com/repos/{repo}/dispatches"


def trigger_training(ticker: str) -> None:
    if not settings.github_dispatch_token or not settings.github_repo:
        print("[training] GITHUB_DISPATCH_TOKEN o GITHUB_REPO no configurados, se omite el disparo automático")
        return

    try:
        response = requests.post(
            GITHUB_API_URL.format(repo=settings.github_repo),
            headers={
                "Authorization": f"Bearer {settings.github_dispatch_token}",
                "Accept": "application/vnd.github+json",
            },
            json={"event_type": "train-symbol", "client_payload": {"ticker": ticker}},
            timeout=10,
        )
        response.raise_for_status()
        print(f"[training] Disparado entrenamiento automático para {ticker}")
    except Exception as e:
        print(f"[training] No se pudo disparar el entrenamiento para {ticker}: {e}")
