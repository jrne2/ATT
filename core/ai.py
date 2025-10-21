# core/ai.py
import boto3
import os
import json
import time
import uuid
import urllib.request

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
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(3)

    transcript_text = ""
    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        transcript_file_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        with urllib.request.urlopen(transcript_file_uri) as response:
            transcript_json = json.loads(response.read())
            transcript_text = transcript_json['results']['transcripts'][0]['transcript']

    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=object_key)
    # 아래 줄은 권한 문제 발생 시 주석 처리할 수 있습니다.
    transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
    
    return transcript_text

def get_ai_response(persona, user_prompt, learning_language='English', feedback_language='Korean'):
    """(LLM) Bedrock Claude 모델로 답변, 피드백, 점수 생성"""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    prompt = f"""
Human: You are an expert AI speech coach.
The user is practicing their '{persona}' persona in {learning_language}.

Your task is to provide a conversational response, detailed feedback, and a score.

1.  **Respond:** First, respond to the user's message naturally IN {learning_language}, in the persona of '{persona}'.
2.  **Feedback:** After your response, provide constructive feedback on the user's message IN {feedback_language}.
3.  **Example (Crucial):** The feedback MUST include an "✅ 추천 표현:" section with one or two revised versions of the user's sentence that are 'just one level up' (i+1) and align more closely with the '{persona}'.
4.  **Score (Crucial):** After the feedback, on a new line, you MUST provide a score for how well the user's utterance matched the persona, in the format `Score: [score]/100`.

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
    response = bedrock_client.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response.get('body').read())
    full_response_text = response_body['content'][0]['text']

    try:
        response_part, feedback_and_score = full_response_text.split("---", 1)
        if "Score:" in feedback_and_score:
            feedback_part, score_part = feedback_and_score.split("Score:", 1)
            score = int(score_part.split('/')[0].strip())
        else:
            feedback_part = feedback_and_score
            score = 0
        return response_part.strip(), feedback_part.strip(), score
    except ValueError:
        return full_response_text, "피드백을 생성하는 데 실패했습니다.", 0

def get_hint(level, conversation_history, learning_language='English'):
    """(LLM) Bedrock Claude 모델로 수준별 힌트 생성"""
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    if level == '초보자':
        instruction = f"Provide one complete and simple sentence in {learning_language} that can naturally follow this conversation."
    else:
        instruction = f"Provide 3-4 relevant keywords in {learning_language} that can be used to continue this conversation."

    history_text = "\n".join([f"<{msg['role']}>{msg['content']}</{msg['role']}>" for msg in conversation_history[-4:]])
    prompt = f"""
Human: You are a helpful language learning assistant. Based on the recent conversation history below, provide a hint for the user.

**Instruction:** {instruction}

--- Conversation History ---
{history_text}
---

Provide only the hint text, without any introductory phrases.
Assistant:"""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": prompt}]
    })
    response = bedrock_client.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response.get('body').read())
    hint_text = response_body['content'][0]['text']
    return hint_text

def text_to_audio(text):
    """(TTS) Amazon Polly로 텍스트를 음성으로 변환"""
    response = polly_client.synthesize_speech(
        VoiceId='Joanna',
        OutputFormat='mp3',
        Text=text,
        Engine='neural'
    )
    return response['AudioStream'].read()