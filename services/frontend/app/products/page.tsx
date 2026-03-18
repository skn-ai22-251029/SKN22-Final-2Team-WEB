"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import FullScreenFrame from "../components/FullScreenFrame";

type ProductPreference = "like" | "dislike" | null;

type ProductItem = {
  id: string;
  name: string;
  category: string;
  preference: ProductPreference;
};

const initialProducts: ProductItem[] = [
  {
    id: "royal-canin-mini-indoor-adult",
    name: "로얄캐닌 미니 인도어 어덜트",
    category: "건식 사료",
    preference: "like",
  },
  {
    id: "ciao-churu-tuna",
    name: "이나바 챠오츄르 참치맛",
    category: "습식 간식",
    preference: "dislike",
  },
  {
    id: "natural-balance-salmon",
    name: "내추럴발란스 연어 포뮬라",
    category: "건식 사료",
    preference: null,
  },
  {
    id: "orijen-original",
    name: "오리젠 오리지널",
    category: "건식 사료",
    preference: null,
  },
  {
    id: "wellness-kitten-pouch",
    name: "웰니스 키튼 파우치",
    category: "습식 사료",
    preference: null,
  },
];

function PreferenceChip({
  active,
  tone,
  children,
  onClick,
}: {
  active: boolean;
  tone: "like" | "dislike";
  children: React.ReactNode;
  onClick: () => void;
}) {
  const activeClasses =
    tone === "like"
      ? "border-[#3182ce] bg-[#ebf8ff] text-[#3182ce]"
      : "border-[#ef4444] bg-[#fff5f5] text-[#ef4444]";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex h-[28px] min-w-[58px] items-center justify-center rounded-full border px-[12px] text-[13px] font-bold transition-colors ${
        active ? activeClasses : "border-[#e2e8f0] bg-white text-[#a0aec0]"
      }`}
    >
      {children}
    </button>
  );
}

export default function ProductsPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<ProductItem[]>(initialProducts);
  const filteredProducts = useMemo(() => products, [products]);

  const updatePreference = (id: string, preference: ProductPreference) => {
    setProducts((current) =>
      current.map((product) =>
        product.id === id
          ? {
              ...product,
              preference: product.preference === preference ? null : preference,
            }
          : product,
      ),
    );
  };

  const removeProduct = (id: string) => {
    setProducts((current) => current.filter((product) => product.id !== id));
  };

  return (
    <FullScreenFrame innerClassName="overflow-hidden">
      <div className="flex h-screen w-full items-center justify-center px-4 py-8">
        <div className="w-full max-w-[860px] rounded-[20px] border border-[#dbe7f5] bg-white px-10 py-8 shadow-[0_6px_20px_rgba(45,55,72,0.04)]">
          <h1 className="text-[24px] font-bold text-[#2d3748]">구매 상품 등록</h1>
          <p className="mt-2 text-[14px] text-[#718096]">
            현재 사용 중이거나 경험해 본 상품을 등록하고 선호/기피 여부를 설정해 주세요.
          </p>

          <div className="mt-6 h-px w-full bg-[#edf2f7]" />

          <div className="mt-6 flex gap-3">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="h-[40px] flex-1 rounded-[8px] border border-[#e2e8f0] px-4 text-[14px] outline-none placeholder:text-[#a0aec0]"
              placeholder="상품명 또는 브랜드를 검색하세요 (추후 전체 상품 목록과 연결 예정)"
            />
            <button
              type="button"
              className="h-[40px] rounded-[8px] bg-[#3182ce] px-5 text-[14px] font-bold text-white"
            >
              검색 및 추가
            </button>
          </div>
          <p className="mt-2 text-[12px] text-[#a0aec0]">
            현재는 검색 UI만 준비된 상태이며, 추후 전체 상품 목록 데이터와 연결될 예정입니다.
          </p>

          <div className="mt-6 text-[16px] font-bold text-[#4a5568]">등록된 상품 리스트</div>

          <div className="mt-3 rounded-[12px] border border-[#e2e8f0] bg-[#fbfdff]">
            <div className="max-h-[270px] overflow-y-auto px-4 py-3">
              <div className="space-y-2">
                {filteredProducts.length === 0 ? (
                  <div className="flex h-[120px] items-center justify-center text-[14px] text-[#a0aec0]">
                    등록된 상품이 없습니다.
                  </div>
                ) : (
                  filteredProducts.map((product) => (
                    <div
                      key={product.id}
                      className="flex min-h-[56px] items-center gap-4 rounded-[10px] border border-[#edf2f7] bg-white px-3 py-2"
                    >
                      <div className="flex h-[40px] w-[40px] items-center justify-center rounded-[6px] bg-[#edf2f7] text-[10px] text-[#a0aec0]">
                        사진
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-[16px] font-bold text-[#2d3748]">{product.name}</div>
                        <div className="mt-1 text-[12px] text-[#718096]">{product.category}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <PreferenceChip
                          active={product.preference === "like"}
                          tone="like"
                          onClick={() => updatePreference(product.id, "like")}
                        >
                          👍 선호
                        </PreferenceChip>
                        <PreferenceChip
                          active={product.preference === "dislike"}
                          tone="dislike"
                          onClick={() => updatePreference(product.id, "dislike")}
                        >
                          👎 기피
                        </PreferenceChip>
                        <button
                          type="button"
                          onClick={() => removeProduct(product.id)}
                          className="px-2 text-[13px] text-[#a0aec0] underline underline-offset-2"
                        >
                          삭제
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <button
            type="button"
            className="mt-8 flex h-[48px] w-full items-center justify-center rounded-[8px] bg-[#3182ce] text-[16px] font-bold text-white"
            onClick={() => router.push("/profile")}
          >
            설정 완료
          </button>
        </div>
      </div>
    </FullScreenFrame>
  );
}
