import React, { useState, useContext, Fragment } from "react";
import { Button, message, Modal, Input, ConfigProvider } from "antd";

import { download_csv, isEmpty, transformToCSV } from "./common/utils";

import styled from "styled-components";
import ThumbsUp from "./svg/ThumbsUp";
import ThumbsDown from "./svg/ThumbsDown";
import { ThemeContext } from "../context/ThemeContext";
// import AgentMain from "./agent/ReportGen";
import { TableChart } from "./TableChart";
import { XCircleIcon } from "@heroicons/react/20/solid";

const errorMessages = {
  noReponse:
    "There seems to be no response from our servers. Please try again.",
};

const DefogDynamicViz = ({
  vizType = null,
  response,
  rawData,
  query,
  debugMode,
  apiKey,
  resetChat,
  sqlOnly,
  narrativeEnabled,
}) => {
  const { theme } = useContext(ThemeContext);
  const [narrative, setNarrative] = useState(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const { TextArea } = Input;

  // if no response, return error
  if (!response || isEmpty(response)) {
    return (
      <ErrorMessageWrap>
        <div className="defog-viz-error">
          <span>{errorMessages.noReponse}</span>
        </div>
      </ErrorMessageWrap>
    );
  }

  const uploadFeedback = (feedback, feedbackText = "") => {
    if (feedback === "Good") {
      fetch(`https://api.defog.ai/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          apiKey: apiKey,
          response: response,
          feedback: feedback,
        }),
      });
    } else {
      fetch(`https://api.defog.ai/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          apiKey: apiKey,
          response: response,
          feedback: feedback,
          text: feedbackText,
        }),
      });

      setModalVisible(false);
    }

    feedback === "Good"
      ? message.success(
          "We are glad that this was a good result. Thank you for the feedback!"
        )
      : message.info(
          "Thank you for the feedback, we will use your feedback to make the results better!"
        );
  };

  let results;

  if (sqlOnly === true) {
    results = null;
  } else if (vizType === "text") {
    results = <pre>{response.results}</pre>;
  } else if (vizType === "agent") {
    // results = <AgentMain agentsEndpoint={"ws://localhost:8000/ws"} />;
  } else {
    results = (
      <TableChart response={response} query={query} vizType={vizType} />
    );
  }

  let csvDownload;

  csvDownload = (
    <div className="exportNarativeBtn">
      {vizType === "agent" ? (
        <></>
      ) : (
        <Button
          onClick={() =>
            download_csv(
              transformToCSV(
                rawData,
                response.columns.map((d) => d.title)
              )
            )
          }
        >
          ⬇️ CSV
        </Button>
      )}

      {narrativeEnabled && (
        <Button
          loading={narrativeLoading}
          onClick={async () => {
            setNarrativeLoading(true);
            const resp = await fetch(
              `https://api.defog.ai/generate_data_insights`,
              {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  apiKey: apiKey,
                  data: {
                    data: rawData.slice(0, 100),
                    columns: response.columns,
                  },
                }),
              }
            );
            const data = await resp.json();
            setNarrative(data.response);
            setNarrativeLoading(false);
          }}
        >
          💭 Narrative
        </Button>
      )}

      <Button onClick={() => resetChat()}>Reset Chat</Button>
    </div>
  );

  return (
    <>
      <ConfigProvider
        theme={{
          token: {
            colorBgElevated: theme.config.background2,
            colorText: theme.config.primaryText,
            colorBgMask: "rgba(0, 0, 0, 0.75)",
          },
        }}
      >
        <Modal
          title="To improve the model, could you please give more details about why this is a bad query? :)"
          open={modalVisible}
          footer={null}
          onCancel={() => setModalVisible(false)}
          centered
          closeIcon={
            <XCircleIcon
              className="w-3 h-3"
              style={{ color: theme.config.brandColor }}
            />
          }
        >
          <FeedbackModalWrap theme={theme.config}>
            <TextArea
              rows={4}
              className="feedback-text"
              placeholder="Optional"
            />
            <Button
              onClick={() => {
                uploadFeedback(
                  "Bad",
                  Array.from(document.querySelectorAll(".feedback-text")).pop()
                    .value
                );
              }}
            >
              Submit
            </Button>
          </FeedbackModalWrap>
        </Modal>
      </ConfigProvider>
      <div>
        <ResultsWrap theme={theme.config}>
          {results && results}
          {sqlOnly === false ? csvDownload : null}
        </ResultsWrap>
        {debugMode && (
          <>
            <RateQualityContainer theme={theme.config}>
              {response.generatedSql && (
                <>
                  <p>The following query was generated:</p>
                  <pre>{response.generatedSql}</pre>
                </>
              )}

              {narrativeEnabled && (
                <div className="generatedNarrative">
                  <p>Narrative</p>
                  {narrative}
                </div>
              )}
            </RateQualityContainer>

            <FeedbackWrap theme={theme.config}>
              <p>How did we do with is this query?</p>
              <button onClick={() => uploadFeedback("Good")}>
                <ThumbsUp />
              </button>
              <button onClick={() => setModalVisible(true)}>
                <ThumbsDown />
              </button>
            </FeedbackWrap>
          </>
        )}
      </div>
    </>
  );
};

