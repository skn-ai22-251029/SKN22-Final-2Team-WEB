"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import FullScreenFrame from "../../../components/FullScreenFrame";

type PetType = "dog" | "cat";
type Sex = "male" | "female";
type Neutered = "yes" | "no" | null;

const petTypeMap: Record<PetType, { label: string; emoji: string; placeholder: string }> = {
  dog: { label: "강아지 1", emoji: "🐶", placeholder: "품종을 검색해주세요 (예: 말티즈)" },
  cat: { label: "고양이 1", emoji: "🐱", placeholder: "품종을 검색해주세요 (예: 코리안숏헤어)" },
};

function DetailsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialType = searchParams.get("type") === "cat" ? "cat" : "dog";

  const [petType, setPetType] = useState<PetType>(initialType);
  const [name, setName] = useState("");
  const [breed, setBreed] = useState("");
  const [sex, setSex] = useState<Sex>("male");
  const [years, setYears] = useState("0");
  const [months, setMonths] = useState("0");
  const [weight, setWeight] = useState("");
  const [neutered, setNeutered] = useState<Neutered>(null);

  const isNextEnabled = useMemo(() => name.trim() && years.trim() && months.trim(), [months, name, years]);

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
          <div className="h-[5px] w-[384px] rounded-full bg-[#3182ce]" />

          <div className="mt-6 text-[14px] font-bold text-[#3182ce]">STEP 2 / 3</div>
          <h1 className="mt-2 text-[28px] font-bold leading-[1.3] text-[#2d3748]">아이들의 기본 정보를 알려주세요</h1>
          <p className="mt-3 text-[16px] text-[#718096]">정확한 맞춤형 케어를 위해 빈칸을 채워주세요.</p>

          <div className="mt-6 flex border-b border-[#e2e8f0]">
            {(["dog", "cat"] as PetType[]).map((type) => {
              const active = petType === type;
              const item = petTypeMap[type];

              return (
                <button
                  key={type}
                  type="button"
                  onClick={() => setPetType(type)}
                  className={`relative flex h-[44px] min-w-[120px] items-center justify-center gap-2 text-[16px] font-bold transition-colors ${
                    active ? "text-[#3182ce]" : "text-[#a0aec0] hover:text-[#4a5568]"
                  }`}
                >
                  <span>{item.emoji}</span>
                  <span>{item.label}</span>
                  <span
                    className={`absolute bottom-[-1px] left-0 h-[3px] w-full rounded-full bg-[#3182ce] transition-opacity ${
                      active ? "opacity-100" : "opacity-0"
                    }`}
                  />
                </button>
              );
            })}
          </div>

          <div className="mt-8 grid grid-cols-2 gap-x-7 gap-y-5">
            <div>
              <label className="text-[14px] font-bold text-[#4a5568]">
                이름 <span className="text-[#e53e3e]">(필수)</span>
              </label>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="반려동물의 이름을 입력해주세요"
                className="mt-2 h-[40px] w-full rounded-[8px] border border-[#e2e8f0] px-3 text-[14px] text-[#2d3748] outline-none transition-colors placeholder:text-[#a0aec0] focus:border-[#90cdf4]"
              />
            </div>

            <div>
              <label className="text-[14px] font-bold text-[#4a5568]">
                품종 <span className="text-[#a0aec0]">(선택)</span>
              </label>
              <input
                value={breed}
                onChange={(event) => setBreed(event.target.value)}
                placeholder={petTypeMap[petType].placeholder}
                className="mt-2 h-[40px] w-full rounded-[8px] border border-[#e2e8f0] px-3 text-[14px] text-[#2d3748] outline-none transition-colors placeholder:text-[#a0aec0] focus:border-[#90cdf4]"
              />
            </div>

            <div>
              <div className="text-[14px] font-bold text-[#4a5568]">
                성별 <span className="text-[#e53e3e]">(필수)</span>
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => setSex("male")}
                  className={`flex h-[40px] flex-1 items-center justify-center rounded-[8px] border text-[14px] font-bold transition-colors ${
                    sex === "male" ? "border-[#3182ce] bg-[#ebf8ff] text-[#3182ce]" : "border-[#e2e8f0] bg-white text-[#4a5568]"
                  }`}
                >
                  수컷 (남아)
                </button>
                <button
                  type="button"
                  onClick={() => setSex("female")}
                  className={`flex h-[40px] flex-1 items-center justify-center rounded-[8px] border text-[14px] font-bold transition-colors ${
                    sex === "female" ? "border-[#3182ce] bg-[#ebf8ff] text-[#3182ce]" : "border-[#e2e8f0] bg-white text-[#4a5568]"
                  }`}
                >
                  암컷 (여아)
                </button>
              </div>
            </div>

            <div>
              <div className="text-[14px] font-bold text-[#4a5568]">
                나이 <span className="text-[#e53e3e]">(필수, 월령 포함)</span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <input
                  value={years}
                  onChange={(event) => setYears(event.target.value.replace(/[^0-9]/g, ""))}
                  className="h-[40px] w-[90px] rounded-[8px] border border-[#e2e8f0] px-3 text-center text-[14px] text-[#2d3748] outline-none transition-colors placeholder:text-[#a0aec0] focus:border-[#90cdf4]"
                />
                <span className="text-[14px] text-[#4a5568]">년</span>
                <input
                  value={months}
                  onChange={(event) => setMonths(event.target.value.replace(/[^0-9]/g, ""))}
                  className="h-[40px] w-[86px] rounded-[8px] border border-[#e2e8f0] px-3 text-center text-[14px] text-[#2d3748] outline-none transition-colors placeholder:text-[#a0aec0] focus:border-[#90cdf4]"
                />
                <span className="text-[14px] text-[#4a5568]">개월</span>
              </div>
            </div>

            <div>
              <label className="text-[14px] font-bold text-[#4a5568]">
                체중 <span className="text-[#a0aec0]">(선택)</span>
              </label>
              <div className="relative mt-2">
                <input
                  value={weight}
                  onChange={(event) => setWeight(event.target.value.replace(/[^0-9.]/g, ""))}
                  placeholder="체중 입력"
                  className="h-[40px] w-full rounded-[8px] border border-[#e2e8f0] px-3 pr-10 text-[14px] text-[#2d3748] outline-none transition-colors placeholder:text-[#a0aec0] focus:border-[#90cdf4]"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[14px] text-[#4a5568]">kg</span>
              </div>
            </div>

            <div>
              <div className="text-[14px] font-bold text-[#4a5568]">
                중성화 여부 <span className="text-[#a0aec0]">(선택)</span>
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => setNeutered("yes")}
                  className={`flex h-[40px] flex-1 items-center justify-center rounded-[8px] border text-[14px] font-bold transition-colors ${
                    neutered === "yes" ? "border-[#3182ce] bg-[#ebf8ff] text-[#3182ce]" : "border-[#e2e8f0] bg-white text-[#4a5568]"
                  }`}
                >
                  예
                </button>
                <button
                  type="button"
                  onClick={() => setNeutered("no")}
                  className={`flex h-[40px] flex-1 items-center justify-center rounded-[8px] border text-[14px] font-bold transition-colors ${
                    neutered === "no" ? "border-[#3182ce] bg-[#ebf8ff] text-[#3182ce]" : "border-[#e2e8f0] bg-white text-[#4a5568]"
                  }`}
                >
                  아니오
                </button>
              </div>
            </div>
          </div>

          <div className="mt-40 flex gap-4">
            <button
              type="button"
              onClick={() => router.push("/pets/add")}
              className="flex h-[48px] w-[130px] items-center justify-center rounded-[10px] bg-[#edf2f7] text-[16px] font-bold text-[#4a5568] transition-colors hover:bg-[#e2e8f0]"
            >
              이전으로
            </button>
            <button
              type="button"
              disabled={!isNextEnabled}
              onClick={() => router.push("/pets")}
              className={`flex h-[48px] flex-1 items-center justify-center rounded-[10px] text-[16px] font-bold transition-colors ${
                isNextEnabled ? "bg-[#3182ce] text-white hover:bg-[#2b6cb0]" : "bg-[#cbd5e0] text-white"
              }`}
            >
              다음 단계로 (건강/식이 입력)
            </button>
          </div>
        </div>
      </div>
    </FullScreenFrame>
  );
}

export default function AddPetDetailsPage() {
  return (
    <Suspense fallback={null}>
      <DetailsContent />
    </Suspense>
  );
}
