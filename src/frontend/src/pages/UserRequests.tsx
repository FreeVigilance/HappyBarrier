import { useState } from "react";
import { useNavigate } from "react-router-dom";

const UserRequests: React.FC = () => {
  const navigate = useNavigate();
  const [requests, setRequests] = useState([
    { id: 1, address: "ул. Ленина 67", status: "pending" },
    { id: 2, address: "ул. Ленина 68", status: "declined" },
    { id: 3, address: "ул. Ленина 69", status: "approved" },
  ]);

  const handleCancel = (id: number) => {
    setRequests(
      requests.map((request) =>
        request.id === id ? { ...request, status: "declined" } : request,
      ),
    );
  };

  const handleClearAll = () => {
    setRequests([]);
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>User Исходящие запросы</h2>
      <div style={styles.tabs}>
        <button style={{ ...styles.tab, borderBottom: "2px solid #5a4478" }}>
          Исходящие
        </button>
        <button style={styles.tab}>Входящие</button>
      </div>
      <div style={styles.requestList}>
        {requests.map((request) => (
          <div
            key={request.id}
            style={{
              ...styles.requestCard,
              borderColor:
                request.status === "approved"
                  ? "green"
                  : request.status === "declined"
                    ? "red"
                    : "gray",
            }}
          >
            <p style={styles.requestText}>{request.address}</p>
            {request.status === "pending" && (
              <button
                style={styles.cancelButton}
                onClick={() => handleCancel(request.id)}
              >
                Отменить
              </button>
            )}
            {request.status === "declined" && (
              <p style={styles.declinedText}>Запрос отклонен</p>
            )}
            {request.status === "approved" && (
              <p style={styles.approvedText}>Запрос принят</p>
            )}
          </div>
        ))}
      </div>
      <button style={styles.clearButton} onClick={handleClearAll}>
        Очистить все
      </button>
      <div style={styles.navbar}>
        <button style={styles.navButton} onClick={() => navigate("/barriers")}>
          Шлагбаумы
        </button>
        <button style={{ ...styles.navButton, fontWeight: "bold" }} disabled>
          Запросы
        </button>
        <button style={styles.navButton} onClick={() => navigate("/profile")}>
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
  tabs: {
    display: "flex",
    width: "90%",
    maxWidth: "400px",
    justifyContent: "space-between",
    marginBottom: "20px",
  },
  tab: {
    flex: 1,
    textAlign: "center",
    padding: "10px",
    backgroundColor: "#f8f3fb",
    border: "none",
    cursor: "pointer",
  },
  requestList: {
    width: "90%",
    maxWidth: "400px",
  },
  requestCard: {
    backgroundColor: "#ffffff",
    padding: "15px",
    borderRadius: "10px",
    border: "2px solid",
    textAlign: "center",
    marginBottom: "10px",
  },
  requestText: {
    fontSize: "16px",
    marginBottom: "10px",
  },
  cancelButton: {
    backgroundColor: "#d9534f",
    color: "#fff",
    border: "none",
    padding: "8px 12px",
    borderRadius: "8px",
    cursor: "pointer",
    fontSize: "14px",
  },
  declinedText: {
    color: "red",
    fontSize: "14px",
  },
  approvedText: {
    color: "green",
    fontSize: "14px",
  },
  clearButton: {
    backgroundColor: "#5a4478",
    color: "#fff",
    border: "none",
    padding: "10px 15px",
    borderRadius: "20px",
    cursor: "pointer",
    fontSize: "14px",
    width: "90%",
    maxWidth: "200px",
    marginTop: "20px",
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

export default UserRequests;
