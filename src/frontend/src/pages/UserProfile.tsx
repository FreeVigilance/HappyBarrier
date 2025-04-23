import { useState } from "react";
import { useNavigate } from "react-router-dom";

const UserProfile: React.FC = () => {
  const navigate = useNavigate();
  const [name, setName] = useState("Иванов Иван");
  const [phone, setPhone] = useState("+79888363930");
  const [isEditingName, setIsEditingName] = useState(false);
  const [isEditingPhone, setIsEditingPhone] = useState(false);
  const [requestSent, setRequestSent] = useState(false);

  const handleSave = () => {
    setRequestSent(true);
    setTimeout(() => setRequestSent(false), 3000);
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>User Профиль</h2>
      <div style={styles.card}>
        {isEditingName ? (
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={styles.input}
          />
        ) : (
          <p style={styles.text}>{name}</p>
        )}
        <button
          style={styles.button}
          onClick={() => {
            isEditingName ? handleSave() : setIsEditingName(true);
          }}
        >
          {isEditingName ? "Запрос отправлен" : "Изменить имя в профиле"}
        </button>
      </div>
      <div style={styles.card}>
        {isEditingPhone ? (
          <input
            type="text"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            style={styles.input}
          />
        ) : (
          <p style={styles.text}>{phone}</p>
        )}
        <button
          style={styles.button}
          onClick={() => {
            isEditingPhone ? handleSave() : setIsEditingPhone(true);
          }}
        >
          {isEditingPhone ? "Запрос отправлен" : "Изменить номер телефона"}
        </button>
      </div>
      <div style={styles.navbar}>
        <button style={styles.navButton} onClick={() => navigate("/barriers")}>
          Шлагбаумы
        </button>
        <button style={styles.navButton} onClick={() => navigate("/requests")}>
          Запросы
        </button>
        <button
          style={styles.navButton}
          onClick={() => navigate("/profile")}
          disabled
        >
          Профиль
        </button>
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
    padding: "20px",
  },
  title: {
    fontSize: "24px",
    fontWeight: "bold",
    color: "#5a4478",
    marginBottom: "20px",
  },
  card: {
    backgroundColor: "#ffffff",
    padding: "15px",
    borderRadius: "10px",
    boxShadow: "0 4px 10px rgba(0, 0, 0, 0.1)",
    textAlign: "center",
    width: "90%",
    maxWidth: "400px",
    marginBottom: "20px",
  },
  text: {
    fontSize: "18px",
    marginBottom: "10px",
  },
  input: {
    width: "100%",
    fontSize: "16px",
    padding: "10px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    outline: "none",
    marginBottom: "10px",
  },
  button: {
    backgroundColor: "#5a4478",
    color: "#fff",
    border: "none",
    padding: "10px 15px",
    borderRadius: "20px",
    cursor: "pointer",
    fontSize: "14px",
    width: "100%",
  },
  navbar: {
    display: "flex",
    justifyContent: "space-around",
    width: "100%",
    position: "fixed",
    bottom: "0",
    backgroundColor: "#f8f3fb",
    padding: "10px 0",
  },
  navButton: {
    background: "none",
    border: "none",
    fontSize: "14px",
    color: "#5a4478",
    cursor: "pointer",
  },
};

export default UserProfile;
