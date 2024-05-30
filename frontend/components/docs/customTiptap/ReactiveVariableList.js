import { Tree } from "antd";
import React, { useContext, useEffect, useMemo } from "react";
import { ReactiveVariablesContext } from "../ReactiveVariablesContext";
import { roundNumber } from "$utils/utils";

export default function ReactiveVariableList({ query, editor, range }) {
  const reactiveContext = useContext(ReactiveVariablesContext);

  const items = useMemo(() => {
    let i = 0;
    const createMenuItems = (obj = {}, nestLocation, tableId) =>
      Object.keys(obj).map((k) => {
        // if obj[k] is not an object, return a menu item
        if (typeof obj[k] !== "object") {
          i++;
          return {
            title: k + ": " + obj[k],
            key: k + ": " + obj[k] + "-k" + i,
            val: obj[k],
            name: k,
            nestLocation: nestLocation + "---" + k,
            tableId: tableId,
          };
        }
        // if obj[k] is an object, return a menu item with a submenu
        if (typeof obj[k] === "object") {
          i++;
          return {
            title: k,
            key: k + "-k" + i,
            children: createMenuItems(
              obj[k],
              nestLocation + "---" + k,
              tableId
            ),
          };
        }
      });

    const tables = Object.keys(reactiveContext.val).map((tableId) => {
      console.log(reactiveContext.val, tableId);
      return {
        title: reactiveContext.val[tableId]?.title,
        key: tableId,
        children: createMenuItems(
          reactiveContext.val[tableId],
          tableId,
          tableId
        ),
      };
    });
    // merge all tables into one array
    return tables.flat();
  }, [reactiveContext.val]);

  return (
    <Tree
      rootClassName="reactive-var-list"
      treeData={items}
      defaultExpandAll={true}
      showIcon={false}
      showLine={true}
      switcherIcon={false}
      titleRender={(nodeData) => {
        return nodeData.children?.length ? (
          <span>{nodeData.title}</span>
        ) : (
          <span
            onClick={() => {
              editor.commands.deleteRange(range);

              editor.view.pasteHTML(`<reactive-var
                         data-reactive-var='true'
                         data-reactive-var-name=${nodeData.name}
                         data-val=${roundNumber(nodeData.val)}
                         data-reactive-var-nest-location=${
                           nodeData.nestLocation
                         }
                        data-table-id=${nodeData.tableId}>
                      </reactive-var>`);

              editor.commands.insertContent(" ");
              editor.chain().focus();
            }}
          >
            <span className="reactive-var-name">{nodeData.name}</span>
            <span className="reactive-var-value is-leaf">
              {roundNumber(nodeData.val)}
            </span>
          </span>
        );
      }}
      filterTreeNode={(node) => {
        return node?.children?.length ? true : node?.title?.includes(query);
      }}
    ></Tree>
  );
}
