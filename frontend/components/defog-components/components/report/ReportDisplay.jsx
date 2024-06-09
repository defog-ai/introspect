import React, { useEffect, Fragment, useState } from "react";
import { marked } from "marked";
import { csvTable, postprocess } from "../agent/analysis-gen/marked-extensions";
import styled from "styled-components";
import WriterGroup from "../agent/WriterGroup";
import Lottie from "lottie-react";
import LoadingLottie from "../svg/loader.json";
import AgentLoader from "../common/AgentLoader";

marked.use({ extensions: [csvTable], hooks: { postprocess } });

export function ReportDisplay({
  sections,
  theme,
  loading,
  animate = false,
  handleEdit = () => {},
}) {
  // marked lexer through each section, parse each of the generated tokens, and render it using the Writer
  // sort sections according to section number
  // keep a record of rendered sections. so we don't render them again
  const [rendered, setRendered] = useState([]);
  const [writerGroups, setWriterGroups] = useState([]);

  function createWriterGroupItems(section) {
    const arr = section.tokens.map((tok, i) => {
      return {
        ...tok,
        key: section.section_number + "-" + i,
        emptyHtml: marked.parse(tok.raw),
        animate: animate,
        text: tok.type === "csvTable" ? "" : tok.text,
      };
    });
    // if /'s a list, convert it to multiple p tags with a class
    // so we can animate them one by one
    arr.forEach((item, i) => {
      if (item.type !== "list") return;
      const list = item;
      const listItems = list.items;
      const pTags = listItems.map((ul, j) => ({
        ...ul,
        text: "- " + ul?.text?.trim(),
        type: "paragraph",
        animate: animate,
        emptyHtml:
          '<p class="writer-target p-list-item" contenteditable="true"></p>',
        key: section.section_number + "-" + (i + j),
      }));

      // insert these p tags into the array
      arr.splice(i, 1, ...pTags);
      // edit the keys for all items after this one
      arr.forEach((item, k) => {
        if (k <= i) return;
        item.key = section.section_number + "-" + k;
      });
    });

    arr.section_number = section.section_number;
    return arr;
  }

  useEffect(() => {
    const nums = sections.map((d) => d.section_number);
    // create writer group for any new sections
    // lex these new sections
    const newSections = sections
      .filter((d) => !rendered.includes(d.section_number))
      .slice()
      .map((d) => ({
        ...d,
        tokens: marked.lexer(d.text).filter((d) => d.type != "space"),
      }));

    // also find the deleted sections
    const deletedSections = rendered.filter((d) => !nums.includes(d));

    const newWriterGroups = newSections.map((d) => createWriterGroupItems(d));

    // keep only non deleted ones
    const keepWriterGroups = writerGroups.filter(
      (d) => !deletedSections.includes(d.section_number)
    );

    setWriterGroups(
      [...keepWriterGroups, ...newWriterGroups].sort(
        (a, b) => a.section_number - b.section_number
      )
    );

    setRendered(
      [
        ...keepWriterGroups.map((d) => d.section_number),
        ...newSections.map((d) => d.section_number),
      ].sort()
    );
  }, [sections]);

  function onChange(ev, item) {
    if (!item || !item.type || !ev || !ev.target || item.type === "csvTable")
      return;
    try {
      const [sectionNumber, tokenIdx] = item.key
        .split("-")
        .map((d) => parseInt(d));
      const newWriterGroups = writerGroups.slice();
      // find the section
      const sectionToUpdate = newWriterGroups.find(
        (d) => d.section_number === sectionNumber
      );
      if (!sectionToUpdate) return;

      const tokenToUpdate = sectionToUpdate[tokenIdx];

      const newText = ev.target.innerText;
      // use tokenToUpdate.text, which is holding the old value of the text
      // find tokenToUpdate.text in tokenToUpdate.raw (which is holding the old markdown)
      // replace the old text with the new text in tokenToUpdate.raw
      // then replace tokenToUpdate.text with the new text
      const newRaw = tokenToUpdate.raw.replace(tokenToUpdate.text, newText);
      tokenToUpdate.raw = newRaw;
      tokenToUpdate.text = newText;

      setWriterGroups(newWriterGroups);

      // send update to the backend
      // merge all raws into one string to get the new section markdown
      const newSectionMarkdown = sectionToUpdate.reduce(
        (acc, curr) => acc + curr.raw + "\n\n",
        ""
      );
      // send this to the backend with the section index
      handleEdit("gen_report", { sectionNumber, newSectionMarkdown });
    } catch (e) {
      console.log(e);
    }
  }

  return (
    <ReportWrap theme={theme.config}>
      {writerGroups.map((wg) => (
        <WriterGroup key={wg.section_number} items={wg} onChange={onChange} />
      ))}
      {loading ? (
        <AgentLoader
          message={
            "Generating report. This might take a while. We will send you an email when done."
          }
          lottie={<Lottie animationData={LoadingLottie} loop={true} />}
        />
      ) : (
        <></>
      )}
    </ReportWrap>
  );
}

