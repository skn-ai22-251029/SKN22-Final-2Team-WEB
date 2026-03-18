import type { CSSProperties, ReactNode } from "react";

type FullScreenFrameProps = {
  children: ReactNode;
  outerClassName?: string;
  innerClassName?: string;
  innerStyle?: CSSProperties;
};

export default function FullScreenFrame({
  children,
  outerClassName,
  innerClassName,
  innerStyle,
}: FullScreenFrameProps) {
  return (
    <div className={`min-h-screen bg-[#f7fafc] ${outerClassName ?? ""}`}>
      <div
        className={`relative h-screen w-full overflow-hidden bg-[#f7fafc] ${innerClassName ?? ""}`}
        style={innerStyle}
      >
        {children}
      </div>
    </div>
  );
}
