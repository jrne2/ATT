# core/analyzer.py

def diagnose_user_level(complexity_score, sentiment_score):
    """
    추출된 특징들을 바탕으로 사용자의 수준을 '초보자' 또는 '중급자'로 진단합니다.
    (규칙 기반 모델)
    """
    # 예시: 문장 복잡도를 주 기준으로 하되, 감성 점수도 약간 반영
    # 긍정적인 감성은 약간의 가산점, 부정적인 감성은 약간의 감점 (예시)
    adjusted_score = complexity_score + (sentiment_score * 0.5)

    # 최종 점수를 기준으로 수준 판별
    if adjusted_score < 7.5: # 기준점을 약간 조정
        return "초보자"
    else:
        return "중급자"