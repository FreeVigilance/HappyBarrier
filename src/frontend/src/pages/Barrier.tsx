import { useState } from "react";
import { useNavigate } from "react-router-dom";

const Barrier: React.FC = () => {
  const [requestSent, setRequestSent] = useState(false);
  const navigate = useNavigate();

  return (
    <div style={styles.container}>
      <div style={styles.contentWrapper}>
        <h2 style={styles.title}>User Публичный шлагбаум</h2>
        <div style={styles.barrierInfo}>
          <h3 style={styles.barrierName}>Ул Ленина 5</h3>
          <p>
            <strong>Администратор:</strong> Владимир Иванов
          </p>
          <p>
            <strong>Телефон шлагбаума:</strong> +7 999 999 00 99
          </p>
          <p>
            <strong>Телефон администратора:</strong> необязательно
          </p>
          <h4>Лимиты шлагбаума:</h4>
          <p>Номеров - 4</p>
          <p>Временных номеров - 1</p>
          <p>Изменений в неделю - 10</p>
          <button
            style={styles.requestButton}
            onClick={() => setRequestSent(true)}
          >
            {requestSent ? "Запрос отправлен" : "Отправить запрос"}
          </button>
        </div>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "100vw",
    height: "100vh",
    backgroundColor: "#fef7fb",
    textAlign: "center",
  },
  contentWrapper: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    maxWidth: "600px",
  },
  title: {
    fontSize: "28px",
    marginBottom: "30px",
    color: "#ffffff",
    textAlign: "center",
  },
  barrierInfo: {
    backgroundColor: "#ffffff",
    padding: "25px",
    borderRadius: "15px",
    boxShadow: "0px 6px 10px rgba(0, 0, 0, 0.15)",
    textAlign: "center",
    width: "100%",
  },
  barrierName: {
    fontSize: "22px",
    marginBottom: "15px",
    color: "#333",
    textAlign: "center",
  },
  requestButton: {
    backgroundColor: "#5a4478",
    color: "#ffffff",
    padding: "12px 20px",
    borderRadius: "25px",
    cursor: "pointer",
    fontSize: "18px",
    border: "none",
    marginTop: "20px",
    width: "100%",
    textAlign: "center",
  },
};

export default Barrier;
