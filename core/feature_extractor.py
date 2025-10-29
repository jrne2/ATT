# core/feature_extractor.py
from textblob import TextBlob
import textstat
import spacy
import re

# ---  'md' 모델 로드 ---
try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    print("en_core_web_md 모델 다운로드 중... (시간이 걸릴 수 있습니다)")
    spacy.cli.download("en_core_web_md")
    nlp = spacy.load("en_core_web_md")
# --- 수정 끝 ---

# --- 페르소나별 '개념' 정의 ---
PERSONA_CONCEPTS = {
    "토니 스타크 (재치있는 억만장자)": [
        "witty confident humor",
        "arrogant but charming",
        "Performative Humility",
        "direct and playful sarcasm",
        "Control through Humor",
        "Maintaining Casual Distance"
    ],
    "친절하고 따뜻한 친구": [
        "warm empathetic and positive feeling",
        "caring about others",
        "casual and friendly conversation",
        "showing support and kindness"
    ],
    "자신감 넘치는 비즈니스 리더": [
        "clear decisive and confident leadership",
        "results-oriented strategy",
        "professional and objective analysis",
        "action items and execution"
    ]
}
# --- 수정 끝 ---

def get_sentiment(text):
    """감성 점수를 추출합니다. (-1: 부정 ~ +1: 긍정)"""
    blob = TextBlob(text)
    return blob.sentiment.polarity

def get_complexity_score(text):
    """문장 복잡도를 Flesch-Kincaid Grade 점수로 추출합니다."""
    try:
        if len(text.split()) < 3: return 0
        return textstat.flesch_kincaid_grade(text)
    except Exception as e:
        print(f"복잡도 계산 오류: {e}")
        return 0

# ---  '시맨틱 유사도' 계산 함수 ---
def calculate_semantic_similarity(persona, user_prompt_doc):
    """사용자 발화와 페르소나 '개념' 벡터 간의 평균 코사인 유사도 계산"""
    expectations = PERSONA_CONCEPTS.get(persona)
    if not expectations:
        return 0.0 # 페르소나 정의 없음
    
    # 페르소나 개념 문장들을 nlp 처리하여 벡터화
    concept_docs = [nlp(concept) for concept in expectations]
    
    total_similarity = 0.0
    valid_concepts = 0
    
    for concept_doc in concept_docs:
        if concept_doc.vector_norm and user_prompt_doc.vector_norm:
            similarity = user_prompt_doc.similarity(concept_doc)
            total_similarity += similarity
            valid_concepts += 1
            
    if valid_concepts == 0:
        return 0.0
        
    average_similarity = total_similarity / valid_concepts
    # 점수를 0~100 사이로 스케일링 (유사도는 보통 0~1 사이)
    scaled_score = (average_similarity + 1) / 2 * 100 
    print(f"--- Semantic Similarity (Persona: {persona}) ---")
    print(f"Avg Similarity: {average_similarity:.4f}, Scaled Score: {scaled_score:.1f}")
    print("-------------------------------------------------")
    return scaled_score

# --- 모든 특징을 한 번에 추출하는 래퍼(wrapper) 함수 ---
def analyze_text_features(persona, user_prompt):
    """
    사용자 발화 텍스트를 분석하여 모든 특징(feature)이 담긴 딕셔너리를 반환
    """
    # 1. spaCy nlp 처리 (한 번만 수행)
    doc = nlp(user_prompt)
    
    # 2. 개별 특징 추출
    complexity = get_complexity_score(user_prompt)
    sentiment = get_sentiment(user_prompt)
    # 3. 시맨틱 유사도 계산
    similarity_score = calculate_semantic_similarity(persona, doc)
    
    # 4. 회피 표현(Hedges) 추출
    hedges = len(re.findall(r'\b(maybe|perhaps|i think|i guess|kind of|sort of|um|uh|well)\b', user_prompt.lower()))

    return {
        "complexity": complexity,
        "sentiment": sentiment,
        "similarity": similarity_score, # 'keywords' 대신 'similarity'
        "hedges": hedges
    }