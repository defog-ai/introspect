import { Plus, Check } from "lucide-react";
import Image from "next/image";

export default function Sources({ sources, setSources }) {
  if (sources.length === 0) {
    return null;
  }
  return (
    <div className="bg-white dark:bg-gray-800 flex w-full flex-col">
      <div className="flex items-start gap-4 pb-3">
        <h3 className="text-base font-bold leading-6 text-black dark:text-white">
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
  const handleSelect = () => {
    setSources((prevSources) =>
      prevSources.map((prevSource) => {
        if (prevSource.link === source.link) {
          return { ...prevSource, selected: !prevSource.selected };
        }
        return prevSource;
      })
    );
  };

  return (
    <div
      className={`relative flex h-[79px] w-full items-center gap-2.5 rounded-lg border border-gray-100 dark:border-gray-700 px-1.5 py-1 shadow-md transition-all hover:shadow-lg hover:border-gray-50 dark:hover:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-700 ${
        source.selected
          ? "bg-gray-100 dark:bg-gray-700 opacity-50"
          : "bg-white dark:bg-gray-800"
      }`}
    >
      {/* Icon and Text Wrapped in a Clickable <a> Tag that redirect to the source link*/}
      <a
        href={source.link}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 z-10"
        aria-label={`Visit ${source.title}`}
      >
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
        <span className="flex min-w-0 max-w-[192px] flex-col justify-center gap-1">
          <h6 className="line-clamp-2 text-xs font-light">{source.title}</h6>
          <span className="truncate text-xs font-light text-[#1B1B16]/30 dark:text-gray-400">
            {source.link}
          </span>
        </span>
      </a>

      {/* Button for Selection */}
      <div
        className="ml-2 mr-2 cursor-pointer relative z-20"
        onClick={(e) => {
          e.stopPropagation(); // Prevent link click
          handleSelect();
        }}
      >
        {source.selected ? (
          <Check className="w-3" style={{ color: "green" }} />
        ) : (
          <Plus className="w-3" />
        )}
      </div>
    </div>
  );
};
