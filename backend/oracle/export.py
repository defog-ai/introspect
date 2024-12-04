import asyncio
from typing import Any, Dict, List

from generic_utils import make_request
from pydantic import BaseModel, ValidationError
from oracle.constants import DEFOG_BASE_URL, TaskType
from utils_logging import LOGGER, truncate_obj


async def generate_report(
    api_key: str,
    report_id: str,
    task_type: TaskType,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will generate the final report, by consolidating all the
    information gathered, explored, predicted, and optimized.
    """
    LOGGER.info(f"Exporting for report {report_id}")
    LOGGER.debug(f"inputs: {inputs}")
    LOGGER.debug(f"inputs: {outputs}")
    json_data = {
        "api_key": api_key,
        "task_type": task_type.value,
        "inputs": inputs,
        "outputs": outputs,
    }

    # generate the full report markdown and mdx
    mdx_task = make_request(
        DEFOG_BASE_URL + "/oracle/generate_report_mdx", json_data, timeout=300
    )
    # generate a synthesized executive summary to the report
    summary_task = make_request(
        DEFOG_BASE_URL + "/oracle/generate_report_summary",
        json_data,
        timeout=300,
    )
    responses = await asyncio.gather(mdx_task, summary_task)
    md = responses[0].get("md")
    mdx = responses[0].get("mdx")
    summary_dict = responses[1]
    if md is None:
        LOGGER.error("No MD returned from backend.")
    else:
        # log truncated markdown for debugging
        trunc_md = truncate_obj(md, max_len_str=1000, to_str=True)
        LOGGER.debug(f"MD generated for report {report_id}\n{trunc_md}")

    if not summary_dict or not isinstance(summary_dict, dict):
        LOGGER.error("No Summary dictionary returned from backend.")
    else:
        trunc_summary = truncate_obj(summary_dict, max_len_str=1000, to_str=True)
        LOGGER.debug(
            f"Summary dictionary generated for report {report_id}\n{trunc_summary}"
        )
        summary_md = summary_dict_to_markdown(summary_dict)
    return {
        "md": summary_md + "\n\n" + md,
        "mdx": summary_md + "\n\n" + mdx,
        "executive_summary": summary_dict,
    }


class Recommendation(BaseModel):
    title: str
    insight: str
    action: str
    analysis_reference: List[int]


class GenerateReportSummaryResponse(BaseModel):
    title: str
    introduction: str
    recommendations: List[Recommendation]


def summary_dict_to_markdown(summary_dict: Dict[str, Any]) -> str:
    """
    Converts the summary dictionary to markdown for compatibility with the
    existing report markdown display.
    """
    try:
        summary = GenerateReportSummaryResponse.model_validate(summary_dict)
    except ValidationError as e:
        LOGGER.error(f"Invalid summary dictionary generated: {e}")
        return ""

    md = f"# {summary.title}\n\n{summary.introduction}\n\n"
    for recommendation in summary.recommendations:
        md += f"""## {recommendation.title}

{recommendation.insight}

*Recommendation*
{recommendation.action}

"""
    return md
