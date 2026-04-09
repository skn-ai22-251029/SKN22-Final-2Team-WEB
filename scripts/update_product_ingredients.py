import json
import os
import psycopg2
from psycopg2.extras import execute_values
from decouple import Config, RepositoryEnv

def update_product_ingredients():
    # .env 파일에서 설정 로드
    env_path = os.path.join(os.path.dirname(__file__), '../services/django/.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(__file__), '../deploy/local/.env')
    
    config = Config(RepositoryEnv(env_path))
    
    db_params = {
        "dbname": config("POSTGRES_DB"),
        "user": config("POSTGRES_USER"),
        "password": config("POSTGRES_PASSWORD"),
        "host": config("POSTGRES_HOST", default="localhost"),
        "port": config("POSTGRES_PORT", default="5432"),
    }
    
    jsonl_path = os.path.join(os.path.dirname(__file__), '../output_gold/gold/ingredients/20260325_ingredients.jsonl')
    
    print(f"Loading data from {jsonl_path}...")
    
    update_data = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            # main_ingredients (list)와 nutrition_info (dict)를 JSON 문자열로 변환하여 준비
            update_data.append((
                json.dumps(item.get("main_ingredients", [])),
                json.dumps(item.get("nutrition_info", {})),
                item.get("goods_id")
            ))
            
    if not update_data:
        print("No data found to update.")
        return

    print(f"Updating {len(update_data)} products in database...")
    
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()
        
        # 임시 테이블을 사용하거나 개별 업데이트 수행
        # 대량 업데이트를 위해 executemany 사용
        sql = """
            UPDATE product 
            SET main_ingredients = %s::jsonb, 
                nutrition_info = %s::jsonb 
            WHERE goods_id = %s
        """
        
        cur.executemany(sql, update_data)
        
        conn.commit()
        print(f"Successfully updated {cur.rowcount} rows.")
        
    except Exception as e:
        print(f"Error during update: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    update_product_ingredients()
