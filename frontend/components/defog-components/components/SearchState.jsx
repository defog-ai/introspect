import React, { useContext } from "react";
import styled from "styled-components";
import { ThemeContext } from "../context/ThemeContext";

const SearchState = ({ type, message, svg, lottie, children }) => {
  const { theme } = useContext(ThemeContext);
  return (
    <SearchStateWrap type={type} theme={theme.config}>
      {svg && svg}
      {lottie && lottie}
      {type === "error" && <h2>ERROR</h2>}
      {message && <h3>{message}</h3>}
      {children && <div className="searchState-child">{children}</div>}
    </SearchStateWrap>
  );
};

export default SearchState;

const SearchStateWrap = styled.div`
  margin-top: 2em;
  background: ${(props) => (props.theme ? props.theme.background2 : "#F8FAFB")};
  color: ${(props) => (props.theme ? props.theme.primaryText : "#0D0D0D")};
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 20px;
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
