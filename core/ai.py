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
        while True:
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = status['TranscriptionJob']['TranscriptionJobStatus']
            if job_status in ['COMPLETED', 'FAILED']: break
            print(f"Transcribe 작업 진행 중... ({job_status})")
            time.sleep(3) # 폴링 간격
        if job_status == 'COMPLETED':
            transcript_file_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            try:
                with urllib.request.urlopen(transcript_file_uri) as response:
                    transcript_json = json.loads(response.read())
                    transcript_text = transcript_json['results']['transcripts'][0]['transcript']
            except urllib.error.URLError as e:
                 print(f"Transcribe 결과 URL 접근 오류: {e}")
                 transcript_text = "[음성 인식 결과 로드 실패]"
            except KeyError:
                 print(f"Transcribe 결과 JSON 형식 오류")
                 transcript_text = "[음성 인식 결과 형식 오류]"
            except Exception as e: # Catch other potential parsing errors
                 print(f"Transcribe 결과 처리 중 알 수 없는 오류: {e}")
                 transcript_text = "[음성 인식 결과 처리 오류]"
        else:
            print(f"Transcribe 작업 실패: {status['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
            transcript_text = "[음성 인식 실패]"
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        print(f"AWS 오류 발생 (Transcribe - {error_code}): {e}")
        transcript_text = f"[음성 인식 오류: {error_code}]"
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Transcribe): {e}")
        transcript_text = "[음성 인식 중 알 수 없는 오류]"
    finally:
        try: s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=object_key)
        except ClientError as e: print(f"S3 파일 삭제 중 오류: {e}")
        try: transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        except ClientError as e: print(f"Transcribe 작업 삭제 중 오류 (무시 가능): {e}")
    return transcript_text

# --- 👇 여기가 최종 수정된 get_ai_response 함수입니다 ---
def get_ai_response(persona, user_prompt, learning_language='English', feedback_language='Korean'):
    """(LLM) Bedrock Claude 모델로 영어 응답 또는 (영어 추천표현 + 한국어 피드백 - 분리된 형식) 생성, 점수 반환."""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    lang_code_map = {'English': 'en-US', '영어': 'en-US', 'Korean': 'ko-KR', '한국어': 'ko-KR', 'Japanese': 'ja-JP','일본어': 'ja-JP', 'Spanish': 'es-US', '스페인어': 'es-US'}
    learning_language_code = lang_code_map.get(learning_language, 'en-US')

    # [수정된 프롬프트] 평가 기준 및 피드백 내용 강화, 출력 형식 명확화
    prompt = f"""
Human: You are an expert AI speech coach evaluating a user's utterance.
The user is practicing their '{persona}' persona in {learning_language}.
Your task is to evaluate the user's last message based on the criteria below and provide EITHER a conversational response OR feedback, along with a score. Use plain text for the output.

**Evaluation Criteria:**
- **Persona Alignment (Primary):** How well does the utterance's overall style (word choice, tone implied by text, sentence structure, confidence level implied) match the '{persona}' persona? Score >= 80 required for a GOOD rating. Evaluate this strictly. Even if grammatically correct, if the style doesn't fit the persona, it needs improvement.
- Fluency & Accuracy: Is the utterance reasonably fluent (minimal hesitation implied by text like 'um', 'uh') and grammatically correct? Minor errors are acceptable if communication is clear AND persona alignment is good.

**Decision Logic & Output Format:**

1.  **If utterance is GOOD** (Score >= 80 based PRIMARILY on Persona Alignment):
    - Respond conversationally IN {learning_language} (1-2 sentences), maintaining the '{persona}' style.
    - Provide a high score (80-100).
    - **Output ONLY:** `RESPONSE:::[Your conversational response in {learning_language}]|||SCORE:::[score]/100`

2.  **If utterance NEEDS IMPROVEMENT** (Score < 80, primarily due to Persona Alignment or significant Fluency/Accuracy issues):
    - Do NOT respond conversationally.
    - Determine 1-2 revised examples IN {learning_language} that better fit the persona.
    - Provide feedback explanation IN {feedback_language}. Focus ONLY on concrete, actionable points related to **why** the utterance didn't match the persona (e.g., "'Maybe' sounds hesitant for a '{persona}'; try 'Definitely'.") or specific grammar/word choice errors. **MUST avoid abstract advice.**
    - Provide a score (0-79).
    - **Format the feedback text EXACTLY like this, starting with the recommended expression label and using required newlines:**
      ```text
      ✅ 추천 표현:
      - "[{learning_language} example 1]"
      - "[{learning_language} example 2 (optional)]"

      피드백: [{feedback_language} explanation focusing on concrete points]
      ```
    - **Output ONLY:** `FEEDBACK:::[The formatted text block above]|||SCORE:::[score]/100`

User's message: "{user_prompt}"
Assistant:"""

    body = json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]})
    main_output_text, score, is_feedback = "", 0, False
    try:
        response = bedrock_client.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        full_response_text = response_body['content'][0]['text'].strip()
        print(f"--- Bedrock Raw Response ---\n{full_response_text}\n--------------------------") # 디버깅용

        score_part_found = False; raw_main_output = full_response_text
        if "|||SCORE:::" in full_response_text:
            parts = full_response_text.split("|||SCORE:::");
            if len(parts) == 2:
                raw_main_output = parts[0].strip(); score_part = parts[1]; score_text = score_part.split('/')[0].strip()
                try: score = int(score_text); score_part_found = True
                except ValueError: print(f"점수 파싱 오류: '{score_text}'")
            else: print("점수 파싱 오류: 분리 실패")
        else: print("응답 형식 오류: '|||SCORE:::' 구분자 없음")
        if not score_part_found: score = 0

        # 피드백 여부 판단 로직 보강
        if raw_main_output.startswith("FEEDBACK:::"):
            is_feedback = True
            main_output_text = raw_main_output.replace("FEEDBACK:::", "").strip()
        elif raw_main_output.startswith("RESPONSE:::"):
            is_feedback = False
            main_output_text = raw_main_output.replace("RESPONSE:::", "").strip()
        # 마커 없더라도 점수 기준으로 판단
        elif score < 80:
             is_feedback = True
             main_output_text = raw_main_output # 마커 없으니 전체 텍스트 사용
             print("경고: 응답 마커 없음, 점수(<80) 기준으로 피드백 판단.")
        else: # 마커 없고 점수 높으면 응답
             is_feedback = False
             main_output_text = raw_main_output # 마커 없으니 전체 텍스트 사용
             print("경고: 응답 마커 없음, 점수(>=80) 기준으로 응답 판단.")

    except ClientError as e: print(f"AWS 오류 (Bedrock): {e}"); main_output_text, score, is_feedback = f"Bedrock 오류: {e}", 0, True
    except Exception as e: print(f"예외 발생 (Bedrock): {e}"); main_output_text, score, is_feedback = "AI 응답 처리 오류", 0, True
    return main_output_text, is_feedback, score
