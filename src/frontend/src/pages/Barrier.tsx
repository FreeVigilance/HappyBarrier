import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FaArrowLeft } from "react-icons/fa";

const Barrier: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const barrierId = location.state?.barrier_id;
  const initialAccessToken =
    location.state?.access_token || localStorage.getItem("access_token");
  const refreshToken =
    location.state?.refresh_token || localStorage.getItem("refresh_token");

  const [accessToken, setAccessToken] = useState(initialAccessToken);
  const [userId, setUserId] = useState<number | null>(null);
  const [barrier, setBarrier] = useState<any>(null);
  const [error, setError] = useState("");
  const [requestSent, setRequestSent] = useState(false);
  const [message, setMessage] = useState("");

  // универсальное обновление токена
  const refreshAndRetry = async (retryFn: (token: string) => void) => {
    try {
      const res = await fetch("/api/auth/token/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      const data = await res.json();
      if (res.ok && data.access) {
        setAccessToken(data.access);
        localStorage.setItem("access_token", data.access);
        retryFn(data.access);
      } else {
        navigate("/login");
      }
    } catch {
      setError("Ошибка обновления токена");
    }
  };

  const fetchUserId = async (token = accessToken) => {
    try {
      const res = await fetch("/api/users/me/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) return refreshAndRetry(fetchUserId);
      const data = await res.json();
      if (res.ok) {
        setUserId(data.id);
      } else {
        setError("Не удалось получить пользователя");
      }
    } catch {
      setError("Ошибка сети при получении пользователя");
    }
  };

  const fetchBarrier = async (token = accessToken) => {
    if (!barrierId) {
      setError("Шлагбаум не найден");
      return;
    }

    try {
      const res = await fetch(`/api/barriers/${barrierId}/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      if (res.status === 401) return refreshAndRetry(fetchBarrier);

      const data = await res.json();
      if (res.ok) {
        setBarrier(data);
      } else {
        setError("Ошибка загрузки данных шлагбаума");
      }
    } catch {
      setError("Ошибка сети");
    }
  };

  const handleRequestAccess = async () => {
    if (!userId || !barrierId) return;

    try {
      const res = await fetch("/api/access_requests/", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ user: userId, barrier: barrierId }),
      });

      if (res.status === 401)
        return refreshAndRetry(() => handleRequestAccess());

      const data = await res.json();

      if (res.ok) {
        setRequestSent(true);
        setMessage("Запрос успешно отправлен");
      } else if (
        data?.error?.[0] === "This user already has access to the barrier."
      ) {
        setMessage("У вас уже есть доступ к шлагбауму.");
      } else {
        setMessage("Ошибка при отправке запроса");
      }
    } catch {
      setMessage("Ошибка сети при отправке запроса");
    }
  };

  useEffect(() => {
    fetchUserId();
    fetchBarrier();
  }, []);

  if (error) {
    return (
      <div style={styles.container}>
        <p style={styles.error}>{error}</p>
      </div>
    );
  }

  if (!barrier) {
    return (
      <div style={styles.container}>
        <p style={{ color: "#5a4478" }}>Загрузка...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <button onClick={() => navigate(-1)} style={styles.backButton}>
        <FaArrowLeft /> Назад
      </button>

      <div style={styles.wrapper}>
        <h2 style={styles.title}>Публичный шлагбаум</h2>
        <div style={styles.card}>
          <h3 style={styles.address}>{barrier.address}</h3>
          <p>
            <strong>Администратор:</strong>{" "}
            {barrier.owner?.full_name || "Неизвестно"}
          </p>
          <p>
            <strong>Телефон администратора:</strong>{" "}
            {barrier.owner?.phone || "не указано"}
          </p>
          <p>
            <strong>Телефон устройства:</strong> {barrier.device_phone}
          </p>
          <p>
            <strong>Доп. информация:</strong> {barrier.additional_info || "—"}
          </p>

          <button
            style={{
              ...styles.button,
              backgroundColor: requestSent ? "#ccc" : "#5a4478",
              cursor: requestSent ? "default" : "pointer",
            }}
            onClick={handleRequestAccess}
            disabled={requestSent}
          >
            {requestSent ? "Запрос отправлен" : "Отправить запрос"}
          </button>

          {message && <p style={styles.success}>{message}</p>}
        </div>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    position: "relative",
    width: "100vw",
    minHeight: "100vh",
    backgroundColor: "#fef7fb",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "sans-serif",
    padding: "20px",
    boxSizing: "border-box",
  },
  backButton: {
    position: "absolute",
    top: "20px",
    left: "20px",
    background: "none",
    border: "none",
    color: "#5a4478",
    fontSize: "18px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  wrapper: {
    width: "100%",
    maxWidth: "500px",
  },
  title: {
    textAlign: "center",
    fontSize: "26px",
    color: "#5a4478",
    fontWeight: "bold",
    marginBottom: "20px",
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    padding: "20px",
    boxShadow: "0 4px 10px rgba(90, 68, 120, 0.15)",
    fontSize: "14px",
    color: "#333",
  },
  address: {
    fontSize: "18px",
    fontWeight: "bold",
    marginBottom: "10px",
    color: "#5a4478",
  },
  button: {
    marginTop: "20px",
    width: "100%",
    padding: "12px",
    fontSize: "16px",
    color: "#fff",
    border: "none",
    borderRadius: "25px",
  },
  error: {
    color: "red",
    fontSize: "16px",
  },
  success: {
    marginTop: "12px",
    color: "#5a4478",
    fontWeight: "bold",
  },
};

export default Barrier;
