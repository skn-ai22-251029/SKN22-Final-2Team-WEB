"use client";

import Link from "next/link";
import FullScreenFrame from "../components/FullScreenFrame";
import { useState } from "react";

const imgCard =
  "https://www.figma.com/api/mcp/asset/eb8b7b54-70cf-4e1f-9cbf-46403968d531";
const imgDivider =
  "https://www.figma.com/api/mcp/asset/c35ab6dc-cd4c-4219-8ee0-4106934db393";
const imgKakao =
  "https://www.figma.com/api/mcp/asset/d22d7edf-9f92-417d-8172-d0122cb9956e";
const imgNaver =
  "https://www.figma.com/api/mcp/asset/7cfb3bd5-c1d7-42df-8155-0281c422f977";
const imgGoogle =
  "https://www.figma.com/api/mcp/asset/579f7bd6-15db-47cc-995e-1510a459db1d";
const imgCheckBox =
  "https://www.figma.com/api/mcp/asset/d87cedfa-0ee2-4f61-8bfd-ac58c6a6fb43";
const imgCheckMark =
  "https://www.figma.com/api/mcp/asset/c1ccc9d0-f595-41ef-8f5c-668456e9975d";

export default function SignupPage() {
  const [rememberMe, setRememberMe] = useState(true);
  const [loadedCount, setLoadedCount] = useState(0);
  const totalAssets = 7;
  const ready = loadedCount >= totalAssets;

  const markLoaded = () => {
    setLoadedCount((count) => count + 1);
  };

  return (
    <FullScreenFrame>
      <div data-name="[FR-AUTH-02, 03] 통합 로그인" data-node-id="2002:295">
        <div style={{ opacity: ready ? 1 : 0 }}>
          <div className="absolute left-1/2 top-1/2 h-[244px] w-[400px] -translate-x-1/2 -translate-y-1/2">
            <img
              alt=""
              className="absolute left-0 top-0 h-[244px] w-[400px]"
              src={imgCard}
              data-node-id="2002:297"
              onLoad={markLoaded}
            />

            <Link
              href="/"
              className="absolute left-[151px] top-[33px] h-[31px] w-[98px] text-center text-[26px] font-bold leading-none text-[#2d3748]"
              data-node-id="2002:298"
            >
              <span className="text-[#3182ce]">Tail</span>
              <span>Talk</span>
            </Link>

            <img
              alt=""
              className="absolute left-[40px] top-[84px] h-[1px] w-[60px]"
              src={imgDivider}
              data-node-id="2002:311"
              onLoad={markLoaded}
            />
            <p
              className="absolute left-[170.5px] top-[77px] h-[15px] w-[59px] text-center text-[12px] text-[#a0aec0]"
              data-node-id="2002:312"
            >
              간편 로그인
            </p>
            <img
              alt=""
              className="absolute left-[300px] top-[84px] h-[1px] w-[60px]"
              src={imgDivider}
              data-node-id="2002:313"
              onLoad={markLoaded}
            />

            <div
              className="absolute left-[106px] top-[114px] flex h-[48px] w-[188px] items-center justify-between"
              data-node-id="2002:314"
            >
              <Link href="/profile" aria-label="카카오 로그인" data-node-id="2002:315">
                <img alt="" className="h-[40px] w-[40px]" src={imgKakao} onLoad={markLoaded} />
              </Link>
              <Link href="/profile" aria-label="네이버 로그인" data-node-id="2002:318">
                <img alt="" className="h-[40px] w-[40px]" src={imgNaver} onLoad={markLoaded} />
              </Link>
              <Link href="/profile" aria-label="구글 로그인" data-node-id="2002:322">
                <img alt="" className="h-[40px] w-[40px]" src={imgGoogle} onLoad={markLoaded} />
              </Link>
            </div>

            <button
              type="button"
              className="absolute left-[139px] top-[190px] h-[18px] w-[120px]"
              data-node-id="2094:1001"
              aria-pressed={rememberMe}
              onClick={() => setRememberMe((prev) => !prev)}
            >
              <img
                alt=""
                className="absolute left-0 top-0 h-[18px] w-[18px]"
                src={imgCheckBox}
                data-node-id="2094:1002"
                onLoad={markLoaded}
              />
              {rememberMe && (
                <img
                  alt=""
                  className="absolute left-[5px] top-[6px] h-[6px] w-[8px]"
                  src={imgCheckMark}
                  data-node-id="2094:1003"
                />
              )}
              <span className="absolute left-[28px] top-0 text-[13px] text-[#4a5568]" data-node-id="2094:1004">
                로그인 상태 유지
              </span>
            </button>
          </div>
        </div>
      </div>
    </FullScreenFrame>
  );
}
