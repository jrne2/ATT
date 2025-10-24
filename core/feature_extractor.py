# core/feature_extractor.py
from textblob import TextBlob
import textstat
import spacy

# 모듈 임포트 시 spaCy 모델 한 번만 로드
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("en_core_web_sm 모델 다운로드 중...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


def get_sentiment(text):
    """감성 극성 점수 추출 (-1 ~ +1)."""
    blob = TextBlob(text)
    return blob.sentiment.polarity

def get_complexity_score(text):
    """Flesch-Kincaid Grade 수준 복잡도 점수 추출."""
    try:
        # 매우 짧은 텍스트에 대한 예외 처리
        if len(text.split()) < 3: # 단어 3개 미만이면 0 반환
            return 0
        return textstat.flesch_kincaid_grade(text)
    except Exception as e:
        print(f"복잡도 계산 오류: {e}")
        return 0 # 계산 실패 시 0 반환

def extract_keywords(text):
    """최대 3개의 키워드(명사/고유명사) 추출."""
    doc = nlp(text)
    keywords = [token.text for token in doc if token.pos_ in ('NOUN', 'PROPN')]
    return keywords[:3]