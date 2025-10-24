# core/ai.py
import boto3
import os
import json
import time
import uuid
import urllib.request
from botocore.exceptions import ClientError # ClientError 임포트

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
    object_key = f"{job_name}.wav"
    transcript_text = ""

    # S3 버킷 이름이 설정되었는지 확인
    if not S3_BUCKET_NAME:
        print("오류: S3_BUCKET_NAME 환경 변수가 설정되지 않았습니다.")
        return "[음성 인식 오류: S3 버킷 설정 필요]"

    try:
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=object_key, Body=audio_bytes)
        media_file_uri = f"s3://{S3_BUCKET_NAME}/{object_key}"

        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_file_uri},
            MediaFormat='wav',
            LanguageCode=language_code
        )

        while True:
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = status['TranscriptionJob']['TranscriptionJobStatus']
            if job_status in ['COMPLETED', 'FAILED']:
                break
            print(f"Transcribe 작업 진행 중... ({job_status})")
            time.sleep(3) # 폴링 간격

        if job_status == 'COMPLETED':
            transcript_file_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            # Transcribe 결과 파일에 접근 시도
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

        else:
            print(f"Transcribe 작업 실패: {status['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
            transcript_text = "[음성 인식 실패]"

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'AccessDeniedException':
             print(f"AWS 권한 오류 발생 (Transcribe): {e}. IAM 정책을 확인하세요.")
             transcript_text = "[음성 인식 오류: 권한 부족]"
        else:
             print(f"AWS 오류 발생 (Transcribe): {e}")
             transcript_text = "[음성 인식 중 오류 발생]"
    except Exception as e: # 예상치 못한 다른 오류 처리
        print(f"예상치 못한 오류 발생 (Transcribe): {e}")
        transcript_text = "[음성 인식 중 알 수 없는 오류]"
    finally:
        # S3 파일 삭제 시도
        try:
            s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=object_key)
        except ClientError as e:
            print(f"S3 파일 삭제 중 오류: {e}")

        # Transcribe 작업 삭제 시도 (작업이 존재할 경우)
        try:
            transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        except ClientError as e:
            # 작업이 이미 완료/실패 후 자동 삭제되었거나, 권한이 없을 수 있음 (무시 가능)
            print(f"Transcribe 작업 삭제 중 오류 (무시 가능): {e}")

    return transcript_text

# --- 👇 여기가 get_ai_response 함수 정의 부분입니다. ---
def get_ai_response(persona, user_prompt, learning_language='English', feedback_language='Korean'):
    """(LLM) Bedrock Claude 모델로 사용자의 발화를 평가하여,
    상황에 맞는 단일 텍스트(영어 응답 또는 한국어 피드백)와 점수를 반환."""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    prompt = f"""
Human: You are an expert AI speech coach evaluating a user's utterance.
The user is practicing their '{persona}' persona in {learning_language}.

Your task is to evaluate the user's last message based on the criteria below and provide EITHER a conversational response OR feedback, along with a score.

**Evaluation Criteria:**
- Persona Alignment: Does the utterance strongly match the '{persona}' style (tone, confidence, vocabulary)? Score >= 80/100 required.
- Fluency & Accuracy: Is the utterance reasonably fluent and grammatically correct? Minor errors acceptable if communication is clear.

**Decision Logic & Output:**

1.  **If the utterance is GOOD** (meets both criteria well, score >= 80):
    - Respond conversationally IN {learning_language}, in the persona of '{persona}'. Keep it concise (1-2 sentences).
    - Provide a high score (80-100).
    - **Your entire output MUST be ONLY the conversational response text.**

2.  **If the utterance NEEDS IMPROVEMENT** (fails one or both criteria, score < 80):
    - Do NOT provide a conversational response.
    - Provide constructive feedback IN {feedback_language}. Focus on the most critical area. Be specific and actionable.
    - Include an "✅ 추천 표현:" section. Crucially, the revised sentence example(s) in this section MUST be written IN {learning_language}.
    - Provide a score reflecting the issues (0-79).
    - **Your entire output MUST be ONLY the feedback text (including the recommended expression written in {learning_language}).**

**Finally, append the score on a new line after your main response or feedback, using the format `|||SCORE:::[score]/100`.**

User's message: "{user_prompt}"
Assistant:"""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    })

    main_output_text = ""
    score = 0
    is_feedback = False

    try:
        response = bedrock_client.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        full_response_text = response_body['content'][0]['text'].strip()
        print(f"--- Bedrock Raw Response --- \n{full_response_text}\n--------------------------") # 디버깅용 출력 추가

        # [수정된 점수 파싱 로직]
        score_part_found = False
        if "|||SCORE:::" in full_response_text:
            parts = full_response_text.split("|||SCORE:::")
            if len(parts) == 2:
                main_output_text = parts[0].strip()
                score_part = parts[1]
                score_text_parts = score_part.split('/')
                if len(score_text_parts) > 0:
                    score_text = score_text_parts[0].strip()
                    print(f"Extracted score text: '{score_text}'") # 디버깅용 출력 추가
                    try:
                        score = int(score_text)
                        score_part_found = True
                        print(f"Parsed score: {score}") # 디버깅용 출력 추가
                    except ValueError:
                        print(f"점수 파싱 오류 (ValueError): '{score_text}'는 숫자가 아님")
                else:
                     print("점수 파싱 오류: '/' 구분자 없음")
            else:
                print("점수 파싱 오류: '|||SCORE:::' 구분자 분리 실패")
        else:
            print("응답 형식 오류: '|||SCORE:::' 구분자 없음")
            main_output_text = full_response_text # 구분자 없으면 전체를 메인 텍스트로

        if not score_part_found:
             score = 0 # 어떤 이유로든 점수 파싱 실패 시 0점 처리

        # 피드백 여부 판단 (점수 기준)
        if score < 80:
            is_feedback = True
        # Bedrock 응답 시작 부분 확인 (더 정확한 방법)
        elif main_output_text.startswith("FEEDBACK:::"): # 실제로는 이 프롬프트는 FEEDBACK::: 를 안만듦
             is_feedback = True
        elif main_output_text.startswith("RESPONSE:::"): # 실제로는 이 프롬프트는 RESPONSE::: 를 안만듦
             is_feedback = False
        # 만약 RESPONSE/FEEDBACK 마커 없이 점수만 80점 미만이면 피드백으로 간주
        elif score < 80:
             is_feedback = True


    except ClientError as e:
        print(f"AWS 오류 발생 (Bedrock): {e}")
        main_output_text = f"Bedrock 호출 중 오류 발생: {e}"
        score = 0
        is_feedback = True # 오류는 피드백으로 처리
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Bedrock): {e}")
        main_output_text = "AI 응답 처리 중 알 수 없는 오류 발생"
        score = 0
        is_feedback = True # 오류는 피드백으로 처리

    # 결과 반환
    return main_output_text, is_feedback, score

