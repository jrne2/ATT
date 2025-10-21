# core/analyzer.py

def diagnose_user_level(complexity_score, sentiment_score):
    """
    추출된 특징들을 바탕으로 사용자의 수준을 '초보자' 또는 '중급자'로 진단합니다.
    (규칙 기반의 간단한 모델)
    """
    # 예시: 문장 복잡도를 기준으로 수준을 판별하는 규칙
    if complexity_score < 8:
        return "초보자"
    else:
        return "중급자"