const ReportWrap = styled.div`
  white-space: pre-wrap;
  max-width: 800px;
  margin: 4em auto;
  .csv-table {
    width: 100%;
    margin: 0 0 4em;
  }

  p {
    margin: 1em 0;
  }

  p.writer-target.p-list-item {
    margin: 0.5em 0;
    padding-inline-start: 1em;
  }

  h1,
  h2,
  h3 {
    margin: 1em 0 0 0;
  }

  // ant styles
  .ant-tabs-nav {
    margin-bottom: 0;
  }
  .ant-tabs-tabpane {
    border-top: none;
  }
  .ant-tabs-nav {
    border: none !important;
  }
  .ant-tabs-content-holder {
    background: ${(props) =>
      props.theme ? props.theme.background2 : "#F8FAFB"};
    padding: 12px;
    border-radius: 0px 0px 7px 7px;
    overflow: hidden;
  }
  .ant-tabs-ink-bar.ant-tabs-ink-bar-animated {
    background: ${(props) =>
      props.theme ? props.theme.background2 : "#F8FAFB"};
    height: 100%;
    border-radius: 7px 7px 0px 0px;
  }
  .ant-tabs-tab {
    background: ${(props) =>
      props.theme ? props.theme.background2 : "#F8FAFB"};
    padding: 12px 20px;
    border-radius: 7px 7px 0px 0px;
    opacity: 0.5;
    overflow: hidden;

    &:hover {
      opacity: 0.75;
    }
  }
  .ant-tabs-tab.ant-tabs-tab-active {
    opacity: 1;
  }
  .ant-tabs .ant-tabs-tab .ant-tabs-tab-btn {
    position: relative;
    z-index: 5;
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  }
  .ant-tabs .ant-tabs-tab + .ant-tabs-tab {
    margin: 0 0 0 2px;
  }

  .ant-table-wrapper .ant-table {
    background: ${(props) =>
      props.theme ? props.theme.background2 : "#F8FAFB"};
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  }
  .ant-table-wrapper .ant-table-thead > tr > th,
  .ant-table-wrapper .ant-table-thead > tr > td {
    background: ${(props) =>
      props.theme ? props.theme.background2 : "#F8FAFB"};
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  }
  .ant-table-wrapper .ant-table-column-sorter {
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  }
  .ant-table-wrapper .ant-table-thead th.ant-table-column-has-sorters:hover {
    background: ${(props) =>
      props.theme ? props.theme.background1 : "#F8FAFB"};
  }
  .ant-table-wrapper .ant-table-column-sorter-up.active,
  .ant-table-wrapper .ant-table-column-sorter-down.active {
    color: ${(props) => (props.theme ? props.theme.brandColor : "#2B59FF")};
  }

  .ant-table-wrapper td.ant-table-column-sort {
    background: ${(props) =>
      props.theme ? props.theme.background3 : "#F8FAFB"};
  }
  .ant-table-wrapper .ant-table-tbody > tr.ant-table-row:hover > td,
  .ant-table-wrapper .ant-table-tbody > tr > td.ant-table-cell-row-hover {
    background: ${(props) =>
      props.theme ? props.theme.background1 : "#F8FAFB"};
  }

  .ant-table-wrapper
    .ant-table:not(.ant-table-bordered)
    .ant-table-tbody
    > tr.ant-table-row:hover
    > td:first-child,
  .ant-table:not(.ant-table-bordered)
    .ant-table-tbody
    > tr
    > td.ant-table-cell-row-hover:first-child,
  .ant-table-wrapper
    .ant-table:not(.ant-table-bordered)
    .ant-table-tbody
    > tr.ant-table-row.ant-table-row-selected
    > td:first-child {
    border-start-start-radius: 2px;
    border-end-start-radius: 2px;
  }

  .chart-container-select h4 {
    color: ${(props) => (props.theme ? props.theme.primaryText : "#F8FAFB")};
  }

  .ant-table-wrapper
    .ant-table:not(.ant-table-bordered)
    .ant-table-tbody
    > tr.ant-table-row:hover
    > td:last-child,
  .ant-table-wrapper
    .ant-table:not(.ant-table-bordered)
    .ant-table-tbody
    > tr
    > td.ant-table-cell-row-hover:last-child,
  .ant-table-wrapper
    .ant-table:not(.ant-table-bordered)
    .ant-table-tbody
    > tr.ant-table-row.ant-table-row-selected
    > td:last-child {
    border-start-end-radius: 2px;
    border-end-end-radius: 2px;
  }

  .ant-table-wrapper
    .ant-table-thead
    > tr
    > th:not(:last-child):not(.ant-table-selection-column):not(
      .ant-table-row-expand-icon-cell
    ):not([colspan])::before,
  .ant-table-wrapper
    .ant-table-thead
    > tr
    > td:not(:last-child):not(.ant-table-selection-column):not(
      .ant-table-row-expand-icon-cell
    ):not([colspan])::before {
    background-color: ${(props) =>
      props.theme ? props.theme.greyBorder : "#F8FAFB"};
  }

  .ant-table-wrapper .ant-table-thead > tr > th,
  .ant-table-wrapper .ant-table-thead > tr > td {
    border-bottom-color: ${(props) =>
      props.theme ? props.theme.greyBorder : "#F8FAFB"};
  }

  .ant-table-wrapper
    .ant-table:not(.ant-table-bordered)
    .ant-table-tbody
    > tr
    > td {
    border-top-color: ${(props) =>
      props.theme ? props.theme.greyBorder : "#F8FAFB"};
    border-bottom-color: ${(props) =>
      props.theme ? props.theme.greyBorder : "#F8FAFB"};
  }
  .ant-table-wrapper
    .ant-table:not(.ant-table-bordered)
    .ant-table-tbody
    > tr:last-child
    > td {
    border-top-color: ${(props) =>
      props.theme ? props.theme.greyBorder : "#F8FAFB"};
    border-bottom-color: ${(props) =>
      props.theme ? props.theme.greyBorder : "#F8FAFB"};
  }
  .ant-pagination .ant-pagination-item a {
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  }
  .ant-pagination .ant-pagination-item-active {
    background: ${(props) => (props.theme ? props.theme.background1 : "#FFF")};
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  }
  .ant-pagination
    .ant-pagination-jump-prev
    .ant-pagination-item-container
    .ant-pagination-item-ellipsis,
  .ant-pagination
    .ant-pagination-jump-next
    .ant-pagination-item-container
    .ant-pagination-item-ellipsis {
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  }

  .ant-pagination-item-link span {
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  }
  .ant-pagination .ant-pagination-item-active {
    border-color: ${(props) =>
      props.theme ? props.theme.brandColor : "#2B59FF"};
  }

  .ant-select:not(.ant-select-customize-input) .ant-select-selector {
    background-color: ${(props) =>
      props.theme ? props.theme.background1 : "#FFF"};
    border: 1px solid
      ${(props) => (props.theme ? props.theme.brandColor : "#FFF")};
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};

    & + .ant-select-arrow {
      color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
    }
  }
`;
