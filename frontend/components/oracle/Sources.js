import Image from "next/image";

export default function Sources({ sources }) {
  if (sources.length === 0) {
    return null;
  }
  console.log(sources);
  return (
    <div className="bg-white flex w-full flex-col">
      <div className="flex items-start gap-4 pb-3">
        <h3 className="text-base font-bold leading-6 text-black">
          Suggested Sources{" "}
        </h3>
      </div>
      <div className="flex w-full items-center overflow-x-scroll gap-6 pb-3">
        {sources.map((source) => (
          <SourceCard source={source} key={source.url} />
        ))}
      </div>
    </div>
  );
}

const SourceCard = ({ source }) => {
  return (
    <div className="flex h-[79px] w-full items-center gap-2.5 rounded-lg border border-gray-100 px-1.5 py-1 shadow-md">
      <div className="shrink-0">
        <Image
          unoptimized
          src={`https://www.google.com/s2/favicons?domain=${source.link}&sz=128`}
          alt={source.link}
          className="rounded-full p-1"
          width={36}
          height={36}
        />
      </div>
      <div className="flex min-w-0 max-w-[192px] flex-col justify-center gap-1">
        <h6 className="line-clamp-2 text-xs font-light">{source.title}</h6>
        <a
          target="_blank"
          rel="noopener noreferrer"
          href={source.link}
          className="truncate text-xs font-light text-[#1B1B16]/30"
        >
          {source.link}
        </a>
      </div>
    </div>
  );
};
