import ThumbsUp from "../../svg/ThumbsUp";
import ThumbsDown from "../../svg/ThumbsDown";
import { useState } from "react";
import GoodModal from "./GoodModal";
import BadModal from "./BadModal";
import { Popover, message } from "antd";
import ErrorBoundary from "../../common/ErrorBoundary";
import setupBaseUrl from "$utils/setupBaseUrl";

const feedbackUrl = setupBaseUrl("http", "submit_feedback");

export function AnalysisFeedback({
  analysisId,
  analysisSteps,
  user_question,
  token,
}) {
  const [modalVisible, setModalVisible] = useState(null);

  const submitFeedback = async (feedback) => {
    const res = await fetch(feedbackUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...feedback,
        analysis_id: analysisId,
        user_question: user_question,
        token: token,
      }),
    });

    const d = await res.json();
    console.log(d);
    if (d.success) {
      message.success(
        `Feedback ${d.did_overwrite ? "updated" : "submitted"} successfully`
      );
    } else {
      message.error("Failed to submit feedback" + (d["error_message"] || ""));
    }
    return d;
  };

  return (
    <ErrorBoundary>
      <div className="analysis-feedback flex flex-row flex-wrap content-center">
        <p className="text-sm m-0 mr-4 text-gray-400 hidden lg:block">
          Was this your desired result?
        </p>

        <Popover content="Yep!">
          <div
            className="good-feedback mr-4 h-4 w-4 cursor-pointer"
            onClick={() => {
              setModalVisible("good");
              submitFeedback({
                is_correct: true,
                comments: {},
              });
            }}
          >
            <ThumbsUp fill="fill-gray-300 hover:fill-medium-blue" />
          </div>
        </Popover>
        <Popover content="Nope">
          <div
            className="bad-feedback h-4 w-4 pt-1 cursor-pointer"
            onClick={() => setModalVisible("bad")}
          >
            <ThumbsDown fill="fill-gray-300 hover:fill-medium-blue" />
          </div>
        </Popover>

        <BadModal
          open={modalVisible === "bad"}
          setModalVisible={setModalVisible}
          analysisSteps={analysisSteps}
          analysisId={analysisId}
          submitFeedback={submitFeedback}
        />
      </div>
    </ErrorBoundary>
  );
}
