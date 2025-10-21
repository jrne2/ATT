# core/feature_extractor.py

from textblob import TextBlob
import textstat
import spacy

# spaCy 언어 모델 로드 (앱 실행 시 한 번만 로드)
nlp = spacy.load("en_core_web_sm")

def get_sentiment(text):
    """감성 점수를 추출합니다. (-1: 부정 ~ +1: 긍정)"""
    blob = TextBlob(text)
    return blob.sentiment.polarity

def get_complexity_score(text):
    """문장 복잡도를 Flesch-Kincaid Grade 점수로 추출합니다."""
    # textstat 라이브러리는 최소 100단어 이상일 때 가장 정확하지만,
    # 짧은 문장에서도 상대적인 복잡도를 측정하는 데 사용할 수 있습니다.
    try:
        return textstat.flesch_kincaid_grade(text)
    except:
        return 0 # 텍스트가 너무 짧아 계산이 불가능한 경우

def extract_keywords(text):
    """문장에서 핵심 키워드(명사)를 2~3개 추출합니다."""
    doc = nlp(text)
    keywords = [token.text for token in doc if token.pos_ in ('NOUN', 'PROPN')]
    return keywords[:3]