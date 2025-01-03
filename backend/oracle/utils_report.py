from enum import Enum
from typing import List

from pydantic import BaseModel


class ORACLE_MDX_TAGS(Enum):
    GATHER_CONTEXT = "ORACLE-GATHER_CONTEXT"
    EXPLORE = "ORACLE-EXPLORE"
    ANALYSIS = "ORACLE-ANALYSIS"
    SUMMARY = "ORACLE-SUMMARY"
    RECOMMENDATION_TITLE = "ORACLE-RECOMMENDATION-TITLE"
    RECOMMENDATION = "ORACLE-RECOMMENDATION"
    PREDICT = "ORACLE-PREDICT"
    OPTIMIZE = "ORACLE-OPTIMIZE"


def wrap_in_mdx_tags(mdx: str, tag: ORACLE_MDX_TAGS, attrs: dict = {}) -> str:
    tag_str = f"<{tag.value}"
    for k, v in attrs.items():
        tag_str += f' {k}="{v}"'
    return tag_str + ">" + mdx + f"</{tag.value}>"


class Recommendation(BaseModel):
    title: str
    insight: str
    action: str
    analysis_reference: List[str]


def summary_dict_to_markdown(summary, wrap_in_tags: bool = False) -> str:
    """
    Converts the summary dictionary to both markdown and mdx formats for
    compatibility with existing report systems. Wraps recommendation titles
    in MDX tags if specified.

    Args:
        summary (dict): A dictionary containing the summary information, with
                        keys 'title', 'introduction', and 'recommendations'.
        wrap_in_tags (bool, optional): If True, wraps the MDX content in specified
                                       tags. Defaults to False.

    Returns:
        Tuple[str, str]: A tuple containing the markdown and mdx strings.
    """

    md = f"# {summary['title']}\n\n{summary['introduction']}\n\n"

    mdx = f"# {summary['title']}\n\n{summary['introduction']}\n\n"
    for idx, recommendation in enumerate(summary["recommendations"]):
        analysis_references = (
            ",".join([str(i) for i in recommendation["analysis_reference"]])
            if recommendation["analysis_reference"]
            else ""
        )
        if wrap_in_tags:
            rec_mdx_title = wrap_in_mdx_tags(
                recommendation["title"],
                ORACLE_MDX_TAGS.RECOMMENDATION_TITLE,
                {"analysis_reference": analysis_references, "idx": idx},
            )
        else:
            rec_mdx_title = f"## {recommendation['title']}"

        rec_md = f"""## {recommendation['title']} \n\n

{recommendation['insight']}

*Recommendation*
{recommendation['action']}

"""
        rec_mdx = f"""{rec_mdx_title} \n\n

{recommendation['insight']}

*Recommendation*
{recommendation['action']}

"""

        md += rec_md
        mdx += rec_mdx

    # mdx += wrap_in_mdx_tags(mdx, ORACLE_MDX_TAGS.SUMMARY)
    return md, mdx
