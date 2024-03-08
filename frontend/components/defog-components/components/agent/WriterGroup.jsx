// group of Writer components
// call their write function one after the other

import React, { Fragment, useState } from "react";
import Writer from "./Writer";
import { createRoot } from "react-dom/client";
import styled from "styled-components";

export default function WriterGroup({ items, onChange = () => {} }) {
  const [active, setActive] = useState(0);

  function onComplete(item) {
    try {
      if (item.type === "csvTable") {
        const id = item.emptyHtml.match(/csv-table-[0-9]+/)[0];
        // find the matching id in window.renders
        const rdr = window.renders.find((d) => d.id === id);

        const Component = rdr.component;
        const root = createRoot(document.getElementById(id));
        root.render(<Component {...rdr.props} apiKey={""} apiEndpoint={""} />);
      }
    } catch (e) {
      console.log(e);
    }
    setActive(active + 1);
  }

  return (
    <>
      {items.map((item, i) => (
        <Writer
          s={item.text}
          key={item.key || i}
          animate={item.animate}
          onComplete={() => onComplete(item)}
          start={item.animate && active === i}
        >
          <WriterCtrWrap>
            <div
              className="writer-ctr"
              dangerouslySetInnerHTML={{ __html: item.emptyHtml }}
              onBlur={(ev) => onChange(ev, item)}
            ></div>
          </WriterCtrWrap>
        </Writer>
      ))}
    </>
  );
}

const WriterCtrWrap = styled.div`
  .writer-target {
    position: relative;
    &:not(.csv-table) {
      &:before {
        content: "";
        position: absolute;
        top: 0;
        left: -20px;
        width: 10px;
        height: 100%;
        background-color: #f5f5f5;
        opacity: 0;
      }

      &:hover {
        &:before {
          opacity: 1;
        }
      }

      &:focus {
        outline: none;
        &:before {
          background-color: #6c8bfc;
          opacity: 1;
        }
      }
    }
  }
`;
