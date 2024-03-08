import { Node, mergeAttributes } from "@tiptap/core";
import Code from "@tiptap/extension-code";
import { ReactNodeViewRenderer } from "@tiptap/react";
import ReactiveVariableNodeView from "./ReactiveVariableNodeView";

// over write the code extension to use html attributes
// export const ReactiveVariableMark = Mark.create({
//   name: "code",
//   parseHTML: (element) => {
//     return [
//       {
//         tag: 'code[data-reactive-var="false"]',
//       },
//     ];
//   },
//   renderHTML: (attributes) => {
//     return ["code", { "data-reactive-var": "true" }, 0];
//   },
// });

export const CustomCodeMark = Code.extend({
  name: "code",
  addAttributes() {
    return {
      "data-reactive-var": {
        default: false,
      },
      "data-reactive-var-name": { default: null },
      "data-val": { default: null },
      "data-reactive-var-nest-location": { default: null },
      "data-table-id": { default: null },
      draggable: {
        default: true,
      },
    };
  },
});

export const ReactiveVariableNode = Node.create({
  name: "reactive-var",
  group: "inline",
  inline: true,
  selectable: false,
  atom: true,
  draggable: true,
  addAttributes() {
    return {
      "data-reactive-var": {
        default: false,
      },
      "data-reactive-var-name": { default: null },
      "data-val": { default: null },
      "data-reactive-var-nest-location": { default: null },
      "data-table-id": { default: null },
      contenteditable: {
        default: false,
      },
    };
  },
  parseHTML() {
    return [
      {
        tag: "reactive-var",
      },
    ];
  },
  renderHTML({ HTMLAttributes }) {
    return ["reactive-var", mergeAttributes(HTMLAttributes)];
  },
  addNodeView(d) {
    console.log(d);

    return ReactNodeViewRenderer(ReactiveVariableNodeView);
  },
});
