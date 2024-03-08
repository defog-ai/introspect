import React from "react";
import styled from "styled-components";

const ThemeSwitchButton = ({ mode, handleMode }) => {
  return (
    <Wrap>
      <button
        className="darkMode-btn"
        onClick={(e) => {
          e.stopPropagation();
          handleMode();
        }}
        title={`Change Color Mode`}
      >
        {mode === "dark" ? (
          <svg
            width="18"
            height="18"
            viewBox="0 0 18 19"
            style={{ transform: "rotate(-90deg)" }}
          >
            <mask id="moon-mask-eoww">
              <rect x="0" y="0" width="18" height="19" fill="#FFF"></rect>
              <circle cx="25" cy="0" r="8" fill="black"></circle>
            </mask>
            <circle
              cx="9"
              cy="9"
              fill="#fff"
              mask="url(#moon-mask-eoww)"
              r="5"
            ></circle>
            <g>
              <circle
                cx="17"
                cy="9"
                r="1.5"
                fill="#fff"
                style={{
                  transform: "scale(1)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="13"
                cy="15.928203230275509"
                r="1.5"
                fill="#fff"
                style={{
                  transform: "scale(1)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="5.000000000000002"
                cy="15.92820323027551"
                r="1.5"
                fill="#fff"
                style={{
                  transform: "scale(1)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="1"
                cy="9.000000000000002"
                r="1.5"
                fill="#fff"
                style={{
                  transform: "scale(1)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="4.9999999999999964"
                cy="2.071796769724492"
                r="1.5"
                fill="#fff"
                style={{
                  transform: "scale(1)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="13"
                cy="2.0717967697244912"
                r="1.5"
                fill="#fff"
                style={{
                  transform: "scale(1)",
                  transformOrigin: "center center",
                }}
              ></circle>
            </g>
          </svg>
        ) : (
          <svg
            width="18"
            height="18"
            viewBox="0 0 18 18"
            style={{ transform: "rotate(395deg)" }}
          >
            <mask id="moon-mask-eoww">
              <rect x="0" y="0" width="18" height="18" fill="#FFF"></rect>
              <circle cx="10" cy="2" r="8" fill="black"></circle>
            </mask>
            <circle
              cx="9"
              cy="9"
              fill="#fcfc00"
              mask="url(#moon-mask-eoww)"
              r="8"
            ></circle>
            <g>
              <circle
                cx="17"
                cy="9"
                r="1.5"
                fill="#fcfc00"
                style={{
                  transform: "scale(0)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="13"
                cy="15.928203230275509"
                r="1.5"
                fill="#fcfc00"
                style={{
                  transform: "scale(0)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="5.000000000000002"
                cy="15.92820323027551"
                r="1.5"
                fill="#fcfc00"
                style={{
                  transform: "scale(0)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="1"
                cy="9.000000000000002"
                r="1.5"
                fill="#fcfc00"
                style={{
                  transform: "scale(0)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="4.9999999999999964"
                cy="2.071796769724492"
                r="1.5"
                fill="#fcfc00"
                style={{
                  transform: "scale(0)",
                  transformOrigin: "center center",
                }}
              ></circle>
              <circle
                cx="13"
                cy="2.0717967697244912"
                r="1.5"
                fill="#fcfc00"
                style={{
                  transform: "scale(0)",
                  transformOrigin: "center center",
                }}
              ></circle>
            </g>
          </svg>
        )}
      </button>
    </Wrap>
  );
};

export default ThemeSwitchButton;

const Wrap = styled.div`
  .darkMode-btn {
    cursor: pointer;
    display: block;
    background-color: #2b59ff;
    border: none;
    outline: none;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    //background-blend-mode: multiply;

    svg {
      transition: all 300ms ease;
    }
  }

  .DarkModeToggle__MoonOrSun {
    width: 70%;
    height: 70%;
  }
`;
