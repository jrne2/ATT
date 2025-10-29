# core/analyzer.py
import re

# --- 페르소나별 기대 지표 (키워드 -> 유사도 점수) ---
PERSONA_EXPECTATIONS = {
    "토니 스타크 (재치있는 억만장자)": {
        "complexity_min": 5.0, "complexity_max": 12.0,
        "sentiment_min": -0.2, "sentiment_max": 0.8,
        "hedging_penalty": 25, # 회피 표현 감점 (높음)
        "similarity_min_bonus": 50, # 최소 이 정도 유사도는 넘어야 보너스
        "similarity_weight": 0.2 # 유사도 점수 반영 가중치 (0.2 = 20%)
    },
    "친절하고 따뜻한 친구": {
        "complexity_min": 3.0, "complexity_max": 9.0,
        "sentiment_min": 0.4, "sentiment_max": 1.0,
        "hedging_penalty": 5, # 회피 표현 감점 (낮음)
        "similarity_min_bonus": 60, # 친구 페르소나는 유사도 기준 높음
        "similarity_weight": 0.3 # 유사도 점수 반영 가중치 (0.3 = 30%)
    },
    "자신감 넘치는 비즈니스 리더": {
        "complexity_min": 7.0, "complexity_max": 13.0,
        "sentiment_min": 0.0, "sentiment_max": 0.6,
        "hedging_penalty": 20, # 회피 표현 감점 (높음)
        "similarity_min_bonus": 55,
        "similarity_weight": 0.25
    }
}

# --- 👇 [수정] calculate_feature_score 함수 ---
def calculate_feature_score(persona, features):
    """추출된 특징(features 딕셔너리)과 페르소나 기대를 비교하여 객관적 점수(0~100) 계산"""
    score = 50 # 기본 점수
    expectations = PERSONA_EXPECTATIONS.get(persona)

    if not expectations:
        print(f"경고: 페르소나 '{persona}'에 대한 기대 지표 정의 없음.")
        return score
        
    # 특징 딕셔너리에서 값 추출
    complexity = features.get("complexity", 0)
    sentiment = features.get("sentiment", 0)
    similarity = features.get("similarity", 0)
    hedges = features.get("hedges", 0)

    # 1. 문장 복잡도 점수 반영
    complexity_adjustment = 0
    if "complexity_min" in expectations and complexity < expectations["complexity_min"]: complexity_adjustment = -10
    elif "complexity_max" in expectations and complexity > expectations["complexity_max"]: complexity_adjustment = -10
    else: complexity_adjustment = 5
    score += complexity_adjustment
    print(f"Complexity Adjustment: {complexity_adjustment}")

    # 2. 감성 점수 반영
    sentiment_adjustment = 0
    if "sentiment_min" in expectations and sentiment < expectations["sentiment_min"]: sentiment_adjustment = -15
    elif "sentiment_max" in expectations and sentiment > expectations["sentiment_max"]: sentiment_adjustment = -10
    else: sentiment_adjustment = 10
    score += sentiment_adjustment
    print(f"Sentiment Adjustment: {sentiment_adjustment}")

    # 3. 시맨틱 유사도 점수 반영
    similarity_bonus = 0
    similarity_weight = expectations.get("similarity_weight", 0.2)
    similarity_min_bonus = expectations.get("similarity_min_bonus", 50)
    if similarity >= similarity_min_bonus: # 최소 기준점 이상일 때만
        # 유사도 점수(0-100)를 가중치(0.2)만큼 보너스로 변환
        similarity_bonus = int((similarity - similarity_min_bonus) * similarity_weight) 
    else:
        similarity_bonus = -10 # 최소 유사도 미달 시 감점
    score += similarity_bonus
    print(f"Semantic Similarity Bonus: {similarity_bonus}")

    # 4. 회피 표현 (Hedging) 사용 여부 반영
    hedging_penalty_score = 0
    if hedges > 0:
        hedging_penalty_score = - (hedges * expectations.get("hedging_penalty", 10))
    score += hedging_penalty_score
    print(f"Hedging Penalty: {hedging_penalty_score}")

    final_score = max(0, min(100, score))
    print(f"--- Feature Score Calculation ({persona}) ---")
    print(f"Complexity: {complexity:.1f}, Sentiment: {sentiment:.1f}, Similarity: {similarity:.1f}, Hedges: {hedges}")
    print(f"Calculated Feature Score: {final_score}")
    print("---------------------------------------")
    return final_score

# --- diagnose_user_level 함수 (final_score 입력) ---
def diagnose_user_level(final_score):
    """'최종 점수'를 바탕으로 수준 진단"""
    if final_score < 50:
        return "초보자"
    elif final_score < 80:
        return "중급자"
    else:
        return "고급자"