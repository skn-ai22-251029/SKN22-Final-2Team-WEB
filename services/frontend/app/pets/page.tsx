"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import FullScreenFrame from "../components/FullScreenFrame";

type PetItem = {
  id: string;
  emoji: string;
  name: string;
  type: string;
  detail: string;
};

const pets: PetItem[] = [
  {
    id: "pet-1",
    emoji: "🐶",
    name: "초코",
    type: "강아지",
    detail: "3년 2개월 · 수컷 · 말티즈",
  },
  {
    id: "pet-2",
    emoji: "🐱",
    name: "나비",
    type: "고양이",
    detail: "1년 5개월 · 암컷 · 코리안숏헤어",
  },
];

export default function PetsPage() {
  const router = useRouter();

  return (
    <FullScreenFrame innerClassName="overflow-hidden">
      <div className="relative flex h-screen w-full items-center justify-center px-4 py-8">
        <Link
          href="/member"
          className="absolute left-8 top-8 text-[26px] font-bold leading-none text-[#2d3748]"
          aria-label="메인으로 이동"
        >
          <span className="text-[#3182ce]">Tail</span>
          <span>Talk</span>
        </Link>

        <div className="w-full max-w-[860px] rounded-[20px] border border-[#dbe7f5] bg-white px-10 py-10 shadow-[0_6px_20px_rgba(45,55,72,0.04)]">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h1 className="text-[24px] font-bold text-[#2d3748]">반려동물 정보</h1>
              <p className="mt-2 text-[14px] text-[#718096]">
                등록된 아이들의 정보를 수정하거나, 새로운 아이를 추가할 수 있습니다.
              </p>
            </div>
            <div className="text-[14px] font-bold text-[#3182ce]">등록 현황: 2 / 5마리</div>
          </div>

          <div className="mt-5 h-px w-full bg-[#edf2f7]" />

          <div className="mt-8 space-y-4">
            {pets.map((pet) => (
              <div
                key={pet.id}
                className="flex items-center gap-5 rounded-[14px] border border-[#e2e8f0] bg-white px-4 py-4 shadow-[0_1px_2px_rgba(45,55,72,0.02)]"
              >
                <div className="flex h-[56px] w-[56px] items-center justify-center rounded-full bg-[#edf2f7] text-[24px]">
                  {pet.emoji}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="text-[18px] font-bold text-[#2d3748]">
                    {pet.name} ({pet.type})
                  </div>
                  <div className="mt-1 text-[14px] text-[#718096]">{pet.detail}</div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    className="flex h-[36px] w-[58px] items-center justify-center rounded-[8px] bg-[#edf2f7] text-[14px] font-bold text-[#4a5568] transition-colors hover:bg-[#e2e8f0]"
                  >
                    수정
                  </button>
                  <button
                    type="button"
                    className="flex h-[36px] w-[58px] items-center justify-center rounded-[8px] border border-[#feb2b2] bg-white text-[14px] font-bold text-[#e53e3e] transition-colors hover:bg-[#fff5f5]"
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => router.push("/pets/add")}
            className="mt-4 flex h-[44px] w-full items-center justify-center rounded-[12px] border border-dashed border-[#90cdf4] bg-[#f8fbff] text-[16px] font-bold text-[#3182ce] transition-colors hover:bg-[#eef7ff]"
          >
            + 새로운 반려동물 추가하기
          </button>
        </div>
      </div>
    </FullScreenFrame>
  );
}
