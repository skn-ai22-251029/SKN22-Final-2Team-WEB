"use client";

import FullScreenFrame from "./components/FullScreenFrame";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const imgMenuIcon =
  "https://www.figma.com/api/mcp/asset/8aa9f692-3df6-4a17-a9e8-f713d7d1a1ee";
const imgSettingsIcon =
  "https://www.figma.com/api/mcp/asset/4eec41a1-b8c0-4611-9d1a-adc716d51753";
const imgPlusIcon =
  "https://www.figma.com/api/mcp/asset/1ff96a70-7f54-490e-9aaf-e8720798c90e";
const imgMicIcon =
  "https://www.figma.com/api/mcp/asset/01523a82-0f56-457b-9208-3c76dc0b544b";
const imgDrawerBg =
  "https://www.figma.com/api/mcp/asset/ad58345b-5dd6-4c4d-9add-d9ce93ab4236";
const imgDrawerClose =
  "https://www.figma.com/api/mcp/asset/915378dd-f8b9-43fe-9cf7-1933a9312d51";
const imgDrawerSettings =
  "https://www.figma.com/api/mcp/asset/07028074-58d6-4ef3-b1b8-303b3868d92b";
const imgDrawerCta =
  "https://www.figma.com/api/mcp/asset/20591019-64ca-4cd7-a3a1-6fea5ee43fa8";

