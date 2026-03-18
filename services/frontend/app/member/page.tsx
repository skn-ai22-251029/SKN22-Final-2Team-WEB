"use client";

import FullScreenFrame from "../components/FullScreenFrame";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const imgMenuIcon =
  "https://www.figma.com/api/mcp/asset/8aa9f692-3df6-4a17-a9e8-f713d7d1a1ee";
const imgEditIcon =
  "https://www.figma.com/api/mcp/asset/d6bb3b36-3d28-4b12-874c-412da87095c8";
const imgSettingsIcon =
  "https://www.figma.com/api/mcp/asset/792ac734-a1f1-4756-b214-34070a46371f";
const imgMemberDrawerBg =
  "https://www.figma.com/api/mcp/asset/0f914b5b-cc10-4bd1-b35c-23768f69ccb7";
const imgMemberDrawerSettings =
  "https://www.figma.com/api/mcp/asset/4a01918a-5820-4bec-b42b-32649376400d";
const imgMemberDrawerProfileSection =
  "https://www.figma.com/api/mcp/asset/50f5e84b-42c0-4a50-9404-59ac09c4f92c";
const imgMemberDrawerListItem =
  "https://www.figma.com/api/mcp/asset/6630cc6d-cbd9-471a-8587-bd6e56070487";
const imgMemberDrawerDivider =
  "https://www.figma.com/api/mcp/asset/29c2734e-0f52-4f9b-80bf-a8e97d42dbc0";
const imgMemberDrawerLogOut =
  "https://www.figma.com/api/mcp/asset/859bd012-3121-4646-8578-a808af8cfaf3";
const imgMemberDrawerToday =
  "https://www.figma.com/api/mcp/asset/a8f9b5e8-9952-47b2-901a-8fdc781f9d80";
const imgMemberDrawerTodayChat =
  "https://www.figma.com/api/mcp/asset/924b342d-35f0-4e89-b8d4-15346ed89526";
const imgMemberDrawerTodayDate =
  "https://www.figma.com/api/mcp/asset/d115771a-8b37-4b87-9680-dcaf0b144491";
const imgMemberDrawerYesterday =
  "https://www.figma.com/api/mcp/asset/84e3b6d7-cc48-4694-8945-98f9ef125bfd";
const imgMemberDrawerYesterdayChat =
  "https://www.figma.com/api/mcp/asset/3cb8d51b-7915-4f93-ba62-0633721f5f53";
const imgMemberDrawerMenu =
  "https://www.figma.com/api/mcp/asset/5f81f82e-a391-4ba4-b447-0ac855e07b12";
const imgMemberDrawerButton =
  "https://www.figma.com/api/mcp/asset/df3ce098-f6c1-4139-a85f-f8777af8e86d";
const imgCart =
  "https://www.figma.com/api/mcp/asset/ba733178-1524-4321-b48c-649741e0bb5f";
const imgProfile =
  "https://www.figma.com/api/mcp/asset/be02fb28-1930-43fb-ac3b-9fcf482e1f58";
const imgChatBorder =
  "https://www.figma.com/api/mcp/asset/4ec52273-5227-44c9-b2fb-f9ed508ae4ba";
const imgChatPlusCircle =
  "https://www.figma.com/api/mcp/asset/bf9036d0-fa6a-4951-8bf1-87121fd476c3";
const imgChatPlusGlyph =
  "https://www.figma.com/api/mcp/asset/ce465e75-6e82-4e2a-88c9-c2fd47a455ac";

const exampleChips = [
  { label: "✨ 가수분해 사료란?", prompt: "가수분해 사료란?" },
  { label: "🚫 닭고기 없는 간식 추천", prompt: "닭고기 없는 간식 추천" },
  { label: "🦷 치석 제거용 껌 추천", prompt: "치석 제거용 껌 추천" },
];

