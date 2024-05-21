import React from "react";
import styled from "styled-components";

import { TbArchive, TbArchiveOff } from "react-icons/tb";
import Link from "next/link";

export default function DocIcon({
  doc,
  addDocIcon = false,
  recentlyViewed = false,
  onClick = null,
}) {
  return (
    <DocIconWrap>
      <Link
        target="_blank"
        href={{
          pathname: "/doc",
          query: { docId: addDocIcon ? "new" : doc && doc.doc_id },
        }}
      >
        <div className={"doc-icon " + (addDocIcon ? "add-doc" : "")}>
          {addDocIcon ? (
            // a full width plus sign so it aligns center vertically
            // https://stackoverflow.com/questions/49491565/uibutton-label-text-vertical-alignment-for-plus-and-minus
            <p className="add-doc-plus">＋</p>
          ) : (
            <></>
          )}
        </div>

        <p className="doc-title">
          {addDocIcon ? "New doc" : doc.doc_title ? doc.doc_title : "Untitled"}
        </p>
        <p className="doc-date">
          {recentlyViewed ? "Last accessed: " : ""}
          {addDocIcon
            ? ""
            : // short string like 28 Aug, 2023
              doc?.timestamp?.toLocaleDateString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
        </p>
        {recentlyViewed ? (
          <p className="doc-date">Created by: {doc?.created_by}</p>
        ) : (
          <></>
        )}
      </Link>
      {!addDocIcon && !recentlyViewed ? (
        <div
          className="doc-archive-icon"
          onClick={(e) => {
            if (
              !onClick ||
              // not a function
              typeof onClick !== "function" ||
              // add doc icon
              addDocIcon ||
              // recently viewed
              recentlyViewed
            )
              return;

            e.preventDefault();
            onClick(doc);
          }}
        >
          {doc.archived ? <TbArchiveOff /> : <TbArchive />}
        </div>
      ) : (
        <></>
      )}
    </DocIconWrap>
  );
}

const DocIconWrap = styled.div`
  width: 200px;
  margin: 10px;
  margin-bottom: 2em;
  position: relative;

  &:hover {
    .doc-archive-icon {
      opacity: 1;
    }
  }

  .doc-archive-icon {
    position: absolute;
    top: -10px;
    right: -10px;
    opacity: 0;
    cursor: pointer;
    font-size: 15px;
    padding: 5px;
    background-color: white;
    border: 1px solid #949494;
    border-radius: 50%;
    height: 30px;
    width: 30px;
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 4;
    svg path:not(:first-child) {
      stroke: #949494;
    }
  }

  .doc-icon {
    border-radius: 8px;
    width: 100%;
    height: 150px;
    display: flex;
    justify-content: center;
    align-items: left;
    background: #a8b1c021;
    flex-direction: column;
    padding: 20px;

    &.add-doc {
      align-items: center;
      .add-doc-plus {
        font-size: 3rem;
        font-weight: bold;
        color: #a8b1c0c3;
      }
    }
    .stage-icon-label {
      color: #a8b1c0ff;
      font-weight: bold;
      &.done {
        color: #a8b1c061;
        text-decoration: line-through;
        .anticon {
          margin-left: 4px;
        }
      }
    }
  }
  .doc-title {
    color: #a8b1c0ff;
    font-weight: bold;
    margin-top: 1em;
  }
  .doc-date {
    color: #a8b1c0ff;
    font-weight: bold;
  }
`;
