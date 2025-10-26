# core/ai.py
import boto3
import os
import json
import time
import uuid
import urllib.request
from botocore.exceptions import ClientError
import re

# --- AWS 클라이언트 설정 ---
region = os.getenv("AWS_DEFAULT_REGION")
s3_client = boto3.client('s3', region_name=region)
transcribe_client = boto3.client('transcribe', region_name=region)
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
polly_client = boto3.client('polly', region_name=region)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def transcribe_audio(audio_bytes, language_code='en-US'):
    """(STT) 오디오를 S3에 올리고 Amazon Transcribe로 텍스트 변환"""
    job_name = f"transcribe-job-{uuid.uuid4()}"
    object_key = f"{job_name}.wav"; transcript_text = ""
    if not S3_BUCKET_NAME:
        print("오류: S3_BUCKET_NAME 환경 변수가 설정되지 않았습니다.")
        return "[음성 인식 오류: S3 버킷 설정 필요]"
    try:
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=object_key, Body=audio_bytes)
        media_file_uri = f"s3://{S3_BUCKET_NAME}/{object_key}"
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name, Media={'MediaFileUri': media_file_uri},
            MediaFormat='wav', LanguageCode=language_code
        )
        start_time = time.time()
        timeout_seconds = 60  # 60초 타임아웃
        while True:
            if time.time() - start_time > timeout_seconds:
                print(f"Transcribe 작업 타임아웃 ({timeout_seconds}초)")
                transcript_text = "[음성 인식 시간 초과]"
                break 
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = status['TranscriptionJob']['TranscriptionJobStatus']
            if job_status in ['COMPLETED', 'FAILED']:
                break 
            print(f"Transcribe 작업 진행 중... ({job_status})")
            time.sleep(3) 
        if job_status == 'COMPLETED':
            transcript_file_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            try:
                with urllib.request.urlopen(transcript_file_uri) as response:
                    transcript_json = json.loads(response.read())
                    transcript_text = transcript_json['results']['transcripts'][0]['transcript']
            except Exception as e:
                print(f"Transcribe 결과 처리 오류: {e}")
                transcript_text = "[음성 인식 결과 처리 오류]"
        elif job_status == 'FAILED':
            print(f"Transcribe 작업 실패: {status['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
            transcript_text = "[음성 인식 실패]"
    except ClientError as e:
        print(f"AWS 오류 발생 (Transcribe): {e}")
        transcript_text = f"[음성 인식 오류: {e.response.get('Error', {}).get('Code', 'Unknown')}]"
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Transcribe): {e}")
        transcript_text = "[음성 인식 중 알 수 없는 오류]"
    finally:
        try: s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=object_key)
        except ClientError as e: print(f"S3 파일 삭제 중 오류: {e}")
        try: transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        except ClientError as e: print(f"Transcribe 작업 삭제 오류: {e}")
    return transcript_text