# --- get_ai_response 함수 정의 끝 ---


def get_hint(level, conversation_history, learning_language='English'):
    """(LLM) Bedrock Claude 모델로 수준별 힌트 생성"""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'; instruction = (f"Provide one simple sentence in {learning_language}..." if level == '초보자' else f"Provide 3-4 keywords in {learning_language}..."); messages_for_prompt = []; last_role = None
    for msg in conversation_history[-4:]: role = "user" if msg.get('role') == "user" else "assistant"; content = msg.get('content');
    if content and role != last_role: messages_for_prompt.append({"role": role, "content": content}); last_role = role
    final_prompt_content = f"Based on history, provide hint.\n**Instruction:** {instruction}\nOnly hint text."
    if not messages_for_prompt or last_role == "assistant": messages_for_prompt.append({"role": "user", "content": final_prompt_content})
    elif last_role == "user": messages_for_prompt[-1]["content"] += "\n\n" + final_prompt_content
    body = json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 50, "messages": messages_for_prompt})
    try:
        response = bedrock_client.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        # 들여쓰기 수정 완료
        if response_body.get('content') and isinstance(response_body['content'], list) and response_body['content'][0].get('type') == 'text':
             return response_body['content'][0]['text'].strip()
        else:
             print(f"예상치 못한 Bedrock 응답 형식(Hint): {response_body}")
             return "힌트 형식 오류."
    except ClientError as e: print(f"AWS 오류 (Hint): {e}"); return "힌트 생성 오류."
    except Exception as e: print(f"예외 발생 (Hint): {e}"); return "힌트 생성 오류."

def text_to_audio(text, language_code='en-US'): # 영어 TTS만 처리
    """(TTS) Amazon Polly로 텍스트를 영어 음성으로 변환 (일반 텍스트 모드)"""
    voice_id = 'Joanna'; plain_text = re.sub('<[^>]+>', '', text) # SSML 태그 제거
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