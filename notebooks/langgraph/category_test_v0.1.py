import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# 1. 환경 변수 로드 및 클라이언트 설정
from dotenv import find_dotenv
load_dotenv(find_dotenv())
client = OpenAI()
LLM_MODEL = "gpt-4o-mini"

# 2. 데이터 경로 설정 및 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORY_FILE = os.path.join(BASE_DIR, "data", "category.json")

def load_categories():
    if not os.path.exists(CATEGORY_FILE):
        return {}
    with open(CATEGORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

categories_data = load_categories()

# 3. 시스템 프롬프트 정의
SYSTEM_PROMPT = f"""
당신은 반려동물 쇼핑 및 지식 상담 서비스의 지능형 분류기입니다.
사용자의 입력을 분석하여 지정된 형식의 JSON으로 반환하세요.

### 고도화 규칙 ###
- "A 중에서 B인 거 있어?" 형태의 질문은 100% [recommend]입니다. 
  예: "사료 중에서 연어 없는 거 있어?", "모래 중에서 먼지 안 나는 거 있어?"
- 특정 상품의 '존재 여부'를 묻는 것은 구매 의사가 있는 것으로 간주합니다.

### 분류 규칙:
    ## 분류 가이드라인
    1. 사용자가 특정 증상(소화불량, 눈물 등)을 언급하며 '무엇이 좋은지' 혹은 '상품'을 찾는다면 이는 쇼핑 의도가 있는 것이므로 [recommend]로 분류합니다.
    2. 반면, 증상의 이유나 대처법 등 '정보' 자체를 묻는다면 [domain_qa]로 분류합니다.

1. **intents**: 다음 중 하나 이상을 선택 (리스트 형식)
   - `recommend`: 상품 추천 요청
   - `domain_qa`: 전문적인 지식 질문 (건강, 사료 성분 등)
   - `small_talk`: 일상적인 대화나 인사
   - `unclear`: 의도가 불분명할 때

    ### Few-shot Examples ###
    Input: "안녕 반가워" -> Output: ["small_talk"]
    Input: "캣잎이 뭐야?" -> Output: ["domain_qa"] (반려동물 용어 설명이므로)
    Input: "강아지가 사료를 안 먹어" -> Output: ["domain_qa"] (상담 및 지식 요청이므로)
    Input: "오늘 날씨 어때?" -> Output: ["small_talk"]
    Input: "간식 좀 골라줄래?" -> Output: ["recommend"]

    ### 의도 분류 예시 ###
    입력: "강아지가 소화불량인 것 같아 왜 그럴까?" -> 출력: domain_qa (원인 파악)
    입력: "눈물 자국은 왜 생기는 거야?" -> 출력: domain_qa (지식 탐색)
    입력: "소화불량일 때 먹이기 좋은 사료나 간식 있어?" -> 출력: recommend (구매 목적)
    입력: "눈물 자국이 심한데 어떤 사료가 좋아?" -> 출력: recommend (해결책 검색)
    입력: "소화가 잘되는 사료는 뭐야?" -> 출력: recommend (구매 목적)

2. **domain_qa 서브 분류** (intents에 `domain_qa`가 포함된 경우에만 해당, 아니면 null):
   - `health_disease`: 질병 및 건강 관련
   - `care_management`: 일상 관리 및 케어
   - `nutrition_diet`: 영양 및 식단
   - `behavior_psychology`: 행동 및 심리
   - `travel`: 여행 및 외출

3. **category & subcategory**:
   - 아래 제공되는 카테고리 데이터를 기반으로 분류하세요.
   - `pet_type`이 `강아지`인 경우: {list(categories_data.get("강아지", {}).keys())}
   - `pet_type`이 `고양이`인 경우: {list(categories_data.get("고양이", {}).keys())}
   - 각 카테고리에 속하는 `subcategories` 목록에서 가장 적절한 것을 선택하세요.
   - **중요**: 사용자가 "사료", "간식" 등 대분류 이름만 말한 경우에도 이를 `category`에 정확히 매핑하세요.

4. **pet_type**:
   - `강아지`, `고양이` 중 하나. 
   - 사용자가 "냥이", "댕댕이", "개", "고양이" 등 종을 나타내는 단어를 사용하면 즉시 해당 종으로 분류하세요.
   - 만약 "subcategory"의 값이 특정 종(예: 고양이 모래 -> 고양이)에만 해당한다면 이를 바탕으로 종을 추론할 수 있습니다.
   - **중요**: 입력 및 기존 맥락에서 종을 도저히 특정할 수 없는 경우에만 `null`을 반환하세요.

### Few-shot Examples (Multi-turn) ###
- Context: (비어있음) / Input: "사료 추천해줘" 
  -> {{"intents": ["recommend"], "pet_type": null, "category": "사료"}}
- Context: (pet_type 보완 중) / Input: "냥이용" 
  -> {{"intents": ["recommend"], "pet_type": "고양이"}}
- Context: (category 보완 중) / Input: "간식" 
  -> {{"intents": ["recommend"], "category": "간식"}}

5. **detected_aspect**: 다음 중 해당되는 것들을 리스트로 추출 (해당 없으면 null)
   - `기호성`, `생체반응`, `소화/배변`, `제품 성상`, `성분/원료`, `냄새`, `가격/구매`, `배송/포장`

6. **budget**:
   - 사용자가 명시한 금액이 있다면 추출 (예: "2만원대" -> "20000", "5000원 이하" -> "5000").
   - 금액 언급이 없으면 null.

### 카테고리 데이터:
{json.dumps(categories_data, ensure_ascii=False, indent=2)}

### 출력 형식 (JSON):
{{
  "intents": ["recommend"],
  "domain_qa_sub": null,
  "category": "사료",
  "subcategory": "습식사료",
  "pet_type": "강아지",
  "detected_aspect": ["기호성"],
  "budget": "20000"
}}

반드시 JSON 형식으로만 답변하세요.
"""

# --- [NEW] 세션 상태 관리 (LangGraph State 역할) ---
session_state = {
    "current_extraction": None,
    "waiting_for": None  # 'pet_type', 'category' 등
}

def analyze_intent(user_input):
    # 만약 특정 정보를 기다리는 중이라면, 현재 대화의 맥락(기존 추출 결과)을 프롬프트에 추가
    context_prompt = ""
    if session_state["current_extraction"]:
        context_prompt = f"\n기존 추출 정보: {json.dumps(session_state['current_extraction'], ensure_ascii=False)}"
        if session_state["waiting_for"]:
            context_prompt += f"\n현재 '{session_state['waiting_for']}' 정보를 보완하는 중입니다."

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + context_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

def process_node(result):
    """LangGraph의 노드 로직: 추출 결과를 검증하고 다음 행동을 결정"""
    intents = result.get("intents") or []
    intent = intents[0] if intents else "unclear"
    
    # [1] recommend 의도 처리
    if intent == "recommend":
        # pet_type 확인
        if not result.get("pet_type"):
            session_state["waiting_for"] = "pet_type"
            session_state["current_extraction"] = result
            return "챗봇: 어떤 반려동물 제품을 찾으시나요? (강아지용인가요? 고양이용인가요?)"
        
        # category 확인
        if not result.get("category"):
            session_state["waiting_for"] = "category"
            session_state["current_extraction"] = result
            pet_type = result.get("pet_type")
            avail_cats = ", ".join(categories_data.get(pet_type, {}).keys())
            return f"챗봇: {pet_type}를 위한 어떤 카테고리의 제품을 추천해 드릴까요? ({avail_cats} 등)"
        
        # 정보가 모두 있으면 완료
        session_state["waiting_for"] = None
        session_state["current_extraction"] = None
        return f"챗봇: {result.get('pet_type')}용 {result.get('category')} 카테고리에서 좋은 상품을 찾아드릴게요!"

    # [2] unclear 의도 처리
    elif intent == "unclear":
        session_state["waiting_for"] = None
        session_state["current_extraction"] = None
        return "챗봇: 죄송합니다, 말씀하신 내용을 잘 이해하지 못했어요. 상품 추천이나 반려동물 건강 관련 질문이 있으신가요? 어떤 도움이 필요하신지 구체적으로 말씀해 주세요."

    # 기타 의도 (domain_qa, small_talk 등)
    session_state["waiting_for"] = None
    session_state["current_extraction"] = None
    return f"챗봇: 분석 결과 ({intent})에 맞는 답변을 준비 중입니다."

def main():
    print(f"[{LLM_MODEL}] LangGraph 스타일 상태 관리 테스트 (종료: q)")
    while True:
        user_input = input("\n사용자: ").strip()
        if user_input.lower() == 'q':
            break
        if not user_input:
            continue
            
        # 1. 추출 노드 (기존 정보가 있으면 병합 고려)
        raw_result = analyze_intent(user_input)
        
        # [수정] 지능형 병합 로직
        if session_state["current_extraction"]:
            result = session_state["current_extraction"].copy()
            # 새로운 결과에서 의미 있는 값들을 기존 정보에 업데이트
            for key, value in raw_result.items():
                # 'small_talk'나 'unclear'로 의도가 바뀌더라도, 이전 'recommend' 등의 기능적 의도를 유지할지 결정
                # (단, 사용자가 완전히 새로운 요청을 하는 경우는 제외)
                if key == "intents":
                    # 신규 의도가 더 구체적이거나(recommend, domain_qa), 기존 의도가 이미 있다면 유지
                    new_intents = value or []
                    if any(i in ["recommend", "domain_qa"] for i in new_intents):
                        result["intents"] = new_intents
                    # 기존 의도가 이미 recommend/domain_qa라면 굳이 small_talk로 덮어쓰지 않음
                elif value and value != "None":
                    result[key] = value
        else:
            result = raw_result

        # 출력용 데이터 정제
        formatted_result = {
            "intents": result.get("intents"),
            "category": result.get("category"),
            "subcategory": result.get("subcategory"),
            "pet_type": result.get("pet_type"),
            "detected_aspect": result.get("detected_aspect"),
            "budget": result.get("budget")
        }
        
        if "domain_qa" in (result.get("intents") or []):
            formatted_result["domain_qa_sub"] = result.get("domain_qa_sub")

        # 의도 우선순위 적용 (Strict Hierarchy)
        intents = formatted_result.get("intents") or []
        if isinstance(intents, list) and intents:
            priority_order = ["recommend", "domain_qa", "small_talk", "unclear"]
            highest_intent = None
            for p in priority_order:
                if p in intents:
                    highest_intent = p
                    break
            if highest_intent:
                formatted_result["intents"] = [highest_intent]

        print("\n[현재 분석 상태]")
        print(json.dumps(formatted_result, ensure_ascii=False, indent=2))

        # 2. 로직 처리 노드 (다음 대화 결정)
        response_msg = process_node(formatted_result)
        print(f"\n{response_msg}")

if __name__ == "__main__":
    main()
