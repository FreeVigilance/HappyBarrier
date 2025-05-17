import { useState } from "react";
import { useNavigate } from "react-router-dom";

const LoginUserPage: React.FC = () => {
  const [phone, setPhone] = useState("+7");
  const [verificationToken, setVerificationToken] = useState<string | null>(
    null,
  );
  const [code, setCode] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null); // 👈
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (phone === "+7" || phone.length < 12) return;

    try {
      const response = await fetch("/api/users/check_admin/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          accept: "application/json",
        },
        body: JSON.stringify({ phone }),
      });

      const data = await response.json();

      if (data.is_admin) {
        navigate("/verifyadmin", {
          state: { phone },
        });
      } else {
        const codeResult = await sendLoginCode(phone);

        if (codeResult) {
          setVerificationToken(codeResult.verification_token);
          setCode(codeResult.code);
          navigate("/verifyuser", {
            state: {
              phone,
              verification_token: codeResult.verification_token,
            },
          });
        } else {
          // Показываем ошибку, но переходим
          navigate("/verifyuser", {
            state: {
              phone,
              verification_token: null,
              error: "Ошибка при отправке кода. Попробуйте позже.",
            },
          });
        }
      }
    } catch (error) {
      console.error(
        "Ошибка при проверке администратора или отправке кода:",
        error,
      );
      setErrorMessage("Ошибка сети. Попробуйте ещё раз.");
    }
  };

  const sendLoginCode = async (
    phone: string,
  ): Promise<{ verification_token: string; code: string } | null> => {
    try {
      const response = await fetch("/api/auth/codes/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          accept: "application/json",
        },
        body: JSON.stringify({
          phone: phone,
          mode: "login",
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        console.error("Ошибка при отправке кода:", data?.error || data.error);
        setErrorMessage(
          data?.error + "Retry after" + data?.retry ||
            "Ошибка при отправке кода",
        ); // 👈
        return null;
      }

      localStorage.setItem("verification_token", data.verification_token);

      return {
        verification_token: data.verification_token,
        code: data.code,
      };
    } catch (error) {
      console.error("Ошибка при запросе кода:", error);
      setErrorMessage("Сервер недоступен. Попробуйте позже.");
      return null;
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.replace(/[^\d]/g, "");

    if (!value.startsWith("7")) {
      value = "7" + value;
    }

    value = value.slice(0, 11);
    setPhone("+7" + value.slice(1));
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Вход</h2>
        <form onSubmit={handleSubmit} style={styles.form}>
          <label htmlFor="phone-input" style={styles.label}>
            Введите номер телефона
          </label>
          <input
            id="phone-input"
            type="text"
            value={phone}
            onChange={handleChange}
            maxLength={12}
            style={styles.input}
            required
            autoFocus
          />
          {errorMessage && <div style={styles.error}>{errorMessage}</div>}
          <button type="submit" style={styles.button}>
            Далее
          </button>
        </form>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "100vh",
    width: "100vw",
    backgroundColor: "#fef7fb",
    padding: "15px",
  },
  card: {
    backgroundColor: "#ffffff",
    padding: "5%",
    borderRadius: "15px",
    boxShadow: "0 4px 15px rgba(90, 68, 120, 0.2)",
    textAlign: "center",
    width: "90%",
    maxWidth: "400px",
  },
  title: {
    fontSize: "24px",
    marginBottom: "20px",
    color: "#5a4478",
    fontWeight: "bold",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    width: "100%",
  },
  label: {
    fontSize: "14px",
    marginBottom: "10px",
    color: "#5a4478",
  },
  input: {
    width: "100%",
    fontSize: "16px",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    backgroundColor: "#ffffff",
    color: "#333333",
    outline: "none",
    transition: "border 0.3s ease",
    marginBottom: "15px",
  },
  button: {
    backgroundColor: "#5a4478",
    color: "#ffffff",
    border: "none",
    padding: "12px 20px",
    borderRadius: "25px",
    cursor: "pointer",
    fontSize: "16px",
    transition: "background 0.3s ease",
    width: "100%",
  },
  error: {
    color: "#d32f2f",
    fontSize: "14px",
    marginBottom: "10px",
    backgroundColor: "#ffe6e6",
    padding: "10px",
    borderRadius: "8px",
    width: "100%",
    textAlign: "center",
  },
};

export default LoginUserPage;
