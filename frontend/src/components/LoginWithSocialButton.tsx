import { getCSRFToken } from "../utils/cookies";

interface LoginWithSocialButtonProps {
  name: string;
  id: string;
}

export default function LoginWithSocialButton({
  name,
  id,
}: LoginWithSocialButtonProps) {
  function handleClick() {
    const form = document.createElement("form");
    form.style.display = "none";
    form.method = "POST";
    form.action = `${import.meta.env.VITE_API_URL}/_allauth/browser/v1/auth/provider/redirect`;
    const data = {
      provider: id,
      callback_url: import.meta.env.VITE_FRONTEND_URL || "http://localhost:8000",
      csrfmiddlewaretoken: getCSRFToken() || "",
      process: "login",
    };
    console.log("data", data);

    Object.entries(data).forEach(([k, v]) => {
      const input = document.createElement("input");
      input.name = k;
      input.value = v;
      form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
  }
  return (
    <button onClick={handleClick} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
      Login with {name}
    </button>
  );
}