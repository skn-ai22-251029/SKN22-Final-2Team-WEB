"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import FullScreenFrame from "../components/FullScreenFrame";

const imgGoogle = "https://www.figma.com/api/mcp/asset/e3eff93a-1607-4896-8a57-8b1125091b0a";
const imgNaver = "https://www.figma.com/api/mcp/asset/7a5a2941-cee1-4c91-a571-7ad9b01bcfc6";
const imgKakao = "https://www.figma.com/api/mcp/asset/527049c9-ee7f-443c-a0c6-0e70f4b905e3";

export default function ProfilePage() {
  const [marketing, setMarketing] = useState(true);
  const [isWithdrawModalOpen, setIsWithdrawModalOpen] = useState(false);
  const router = useRouter();

  return (
    <FullScreenFrame innerClassName="h-auto min-h-screen overflow-y-auto">
      <div className="relative w-full px-4 py-10">
        {isWithdrawModalOpen && (
          <div
            className="absolute inset-0 z-[60] flex items-center justify-center bg-black/10"
            onClick={() => setIsWithdrawModalOpen(false)}
          >
            <div
              className="relative h-[279px] w-[399px] rounded-[20px] border border-[#dbe7f5] bg-white shadow-[0_14px_36px_rgba(45,55,72,0.10)]"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="absolute left-1/2 top-[27px] flex h-[81px] w-[81px] -translate-x-1/2 items-center justify-center rounded-full border-[4px] border-[#ef4444]">
                <span className="relative top-[-1px] text-[48px] font-bold leading-none text-[#ef4444]">!</span>
              </div>
              <p className="absolute left-1/2 top-[127px] -translate-x-1/2 whitespace-nowrap text-center text-[19px] font-bold leading-none text-[#2d3748]">
                정말 탈퇴하시겠습니까?
              </p>
              <p className="absolute left-1/2 top-[171px] -translate-x-1/2 whitespace-nowrap text-center text-[14px] leading-none text-[#718096]">
                모든 사용자 데이터가 영구적으로 삭제됩니다
              </p>
              <div className="absolute bottom-[24px] left-[40px] right-[40px] flex h-[42px] items-center justify-between">
                <button
                  type="button"
                  className="flex h-full w-[150px] items-center justify-center rounded-[8px] bg-[#edf2f7] text-[14px] font-bold text-[#4a5568]"
                  onClick={() => setIsWithdrawModalOpen(false)}
                >
                  취소
                </button>
                <button
                  type="button"
                  className="flex h-full w-[150px] items-center justify-center rounded-[8px] bg-[#ef4444] text-[14px] font-bold text-white"
                  onClick={() => {
                    if (typeof window !== "undefined") {
                      window.localStorage.removeItem("tt_logged_in");
                    }
                    setIsWithdrawModalOpen(false);
                    router.push("/");
                  }}
                >
                  탈퇴하기
                </button>
              </div>
            </div>
          </div>
        )}

        <Link
          href="/member"
          className="absolute left-8 top-8 text-[26px] font-bold leading-none text-[#2d3748]"
          aria-label="메인으로 이동"
        >
          <span className="text-[#3182ce]">Tail</span>
          <span>Talk</span>
        </Link>
        <div className="mx-auto w-full max-w-[860px] rounded-[20px] border border-[#e2e8f0] bg-white">
          <div className="px-8 pt-6 pb-4 text-[24px] font-bold text-[#2d3748]">설정</div>
          <div className="h-px w-full bg-[#e2e8f0]" />

          <div className="px-8 py-6">
            <div className="text-[18px] font-bold text-[#2d3748]">1. 프로필 관리</div>

            <div className="mt-6 flex flex-col items-center">
              <div className="relative flex h-[72px] w-[72px] items-center justify-center rounded-full bg-[#cbd5e0] text-[12px] text-[#4a5568]">
                IMG
                <div className="absolute -right-1 -bottom-1 flex h-5 w-5 items-center justify-center rounded-full bg-[#3182ce] text-white">
                  +
                </div>
              </div>
              <div className="mt-3 text-[12px] text-[#718096]">클릭하여 이미지 업로드</div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <div className="mb-2 text-[14px] font-bold text-[#4a5568]">닉네임</div>
                <div className="flex gap-3">
                  <input
                    className="h-[36px] flex-1 rounded-[8px] border border-[#e2e8f0] px-3 text-[14px]"
                    defaultValue="김반려"
                  />
                  <button className="h-[36px] w-[90px] rounded-[8px] border border-[#3182ce] text-[14px] font-bold text-[#3182ce]">
                    중복확인
                  </button>
                </div>
              </div>
              <div>
                <div className="mb-2 text-[14px] font-bold text-[#4a5568]">연락처</div>
                <div className="flex gap-3">
                  <input
                    className="h-[36px] flex-1 rounded-[8px] border border-[#e2e8f0] px-3 text-[12px] text-[#718096]"
                    placeholder="- 없이 숫자만 입력해주세요"
                  />
                  <button className="h-[36px] w-[90px] rounded-[8px] border border-[#3182ce] text-[14px] font-bold text-[#3182ce]">
                    인증요청
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <div className="mb-2 text-[14px] font-bold text-[#4a5568]">배송지 정보</div>
              <div className="flex gap-3">
                <input className="h-[36px] w-[140px] rounded-[8px] border border-[#e2e8f0] px-3 text-[14px]" placeholder="우편번호" />
                <button className="h-[36px] w-[120px] rounded-[8px] border border-[#3182ce] text-[14px] font-bold text-[#3182ce]">
                  우편번호 찾기
                </button>
              </div>
              <input className="mt-3 h-[36px] w-full rounded-[8px] border border-[#e2e8f0] px-3 text-[14px]" placeholder="주소" />
              <input
                className="mt-3 h-[36px] w-full rounded-[8px] border border-[#e2e8f0] px-3 text-[14px]"
                placeholder="상세주소"
              />
            </div>

            <div className="mt-6">
              <div>
                <div className="mb-2 text-[14px] font-bold text-[#4a5568]">알림 설정</div>
                <div className="flex items-center gap-3 rounded-[10px] border border-[#e2e8f0] px-3 py-2">
                  <span className="text-[14px] text-[#718096]">마케팅 푸시/이메일 수신 동의</span>
                  <button
                    type="button"
                    onClick={() => setMarketing((prev) => !prev)}
                    className={`ml-auto h-[20px] w-[36px] rounded-full p-[2px] transition ${
                      marketing ? "bg-[#3182ce]" : "bg-[#cbd5e0]"
                    }`}
                    aria-pressed={marketing}
                  >
                    <span
                      className={`block h-[16px] w-[16px] rounded-full bg-white transition ${
                        marketing ? "translate-x-[16px]" : "translate-x-0"
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-8 h-px w-full bg-[#e2e8f0]" />

            <div className="mt-6 text-[18px] font-bold text-[#2d3748]">2. 계정 관리</div>
            <div className="mt-4 rounded-[14px] border border-[#e2e8f0] bg-[#f7fafc] p-4">
              <div className="flex items-center gap-3">
                <img alt="Kakao" className="h-8 w-8" src={imgKakao} />
                <div className="flex-1">
                  <div className="text-[14px] font-bold text-[#2d3748]">Kakao 계정 연동 중</div>
                  <div className="text-[12px] text-[#718096]">abc1234@example.com</div>
                </div>
                <button className="text-[12px] font-bold text-[#e53e3e]">연동 해제</button>
              </div>
              <div className="my-4 h-px w-full bg-[#e2e8f0]" />
              <div className="flex items-center gap-3">
                <img alt="Naver" className="h-8 w-8" src={imgNaver} />
                <div className="flex-1">
                  <div className="text-[14px] font-bold text-[#2d3748]">NAVER 계정 연동하기</div>
                </div>
              </div>
              <div className="my-4 h-px w-full bg-[#e2e8f0]" />
              <div className="flex items-center gap-3">
                <img alt="Google" className="h-8 w-8" src={imgGoogle} />
                <div className="flex-1">
                  <div className="text-[14px] font-bold text-[#2d3748]">Google 계정 연동 중</div>
                  <div className="text-[12px] text-[#718096]">abc1234@example.com</div>
                </div>
                <button className="text-[12px] font-bold text-[#e53e3e]">연동 해제</button>
              </div>
            </div>

            <div className="mt-6 flex flex-col gap-3 md:flex-row">
              <Link
                href="/signup"
                className="flex h-[44px] flex-1 items-center justify-center rounded-[10px] bg-[#edf2f7] text-[16px] font-bold text-[#4a5568]"
              >
                취소
              </Link>
              <button
                type="button"
                className="flex h-[44px] flex-1 items-center justify-center rounded-[10px] bg-[#3182ce] text-[16px] font-bold text-white"
                onClick={() => {
                  if (typeof window !== "undefined") {
                    window.localStorage.setItem("tt_logged_in", "1");
                  }
                  router.push("/member");
                }}
              >
                변경사항 저장
              </button>
            </div>

            <button
              type="button"
              className="mt-4 text-[13px] font-bold text-[#c53030]"
              onClick={() => setIsWithdrawModalOpen(true)}
            >
              회원 탈퇴
            </button>
          </div>
        </div>
      </div>
    </FullScreenFrame>
  );
}
