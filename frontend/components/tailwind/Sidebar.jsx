// sidebar that can be toggled open and closed

import { ArrowLeftStartOnRectangleIcon } from "@heroicons/react/20/solid";
import React, { useEffect, useRef, useState } from "react";
import { twMerge } from "tailwind-merge";
import { Collapse } from "./Collapse";

export default function Sidebar({
  title = "Menu",
  children,
  rootClassNames = "",
  contentClassNames = "",
}) {
  const [open, setOpen] = useState(true);
  const contentRef = useRef(null);
  const containerRef = useRef(null);

  const handleClick = () => {
    if (!containerRef.current || !contentRef.current) return;
    // if opening, set container width to children width
    if (open) {
      // change the container width to 0
      containerRef.current.style.width = `0px`;
      setOpen(false);
    } else {
      containerRef.current.style.width = `${contentRef.current.clientWidth}px`;
      setOpen(true);
    }
  };

  useEffect(() => {
    if (!containerRef.current || !contentRef.current) return;
    console.log(containerRef.current, contentRef.current);
    containerRef.current.style.width = `${contentRef.current.clientWidth}px`;
  }, []);

  return (
    <div className={twMerge("relative", rootClassNames)}>
      <div className="hidden lg:block">
        <button
          className={`toggle-button absolute top-5 z-10 right-5 cursor-pointer`}
          onClick={() => handleClick()}
        >
          <ArrowLeftStartOnRectangleIcon className="h-4 w-4" />
        </button>
        <div ref={containerRef} className="overflow-hidden transition-all">
          <div
            className={twMerge("content w-80 ", contentClassNames)}
            ref={contentRef}
          >
            <h2 className="px-2 mb-3">{title}</h2>
            {children}
          </div>
        </div>
      </div>
      <div className="lg:hidden">
        {/* a collapse that opens from the top but still within the container*/}
        <Collapse title={title} rootClassName="rounded-t-md p-2">
          {children}
        </Collapse>
      </div>
    </div>
  );
}
