import { useState } from "react";
import { PlusOutlined, CheckOutlined } from "@ant-design/icons";
import Image from "next/image";

export default function Sources({ sources, setSources }) {
  if (sources.length === 0) {
    return null;
  }
  return (
    <div className="bg-white flex w-full flex-col">
      <div className="flex items-start gap-4 pb-3">
        <h3 className="text-base font-bold leading-6 text-black">
          Suggested Sources{" "}
        </h3>
      </div>
      <div className="flex w-full items-center overflow-x-scroll gap-6 pb-3">
        {sources.map((source, i) => (
          <SourceCard source={source} setSources={setSources} key={i} />
        ))}
      </div>
    </div>
  );
}

const SourceCard = ({ source, setSources }) => {
  const [selected, setSelected] = useState(source.selected);
  const handleSelect = () => {
    setSelected(!selected);
    setSources((prevSources) =>
      prevSources.map((prevSource) => {
        if (prevSource.link === source.link) {
          return { ...prevSource, selected: !selected };
        }
        return prevSource;
      })
    );
  };
  return (
    <div
      className={`"flex h-[79px] w-full items-center gap-2.5 rounded-lg border border-gray-100 px-1.5 py-1 shadow-md ${selected ? "bg-gray-100 opacity-50" : "bg-white"}`}
    >
      <div className="flex items-center relative">
        <span className="shrink-0">
          <Image
            unoptimized
            src={`https://www.google.com/s2/favicons?domain=${source.link}&sz=128`}
            alt={source.link}
            className="rounded-full p-1"
            width={36}
            height={36}
          />
        </span>
        <span className="flex min-w-0 max-w-[192px] flex-col justify-center gap-1 ml-2 mt-2">
          <h6 className="line-clamp-2 text-xs font-light">{source.title}</h6>
          <a
            target="_blank"
            rel="noopener noreferrer"
            href={source.link}
            className="truncate text-xs font-light text-[#1B1B16]/30"
          >
            {source.link}
          </a>
        </span>
        <div
          className="ml-auto cursor-pointer top-2 right-2"
          onClick={handleSelect}
        >
          {selected ? (
            <CheckOutlined style={{ color: "green" }} />
          ) : (
            <PlusOutlined />
          )}
        </div>
      </div>
    </div>
  );
};
