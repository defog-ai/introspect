// import React, { useContext } from "react";
// import styled from "styled-components";
// import { ThemeContext } from "../context/ThemeContext";

// const AgentLoader = ({ type, message, svg, lottie, children }) => {
//   const { theme } = useContext(ThemeContext);
//   return (
//     <AgentLoaderWrap type={type} theme={theme.config}>
//       {message && <div className="message">{message}</div>}
//       <div className="loader">
//         <div className="dot-mask"></div>
//         <div className="dot"></div>
//         <div className="dot"></div>
//         <div className="dot"></div>
//       </div>
//     </AgentLoaderWrap>
//   );
// };

// export default AgentLoader;

// const AgentLoaderWrap = styled.div`
//   width: 100%;
//   text-align: center;
//   font-weight: bold;
//   .message {
//     display: inline-block;
//   }
//   .loader {
//     display: inline-block;
//     position: relative;
//     .dot {
//       width: 3px;
//       height: 3px;
//       border-radius: 50%;
//       margin: 2px;
//       margin-bottom: 0;
//       display: inline-block;
//       background-color: #0d0d0d;
//     }
//     .dot-mask {
//       position: absolute;
//       top: 0;
//       left: 0;
//       width: 100%;
//       height: 100%;
//       animation: load 1.5s infinite;
//       animation-timing-function: step-start;
//       background-color: white;
//     }
//   }

//   @keyframes load {
//     0% {
//       transform: translateX(0%);
//     }
//     33.33% {
//       transform: translateX(33.33%);
//     }
//     66.67% {
//       transform: translateX(66.7%);
//     }
//     100% {
//       transform: translateX(100%);
//     }
//   }
// `;

import React, { useContext } from "react";
import { ThemeContext } from "../../context/ThemeContext";
import styled from "styled-components";

const AgentLoader = ({ type, message, svg, lottie, children }) => {
  const { theme } = useContext(ThemeContext);
  return (
    <AgentLoaderWrap type={type} theme={theme.config} className="agent-loader">
      {svg && svg}
      {lottie && lottie}
      {type === "error" && <h2>ERROR</h2>}
      {message && <h3>{message}</h3>}
      {children && <div className="searchState-child">{children}</div>}
    </AgentLoaderWrap>
  );
};

export default AgentLoader;

const AgentLoaderWrap = styled.div`
  margin-top: 2em;
  color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;

  h2 {
    margin-top: 1.2em;
  }
  h3 {
    font-size: ${(props) => (props.type === "error" ? "14px" : "14px")};
    margin-top: -20px;
  }
  svg {
    display: block;
    max-width: 70%;
    margin-inline: auto;
  }
  pre {
    white-space: pre-wrap;
    margin-top: 1.2em;
  }
`;
