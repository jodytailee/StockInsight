from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score_sentiment(text: str) -> float:
    """Retorna un score de -1 (muy negativo) a +1 (muy positivo)."""
    return _analyzer.polarity_scores(text)["compound"]
