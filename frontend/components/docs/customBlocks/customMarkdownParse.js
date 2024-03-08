// import { reFormatData } from "../../defog-components/components/common/utils";

function tableChart() {
  const fullMatch = /<csv.*?>([\s\S]*?)<\/csv>(?:\n|$)/;
  const contentMatch = /^(?:<csv.*?>)([\s\S]*?)(?:<\/csv>)(?:\n|$)/;
  const idMatch = /(?:id=")(.*?)(?:")/;

  return {
    contentMatch: contentMatch,
    fullMatch: fullMatch,
    parse: (fullText) => {
      const id = idMatch.exec(fullText) ? idMatch.exec(fullText)[1] : "";
      if (id === "") return false;

      // --- don't need to parse md anymore because we get it from the server ---
      // get content
      // let text = contentMatch.exec(fullText)[1].trim();

      // const colNames = text.split("\n")[0].split(",");
      // // find if there's an <sql> or <report-plot> tag
      // // if so, save it separately
      // let sql = text.match(/(?:<sql>)([\s\S]*)(?:<\/sql>)/);
      // if (sql && sql.length > 1) {
      //   // remove this from the text
      //   text = text.replace(sql[0], "");
      //   sql = sql[1];
      // } else {
      //   sql = null;
      // }

      // // find if there's an <code_str> or <report-plot> tag
      // // if so, save it separately
      // let code_str = text.match(/(?:<code_str>)([\s\S]*)(?:<\/code_str>)/);
      // if (code_str && code_str.length > 1) {
      //   // remove this from the text
      //   text = text.replace(code_str[0], "");
      //   code_str = code_str[1];
      // } else {
      //   code_str = null;
      // }

      // // find chart image
      // let chartImages = Array.from(
      //   text.matchAll(/<report-img-chart[\s\S]*?<\/report-img-chart>/gi)
      // );
      // if (chartImages.length) {
      //   chartImages.forEach((chartImage, i) => {
      //     try {
      //       // remove this from the text
      //       text = text.replace(chartImage[0], "");
      //       // get chartType
      //       chartImages[i] = {
      //         path: chartImage[0].match(/path="(.*)" /)[1],
      //         type: chartImage[0].match(/type="(.*)"/)[1],
      //       };
      //     } catch (err) {
      //       console.log(err);
      //     }
      //   });
      // }

      // const rows = text
      //   .split("\n")
      //   .slice(1)
      //   .map((d) => d.split(","));

      // const r = reFormatData(rows, colNames);
      return {
        type: "table-chart",
        id: id,
        children: [],
        content: [],
        props: {
          id: id,
          //   initialSql: sql,
          //   initialCodeStr: code_str,
          //   chartImages,
          //   response: {
          //     columns: r.newCols,
          //     data: r.newRows,
          //   },
        },
      };
    },
  };
}

const customBlocks = [tableChart()];

export async function customMarkdownToBlocks(markdown, editor) {
  // replace all level-1 headings in the markdown with level 3 headings
  markdown = markdown.replace(/^# /gm, "### ");

  // search for each custom block
  // but keep order intact
  // all non custom blocks, which can be parsed using blocknote's default editor.markdownToBlocks
  // have the type "default-parseable-block"
  const blocks = [
    {
      type: "default-parseable-block",
      text: markdown,
    },
  ];

  customBlocks.forEach((blockToSearch) => {
    // go through blocks and try to match in each text block
    let i = 0;
    while (i < blocks.length) {
      const block = blocks[i];
      if (block.type === "default-parseable-block") {
        // search for block
        const match = blockToSearch.fullMatch.exec(block.text);
        if (match && match[0]) {
          // remove text from this block's text
          // split the text of this block into 3 parts
          // before, match, after
          const before = block.text.slice(0, match.index);
          const matchText = match[0].trim();
          const after = block.text.slice(match.index + matchText.length);
          // splice and replace it with the three blocks
          blocks.splice(
            i,
            1,
            {
              type: "default-parseable-block",
              text: before,
            },
            blockToSearch.parse(matchText),
            {
              type: "default-parseable-block",
              text: after,
            }
          );
          i += 2;
          continue;
        }
      }
      i++;
    }
  });

  let i = 0;
  while (i < blocks.length) {
    const block = blocks[i];
    if (block.type === "default-parseable-block") {
      const thisBlocks = await editor.tryParseMarkdownToBlocks(block.text);
      blocks.splice(i, 1, ...thisBlocks);
      i += thisBlocks.length;
      continue;
    }
    i++;
  }

  return blocks;
}
