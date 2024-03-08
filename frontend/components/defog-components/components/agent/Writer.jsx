// writes a string like a "chat" message

import React, { useEffect, useMemo, useRef } from "react";

export default function Writer({
  s = "",
  // so you want the writer to "animate" or not.
  // if animate is false, it will just show the string
  // if animate is true, it will type in the string one character at a time
  animate = true,
  children,
  onComplete = () => {},
  // this prop allows you to control when the animation starts
  start = true,
  ctrStyle = {},
}) {
  const targetEl = useRef(null);
  const ctr = useRef(null);
  const writing = useRef(false);
  const done = useRef(false);

  function write() {
    let i = targetEl.current.innerHTML.length;
    if (i < s.length) {
      writing.current = true;
      done.current = false;
      targetEl.current.innerHTML += s.charAt(i);
      setTimeout(write, 20);
    } else {
      done.current = true;
      onComplete();
      writing.current = false;
      // show hidden
      try {
        if (!ctr.current) return;
        let c = ctr.current.getElementsByClassName("writer-children");
        //   for child inside writer-children, show opacity one by one
        if (c.length) {
          c[0].style.opacity = 1;

          let ch = c[0].children;

          for (let i = 0; i < ch.length; i++) {
            ch[i].style.transitionProperty = "opacity";
            ch[i].style.transitionDuration = "1s";
            ch[i].style.transitionDelay = i * 0.5 + "s";
            ch[i].style.opacity = 1;
          }
        }
      } catch (err) {
        console.log(err);
      }
    }
  }

  useEffect(() => {
    if (!ctr.current) return;

    let tmp;
    // weirdness in carousel where it's cloning stuff
    let clone = ctr.current.closest(".slick-cloned");
    tmp = ctr.current.getElementsByClassName("writer-target");

    // if has targets, and animate is true, hide children
    if (animate && !clone && tmp.length) {
      // hide children
      let c = ctr.current.getElementsByClassName("writer-children");

      if (c.length) {
        let ch = c[0].children;
        for (let i = 0; i < ch.length; i++) {
          ch[i].style.opacity = 0;
        }
      }
    }

    if (tmp.length) {
      // write target
      targetEl.current = tmp[0];
    }
  }, []);

  useEffect(() => {
    if (!writing.current && ctr.current && !done.current && targetEl.current) {
      if (start && animate) write();
      else if (!animate) {
        // no animation. just show everything.
        done.current = true;
        writing.current = false;
        if (targetEl.current) {
          targetEl.current.innerHTML = s;
        }
        onComplete();
      }
    }
  }, [start]);

  return (
    <div ref={ctr} style={ctrStyle}>
      {children}
    </div>
  );
}
