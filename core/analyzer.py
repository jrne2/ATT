# core/analyzer.py
import re

# --- 👇 [수정된 부분] 페르소나 이름 변경 ---
PERSONA_EXPECTATIONS = {
    "토니 스타크 (재치있는 억만장자)": { # '아이언맨' 제거
        "complexity_min": 6.0, "complexity_max": 11.0,
        "sentiment_min": -0.1, "sentiment_max": 0.9,
        "hedging_penalty": 25,
        "keywords": ["genius", "billionaire", "tech", "obviously", "right?", "exactly", "let's be honest", "diagnostics", "optimize", "performance", "boost", "protocol"], # 'suit' 등 제거
        "keyword_bonus": 7
    },
    "친절하고 따뜻한 친구": {
        "complexity_min": 4.0, "complexity_max": 9.0,
        "sentiment_min": 0.4,
        "hedging_penalty": 5,
        "keywords": ["friend", "together", "hang out", "awesome", "great", "fun", "feel", "how are you", "what's up", "worry", "listen", "care", "totally", "amazing"],
        "keyword_bonus": 5
    },
    "자신감 넘치는 비즈니스 리더": {
        "complexity_min": 7.0, "complexity_max": 12.0,
        "sentiment_min": 0.0, "sentiment_max": 0.6,
        "hedging_penalty": 20,
        "keywords": ["strategy", "efficiency", "execute", "plan", "data", "results", "objective", "action item", "propose", "suggest", "lead", "manage", "target", "deadline", "metrics", "solution"],
        "keyword_bonus": 6
    }
}
# --- 수정 끝 ---

def calculate_feature_score(persona, complexity, sentiment, keywords, user_prompt):
    # ... (이전 코드와 동일, 변경 없음) ...
    score = 50
    expectations = PERSONA_EXPECTATIONS.get(persona)
    if not expectations: print(f"경고: 페르소나 '{persona}' 기대 지표 없음."); return score
    complexity_adjustment = 0
    if "complexity_min" in expectations and complexity < expectations["complexity_min"]: complexity_adjustment = -5
    elif "complexity_max" in expectations and complexity > expectations["complexity_max"]: complexity_adjustment = -5
    score += complexity_adjustment
    sentiment_adjustment = 0
    if "sentiment_min" in expectations and sentiment < expectations["sentiment_min"]: sentiment_adjustment = -15
    elif "sentiment_max" in expectations and sentiment > expectations["sentiment_max"]: sentiment_adjustment = -10
    else: sentiment_adjustment = 10
    score += sentiment_adjustment
    keyword_count = 0
    if "keywords" in expectations:
        prompt_lower = user_prompt.lower()
        for kw in expectations["keywords"]:
            if kw in prompt_lower: keyword_count += 1
    score += keyword_count * expectations.get("keyword_bonus", 5)
    hedges = len(re.findall(r'\b(maybe|perhaps|i think|i guess|kind of|sort of|um|uh|well)\b', user_prompt.lower()))
    hedging_penalty_score = 0
    if hedges > 0: hedging_penalty_score = - (hedges * expectations.get("hedging_penalty", 10))
    score += hedging_penalty_score
    final_score = max(0, min(100, score))
    print(f"--- Feature Score Calculation ({persona}) ---"); print(f"Complexity: {complexity:.1f}, Sentiment: {sentiment:.1f}, Keywords: {keyword_count}, Hedges: {hedges}"); print(f"Calculated Feature Score: {final_score}"); print("---------------------------------------")
    return final_score

def diagnose_user_level(final_score):
    """'최종 점수'를 바탕으로 수준 진단"""
    # ... (이전 코드와 동일, 변경 없음) ...
    if final_score < 50: return "초보자"
    elif final_score < 80: return "중급자"
    else: return "고급자"