export default React.memo(DefogDynamicViz, () => true);

const ResultsWrap = styled.div`
  position: relative;
  width: 100%;

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

  .chart-container-select h4 {
    color: ${(props) => (props.theme ? props.theme.primaryText : "#F8FAFB")};
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

  .exportNarativeBtn {
    position: absolute;
    top: 0;
    right: 0;
    display: flex;
    gap: 2px;

    position: relative;
    margin-top: 12px;
    gap: 12px;

    button {
      background: ${(props) =>
        props.theme ? props.theme.background2 : "#F8FAFB"};
      color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
      border-radius: 7px 7px 0px 0px;
      min-height: 46px;
      border: none;
      box-shadow: none;

      @container (max-width: 650px) {
        border-radius: 7px;
        width: 100%;
      }
    }
  }
`;

const RateQualityContainer = styled.div`
  color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  & > p:nth-of-type(1) {
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 0px;
  }

  & > pre {
    margin-top: 6px;
    margin-bottom: 20px;
    overflow-x: auto;
    padding-bottom: 4px;
    white-space: pre-line;
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
    &::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }

    &::-webkit-scrollbar-track {
      box-shadow: inset 0 0 4px rgba(0, 0, 0, 0.15);
      border-radius: 2px;
    }

    &::-webkit-scrollbar-thumb {
      background-color: #1677ffc4;
      border-radius: 2px;
    }
  }

  & > .generatedNarrative {
    margin-bottom: 20px;
    p {
      font-weight: 600;
      margin-top: 20px;
      margin-bottom: 0px;
    }
  }
`;

const FeedbackWrap = styled.div`
  background: ${(props) => (props.theme ? props.theme.background2 : "#F8FAFB")};
  color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  border-radius: 7px;
  display: inline-flex;
  padding: 12px;
  font-size: 14px;
  gap: 12px;
  margin-top: 20px;
  line-height: 1;

  @container (max-width: 650px) {
    padding: 12px;
    gap: 8px;
  }

  & > p {
    margin: 0;
    margin-right: 20px;
    @container (max-width: 650px) {
      font-size: 13px;
      margin-right: 12px;
    }
  }
  & > button {
    border: none;
    background: none;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    cursor: pointer;
    svg {
      width: 12px;
      height: 12px;
      @container (max-width: 650px) {
        width: 12px;
        height: 12px;
      }
    }

    &:nth-of-type(2) {
      transform: translateY(4px);
    }

    &:hover {
      svg {
        path {
          fill: #444;
        }
      }
    }
  }
`;

const FeedbackModalWrap = styled.div`
  padding-top: 12px;

  .ant-input {
    background: ${(props) =>
      props.theme ? props.theme.background1 : "#F8FAFB"};
    color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
    box-shadow: none;
    border-color: ${(props) =>
      props.theme ? props.theme.questionBorder : "#F8FAFB"};

    &:hover {
      border-color: ${(props) =>
        props.theme ? props.theme.brandColor : "#F8FAFB"};
    }
    &::placeholder {
      color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
      opacity: 0.7;
    }
  }

  button {
    margin-top: 12px;
    color: #fff;
    box-shadow: none;
    border: none;
    background: ${(props) =>
      props.theme ? props.theme.brandColor : "#2B59FF"};
    width: 100%;

    &:hover {
      color: #fff !important;
      opacity: 0.8;
    }
  }
`;

const ErrorMessageWrap = styled.div`
    .defog-viz-error {
      width: 100%;
      height: 200px;
      display: flex;
      justify-content: center;
      align-items: center;
      span {
        color: ${(props) =>
          props.theme ? props.theme.secondaryText : "#606060"};
      }
    }
  }
`;
