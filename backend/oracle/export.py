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
    LOGGER.debug(f"outputs: {outputs}")
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
    analyses_mdx = responses[0].get("analyses_mdx")

    LOGGER.info(f"Generated MDX for report {report_id}")

    summary_response = responses[1]

    summary_dict = summary_response.get("summary_dict")
    summary_md = summary_response.get("summary_md")
    summary_mdx = summary_response.get("summary_mdx")

    # log the md and summary
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
    return {
        "md": summary_md + "\n\n" + md,
        "mdx": summary_mdx + "\n\n" + mdx,
        "executive_summary": summary_dict,
        "analyses_mdx": analyses_mdx,
    }


class Recommendation(BaseModel):
    title: str
    insight: str
    action: str
    analysis_reference: List[int]
