import { useState } from "react";
import { useNavigate } from "react-router-dom";

const LoginUserPage: React.FC = () => {
  const [phone, setPhone] = useState("+7");
  const [verificationToken, setVerificationToken] = useState<string | null>(
    null,
  );
  const [code, setCode] = useState<string | null>(null);
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
        // Переход к verifyadmin без вызова /api/auth/codes/
        navigate("/verifyadmin", {
          state: {
            phone,
          },
        });
      } else {
        // Только для обычных пользователей отправляется код
        const codeResult = await sendLoginCode(phone);

        if (codeResult) {
          setVerificationToken(codeResult.verification_token);
          setCode(codeResult.code);
          console.log(
            "Код и токен получены:",
            codeResult.code,
            codeResult.verification_token,
          );

          navigate("/verifyuser", {
            state: {
              phone,
              verification_token: codeResult.verification_token,
            },
          });
        }
      }
    } catch (error) {
      console.error(
        "Ошибка при проверке администратора или отправке кода:",
        error,
      );
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

      if (!response.ok) {
        console.error("Ошибка при отправке кода:", response.statusText);
        return null;
      }

      const data = await response.json();
      localStorage.setItem("verification_token", data.verification_token);

      return {
        verification_token: data.verification_token,
        code: data.code,
      };
    } catch (error) {
      console.error("Ошибка при запросе кода:", error);
      return null;
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.replace(/\D/g, "");

    if (value.length === 0) {
      setPhone("");
      return;
    }

    if (!value.startsWith("7")) return;

    value = "+" + value;
    setPhone(value.trim());
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
    backgroundColor: "#fef7fb", // фиксированный светло-фиолетовый фон
    padding: "15px",
  },
  card: {
    backgroundColor: "#ffffff", // белый фон карточки
    padding: "5%",
    borderRadius: "15px",
    boxShadow: "0 4px 15px rgba(90, 68, 120, 0.2)", // фиолетовая тень
    textAlign: "center",
    width: "90%",
    maxWidth: "400px",
  },
  title: {
    fontSize: "24px",
    marginBottom: "20px",
    color: "#5a4478", // насыщенный фиолетовый
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
    color: "#5a4478", // фиолетовый для подписей
  },
  input: {
    width: "100%",
    fontSize: "16px",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    backgroundColor: "#ffffff", // белый инпут
    color: "#333333", // тёмно-серый текст
    outline: "none",
    transition: "border 0.3s ease",
    marginBottom: "15px",
  },
  button: {
    backgroundColor: "#5a4478", // фиолетовая кнопка
    color: "#ffffff",
    border: "none",
    padding: "12px 20px",
    borderRadius: "25px",
    cursor: "pointer",
    fontSize: "16px",
    transition: "background 0.3s ease",
    width: "100%",
  },
};

export default LoginUserPage;