# --- 👇 여기가 수정된 get_ai_response 함수입니다 (해석 추가) ---
def get_ai_response(persona, user_prompt, last_recommendation=None, learning_language='English', feedback_language='Korean'):
    """(LLM) Bedrock Claude 모델로 영어 응답 또는 (개선된 피드백 형식) 생성, 점수 반환."""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    lang_code_map = {'English': 'en-US', '영어': 'en-US', 'Korean': 'ko-KR', '한국어': 'ko-KR', 'Japanese': 'ja-JP','일본어': 'ja-JP', 'Spanish': 'es-US', '스페인어': 'es-US'}
    learning_language_code = lang_code_map.get(learning_language, 'en-US')

    persona_specific_instructions = ""
    # '토니 스타크' 페르소나 지시사항
    if persona == "토니 스타크 (재치있는 억만장자)":
        persona_specific_instructions = f"""
**Instructions for the '{persona}' Persona (This is the USER's goal):**
**Context:** This persona is NOT the 'movie hero'. The user's goal is to practice the *attitude* of a **'witty and confident leader in an everyday conversation.'**
- **Core Principle (80/20 Rule):** Your response MUST be 80% clear, direct information (plain-spoken) and 20% witty/sarcastic commentary. Wit is a seasoning, not the main course. Do NOT twist every sentence into a joke.
- **[DO - How to sound]:**
    - **Be Confident:** Always sound certain. (e.g., Instead of "That's a good idea," try "That's the *only* idea that makes sense.")
    - **Be Direct:** Get to the point. Don't hedge or talk around the issue.
    - **Be Witty:** Use occasional dry humor or sarcasm that fits the context. (e.g., "I like your plan. Almost as much as I like my own.")
- **[DON'T - What to avoid]:**
    - **[CRITICAL] NO LORE:** **NEVER** mention 'Iron Man', 'suits', 'Avengers', 'reactors', 'engineers', 'geniuses', 'superheroes', or ANY word that implies your job or movie background. We are only practicing the *tone of voice*.
    - **NO JOKE-STACKING:** Do not distort information, use childish/goofy jokes, or make every single sentence sarcastic. (The goal is 'witty', not 'clown'.)
    - **NO AGGRESSION:** Arrogant is not rude. Do not be aggressive or villainous.
- **[CRITICAL RULE - INTENT]:**
    - Recommendations MUST strictly maintain the user's original intent and scale.
    - If the user says, "Hello?" (a simple greeting), you must correct the *style* to be a more confident greeting (e.g., "Yeah?" or "You got my attention. What's the plan?").
    - DO NOT change the topic or escalate (e.g., "Another genius calling?")."""
    # '친절하고 따뜻한 친구' 페르소나 지시사항
    elif persona == "친절하고 따뜻한 친구":
        persona_specific_instructions = """
**Instructions for the '{persona}' Persona (This is the USER's goal):**
- **Tone:** Warm, empathetic, positive, casual.
- **[CRITICAL RULE - INTENT]:** Recommendations must maintain the user's original intent."""
    # '자신감 넘치는 비즈니스 리더' 페르소나 지시사항
    elif persona == "자신감 넘치는 비즈니스 리더":
          persona_specific_instructions = """
**Instructions for the '{persona}' Persona (This is the USER's goal):**
- **Tone:** Clear, concise, confident, decisive.
- **[CRITICAL RULE - INTENT]:** Recommendations must maintain the user's original intent."""

    # 'CRITICAL RULE 0' (추천 표현 반복 시)
    rule_0_text = ""
    if last_recommendation:
        def normalize(text):
            return re.sub(r'[^\w\s]', '', text).lower().strip()
        
        if normalize(user_prompt) == normalize(last_recommendation):
            rule_0_text = f"""
**CRITICAL RULE 0: FORCED SUCCESS**
The user's message ("{user_prompt}") is a direct and correct repetition of the previous recommendation ("{last_recommendation}").
You MUST NOT provide 'NEEDS IMPROVEMENT' (Decision Logic 2) feedback.
You MUST treat this as a "GOOD" utterance (Score >= 80).
You MUST provide a conversational response (Decision Logic 1).
"""

    prompt = f"""
Human: **[CRITICAL] Your (the AI's) persona is *always* that of a normal, supportive, and helpful speech coach.** You are friendly and encouraging.
You are *evaluating* the user's attempt to practice the '{persona}' persona, which is defined below.
{rule_0_text} 
---
[Instructions for the USER'S Target Persona: '{persona}']
{persona_specific_instructions}
---
[End of Persona Instructions]

Your task is to evaluate the user's last message.
{rule_0_text} 

**Evaluation Criteria:** Score >= 80 for Persona Alignment & Fluency/Accuracy.

**Decision Logic & Output Format:**

1.  **If utterance is GOOD** (Score >= 80):
    -   **[HEAVILY MODIFIED]** Respond conversationally IN {learning_language}.
    -   **CRITICAL: Your reply MUST be as a 'normal, supportive coach'. DO NOT use the '{persona}' style.** Your reply must *react* to the user's statement.
    -   **[NEW] Also, provide a concise, literal translation of your response IN {feedback_language}.**
    -   Provide a high score (80-100).
    -   **[MODIFIED] Format the output EXACTLY like this (using a newline and parentheses for the translation):**
        ```text
        [Your *new* conversational (NORMAL COACH) REPLY in {learning_language}]
        (해석: [Your {feedback_language} translation])
        ```
    -   **Output ONLY:** `RESPONSE:::[The formatted text block above]|||SCORE:::[score]/100`

2.  **If utterance NEEDS IMPROVEMENT** (Score < 80):
    -   Do NOT respond conversationally.
    -   Determine 1-2 revised examples IN {learning_language}. These examples **must be a better way *for the user* to say what they tried to say, matching the '{persona}' instructions.**
    -   **CRITICAL:** The recommendation is **NOT your reply**. It is a suggestion for the *user* to say *next time*, matching their *target persona*.
    -   Your `진단` and `페르소나 분석` MUST be from the 'normal, supportive coach' perspective.
    -   **Format the feedback text EXACTLY like this. PAY ATTENTION TO THE LANGUAGES:**
        ```text
        🧐 진단: [Your diagnosis as a helpful coach in {feedback_language}.]

        ✅ 추천 표현:
        - "[Your first example (matching the '{persona}' target). This MUST be in {learning_language}.]"
          (해석: [Your literal translation of the first example. This MUST be in {feedback_language}.])
        - "[Your optional second example (matching the '{persona}' target). This MUST be in {learning_language}.]"
          (해석: [Your literal translation of the second example. This MUST be in {feedback_language}.])

        💡 이 표현은...
        1.  페르소나 분석: [Your analysis as a helpful coach in {feedback_language}. Explain *how* this suggestion matches the '{persona}' target (e.g., "This version sounds more confident...").]
        2.  **📚 표현 노트:** [Your explanation of a key idiom/word in {feedback_language}.]
        ```
    -   **Output ONLY:** `FEEDBACK:::[The formatted text block above]|||SCORE:::[score]/100`

**CRITICAL RULE 2 (PARSING):** Your entire output MUST be only ONE format (RESPONSE or FEEDBACK) and end with the score marker. **DO NOT add any extra text, reasoning, or "Here is my evaluation..." text before the `RESPONSE:::` or `FEEDBACK:::` markers.** Your response must *start* immediately with `RESPONSE:::` or `FEEDBACK:::`.

User's message: "{user_prompt}"
Assistant:"""

    body = json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]})
    main_output_text, score, is_feedback = "", 0, False
    try:
        response = bedrock_client.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        full_response_text = response_body['content'][0]['text'].strip()
        print(f"--- Bedrock Raw Response ---\n{full_response_text}\n--------------------------") # 디버깅용

        score_part_found = False; raw_main_output = full_response_text; score = 0
        
        if "|||SCORE:::" in full_response_text:
            parts = full_response_text.split("|||SCORE:::", 1) # 1번만 분리
            if len(parts) == 2:
                raw_main_output = parts[0].strip() # 점수 앞부분 (찌꺼기 포함)
                score_part = parts[1]; score_text = score_part.split('/')[0].strip()
                try: score = int(score_text); score_part_found = True
                except ValueError: print(f"점수 파싱 오류: '{score_text}'")
            else: print("점수 파싱 오류: 분리 실패")
        else: print("응답 형식 오류: '|||SCORE:::' 구분자 없음")
        
        # 찌꺼기를 걸러내는 파싱 로직
        if "FEEDBACK:::" in raw_main_output:
            is_feedback = True
            main_output_text = raw_main_output.split("FEEDBACK:::", 1)[-1].strip()
        elif "RESPONSE:::" in raw_main_output:
            is_feedback = False
            main_output_text = raw_main_output.split("RESPONSE:::", 1)[-1].strip()
        
        elif score < 80: 
            is_feedback = True
            main_output_text = raw_main_output 
            print("경고: 마커 없음, 점수(<80) 피드백.")
        else: 
            is_feedback = False
            main_output_text = raw_main_output 
            print("경고: 마커 없음, 점수(>=80) 응답.")

    except ClientError as e: print(f"AWS 오류 (Bedrock): {e}"); main_output_text, score, is_feedback = f"Bedrock 오류: {e}", 0, True
    except Exception as e: print(f"예외 발생 (Bedrock): {e}"); main_output_text, score, is_feedback = "AI 응답 처리 오류", 0, True
    return main_output_text, is_feedback, score
