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
            # 상태 확인 전에 작업 존재 여부 확인 로직은 복잡하므로, 일단 삭제 시도
            transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        except ClientError as e:
            # 작업이 이미 완료/실패 후 자동 삭제되었거나, 권한이 없을 수 있음 (무시 가능)
            print(f"Transcribe 작업 삭제 중 오류 (무시 가능): {e}")

    return transcript_text

def get_ai_response(persona, user_prompt, learning_language='English', feedback_language='Korean'):
    """(LLM) Bedrock Claude 모델로 답변, 피드백, 점수 생성"""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    prompt = f"""
Human: You are an expert AI speech coach.
The user is practicing their '{persona}' persona in {learning_language}.

Your task is to provide a conversational response, detailed feedback, and a score.

1.  **Respond:** First, respond to the user's message naturally IN {learning_language}, in the persona of '{persona}'. Keep the response concise, about 1-2 sentences.
2.  **Feedback:** After your response, provide constructive feedback on the user's message IN {feedback_language}. Focus on pronunciation, intonation, confidence, and persona alignment. Be specific.
3.  **Example (Crucial):** The feedback MUST include an "✅ 추천 표현:" section with one or two revised versions of the user's sentence that are 'just one level up' (i+1) and align more closely with the '{persona}'.
4.  **Score (Crucial):** After the feedback, on a new line, you MUST provide a score for how well the user's utterance matched the persona, in the format `Score: [score]/100`. The score should be an integer between 0 and 100.

Strictly follow this format, using '---' as a separator:
[Your persona-based response in {learning_language}]
---
[Your feedback in {feedback_language}]

✅ 추천 표현:
- "[Revised sentence example 1]"

Score: [score]/100

User's message: "{user_prompt}"
Assistant:"""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    })

    try:
        response = bedrock_client.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        full_response_text = response_body['content'][0]['text']

        try:
            response_part, feedback_and_score = full_response_text.split("---", 1)
            if "Score:" in feedback_and_score:
                feedback_part, score_part = feedback_and_score.rsplit("Score:", 1) # rsplit으로 마지막 Score만 분리
                score_text = score_part.split('/')[0].strip()
                # 점수 파싱 오류 방지
                try:
                    score = int(score_text)
                except ValueError:
                    print(f"점수 파싱 오류: '{score_text}'")
                    score = 0
            else:
                feedback_part = feedback_and_score
                score = 0 # 응답 형식에 Score가 없는 경우
            return response_part.strip(), feedback_part.strip(), score
        except ValueError: # '---' 분리 실패 시
             print("응답 형식 오류: '---' 구분자 없음")
             return full_response_text, "피드백 형식 오류가 발생했습니다.", 0

    except ClientError as e:
        print(f"AWS 오류 발생 (Bedrock): {e}")
        return "[AI 응답 오류]", f"Bedrock 호출 중 오류 발생: {e}", 0
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Bedrock): {e}")
        return "[AI 응답 오류]", "AI 응답 처리 중 알 수 없는 오류 발생", 0


def get_hint(level, conversation_history, learning_language='English'):
    """(LLM) Bedrock Claude 모델로 수준별 힌트 생성"""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    if level == '초보자':
        instruction = f"Provide one complete and simple sentence in {learning_language} that can naturally follow this conversation."
    else:
        instruction = f"Provide 3-4 relevant keywords in {learning_language} that can be used to continue this conversation."

    # Claude 형식에 맞게 user/assistant 턴으로 변환 (최근 4개만)
    messages_for_prompt = []
    for msg in conversation_history[-4:]:
        role = "user" if msg['role'] == "user" else "assistant"
        # 피드백 등 다른 키 제외하고 content만 포함
        messages_for_prompt.append({"role": role, "content": msg['content']})

    # Claude는 Human/Assistant 턴을 messages 리스트로 받음
    # 마지막 지시는 Human 턴으로 추가
    final_prompt_content = f"""Based on the recent conversation history above, provide a hint for the user.

**Instruction:** {instruction}

Provide only the hint text itself, without any introductory phrases like "Here's a hint:"."""

    messages_for_prompt.append({"role": "user", "content": final_prompt_content})


    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 50,
        "messages": messages_for_prompt # 대화 기록 + 최종 지시
    })

    try:
        response = bedrock_client.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        hint_text = response_body['content'][0]['text']
        return hint_text.strip()
    except ClientError as e:
        print(f"AWS 오류 발생 (Hint Generation): {e}")
        return "힌트 생성 중 오류가 발생했습니다."
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Hint Generation): {e}")
        return "힌트 생성 중 알 수 없는 오류 발생."


def text_to_audio(text):
    """(TTS) Amazon Polly로 텍스트를 음성으로 변환"""
    try:
        response = polly_client.synthesize_speech(
            VoiceId='Joanna', # 다른 VoiceId 사용 가능 (예: Matthew, Amy)
            OutputFormat='mp3',
            Text=text,
            Engine='neural' # neural 엔진 사용 권장
        )
        return response['AudioStream'].read()
    except ClientError as e:
        print(f"AWS 오류 발생 (Polly): {e}")
        return None # 오류 발생 시 None 반환
    except Exception as e:
        print(f"예상치 못한 오류 발생 (Polly): {e}")
        return None