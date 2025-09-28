# core/ai.py
import boto3
import os
import json
# STT 기능은 임시로 google-generativeai를 유지합니다.
import google.generativeai as genai
import io

# --- AWS 클라이언트 설정 ---
# .env 파일의 인증 정보를 boto3가 자동으로 인식합니다.
region = os.getenv("AWS_DEFAULT_REGION")
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
polly_client = boto3.client('polly', region_name=region)

# --- STT 기능 (임시로 Gemini 사용) ---
# app.py에서 API 키를 설정하므로 여기서는 모델만 로드합니다.
genai_model = genai.GenerativeModel('gemini-2.5-flash')

def transcribe_audio(audio_bytes):
    """오디오 바이트를 받아 텍스트로 변환합니다. (STT)"""
    audio_file = genai.upload_file(
        path=io.BytesIO(audio_bytes),
        display_name="recorded_audio.wav",
        mime_type="audio/wav"
    )
    prompt = "Please transcribe this audio."
    response = genai_model.generate_content([prompt, audio_file])
    genai.delete_file(audio_file.name)
    return response.text

# --- AI 답변 및 피드백 (Amazon Bedrock 사용) ---
def get_ai_response(persona, user_prompt):
    """페르소나와 사용자 입력을 바탕으로 AI의 답변과 피드백을 생성합니다. (LLM)"""
    # Anthropic의 Claude 3 Sonnet 모델을 사용합니다.
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    # Claude 모델에 맞는 프롬프트 형식
    prompt = f"""
        Human: You are a helpful AI speech coach. Your goal is to act as a conversation partner and provide feedback.
        The user is practicing their '{persona}' persona.

        1. First, respond to the user's message naturally, in the persona of '{persona}'.
        2. After your response, provide constructive feedback on the user's message. The feedback should be concise and focus on how well they embodied the '{persona}'.
        3. Format your entire output strictly as follows, using '---' as a separator:
        [Your persona-based response]
        ---
        [Your feedback on the user's message]

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
        response_part, feedback_part = full_response_text.split("---", 1)
        return response_part.strip(), feedback_part.strip()
    except ValueError:
        return full_response_text, "피드백을 생성하는 데 실패했습니다."

# --- TTS 기능 (Amazon Polly 사용) ---
def text_to_audio(text):
    """텍스트를 받아 MP3 오디오 바이트를 반환합니다. (TTS)"""
    response = polly_client.synthesize_speech(
        VoiceId='Joanna',  # 사용할 목소리 ID (예: Joanna, Seoyeon)
        OutputFormat='mp3',
        Text=text,
        Engine='neural' # 더 자연스러운 Neural 엔진 사용
    )
    return response['AudioStream'].read()