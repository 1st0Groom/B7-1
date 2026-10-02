import { Link } from "react-router-dom";
export function Brand() {
  return (
    <Link className="brand" to="/chat">
      배움<span>LEARNING CHAT</span>
    </Link>
  );
}
