import { ChevronRightIcon } from "@heroicons/react/20/solid";
import { useRef, useState } from "react";
import { twMerge } from "tailwind-merge";

export function Collapse({
  children,
  title,
  rootClassName = "",
  headerClassNames = "",
}) {
  const [collapsed, setCollapsed] = useState(false);
  const ctr = useRef(null);

  return (
    <>
      <div
        className={twMerge(
          "flex flex-col max-h-96 mb-2 pointer-events-auto cursor-pointer",
          rootClassName
        )}
        onClick={() => {
          console.log("bleh");
          setCollapsed(!collapsed);
          if (ctr.current) {
            const contentCtr = ctr.current.querySelector(".content");
            if (contentCtr) {
              ctr.current.style.maxHeight = collapsed
                ? `${contentCtr.scrollHeight}px`
                : "0px";
            }
          }
        }}
      >
        <div className={twMerge("h-10 flex items-center", headerClassNames)}>
          <ChevronRightIcon
            className="w-4 h-4 inline fill-gray-500"
            style={{
              transition: "transform 0.3s ease-in-out",
              marginRight: "3px",
              top: "1px",
              transform: collapsed ? "rotate(0deg)" : "rotate(90deg)",
            }}
          />
          <span className="font-bold text-md">{title}</span>
        </div>
        <div
          ref={ctr}
          style={{
            overflow: "hidden",
            maxHeight: "0px",
            transition: "max-height 0.6s ease-in-out",
          }}
        >
          <div className="content">{children}</div>
        </div>
      </div>
    </>
  );
}