export default function Page() {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const drawerWidth = 281;
  const collapsedWidth = 68;
  const contentShift = drawerWidth - collapsedWidth;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const isLoggedIn = window.localStorage.getItem("tt_logged_in") === "1";
    if (isLoggedIn) {
      router.replace("/member");
    }
  }, [router]);

  return (
    <FullScreenFrame>
      <div data-name="[FR-MAIN-01] 비회원 사이드바(Hidden)" data-node-id="2021:1107">
        {isSidebarOpen && (
          <button
            className="absolute inset-0 z-[15] cursor-default"
            type="button"
            aria-label="사이드바 닫기"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        <aside
          className="absolute left-0 top-0 z-20 h-full w-[281px] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
          style={{ transform: isSidebarOpen ? "translateX(0px)" : `translateX(-${contentShift}px)` }}
          data-name={isSidebarOpen ? "비회원 사이드바(Open)" : "사이드바(Hidden)"}
          data-node-id={isSidebarOpen ? "2180:4" : "2020:1070"}
        >
          <div className="relative h-full w-full">
            <div
              className={`absolute inset-0 transition-opacity duration-200 ${
                isSidebarOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
              }`}
            >
              <img alt="" className="absolute inset-0 h-full w-full" src={imgDrawerBg} data-node-id="2180:5" />
              <button
                className="absolute right-[15px] top-[31px] h-[16px] w-[24px]"
                type="button"
                onClick={() => setIsSidebarOpen(false)}
                aria-label="사이드바 닫기"
                data-node-id="2180:6"
              >
                <img alt="" className="block h-full w-full" src={imgDrawerClose} />
              </button>
              <Link
                href="/signup"
                className="absolute left-[16px] top-[20px] flex h-[37px] w-[207px] items-center justify-center"
                data-node-id="2180:10"
              >
                <img alt="" className="absolute inset-0 h-full w-full" src={imgDrawerCta} data-node-id="2180:11" />
                <span className="relative text-[16px] font-bold text-white" data-node-id="2180:12">
                  로그인 / 회원가입
                </span>
              </Link>
              <p
                className="absolute left-[29px] top-[72px] text-[12px] text-[#718096]"
                data-node-id="2180:13"
              >
                맞춤형 반려동물 케어와 대화 기록 저장을 위해
              </p>
              <p
                className="absolute left-[85px] top-[87px] text-[12px] text-[#718096]"
                data-node-id="2180:7"
              >
                로그인을 진행해 주세요
              </p>
              <img
                alt="설정"
                className="absolute bottom-[31px] right-[24px] h-[19.1px] w-[18.68px]"
                src={imgDrawerSettings}
                data-node-id="2180:8"
              />
            </div>
            <div
              className={`absolute right-0 top-0 h-full w-[68px] bg-[#edf2f7] will-change-opacity ${
                isSidebarOpen ? "pointer-events-none opacity-0" : "pointer-events-auto opacity-100"
              }`}
              style={{
                transition: isSidebarOpen ? "none" : "opacity 180ms linear",
                visibility: isSidebarOpen ? "hidden" : "visible",
              }}
            >
              <button
                className="absolute left-1/2 top-[31px] h-[16px] w-[24px] -translate-x-1/2"
                type="button"
                onClick={() => setIsSidebarOpen(true)}
                aria-label="사이드바 열기"
                data-node-id="2021:1120"
              >
                <img alt="" className="block h-full w-full" src={imgMenuIcon} />
              </button>
              <img
                alt="설정"
                className="absolute bottom-[28.45px] left-1/2 h-[19.1px] w-[18.68px] -translate-x-1/2"
                src={imgSettingsIcon}
                data-node-id="2021:1151"
              />
            </div>
          </div>
        </aside>

        <div
          className="absolute inset-0 z-10 transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
          style={{ transform: isSidebarOpen ? `translateX(${contentShift}px)` : "translateX(0px)" }}
        >
          <header
            className="absolute left-0 top-0 h-[80px] w-full border-b border-[#e2e8f0] bg-white"
            data-name="[FR-NAV-01] 라이트(비회원)"
            data-node-id="2009:815"
          >
            <div
              className="absolute left-[87.5px] top-1/2 -translate-y-1/2 text-[26px] font-bold leading-none text-[#2d3748]"
              data-node-id="2116:17"
            >
              <span className="text-[#3182ce]">Tail</span>
              <span>Talk</span>
            </div>
          </header>

          <div
            className="absolute left-1/2 text-center transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform"
            style={{
              top: "clamp(240px, 33vh, 320px)",
              width: "min(540px, 90vw)",
              transform: `translateX(-50%) translateX(${collapsedWidth - (isSidebarOpen ? drawerWidth : collapsedWidth) / 2}px)`,
            }}
            data-name="Hero_Section"
            data-node-id="2021:1136"
          >
            <p
              className="whitespace-nowrap text-[32px] font-bold leading-[1.2] text-[#1a202c]"
              data-node-id="2021:1137"
            >
              <span className="text-[#3182ce]">Tail</span>
              <span>Talk 와 함께하는 스마트한 집사 생활 </span>
            </p>
            <p className="mt-[12px] text-[16px] text-[#718096]" data-node-id="2021:1138">
              로그인 후 AI 비서와 대화를 시작하고 다양한 혜택을 만나보세요.
            </p>
          </div>

          <div
            className="absolute left-1/2 flex h-[61px] items-center justify-between rounded-full border border-[#e2e8f0] bg-[#edf2f7] px-[12px] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform"
            style={{
              top: "clamp(430px, 56vh, 520px)",
              width: "min(801px, 90vw)",
              transform: `translateX(-50%) translateX(${collapsedWidth - (isSidebarOpen ? drawerWidth : collapsedWidth) / 2}px)`,
            }}
            data-name="Frame"
            data-node-id="2021:1140"
          >
            <div className="flex h-[40px] w-[40px] items-center justify-center rounded-full bg-[#e2e8f0]">
              <img alt="추가" className="h-[12px] w-[12px]" src={imgPlusIcon} data-node-id="2021:1143" />
            </div>
            <div className="text-[14px] text-[#a0aec0]" data-node-id="2021:1144">
              로그인이 필요한 서비스입니다
            </div>
            <div className="flex h-[40px] w-[40px] items-center justify-center rounded-full bg-[#e2e8f0]">
              <img alt="마이크" className="h-[17px] w-[14px]" src={imgMicIcon} data-node-id="2021:1146" />
            </div>
          </div>
        </div>

        <div className="absolute left-0 top-0 z-30 h-[80px] w-full pointer-events-none">
          <div className="absolute right-[32px] top-[20px] flex h-[40px] items-center gap-[17px] pointer-events-auto">
            <div
              className="h-[36px] w-[72px] rounded-full border border-[#e2e8f0] bg-white"
              data-name="Frame"
              data-node-id="2009:828"
            >
              <div className="flex h-full w-full items-center justify-between px-[10px] text-[16px]">
                <span className="text-[#f6ad55]" data-node-id="2009:831">
                  ☀️
                </span>
                <span className="text-[#a0aec0]" data-node-id="2009:832">
                  🌙
                </span>
              </div>
            </div>
            <div className="flex h-[40px] w-[200px] items-center gap-[10px]" data-name="Group" data-node-id="2009:821">
              <Link
                href="/signup"
                className="flex h-full w-[90px] items-center justify-center rounded-full border border-[#cbd5e0] bg-white text-[14px] font-bold text-[#4a5568]"
                data-node-id="2009:824"
              >
                로그인
              </Link>
              <Link
                href="/signup"
                className="flex h-full w-[100px] items-center justify-center rounded-full bg-[#3182ce] text-[14px] font-bold text-white"
                data-node-id="2009:827"
              >
                회원가입
              </Link>
            </div>
          </div>
        </div>
      </div>
    </FullScreenFrame>
  );
}
