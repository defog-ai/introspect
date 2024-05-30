import { NodeViewWrapper } from "@tiptap/react";
import React, { useContext, useEffect, useMemo, useRef } from "react";
import { ReactiveVariablesContext } from "../ReactiveVariablesContext";
import { isNullOrUndefined, roundNumber } from "$utils/utils";

export default function ReactiveVariableNodeView({ node }) {
  const ref = useRef(null);
  const reactiveContext = useContext(ReactiveVariablesContext);
  const ctxVal = useMemo(() => {
    // if we can find this in reactive context, use the latest value
    // otherwise use the value stored in the node with an error message
    const nestLocation =
      node.attrs["data-reactive-var-nest-location"].split("---");

    let ctxVal = reactiveContext.val;

    for (let i = 0; i < nestLocation.length; i++) {
      if (typeof ctxVal !== "undefined") {
        ctxVal = ctxVal[nestLocation[i]];
      } else {
        ctxVal = null;
        break;
      }
    }

    if (!isNullOrUndefined(ctxVal)) {
      ctxVal = roundNumber(ctxVal);
    }
    return ctxVal;
  }, [reactiveContext]);

  return (
    <NodeViewWrapper as="span">
      <div data-drag-handle></div>
      <code
        data-reactive-var="true"
        data-reactive-name={node.attrs["data-reactive-var-name"]}
        data-reactive-var-nest-location={
          node.attrs["data-reactive-var-nest-location"]
        }
        data-table-id={node.attrs["data-table-id"]}
        data-in-ctx={!isNullOrUndefined(ctxVal) ? true : false}
      >
        {!isNullOrUndefined(ctxVal) ? ctxVal : node.attrs["data-val"]}
      </code>
    </NodeViewWrapper>
  );
}
