const hexToRgb = (hex, alpha) => {
  if (hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    const colorObj = {
      r: String(parseInt(result[1], 16)),
      g: String(parseInt(result[2], 16)),
      b: String(parseInt(result[3], 16))
    };
    return "rgba(" + colorObj.r + ", " + colorObj.g + ", " + colorObj.b + ", " + String(alpha) + ")";
  } else {
    return null;
  }
}

export default hexToRgb;