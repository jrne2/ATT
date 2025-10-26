# core/analyzer.py
import re

# --- 페르소나별 기대 지표 (my.py에서 이 데이터를 사용합니다) ---
PERSONA_EXPECTATIONS = {
    "토니 스타크 (재치있는 억만장자)": {
        "complexity_min": 5.0, "complexity_max": 12.0, # 너무 단순하지도, 너무 장황하지도 않게
        "sentiment_min": -0.2, "sentiment_max": 0.8,  # 중립 ~ 재치있는 긍정 (약간의 냉소 허용)
        "hedging_penalty": 25, # 회피 표현 감점 (높음)
        "keywords": ["genius", "billionaire", "tech", "obviously", "right?", "exactly", "let's be honest", "diagnostics", "optimize", "performance", "boost", "protocol"],
        "keyword_bonus": 7
    },
    "친절하고 따뜻한 친구": {
        "complexity_min": 3.0, "complexity_max": 9.0,  # 쉽고 간결한 문장
        "sentiment_min": 0.4, "sentiment_max": 1.0,   # 높은 긍정성 요구
        "hedging_penalty": 5, # 회피 표현 감점 (낮음)
        "keywords": ["friend", "together", "hang out", "awesome", "great", "fun", "feel", "how are you", "what's up", "worry", "listen", "care", "totally", "amazing"],
        "keyword_bonus": 6 # 키워드 가중치 증가
    },
    "자신감 넘치는 비즈니스 리더": {
        "complexity_min": 7.0, "complexity_max": 13.0, # 명확하고 구조적
        "sentiment_min": 0.0, "sentiment_max": 0.6,   # 중립 ~ 통제된 긍정
        "hedging_penalty": 20, # 회피 표현 감점 (높음)
        "keywords": ["strategy", "efficiency", "execute", "plan", "data", "results", "objective", "action item", "propose", "suggest", "lead", "manage", "target", "deadline", "metrics", "solution"],
        "keyword_bonus": 7 # 키워드 가중치 증가
    }
}
# --- 기대 지표 끝 ---

def calculate_feature_score(persona, complexity, sentiment, keywords, user_prompt):
    """추출된 특징과 페르소나 기대를 비교하여 객관적 점수(0~100) 계산"""
    score = 50 # 기본 점수
    expectations = PERSONA_EXPECTATIONS.get(persona)

    if not expectations:
        print(f"경고: 페르소나 '{persona}'에 대한 기대 지표 정의 없음.")
        return score

    # 1. 문장 복잡도 점수 반영
    complexity_adjustment = 0
    if "complexity_min" in expectations and complexity < expectations["complexity_min"]:
        complexity_adjustment = -10 # 감점 조정
    elif "complexity_max" in expectations and complexity > expectations["complexity_max"]:
        complexity_adjustment = -10 # 감점 조정
    else:
        complexity_adjustment = 5 # 범위 내 가점
    score += complexity_adjustment
    print(f"Complexity Adjustment: {complexity_adjustment}")

    # 2. 감성 점수 반영
    sentiment_adjustment = 0
    if "sentiment_min" in expectations and sentiment < expectations["sentiment_min"]:
        sentiment_adjustment = -15
    elif "sentiment_max" in expectations and sentiment > expectations["sentiment_max"]:
        sentiment_adjustment = -10
    else:
        sentiment_adjustment = 10 # 감성 부합 가점
    score += sentiment_adjustment
    print(f"Sentiment Adjustment: {sentiment_adjustment}")

    # 3. 키워드 포함 여부 반영
    keyword_count = 0
    if "keywords" in expectations:
        prompt_lower = user_prompt.lower()
        for kw in expectations["keywords"]:
            if kw in prompt_lower: keyword_count += 1
    keyword_bonus = keyword_count * expectations.get("keyword_bonus", 5)
    score += keyword_bonus
    print(f"Keyword Bonus: {keyword_bonus}")

    # 4. 회피 표현 (Hedging) 사용 여부 반영
    hedges = len(re.findall(r'\b(maybe|perhaps|i think|i guess|kind of|sort of|um|uh|well)\b', user_prompt.lower()))
    hedging_penalty_score = 0
    if hedges > 0:
        hedging_penalty_score = - (hedges * expectations.get("hedging_penalty", 10))
    score += hedging_penalty_score
    print(f"Hedging Penalty: {hedging_penalty_score}")

    # 최종 점수를 0~100 범위로 제한
    final_score = max(0, min(100, score))
    print(f"--- Feature Score Calculation ({persona}) ---")
    print(f"Complexity: {complexity:.1f}, Sentiment: {sentiment:.1f}, Keywords: {keyword_count}, Hedges: {hedges}")
    print(f"Calculated Feature Score: {final_score}")
    print("---------------------------------------")
    return final_score

# --- 👇 [수정된 부분] 수준 진단 함수 ---
def diagnose_user_level(final_score):
    """'최종 점수'를 바탕으로 수준 진단"""
    if final_score < 50:
        return "초보자"
    elif final_score < 80: # 80점 미만은 중급자
        return "중급자"
    else: # 80점 이상은 고급자 (AI가 피드백 대신 응답을 주는 기준과 일치)
        return "고급자"
# --- 수정 끝 ---