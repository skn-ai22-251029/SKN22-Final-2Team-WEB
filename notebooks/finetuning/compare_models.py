import os
import torch
from dotenv import load_dotenv
from openai import OpenAI
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import PeftModel
from huggingface_hub import login

# 1. 환경 설정 및 로그인
load_dotenv()
hf_token = os.getenv("HF_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")

if hf_token:
    login(token=hf_token)
else:
    print("Warning: HF_TOKEN not found in .env")

if not openai_api_key:
    print("Error: OPENAI_API_KEY not found in .env. OpenAI comparison will not work.")

# 2. 모델 설정 경로
base_model_id = "google/gemma-2-9b-it"
# Windows 절대 경로 대신 상대 경로를 사용하여 HFValidationError 방지
adapter_path = "./gemma2-pet-counselor-lora"

if not os.path.exists(adapter_path):
    print(f"Error: Adapter directory not found at {adapter_path}")
    print("파인튜닝된 결과물이 해당 폴더에 있는지 확인해주세요.")
    exit()

print("Loading Fine-tuned Gemma 2 model... (This may take a few minutes)")

# 3. Gemma 2 모델 로드 (4-bit QLoRA)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

base_model = AutoModelForCausalLM.from_pretrained(
    base_model_id,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

# 학습된 LoRA 어댑터 결합
model = PeftModel.from_pretrained(base_model, adapter_path)
tokenizer = AutoTokenizer.from_pretrained(base_model_id)

# 4. OpenAI 클라이언트 설정
client = OpenAI(api_key=openai_api_key)

def get_gemma_response(instruction, user_input):
    prompt = (
        f"<start_of_turn>user\n"
        f"{instruction}\n\n"
        f"질문: {user_input}<end_of_turn>\n"
        f"<start_of_turn>model\n"
    )
    
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
    )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # 프롬프트 부분 제외하고 답변만 추출
    if "model\n" in response:
        response = response.split("model\n")[-1]
    return response.strip()

def get_gpt_response(instruction, user_input):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_input}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"OpenAI Error: {str(e)}"

# 5. 비교 루프 실행
instruction = "당신은 반려동물 관리 및 건강 상담을 제공하는 '다정하고 전문적인 펫 상담사'입니다. 사용자의 질문에 대해 공감하며 전문적인 조언을 제공하세요."

print("\n" + "="*50)
print("반려동물 상담사 모델 비교 테스트를 시작합니다.")
print("종료하려면 'quit' 또는 'exit'를 입력하세요.")
print("="*50 + "\n")

while True:
    user_input = input("사용자 질문 입력: ")
    if user_input.lower() in ['quit', 'exit', 'q']:
        break
        
    print("\n[AI 답변 생성 중...]")
    
    # Gemma 2 답변 호출
    gemma_reply = get_gemma_response(instruction, user_input)
    
    # GPT-4o-mini 답변 호출
    gpt_reply = get_gpt_response(instruction, user_input)
    
    print("\n" + "-"*20 + " [Fine-tuned Gemma 2] " + "-"*20)
    print(gemma_reply)
    
    print("\n" + "-"*20 + " [GPT-4o-mini] " + "-"*20)
    print(gpt_reply)
    print("\n" + "="*60 + "\n")
