"use client";

import Link from "next/link";
import { useState } from "react";
import FullScreenFrame from "../components/FullScreenFrame";

type OrderTab = "history" | "favorite" | "avoid";

type OrderItem = {
  id: string;
  orderedAt: string;
  title: string;
  price: string;
  status: string;
  products: Array<{
    id: string;
    name: string;
    category: string;
    price: string;
    preference: ProductPreference;
  }>;
};

type PreferenceItem = {
  id: string;
  title: string;
  category: string;
};

type ProductPreference = "like" | "dislike" | null;

const orderItems: OrderItem[] = [
  {
    id: "order-1",
    orderedAt: "2026.03.11 주문 (주문번호: 20260311-0001)",
    title: "연어 담은 가수분해 사료 외 1건",
    price: "51,500원",
    status: "배송준비중",
    products: [
      { id: "o1-p1", name: "연어 담은 가수분해 사료", category: "기능성 사료", price: "31,500원", preference: "like" },
      { id: "o1-p2", name: "피부 보습 영양 간식", category: "영양 간식", price: "12,000원", preference: null },
      { id: "o1-p3", name: "오메가 밸런스 트릿", category: "간식", price: "8,000원", preference: null },
    ],
  },
  {
    id: "order-2",
    orderedAt: "2026.02.15 주문 (주문번호: 20260215-0003)",
    title: "관절 튼튼 칼슘 껌",
    price: "12,000원",
    status: "배송완료",
    products: [{ id: "o2-p1", name: "관절 튼튼 칼슘 껌", category: "기능 간식", price: "12,000원", preference: "like" }],
  },
];

const favoriteItems: PreferenceItem[] = [
  { id: "fav-1", title: "로얄캐닌 미니 인도어 어덜트", category: "건식 사료" },
  { id: "fav-2", title: "연어 담은 가수분해 사료", category: "기능성 사료" },
];