# --- get_ai_response 함수 정의 끝 ---

def get_hint(level, conversation_history, learning_language='English'):
    """(LLM) Bedrock Claude 모델로 수준별 힌트 생성"""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'; instruction = (f"Provide one simple sentence in {learning_language}..." if level == '초보자' else f"Provide 3-4 keywords in {learning_language}..."); messages_for_prompt = []; last_role = None
    for msg in conversation_history[-4:]:
        role = "user" if msg.get('role') == "user" else "assistant"
        content = msg.get('content')
        if content and role != last_role: 
            messages_for_prompt.append({"role": role, "content": content})
            last_role = role
            
    final_prompt_content = f"Based on history, provide hint.\n**Instruction:** {instruction}\nOnly hint text."
    if not messages_for_prompt or last_role == "assistant": messages_for_prompt.append({"role": "user", "content": final_prompt_content})
    elif last_role == "user": messages_for_prompt[-1]["content"] += "\n\n" + final_prompt_content
    
    body = json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 50, "messages": messages_for_prompt})
    
    try:
        response = bedrock_client.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        
        if response_body.get('content') and isinstance(response_body['content'], list) and response_body['content'][0].get('type') == 'text':
             return response_body['content'][0]['text'].strip()
        else:
             print(f"예상치 못한 Bedrock 응답 형식(Hint): {response_body}")
             return "힌트 형식 오류."
             
    except ClientError as e: 
        print(f"AWS 오류 (Hint): {e}")
        return "힌트 생성 오류."
    except Exception as e: 
        print(f"예외 발생 (Hint): {e}")
        return "힌트 생성 오류."
# --- get_hint 함수 정의 끝 ---

def text_to_audio(text, language_code='en-US'): # 영어 TTS만 처리
    """(TTS) Amazon Polly로 텍스트를 영어 음성으로 변환 (일반 텍스트 모드)"""
    voice_id = 'Joanna'
    
    # (해석:...) 부분 제거
    english_only_text = text.split('\n')[0].strip()
    # ------------------------------------

    plain_text = re.sub('<[^>]+>', '', english_only_text) # 혹시 모를 SSML 태그 제거
    
    try:
        response = polly_client.synthesize_speech(
            VoiceId=voice_id, OutputFormat='mp3', Text=plain_text,
            Engine='neural', LanguageCode=language_code, TextType='text'
        )
        return response['AudioStream'].read()
    except ClientError as e:
        print(f"AWS 오류 발생 (Polly): {e}")
        return None
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Polly): {e}")
        return None