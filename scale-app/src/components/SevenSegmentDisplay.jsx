import React from "react";
import "./SevenSegmentDisplay.css";

const DIGIT_SEGMENTS = [
  [1,1,1,1,1,1,0], // 0
  [0,1,1,0,0,0,0], // 1
  [1,1,0,1,1,0,1], // 2
  [1,1,1,1,0,0,1], // 3
  [0,1,1,0,0,1,1], // 4
  [1,0,1,1,0,1,1], // 5
  [1,0,1,1,1,1,1], // 6
  [1,1,1,0,0,0,0], // 7
  [1,1,1,1,1,1,1], // 8
  [1,1,1,1,0,1,1], // 9
];

const SevenSegmentDigit = ({ digit }) => {
  const segs = DIGIT_SEGMENTS[digit] || [0,0,0,0,0,0,0];
  return (
    <div className="seven-segment-digit">
      <div className={`segment a ${segs[0] ? 'on' : ''}`}></div>
      <div className={`segment b ${segs[1] ? 'on' : ''}`}></div>
      <div className={`segment c ${segs[2] ? 'on' : ''}`}></div>
      <div className={`segment d ${segs[3] ? 'on' : ''}`}></div>
      <div className={`segment e ${segs[4] ? 'on' : ''}`}></div>
      <div className={`segment f ${segs[5] ? 'on' : ''}`}></div>
      <div className={`segment g ${segs[6] ? 'on' : ''}`}></div>
    </div>
  );
};

const SevenSegmentDisplay = ({ value }) => {
  // Split value into digits, handle decimal point as needed
  const stringValue = value?.toString() ?? "";
  const chars = stringValue.split('');
  return (
    <div className="seven-segment-display">
      {chars.map((char, idx) => 
        /\d/.test(char) ? (
          <SevenSegmentDigit digit={parseInt(char)} key={idx} />
        ) : (
          <span className="seven-segment-dot" key={idx}>{char}</span>
        )
      )}
    </div>
  );
};

export default SevenSegmentDisplay;