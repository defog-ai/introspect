import { parseData } from "@defogdotai/agents-ui-components/agent";
import { Table } from "@defogdotai/agents-ui-components/core-ui";
import { useEffect, useState } from "react";
import { v4 } from "uuid";
import setupBaseUrl from "./setupBaseUrl";

/**
 *
 * Parse tables from an mdx string.
 *
 * Looks for `<Table csv={CSV_STRING} />` in the mdx string.
 *
 * 1. First parse the CSV STRING.
 * 2. Convert the CSV string into an array of objects.
 * 3. Converts it into a string that is compatible with the agents-ui-components Table component.
 *
 */
export function parseTables(mdx: string) {
  const tables = {};
  const tableRegex = /<Table csv=([\s\S]+?) \/>/g;

  let newMdx = mdx;

  let match: RegExpExecArray | null;
  while ((match = tableRegex.exec(mdx)) !== null) {
    const csv = match[1];

    const id = v4();
    const { columns, data } = parseData(csv);

    tables[id] = { columns, data };

    newMdx = newMdx.replace(
      match[0],
      `<oracle-table id="${id}"></oracle-table>`
    );
  }

  return { newMdx, tables };
}

/**
 *
 * Parse images from an mdx string.
 *
 * Looks for `<Image src={SRC} alt={ALT_TEXT} />`
 */
export function parseImages(mdx: string) {
  const images = {};
  const imageRegex = /<Image src=([\s\S]+?) alt=([\s\S]+?) \/>/g;

  let newMdx = mdx;

  let match: RegExpExecArray | null;
  while ((match = imageRegex.exec(mdx)) !== null) {
    const src = match[1];
    const alt = match[2];

    const id = v4();

    newMdx = newMdx.replace(
      match[0],
      `<oracle-image id="${id}"></oracle-image>`
    );

    images[id] = { src, alt };
  }

  return { newMdx, images };
}

/**
 *
 * Thin wrapper around the <img> element.
 *
 * Downloads the image's data from the backend, and displays it.
 *
 */
export function OracleImage({ src, alt }) {
  const [base64, setBase64] = useState<string | null>(null);

  useEffect(() => {
    const getImage = async () => {
      const res = await fetch(setupBaseUrl("http", `oracle/get_image`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          src,
        }),
      });

      const data = await res.json();

      setBase64(data.base64);
    };

    getImage();
  });

  return base64 ? <img src={base64} alt={alt} /> : null;
}
