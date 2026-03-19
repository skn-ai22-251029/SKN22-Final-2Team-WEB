import os
import json
import sys
import importlib.util
from tqdm import tqdm

# 카테고리 테스트 모듈 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_PATH = os.path.join(BASE_DIR, "category_test_v0.1.py")
MODULE_NAME = "category_test_v01"
DATA_PATH = os.path.join(BASE_DIR, "data", "test.json")

# 모듈 동적 로드 (파일명에 점이 포함되어 있어 직접 임포트가 까다로움)
spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)

from category_test_v01 import analyze_intent

def run_evaluation():
    # 데이터 로드
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} 파일을 찾을 수 없습니다.")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    print(f"총 {len(test_data)}개의 테스트 케이스를 시작합니다.\n")

    results = []
    correct_count = 0

    # 랩핑 함수: 메인 스크립트의 우선순위 로직을 동일하게 적용
    def get_final_intent(user_input):
        raw_res = analyze_intent(user_input)
        intents = raw_res.get("intents") or []
        
        if isinstance(intents, list) and intents:
            priority_order = ["recommend", "domain_qa", "small_talk", "unclear"]
            highest_intent = None
            for p in priority_order:
                if p in intents:
                    highest_intent = p
                    break
            return highest_intent if highest_intent else intents[0]
        return "unclear"

    # 평가 루프
    for i, item in enumerate(tqdm(test_data, desc="Evaluating")):
        input_text = item["input"]
        ground_truth = item["output"]
        
        # JSON의 'smalltalk'을 코드의 'small_talk'로 매핑
        if ground_truth == "smalltalk":
            ground_truth = "small_talk"
            
        prediction = get_final_intent(input_text)
        
        is_correct = (prediction == ground_truth)
        if is_correct:
            correct_count += 1
            
        results.append({
            "input": input_text,
            "ground_truth": ground_truth,
            "prediction": prediction,
            "is_correct": is_correct
        })
        
        if (i + 1) % 5 == 0:
            print(f"진행 상황: {i + 1}/{len(test_data)} 완료 (현재 정확도: {(correct_count/(i+1)*100):.2f}%)")
            sys.stdout.flush()

    # 지표 계산
    accuracy = (correct_count / len(test_data)) * 100

    # 결과 리포트 출력
    print("\n" + "="*50)
    print("평가 결과 리포트")
    print("="*50)
    print(f"전체 테스트 케이스: {len(test_data)}")
    print(f"정답 개수: {correct_count}")
    print(f"정확도 (Accuracy): {accuracy:.2f}%")
    print("="*50)

    # 틀린 케이스 상세 출력 (최대 20개)
    failures = [r for r in results if not r["is_correct"]]
    if failures:
        print(f"\n[실패 사례 요약 (총 {len(failures)}개)]")
        for i, f in enumerate(failures[:20]):
            print(f"{i+1}. 입력: {f['input']}")
            print(f"   정답: {f['ground_truth']} | 예측: {f['prediction']}")
        if len(failures) > 20:
            print("... 이하 생략")
    else:
        print("\n모든 테스트를 통과했습니다! (Accuracy 100%)")

if __name__ == "__main__":
    run_evaluation()
