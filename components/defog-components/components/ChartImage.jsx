import React, { Fragment, useEffect, useRef } from "react";

export default function ChartImage({ images = [] }) {
  const imgRefs = useRef(images.map(() => null));

  return (
    <div className="chart-images-ctr">
      {images.map((image, i) => (
        <img
          ref={(ref) => (imgRefs.current[i] = ref)}
          src={
            "https://storage.googleapis.com/defog-agents/report-assets/" +
            image.path
          }
          key={i}
          alt={"Loading image"}
        />
      ))}
    </div>
  );
}
