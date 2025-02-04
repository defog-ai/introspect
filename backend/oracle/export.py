import asyncio
from typing import Any, Dict, List
from db_models import OracleGuidelines
from db_config import engine

from oracle_utils import (
    add_or_update_analysis,
    update_report_name,
)
from generic_utils import make_request
from oracle.constants import DEFOG_BASE_URL, TaskStage, TaskType
from oracle.utils_report import summary_dict_to_markdown
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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

    # get the generate_report_guidelines from the database and add it to the json_data
    async with AsyncSession(engine) as session:
        async with session.begin():
            row = await session.execute(
                select(OracleGuidelines.generate_report_guidelines).where(
                    OracleGuidelines.api_key == api_key
                )
            )
            row = row.scalar_one_or_none()
            if row:
                json_data["generate_report_guidelines"] = row[0]

    # generate the full report markdown and mdx
    mdx_task = make_request(
        DEFOG_BASE_URL + "/oracle/generate_report_mdx", json_data, timeout=300
    )
    # recall that in JSON, keys are ALWAYS strings. Therefore, we MUST expect a string in the keys returned from mdx_task

    # generate a synthesized executive summary to the report
    summary_task = make_request(
        DEFOG_BASE_URL + "/oracle/generate_report_summary",
        json_data,
        timeout=300,
    )
    responses = await asyncio.gather(mdx_task, summary_task)
    md = responses[0].get("md")
    analyses_mdx = responses[0].get("analyses_mdx", "")

    LOGGER.info(f"Generated MDX for report {report_id}")
    LOGGER.debug(f"Analysis MDX: {analyses_mdx}")

    summary_response = responses[1]

    # Extract title from the summary dict
    summary_dict = summary_response.get("summary_dict", {})
    title = summary_dict.get("title", "")
    # Update report name in database if title is present
    if title:
        await update_report_name(report_id=report_id, report_name=title)

    summary_dict = summary_response.get("summary_dict", {})
    LOGGER.info(f"Generated Summary for report {report_id}")
    summary_md, summary_mdx = summary_dict_to_markdown(summary_dict, wrap_in_tags=False)

    # log the md and summary
    if summary_md is None:
        LOGGER.error("No MD returned from backend.")
    else:
        # log truncated markdown for debugging
        trunc_md = truncate_obj(summary_md, max_len_str=1000, to_str=True)
        LOGGER.debug(f"MD generated for report {report_id}\n{trunc_md}")

    if not summary_dict or not isinstance(summary_dict, dict):
        LOGGER.error("No Summary dictionary returned from backend.")
    else:
        trunc_summary = truncate_obj(summary_dict, max_len_str=1000, to_str=True)
        LOGGER.debug(
            f"Summary dictionary generated for report {report_id}\n{trunc_summary}"
        )

    # currently the summary dict's analysis_reference is a list of qn_ids (ints) and analysis_references (strings)
    # the qn_ids are from the original report generation process which link the analysis to the questions
    # but the follow on questions are also stored in the analysis_reference
    # but they are not linked to the qn_ids
    # the analyses are saved with uuids in the key analysis_id
    # so we need to replace the initial analysis_references with the analysis_ids instead of qn_ids
    # but keep the rest the same
    analyses = outputs.get(TaskStage.EXPLORE.value, {}).get("analyses", [])

    qn_ids = [analysis["qn_id"] for analysis in analyses]
    analysis_ids = [analysis["analysis_id"] for analysis in analyses]
    LOGGER.info(qn_ids)
    LOGGER.info(summary_dict["recommendations"])
    for summary_rec in summary_dict["recommendations"]:
        uuid_refs = []
        for qn_id in summary_rec["analysis_reference"]:
            if qn_id in qn_ids:
                qn_id_idx = qn_ids.index(qn_id)
                analysis_id = analysis_ids[qn_id_idx]
                uuid_refs.append(analysis_id)

        summary_rec["analysis_reference"] = uuid_refs

    _, tiptap_mdx = summary_dict_to_markdown(summary_dict, wrap_in_tags=True)

    # the same for analyses_mdx
    for idx in range(len(analyses)):
        analysis_id = analyses[idx]["analysis_id"]
        qn_id = analyses[idx]["qn_id"]
        if str(qn_id) in analyses_mdx:
            analyses_mdx[analysis_id] = analyses_mdx[str(qn_id)]
            del analyses_mdx[str(qn_id)]
        else:
            LOGGER.error(
                f"No mdx found for analysis with id {analysis_id} and qn_id {qn_id}"
            )
            LOGGER.error(f"analyses_mdx keys: {analyses_mdx.keys()}")

    LOGGER.info(f"Adding analyses to database for report {report_id}")
    for analysis in analyses:
        LOGGER.debug(
            f"Adding analysis with id {analysis['analysis_id']} to report {report_id}"
        )
        analysis_id = analysis["analysis_id"]
        # if this is a revision request, we will add the analyses to the original report's id
        # and not the report_id
        analysis_report_id = inputs.get("original_report_id", report_id)
        await add_or_update_analysis(
            api_key=api_key,
            analysis_id=analysis_id,
            report_id=analysis_report_id,
            analysis_json=analysis,
            status="DONE",
            mdx=analyses_mdx.get(analysis_id, ""),
        )

    return {
        "mdx": summary_mdx,
        # tiptap's mdx is separated from the mdx and md
        # because we will need to reuse the vanilla mdx for future revision of reports
        "tiptap_mdx": tiptap_mdx,
        # but we keep the md even though it's not important for the front end, so it can be used to generate a pdf file later.
        "md": summary_md + "\n\n" + "" if not md else md,
        "executive_summary": summary_dict,
        "analyses_mdx": analyses_mdx,
    }


class Recommendation(BaseModel):
    title: str
    insight: str
    action: str
    analysis_reference: List[int]