# --- 힌트 생성 함수 ---
def get_hint(level, conversation_history, learning_language='English'):
    """(LLM) Bedrock Claude 모델로 수준별 힌트 생성 (역할 교대 보장)"""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    if level == '초보자':
        instruction = f"Provide one complete and simple sentence in {learning_language} that can naturally follow this conversation."
    else:
        instruction = f"Provide 3-4 relevant keywords in {learning_language} that can be used to continue this conversation."

    messages_for_prompt = []
    last_role = None # 마지막 역할 추적 변수

    # 대화 기록을 Claude 형식으로 변환 (최근 4개 턴)
    for msg in conversation_history[-4:]:
        current_role = "user" if msg['role'] == "user" else "assistant"
        # content 키가 있고, 이전 역할과 다를 때만 추가
        if 'content' in msg and msg['content'] and current_role != last_role:
             messages_for_prompt.append({"role": current_role, "content": msg['content']})
             last_role = current_role # 마지막 역할 업데이트

    # 최종 지시사항 추가
    final_prompt_content = f"""Based on the recent conversation history above, provide a hint for the user.

**Instruction:** {instruction}

Provide only the hint text itself, without any introductory phrases like "Here's a hint:"."""

    # 마지막 역할이 assistant였거나 메시지가 비어있으면 user로 추가
    if not messages_for_prompt or last_role == "assistant":
        messages_for_prompt.append({"role": "user", "content": final_prompt_content})
    # 마지막 역할이 user였다면, 마지막 user 메시지에 지시사항을 덧붙임 (더 안전한 방법)
    elif last_role == "user":
        messages_for_prompt[-1]["content"] += "\n\n" + final_prompt_content
        # 만약 마지막 user 메시지에 지시사항을 덧붙이는 대신
        # assistant 턴을 하나 임의로 넣고 user 턴을 넣는 방법도 고려 가능
        # messages_for_prompt.append({"role": "assistant", "content": "Okay."})
        # messages_for_prompt.append({"role": "user", "content": final_prompt_content})


    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 50, # 힌트는 짧게
        "messages": messages_for_prompt
    })

    try:
        response = bedrock_client.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        # Claude 3 모델 응답 형식에 맞게 content 블록 확인
        if response_body.get('content') and isinstance(response_body['content'], list) and response_body['content'][0].get('type') == 'text':
             hint_text = response_body['content'][0]['text']
             return hint_text.strip()
        else:
             print(f"예상치 못한 Bedrock 응답 형식(Hint): {response_body}")
             return "힌트 형식 오류."

    except ClientError as e:
        print(f"AWS 오류 발생 (Hint Generation): {e}")
        return "힌트 생성 중 오류가 발생했습니다."
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Hint Generation): {e}")
        return "힌트 생성 중 알 수 없는 오류 발생."

# --- TTS 함수 ---
def text_to_audio(text, language_code='en-US'): # language_code는 받지만 현재는 영어만 처리
    """(TTS) Amazon Polly로 텍스트를 영어 음성으로 변환"""
    voice_id = 'Joanna' # 항상 영어 목소리 사용

    # SSML 태그가 있는지 간단히 확인 (AI가 생성할 수 있으므로 대비)
    is_ssml = text.strip().startswith('<speak>') and text.strip().endswith('</speak>')
    ssml_text = text if is_ssml else f"<speak>{text}</speak>" # 기본 태그 추가

    try:
        response = polly_client.synthesize_speech(
            VoiceId=voice_id,
            OutputFormat='mp3',
            Text=ssml_text,
            Engine='neural',
            # LanguageCode='en-US', # VoiceId가 영어이므로 생략 가능
            TextType='ssml' # SSML 시도
        )
        return response['AudioStream'].read()
    except ClientError as e:
        print(f"AWS 오류 발생 (Polly - SSML 시도): {e}")
        # 오류 시 일반 텍스트 재시도
        try:
            plain_text = re.sub('<[^>]+>', '', text) # 간단히 태그 제거
            response = polly_client.synthesize_speech(
                VoiceId=voice_id, OutputFormat='mp3', Text=plain_text,
                Engine='neural', TextType='text'
            )
            return response['AudioStream'].read()
        except Exception as fallback_e:
            print(f"Polly 재시도 실패: {fallback_e}")
            return None
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Polly): {e}")
        return None