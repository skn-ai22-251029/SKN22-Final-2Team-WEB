"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import FullScreenFrame from "../../components/FullScreenFrame";

type PetKind = "dog" | "cat" | "future";

const petOptions: Array<{
  id: PetKind;
  emoji: string;
  label: string;
}> = [
  { id: "dog", emoji: "🐶", label: "강아지" },
  { id: "cat", emoji: "🐱", label: "고양이" },
  { id: "future", emoji: "🏠", label: "예비 집사" },
];

export default function AddPetPage() {
  const router = useRouter();
  const [selectedKind, setSelectedKind] = useState<PetKind | null>(null);

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

        <div className="w-full max-w-[860px] rounded-[20px] border border-[#dbe7f5] bg-white px-8 py-8 shadow-[0_6px_20px_rgba(45,55,72,0.04)]">
          <div className="h-[5px] w-[160px] rounded-full bg-[#3182ce]" />

          <div className="mt-6 text-[14px] font-bold text-[#3182ce]">STEP 1 / 3</div>
          <h1 className="mt-2 text-[28px] font-bold leading-[1.3] text-[#2d3748]">
            어떤 반려동물과 함께하고 계신가요?
          </h1>
          <p className="mt-3 text-[16px] text-[#718096]">
            원하는 동물을 클릭하여 추가해 주세요. (최대 5마리)
          </p>
          <p className="mt-1 text-[14px] text-[#e53e3e]">※ 필수 입력 단계입니다.</p>

          <div className="mt-8 grid grid-cols-3 gap-5">
            {petOptions.map((option) => {
              const active = selectedKind === option.id;

              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setSelectedKind(option.id)}
                  className={`flex h-[160px] flex-col items-center justify-center rounded-[14px] border transition-all duration-150 ${
                    active
                      ? "border-[#3182ce] bg-[#f7fbff] shadow-[0_0_0_2px_rgba(49,130,206,0.08)]"
                      : "border-[#e2e8f0] bg-white hover:border-[#90cdf4] hover:bg-[#fbfdff]"
                  }`}
                >
                  <div className="flex h-[56px] w-[56px] items-center justify-center rounded-full bg-[#edf2f7] text-[24px]">
                    {option.emoji}
                  </div>
                  <div className="mt-6 text-[18px] font-bold text-[#4a5568]">{option.label}</div>
                </button>
              );
            })}
          </div>

          <button
            type="button"
            disabled={!selectedKind}
            onClick={() => {
              if (!selectedKind || selectedKind === "future") return;
              router.push(`/pets/add/details?type=${selectedKind}`);
            }}
            className={`mt-8 flex h-[48px] w-full items-center justify-center rounded-[10px] text-[16px] font-bold transition-colors ${
              selectedKind && selectedKind !== "future"
                ? "bg-[#3182ce] text-white hover:bg-[#2b6cb0]"
                : "bg-[#cbd5e0] text-white"
            }`}
          >
            다음 단계로 (기본 정보 입력)
          </button>
        </div>
      </div>
    </FullScreenFrame>
  );
}
