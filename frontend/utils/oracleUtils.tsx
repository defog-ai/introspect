import { parseData } from "@defogdotai/agents-ui-components/agent";

interface TableAttributes {
  /**
   * The type of the table.
   */
  type: string;
  /**
   * The csv data of the table.
   */
  csv: string;
  /**
   * The id of the table.
   */
  id: string;
  [key: string]: string;
}

/**
 *
 * Parse tables from an mdx string.
 * For example:
 *
 * <MultiTable>
 *  <Table id={TABLE_ID} />
 *  <Table id={xxx} />
 * </MultiTable>
 *
 * Or just:
 * <Table id={TABLE_ID} text-stage={TT} />
 *
 * 1. First look for table tags. Parse all data in them.
 * 2. Replace those table tags with oracle-table tags. Keep storing the parsed data with the table id inside a dict.
 * 3. Then look for multi-table tags. For each multi-table tag, replace it with an oracle-multi-table tag.
 * 4. Store the table ids within each multi table tag inside a dict.
 * 5. Replace all content inside a multi table tag with nothing.
 *
 */
export function parseTables(mdx: string) {
  const tables = {};
  const multiTables = {};
  const multiTableRegex = /<MultiTable>([\s\S]*?)<\/MultiTable>/g;
  const tableRegex = /<Table\s+([^>]*?)\s*\/>/g;
  const attributesRegex = /([\w-]+)=[\{'\"]([\s\S]+?)[\}'\"]/g;
  let newMdx = mdx;

  // first find all tables
  let tableMatch: RegExpExecArray | null;
  while ((tableMatch = tableRegex.exec(mdx)) !== null) {
    // find all attributes
    const tableId = crypto.randomUUID();
    const attributes: TableAttributes = {
      csv: null,
      type: null,
      id: tableId,
    };
    let attributeMatch;

    while ((attributeMatch = attributesRegex.exec(tableMatch[1])) !== null) {
      attributes[attributeMatch[1]] = attributeMatch[2];
    }

    const { columns, data } = parseData(attributes.csv);
    tables[tableId] = { columns, data, ...attributes };

    // replace the table with an oracle-table tag
    newMdx = newMdx.replace(
      tableMatch[0],
      `<oracle-table id="${tableId}"></oracle-table>`
    );
  }

  // handle MultiTables
  mdx = newMdx;

  let multiMatch: RegExpExecArray | null;
  while ((multiMatch = multiTableRegex.exec(mdx)) !== null) {
    const multiTableContent = multiMatch[1];
    const multiTableId = crypto.randomUUID();
    const tableIds = [];

    // Find all tables within this MultiTable
    let localTableIdMatch: RegExpExecArray | null;
    const localTableIdRegex = /id=["'](.*?)["']/g;
    while (
      (localTableIdMatch = localTableIdRegex.exec(multiTableContent)) !== null
    ) {
      const tableId = localTableIdMatch[1];
      tableIds.push(tableId);
    }

    // Store MultiTable metadata
    multiTables[multiTableId] = { tableIds };

    // Replace the entire MultiTable with a single oracle-multi-table tag
    newMdx = newMdx.replace(
      multiMatch[0],
      `<oracle-multi-table id="${multiTableId}"></oracle-multi-table>`
    );
  }

  return { mdx: newMdx, tables, multiTables };
}

/**
 *
 * Parse images from an mdx string.
 *
 * Looks for `<Image src={SRC} alt={ALT_TEXT} />`
 */
export function parseImages(mdx: string) {
  const images = {};
  const imageRegex =
    /<Image src=[\{'\"]([\s\S]+?)[\}'\"] alt=[\{'\"]([\s\S]+?)[\}'\"] \/>/g;

  let newMdx = mdx;

  let match: RegExpExecArray | null;
  while ((match = imageRegex.exec(mdx)) !== null) {
    const src = match[1];
    const alt = match[2];

    const id = crypto.randomUUID();

    newMdx = newMdx.replace(
      match[0],
      `<oracle-image id="${id}"></oracle-image>`
    );

    images[id] = { src, alt };
  }

  return { mdx: newMdx, images };
}

export const TABLE_TYPE_TO_NAME = {
  table_csv: "Aggregated data",
  fetched_table_csv: "Fetched data",
  anomalies_csv: "Anomalies data",
};