const avoidItems: PreferenceItem[] = [
  { id: "avoid-1", title: "이나바 챠오츄르 참치맛", category: "습식 간식" },
  { id: "avoid-2", title: "닭고기 베이스 트릿", category: "간식" },
];

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative flex h-[38px] items-center justify-center px-[4px] text-[20px] font-bold transition-colors ${
        active ? "text-[#2d3748]" : "text-[#a0aec0] hover:text-[#4a5568]"
      }`}
    >
      {children}
      <span
        className={`absolute bottom-[-10px] left-0 h-[3px] w-full rounded-full bg-[#3182ce] transition-opacity duration-150 ${
          active ? "opacity-100" : "opacity-0"
        }`}
      />
    </button>
  );
}

export default function OrdersPage() {
  const [activeTab, setActiveTab] = useState<OrderTab>("history");
  const [expandedOrderId, setExpandedOrderId] = useState<string | null>(orderItems[0]?.id ?? null);
  const [orders, setOrders] = useState<OrderItem[]>(orderItems);

  const updateOrderProductPreference = (
    orderId: string,
    productId: string,
    preference: ProductPreference,
  ) => {
    setOrders((current) =>
      current.map((order) =>
        order.id === orderId
          ? {
              ...order,
              products: order.products.map((product) =>
                product.id === productId
                  ? {
                      ...product,
                      preference: product.preference === preference ? null : preference,
                    }
                  : product,
              ),
            }
          : order,
      ),
    );
  };

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
        <div className="w-full max-w-[860px] rounded-[20px] border border-[#dbe7f5] bg-white px-10 py-8 shadow-[0_6px_20px_rgba(45,55,72,0.04)]">
          <div className="flex items-center gap-[28px] border-b border-[#edf2f7] pb-4">
            <TabButton active={activeTab === "history"} onClick={() => setActiveTab("history")}>
              주문 내역
            </TabButton>
            <TabButton active={activeTab === "favorite"} onClick={() => setActiveTab("favorite")}>
              선호 상품
            </TabButton>
            <TabButton active={activeTab === "avoid"} onClick={() => setActiveTab("avoid")}>
              기피 상품
            </TabButton>
          </div>

          <div className="mt-6 h-[520px] overflow-hidden rounded-[16px] border border-[#edf2f7] bg-[#fbfdff]">
            {activeTab === "history" && (
              <div className="h-full overflow-y-auto p-6">
                <div className="space-y-5">
                  {orders.map((order) => (
                    <div key={order.id} className="rounded-[18px] border border-[#e2e8f0] bg-white p-5">
                      <div className="flex items-start justify-between gap-4">
                        <div className="text-[13px] text-[#718096]">{order.orderedAt}</div>
                        <div
                          className={`text-[13px] font-bold ${
                            order.status === "배송준비중" ? "text-[#3182ce]" : "text-[#4a5568]"
                          }`}
                        >
                          {order.status}
                        </div>
                      </div>
                      {order.products.length === 1 ? (
                        <div className="mt-4 flex items-center gap-4 rounded-[12px]">
                          <div className="flex h-[70px] w-[70px] items-center justify-center rounded-[10px] bg-[#edf2f7] text-[10px] text-[#a0aec0]">
                            사진
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-[15px] font-bold text-[#2d3748]">{order.products[0].name}</div>
                            <div className="mt-1 text-[12px] text-[#718096]">{order.products[0].category}</div>
                            <div className="mt-2 text-[16px] font-bold text-[#2d3748]">{order.products[0].price}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => updateOrderProductPreference(order.id, order.products[0].id, "like")}
                              className={`flex h-[30px] items-center justify-center rounded-full px-4 text-[13px] font-bold ${
                                order.products[0].preference === "like"
                                  ? "border border-[#3182ce] bg-[#ebf8ff] text-[#3182ce]"
                                  : "border border-[#e2e8f0] bg-white text-[#a0aec0]"
                              }`}
                            >
                              👍 선호
                            </button>
                            <button
                              type="button"
                              onClick={() => updateOrderProductPreference(order.id, order.products[0].id, "dislike")}
                              className={`flex h-[30px] items-center justify-center rounded-full px-4 text-[13px] font-bold ${
                                order.products[0].preference === "dislike"
                                  ? "border border-[#ef4444] bg-[#fff5f5] text-[#ef4444]"
                                  : "border border-[#e2e8f0] bg-white text-[#a0aec0]"
                              }`}
                            >
                              👎 기피
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedOrderId((current) => (current === order.id ? null : order.id))
                            }
                            className="mt-4 flex w-full items-center gap-4 rounded-[12px] text-left transition-colors hover:bg-[#f8fbff]"
                          >
                            <div className="flex h-[70px] w-[70px] items-center justify-center rounded-[10px] bg-[#edf2f7] text-[10px] text-[#a0aec0]">
                              사진
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="truncate text-[15px] font-bold text-[#2d3748]">{order.title}</div>
                              <div className="mt-2 text-[16px] font-bold text-[#2d3748]">{order.price}</div>
                            </div>
                          </button>
                          <div
                            className={`overflow-hidden transition-all duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                              expandedOrderId === order.id ? "mt-4 max-h-[260px] opacity-100" : "max-h-0 opacity-0"
                            }`}
                          >
                            <div className="rounded-[14px] border border-[#edf2f7] bg-[#fbfdff] p-4">
                              <div className="mb-3 text-[14px] font-bold text-[#4a5568]">주문 상품 목록</div>
                              <div className="max-h-[168px] space-y-2 overflow-y-auto pr-1">
                                {order.products.map((product) => (
                                  <div
                                    key={product.id}
                                    className="flex items-center justify-between rounded-[12px] border border-[#e2e8f0] bg-white px-4 py-3"
                                  >
                                    <div className="min-w-0 flex-1">
                                      <div className="truncate text-[14px] font-bold text-[#2d3748]">{product.name}</div>
                                      <div className="mt-1 text-[12px] text-[#718096]">{product.category}</div>
                                      <div className="mt-2 text-[14px] font-bold text-[#2d3748]">{product.price}</div>
                                    </div>
                                    <div className="ml-4 flex items-center gap-2">
                                      <button
                                        type="button"
                                        onClick={() => updateOrderProductPreference(order.id, product.id, "like")}
                                        className={`flex h-[28px] items-center justify-center rounded-full px-3 text-[12px] font-bold ${
                                          product.preference === "like"
                                            ? "border border-[#3182ce] bg-[#ebf8ff] text-[#3182ce]"
                                            : "border border-[#e2e8f0] bg-white text-[#a0aec0]"
                                        }`}
                                      >
                                        👍 선호
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => updateOrderProductPreference(order.id, product.id, "dislike")}
                                        className={`flex h-[28px] items-center justify-center rounded-full px-3 text-[12px] font-bold ${
                                          product.preference === "dislike"
                                            ? "border border-[#ef4444] bg-[#fff5f5] text-[#ef4444]"
                                            : "border border-[#e2e8f0] bg-white text-[#a0aec0]"
                                        }`}
                                      >
                                        👎 기피
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "favorite" && (
              <div className="h-full overflow-y-auto p-6">
                <div className="space-y-3">
                  {favoriteItems.map((item) => (
                    <div key={item.id} className="flex items-center justify-between rounded-[14px] border border-[#e2e8f0] bg-white px-4 py-4">
                      <div>
                        <div className="text-[15px] font-bold text-[#2d3748]">{item.title}</div>
                        <div className="mt-1 text-[12px] text-[#718096]">{item.category}</div>
                      </div>
                      <span className="rounded-full border border-[#3182ce] bg-[#ebf8ff] px-4 py-2 text-[13px] font-bold text-[#3182ce]">
                        👍 선호
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "avoid" && (
              <div className="h-full overflow-y-auto p-6">
                <div className="space-y-3">
                  {avoidItems.map((item) => (
                    <div key={item.id} className="flex items-center justify-between rounded-[14px] border border-[#e2e8f0] bg-white px-4 py-4">
                      <div>
                        <div className="text-[15px] font-bold text-[#2d3748]">{item.title}</div>
                        <div className="mt-1 text-[12px] text-[#718096]">{item.category}</div>
                      </div>
                      <span className="rounded-full border border-[#ef4444] bg-[#fff5f5] px-4 py-2 text-[13px] font-bold text-[#ef4444]">
                        👎 기피
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </FullScreenFrame>
  );
}
