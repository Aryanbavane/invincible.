interface EyeIllustrationProps {
  blink: boolean;
}

export default function EyeIllustration({ blink }: EyeIllustrationProps) {
  return (
    <svg
      aria-label={blink ? "Eye blink detected" : "Eye open, waiting for a gesture"}
      className={`eye-illustration ${blink ? "eye-illustration--blink" : ""}`}
      role="img"
      viewBox="0 0 320 190"
    >
      <path className="eye-outline" d="M28 95c34-45 78-67 132-67s98 22 132 67c-34 45-78 67-132 67S62 140 28 95Z" />
      <circle className="eye-iris" cx="160" cy="95" r="37" />
      <circle className="eye-pupil" cx="160" cy="95" r="15" />
      <path className="eye-glint" d="M170 82a7 7 0 0 0-7-7" />
      <path className="eye-lid" d="M28 95c34 0 78 0 132 0s98 0 132 0" />
      <path className="eye-lash" d="M61 46 49 35m210 11 12-11" />
    </svg>
  );
}