export default function MemberPage() {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [sidebarAssetsReady, setSidebarAssetsReady] = useState(false);
  const [message, setMessage] = useState("");
  const [chatHistories, setChatHistories] = useState([
    { id: "history-1", title: "피부 알레르기 사료 추천", date: "26/03/11" },
    { id: "history-2", title: "슬개골 탈구 예방 훈련", date: "26/03/10" },
  ]);
  const [editingHistoryId, setEditingHistoryId] = useState<string | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [hoveredHistoryId, setHoveredHistoryId] = useState<string | null>(null);
  const [pendingDeleteHistoryId, setPendingDeleteHistoryId] = useState<string | null>(null);
  const recentChatInputRef = useRef<HTMLInputElement>(null);
  const messageInputRef = useRef<HTMLTextAreaElement>(null);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const [composerHeight, setComposerHeight] = useState(61);
  const drawerWidth = 281;
  const collapsedWidth = 68;
  const contentShift = drawerWidth - collapsedWidth;
  const hasMessage = message.trim().length > 0;

  const resetToNewChat = () => {
    setMessage("");
    setIsSidebarOpen(false);
    setIsProfileMenuOpen(false);
    setEditingHistoryId(null);
    setHoveredHistoryId(null);
    router.push("/member");
  };

  const handleExampleChipClick = (prompt: string) => {
    setMessage(prompt);
    requestAnimationFrame(() => {
      messageInputRef.current?.focus();
      messageInputRef.current?.setSelectionRange(prompt.length, prompt.length);
    });
  };

  useEffect(() => {
    if (editingHistoryId) {
      recentChatInputRef.current?.focus();
      recentChatInputRef.current?.select();
    }
  }, [editingHistoryId]);

  useEffect(() => {
    const textarea = messageInputRef.current;
    if (!textarea) return;

    textarea.style.height = "24px";
    const nextTextareaHeight = Math.min(Math.max(textarea.scrollHeight, 24), 120);
    textarea.style.height = `${nextTextareaHeight}px`;
    setComposerHeight(Math.max(61, nextTextareaHeight + 36));
  }, [message]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!profileMenuRef.current) return;
      if (!profileMenuRef.current.contains(event.target as Node)) {
        setIsProfileMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const sidebarAssets = [
      imgMemberDrawerBg,
      imgMemberDrawerSettings,
      imgMemberDrawerProfileSection,
      imgMemberDrawerListItem,
      imgMemberDrawerDivider,
      imgMemberDrawerLogOut,
      imgMemberDrawerToday,
      imgMemberDrawerTodayChat,
      imgMemberDrawerTodayDate,
      imgMemberDrawerYesterday,
      imgMemberDrawerYesterdayChat,
      imgMemberDrawerMenu,
      imgMemberDrawerButton,
    ];

    let loaded = 0;
    let cancelled = false;

    const markLoaded = () => {
      loaded += 1;
      if (!cancelled && loaded === sidebarAssets.length) {
        setSidebarAssetsReady(true);
      }
    };

    sidebarAssets.forEach((src) => {
      const image = new window.Image();
      image.onload = markLoaded;
      image.onerror = markLoaded;
      image.src = src;
    });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <FullScreenFrame>
      <div data-name="[FR-MAIN-02] 회원 사이드바(Hidden)" data-node-id="2046:1388">
        {isDeleteModalOpen && (
          <div
            className="absolute inset-0 z-[60] flex items-center justify-center bg-black/10"
            onClick={() => {
              setIsDeleteModalOpen(false);
              setPendingDeleteHistoryId(null);
            }}
          >
            <div
              className="relative h-[279px] w-[399px] rounded-[20px] border border-[#dbe7f5] bg-white shadow-[0_14px_36px_rgba(45,55,72,0.10)]"
              data-name="대화 기록 삭제 모달"
              data-node-id="2204:27"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="absolute left-1/2 top-[27px] flex h-[81px] w-[81px] -translate-x-1/2 items-center justify-center rounded-full border-[4px] border-[#ef4444]">
                <span className="relative top-[-1px] text-[48px] font-bold leading-none text-[#ef4444]" data-node-id="2204:29">
                  !
                </span>
              </div>
              <p
                className="absolute left-1/2 top-[127px] -translate-x-1/2 whitespace-nowrap text-center text-[19px] font-bold leading-none text-[#2d3748]"
                data-node-id="2204:31"
              >
                정말 삭제하시겠습니까?
              </p>
              <p
                className="absolute left-1/2 top-[171px] -translate-x-1/2 whitespace-nowrap text-center text-[14px] leading-none text-[#718096]"
                data-node-id="2204:32"
              >
                대화 기록이 영구적으로 삭제됩니다
              </p>
              <div className="absolute bottom-[24px] left-[40px] right-[40px] flex h-[42px] items-center justify-between">
                <button
                  type="button"
                  className="flex h-full w-[150px] items-center justify-center rounded-[8px] bg-[#edf2f7] text-[14px] font-bold text-[#4a5568]"
                  onClick={() => setIsDeleteModalOpen(false)}
                  data-node-id="2204:33"
                >
                  취소
                </button>
                <button
                  type="button"
                  className="flex h-full w-[150px] items-center justify-center rounded-[8px] bg-[#ef4444] text-[14px] font-bold text-white"
                  onClick={() => {
                    setChatHistories((current) =>
                      current.filter((history) => history.id !== pendingDeleteHistoryId),
                    );
                    setIsDeleteModalOpen(false);
                    setEditingHistoryId(null);
                    setPendingDeleteHistoryId(null);
                  }}
                  data-node-id="2204:35"
                >
                  삭제하기
                </button>
              </div>
            </div>
          </div>
        )}

        {isSidebarOpen && (
          <button
            className="absolute inset-0 z-[15] cursor-default"
            type="button"
            aria-label="사이드바 닫기"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        <aside
          className="absolute left-0 top-0 z-20 h-full w-[281px] overflow-hidden transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
          style={{ transform: isSidebarOpen ? "translateX(0px)" : `translateX(-${contentShift}px)` }}
          data-name={isSidebarOpen ? "회원 사이드바(Open)" : "[FR-MAIN-02] 회원 사이드바(Hidden)"}
          data-node-id={isSidebarOpen ? "2116:120" : "2046:1397"}
        >
          <div className="relative h-full w-full">
            <div
              className={`absolute inset-0 transition-opacity duration-200 ${
                isSidebarOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
              }`}
            >
              <div
                className="relative h-full w-full transition-opacity duration-150"
                style={{ opacity: sidebarAssetsReady ? 1 : 0 }}
              >
                <img alt="" className="absolute inset-0 h-full w-full" src={imgMemberDrawerBg} data-node-id="2116:121" />
              <button
                type="button"
                className="absolute left-[16px] top-[21px] flex h-[37px] w-[207px] items-center justify-center"
                onClick={resetToNewChat}
                data-node-id="2116:140"
              >
                  <img alt="" className="absolute inset-0 h-full w-full" src={imgMemberDrawerButton} data-node-id="2116:141" />
                  <span className="relative whitespace-nowrap text-[16px] font-bold leading-none text-white" data-node-id="2116:142">
                    새 대화 시작
                  </span>
                </button>
                <button
                  className="absolute left-[242px] top-[32px] h-[16px] w-[24px]"
                  type="button"
                  onClick={() => setIsSidebarOpen(false)}
                  aria-label="사이드바 닫기"
                  data-node-id="2116:139"
                >
                  <img alt="" className="block h-full w-full" src={imgMemberDrawerMenu} />
                </button>
                <img
                  alt="프로필 선택"
                  className="absolute left-[20.5px] top-[89.28px] h-[55.22px] w-[240px]"
                  src={imgMemberDrawerProfileSection}
                  data-node-id="2116:124"
                />
                <div className="absolute left-[15.5px] top-[182px] flex w-[250px] flex-col gap-[12px]">
                  {chatHistories.map((history) => {
                    const isHovered = hoveredHistoryId === history.id;
                    const isEditing = editingHistoryId === history.id;

                    return (
                      <div
                        key={history.id}
                        className={`relative h-[40px] w-[250px] rounded-[8px] transition-colors duration-150 ${
                          isHovered ? "bg-[#e2e8f0]" : "bg-transparent"
                        }`}
                        onMouseEnter={() => setHoveredHistoryId(history.id)}
                        onMouseLeave={() => setHoveredHistoryId((current) => (current === history.id ? null : current))}
                      >
                        <img
                          alt=""
                          className={`absolute inset-0 h-[40px] w-[250px] transition-opacity duration-150 ${
                            isHovered ? "opacity-0" : "opacity-100"
                          }`}
                          src={imgMemberDrawerListItem}
                        />
                        {isEditing ? (
                          <input
                            ref={recentChatInputRef}
                            type="text"
                            value={history.title}
                            onChange={(event) => {
                              const nextTitle = event.target.value;
                              setChatHistories((current) =>
                                current.map((item) =>
                                  item.id === history.id ? { ...item, title: nextTitle } : item,
                                ),
                              );
                            }}
                            onBlur={() => setEditingHistoryId(null)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === "Escape") {
                                setEditingHistoryId(null);
                              }
                            }}
                            className="absolute left-[10.5px] top-[7.8px] h-[24px] w-[175px] rounded border border-[#cbd5e0] bg-white px-[6px] text-[12px] font-semibold text-[#2d3748] outline-none"
                            aria-label="대화 기록 제목 수정"
                          />
                        ) : (
                          <div className="absolute left-[10.5px] right-[66px] top-[11.8px] overflow-hidden text-ellipsis whitespace-nowrap text-[12px] font-semibold leading-none text-[#2d3748]">
                            {history.title}
                          </div>
                        )}
                        <div className="absolute right-[10px] top-[11px] h-[18px] w-[62px]">
                          <div
                            className={`absolute right-0 top-[1px] w-full transition-opacity duration-150 ${
                              isHovered ? "opacity-0" : "opacity-100"
                            }`}
                          >
                            <div
                              className="w-full whitespace-nowrap text-right text-[11px] leading-none tabular-nums text-[#a0aec0]"
                              style={{ fontVariantNumeric: "tabular-nums lining-nums", fontFeatureSettings: '"tnum" 1, "lnum" 1' }}
                            >
                              {history.date}
                            </div>
                          </div>
                          <div
                            className={`absolute right-0 top-0 flex w-full items-center justify-end gap-[7px] transition-opacity duration-150 ${
                              isHovered ? "opacity-100" : "opacity-0"
                            }`}
                          >
                            <button
                              type="button"
                              className="flex h-[18px] w-[18px] items-center justify-center text-[12px] leading-none"
                              onClick={() => setEditingHistoryId(history.id)}
                              aria-label="대화 기록 제목 수정"
                              data-node-id="2116:136"
                            >
                              ✏️
                            </button>
                            <button
                              type="button"
                              className="flex h-[18px] w-[18px] items-center justify-center text-[12px] leading-none"
                              onClick={() => {
                                setPendingDeleteHistoryId(history.id);
                                setIsDeleteModalOpen(true);
                              }}
                              aria-label="대화 기록 삭제"
                              data-node-id="2116:137"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <img
                  alt="하단 구분선"
                  className="absolute bottom-[69.5px] left-[20.5px] h-px w-[240px]"
                  src={imgMemberDrawerDivider}
                  data-node-id="2116:134"
                />
                <button
                  type="button"
                  className="absolute bottom-[34.26px] left-[25.07px] h-[12.96px] w-[50.37px]"
                  data-node-id="2116:135"
                  aria-label="로그아웃"
                  onClick={() => {
                    if (typeof window !== "undefined") {
                      window.localStorage.removeItem("tt_logged_in");
                    }
                    setIsSidebarOpen(false);
                    router.push("/");
                  }}
                >
                  <img alt="" className="block h-full w-full" src={imgMemberDrawerLogOut} />
                </button>
                <img
                  alt="설정"
                  className="absolute bottom-[30.9px] left-[237px] h-[19.1px] w-[18.68px]"
                  src={imgMemberDrawerSettings}
                  data-node-id="2116:122"
                />
              </div>
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
                data-node-id="2116:139"
              >
                <img alt="" className="block h-full w-full" src={imgMenuIcon} />
              </button>
              <button
                className="absolute left-1/2 top-[93.19px] h-[14.81px] w-[14.81px] -translate-x-1/2"
                type="button"
                onClick={resetToNewChat}
                aria-label="새 대화 시작"
                data-node-id="2021:1121"
              >
                <img alt="" className="block h-full w-full" src={imgEditIcon} />
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
            data-name="Header"
            data-node-id="2046:1391"
          >
            <div
              className="absolute left-[87.5px] top-1/2 -translate-y-1/2 text-[26px] font-bold leading-none text-[#2d3748]"
              data-node-id="2116:38"
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
            data-node-id="2046:1415"
          >
            <p className="whitespace-nowrap text-[32px] font-bold leading-[1.2] text-[#1a202c]" data-node-id="2046:1416">
              <span className="text-[#3182ce]">Tail</span>
              <span>Talk 와 함께하는 스마트한 집사 생활 </span>
            </p>
          </div>

          <div
            className="absolute left-1/2 flex flex-wrap items-center justify-center gap-[12px] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform"
            style={{
              top: "clamp(305px, 41vh, 380px)",
              width: "min(820px, 92vw)",
              transform: `translateX(-50%) translateX(${collapsedWidth - (isSidebarOpen ? drawerWidth : collapsedWidth) / 2}px)`,
            }}
            data-name="Example_Chips"
          >
            {exampleChips.map((chip) => (
              <button
                key={chip.label}
                type="button"
                className="flex h-[36px] items-center justify-center rounded-full border border-[#3182ce] bg-white px-[18px] text-[13px] font-bold text-[#3182ce] shadow-[0_1px_2px_rgba(49,130,206,0.08)]"
                onClick={() => handleExampleChipClick(chip.prompt)}
              >
                {chip.label}
              </button>
            ))}
          </div>

          <div
            className="absolute left-1/2 bg-white transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform"
            style={{
              top: "clamp(430px, 56vh, 520px)",
              height: composerHeight,
              width: "min(801px, 90vw)",
              transform: `translateX(-50%) translateX(${collapsedWidth - (isSidebarOpen ? drawerWidth : collapsedWidth) / 2}px)`,
            }}
            data-name="Frame"
            data-node-id={hasMessage ? "2046:1592" : "2046:1574"}
          >
            <img alt="" className="absolute inset-0 h-full w-full" src={imgChatBorder} data-node-id="2046:1579" />
            <div className="absolute bottom-[10.5px] left-[10.5px] h-[40px] w-[40px]">
              <img alt="" className="absolute inset-0 h-full w-full" src={imgChatPlusCircle} data-node-id="2046:1580" />
              <img
                alt="추가"
                className="absolute left-[14px] top-[14px] h-[12px] w-[12px]"
                src={imgChatPlusGlyph}
                data-node-id="2046:1581"
              />
            </div>
            <textarea
              ref={messageInputRef}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              rows={1}
              className="absolute bottom-[18px] left-[63px] right-[64px] min-h-[24px] resize-none overflow-y-auto bg-transparent text-[16px] leading-[24px] text-black outline-none placeholder:text-[#a6a6a6]"
              placeholder="메시지를 입력하세요..."
              aria-label="메시지 입력"
              data-node-id={hasMessage ? "2046:1608" : "2046:1591"}
            />
            <button
              type="button"
              className="absolute bottom-[10.5px] right-[10.5px] flex h-[40px] w-[40px] items-center justify-center overflow-hidden rounded-full"
              aria-label={hasMessage ? "메시지 전송" : "음성 입력"}
            >
              <div className="absolute inset-0 rounded-full bg-[#3182ce]" />
              <div
                className={`pointer-events-none absolute flex items-center justify-center transition-all duration-220 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                  hasMessage ? "translate-y-[-6px] scale-75 opacity-0" : "translate-y-0 scale-100 opacity-100"
                }`}
                data-node-id="2046:1585"
              >
                <svg
                  aria-hidden="true"
                  className="h-[19px] w-[16px]"
                  viewBox="0 0 16 19"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M8 12.25C9.933 12.25 11.5 10.683 11.5 8.75V5.25C11.5 3.317 9.933 1.75 8 1.75C6.067 1.75 4.5 3.317 4.5 5.25V8.75C4.5 10.683 6.067 12.25 8 12.25Z"
                    stroke="white"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M2.75 8.75C2.75 11.649 5.101 14 8 14C10.899 14 13.25 11.649 13.25 8.75"
                    stroke="white"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path d="M8 14V17.25" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
                  <path d="M5.5 17.25H10.5" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </div>
              <div
                className={`pointer-events-none absolute inset-0 flex items-center justify-center transition-all duration-220 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                  hasMessage ? "translate-y-0 scale-100 opacity-100" : "translate-y-[6px] scale-80 opacity-0"
                }`}
                data-node-id="2046:1604"
              >
                <svg
                  aria-hidden="true"
                  className="h-[20px] w-[14px]"
                  viewBox="0 0 14 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  data-node-id="2046:1605"
                >
                  <path
                    d="M7 18V3M7 3L1.75 8.25M7 3L12.25 8.25"
                    stroke="white"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            </button>
          </div>
        </div>

        <div className="absolute left-0 top-0 z-30 h-[80px] w-full pointer-events-none">
          <div className="absolute right-[32px] top-[20px] flex h-[40px] items-center gap-[17px] pointer-events-auto">
            <div
              className="h-[36px] w-[72px] rounded-full border border-[#e2e8f0] bg-white"
              data-name="Frame"
              data-node-id="2046:1410"
            >
              <div className="flex h-full w-full items-center justify-between px-[10px] text-[16px]">
                <span className="text-[#f6ad55]" data-node-id="2046:1413">
                  ☀️
                </span>
                <span className="text-[#a0aec0]" data-node-id="2046:1414">
                  🌙
                </span>
              </div>
            </div>
            <div className="h-[40px] w-[40px]">
              <img alt="장바구니" className="h-full w-full" src={imgProfile} data-node-id="2046:1458" />
            </div>
            <div ref={profileMenuRef} className="relative h-[40px] w-[40px]">
              <button
                type="button"
                className="h-[40px] w-[40px]"
                aria-label="프로필 메뉴 열기"
                onClick={() => setIsProfileMenuOpen((current) => !current)}
              >
                <img alt="프로필" className="h-full w-full" src={imgCart} data-node-id="2046:1454" />
              </button>
              <div
                className={`absolute right-0 top-[52px] w-[160px] origin-top-right rounded-[16px] border border-[#dbe7f5] bg-white shadow-[0_14px_36px_rgba(45,55,72,0.10)] transition-all duration-180 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                  isProfileMenuOpen
                    ? "pointer-events-auto translate-y-0 scale-100 opacity-100"
                    : "pointer-events-none translate-y-[-8px] scale-95 opacity-0"
                }`}
                data-name="[FR-NAV-05] 드롭다운(라이트)"
                data-node-id="2009:728"
              >
                <button
                  type="button"
                  className="flex h-[44px] w-full items-center rounded-t-[16px] px-[16px] text-left text-[14px] font-normal text-[#2d3748] transition-colors duration-150 hover:bg-[#edf2f7]"
                  onClick={() => {
                    setIsProfileMenuOpen(false);
                    router.push("/profile");
                  }}
                  data-node-id="2009:730"
                >
                  내 정보
                </button>
                <div className="mx-[12px] h-px bg-[#edf2f7]" data-node-id="2009:733" />
                <button
                  type="button"
                  className="flex h-[44px] w-full items-center px-[16px] text-left text-[14px] font-normal text-[#2d3748] transition-colors duration-150 hover:bg-[#edf2f7]"
                  onClick={() => {
                    setIsProfileMenuOpen(false);
                    router.push("/pets");
                  }}
                  data-node-id="2009:734"
                >
                  반려동물 정보
                </button>
                <div className="mx-[12px] h-px bg-[#edf2f7]" data-node-id="2009:737" />
                <button
                  type="button"
                  className="flex h-[44px] w-full items-center px-[16px] text-left text-[14px] font-normal text-[#2d3748] transition-colors duration-150 hover:bg-[#edf2f7]"
                  onClick={() => {
                    setIsProfileMenuOpen(false);
                    router.push("/orders");
                  }}
                  data-node-id="2009:738"
                >
                  주문 내역
                </button>
                <div className="mx-[12px] h-px bg-[#edf2f7]" />
                <button
                  type="button"
                  className="flex h-[44px] w-full items-center rounded-b-[16px] px-[16px] text-left text-[14px] font-normal text-[#ef4444] transition-colors duration-150 hover:bg-[#fef2f2]"
                  onClick={() => {
                    if (typeof window !== "undefined") {
                      window.localStorage.removeItem("tt_logged_in");
                    }
                    setIsProfileMenuOpen(false);
                    router.push("/");
                  }}
                >
                  로그아웃
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </FullScreenFrame>
  );
}
