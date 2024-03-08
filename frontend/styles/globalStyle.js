// globalStyles.js
import styled, { createGlobalStyle } from "styled-components";

const GlobalStyle = createGlobalStyle`
  *,
  *::after,
  *::before {
    margin: 0;
    padding: 0;
    box-sizing: inherit;
  }
  html {
    box-sizing: border-box;
    font-size: 10px;
     @media (min-width: 1900px) {
      font-size: 12px;
    }
   /* @media (min-width: 2200px) {
      font-size: 16px;
    }*/

    @media (min-width: 2600px) {
      font-size: 14px;
      
    } 
  }
  body {
    margin: 0;
    padding: 0;
    font-size: 1.6rem;
    background-color: ${(props) =>
      props.theme ? props.theme.background1 : "#131321"};
    color: ${(props) => (props.theme ? props.theme.primaryText : "#182547")};
    font-weight: 400;
    -webkit-font-smoothing: antialiased;
    -moz-font-smoothing: antialiased;
    -o-font-smoothing: antialiased;
    opacity: 1;
  }
  

  svg,video,canvas{
    display: inline-block;
    max-width: 100%;
  }
  img{
    display: block;
    max-width: 100%;
  }
  ul{
    list-style-type: none;
  }
  a{
    text-decoration: none;

  }

  .mainPageWrap{
    min-height: 80vh;
  }

  @keyframes infiniteRotate {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
  @keyframes infiniteRotateReverse {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(720deg);
    }
  }

  
`;

export default GlobalStyle;
