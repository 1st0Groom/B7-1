const suggestions = [
  [
    "개념 이해하기",
    "FastAPI의 라우터란? ↗",
    "FastAPI에서 라우터가 뭐야? 쉬운 예시로 설명해 줘.",
  ],
  [
    "차이 알아보기",
    "JOIN과 UNION 비교 ↗",
    "SQL JOIN과 UNION의 차이를 예시로 알려줘.",
  ],
  [
    "학습 계획 세우기",
    "비동기 프로그래밍 시작 ↗",
    "Python 비동기 프로그래밍을 공부할 순서를 알려줘.",
  ],
];
export function Welcome({
  onSuggest,
}: {
  onSuggest: (question: string) => void;
}) {
  return (
    <div id="welcome" className="welcome">
      <div className="welcome-mark" aria-hidden="true">
        ✳
      </div>
      <p className="eyebrow">한 가지 질문, 새로운 발견</p>
      <h1>오늘은 무엇이 궁금한가요?</h1>
      <p className="muted">어려운 개념도 한 걸음씩, 함께 풀어봐요.</p>
      <div className="suggestions">
        {suggestions.map(([title, hint, question]) => (
          <button key={title} onClick={() => onSuggest(question)}>
            {title}
            <span>{hint}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
