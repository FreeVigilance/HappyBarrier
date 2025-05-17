import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const UserRequests: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [type, setType] = useState<"outgoing" | "incoming">("outgoing");
  const [requests, setRequests] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [accessToken, setAccessToken] = useState(
    location.state?.access_token || localStorage.getItem("access_token"),
  );
  const [refreshToken] = useState(
    location.state?.refresh_token || localStorage.getItem("refresh_token"),
  );

  const fetchRequests = async (token = accessToken) => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/access_requests/my/?type=${type}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        const refresh = await fetch("/api/auth/token/refresh/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh: refreshToken }),
        });
        const newData = await refresh.json();
        if (refresh.ok && newData.access) {
          setAccessToken(newData.access);
          localStorage.setItem("access_token", newData.access);
          fetchRequests(newData.access);
        } else navigate("/login");
        return;
      }

      const data = await res.json();
      if (res.ok && data.access_requests) {
        const requestsWithAddresses = await Promise.all(
          data.access_requests.map(async (r: any) => {
            const barrierRes = await fetch(`/api/barriers/${r.barrier}/`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            const barrierData = await barrierRes.json();
            return { ...r, address: barrierData.address || "Неизвестно" };
          }),
        );
        setRequests(requestsWithAddresses);
      }
    } catch {
      console.error("Ошибка загрузки заявок");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, [type]);

  const updateRequestStatus = async (
    requestId: number,
    status: string,
    hide = false,
  ) => {
    try {
      await fetch(`/api/access_requests/${requestId}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          status,
          ...(hide ? { hidden_for_user: true } : {}),
        }),
      });
      fetchRequests();
    } catch {
      console.error("Ошибка при обновлении запроса");
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Запросы</h2>
      <div style={styles.tabs}>
        <button
          style={{
            ...styles.tab,
            borderBottom: type === "outgoing" ? "2px solid #5a4478" : "none",
          }}
          onClick={() => setType("outgoing")}
        >
          Исходящие
        </button>
        <button
          style={{
            ...styles.tab,
            borderBottom: type === "incoming" ? "2px solid #5a4478" : "none",
          }}
          onClick={() => setType("incoming")}
        >
          Входящие
        </button>
      </div>
      <div style={styles.requestList}>
        {isLoading ? (
          <p>Загрузка...</p>
        ) : (
          requests.map((request) => (
            <div key={request.id} style={styles.requestCard}>
              <p style={styles.requestText}>{request.address}</p>
              {type === "outgoing" && request.status === "pending" && (
                <button
                  style={styles.cancelButton}
                  onClick={() =>
                    updateRequestStatus(request.id, "cancelled", true)
                  }
                >
                  Отменить
                </button>
              )}
              {type === "incoming" && request.status === "pending" && (
                <div style={styles.actionRow}>
                  <button
                    style={styles.acceptButton}
                    onClick={() => updateRequestStatus(request.id, "accepted")}
                  >
                    Принять
                  </button>
                  <button
                    style={styles.declineButton}
                    onClick={() => updateRequestStatus(request.id, "rejected")}
                  >
                    Отклонить
                  </button>
                </div>
              )}
              {request.status === "accepted" && (
                <p style={styles.approvedText}>Принят</p>
              )}
              {request.status === "rejected" && (
                <p style={styles.declinedText}>Отклонен</p>
              )}
              {request.status === "cancelled" && (
                <p style={styles.declinedText}>Отменен</p>
              )}
            </div>
          ))
        )}
      </div>

      <div style={styles.navbar}>
        <button
          style={styles.navButton}
          onClick={() =>
            navigate("/barriers", {
              state: { access_token: accessToken, refresh_token: refreshToken },
            })
          }
        >
          Шлагбаумы
        </button>
        <button style={{ ...styles.navButton, ...styles.navButtonActive }}>
          Запросы
        </button>
        <button
          style={styles.navButton}
          onClick={() =>
            navigate("/user", {
              state: { access_token: accessToken, refresh_token: refreshToken },
            })
          }
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
    minHeight: "100vh",
    width: "100vw",
    backgroundColor: "#fef7fb",
    color: "#333",
    padding: "20px",
  },
  title: {
    fontSize: "24px",
    color: "#5a4478",
    fontWeight: "bold",
    marginBottom: "20px",
    textAlign: "center",
  },
  tabs: {
    display: "flex",
    justifyContent: "center",
    marginBottom: "20px",
    gap: "10px",
  },
  tab: {
    padding: "10px 20px",
    backgroundColor: "#f8f3fb",
    border: "none",
    cursor: "pointer",
    color: "#5a4478",
    fontWeight: "bold",
  },
  requestList: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  requestCard: {
    backgroundColor: "#fff",
    padding: "15px",
    borderRadius: "10px",
    boxShadow: "0 4px 10px rgba(0, 0, 0, 0.05)",
  },
  requestText: {
    fontSize: "16px",
    color: "#333",
    marginBottom: "10px",
  },
  cancelButton: {
    backgroundColor: "#d9534f",
    color: "#fff",
    padding: "8px 12px",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
  },
  acceptButton: {
    backgroundColor: "#5cb85c",
    color: "#fff",
    padding: "8px 12px",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    marginRight: "10px",
  },
  declineButton: {
    backgroundColor: "#f0ad4e",
    color: "#fff",
    padding: "8px 12px",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
  },
  approvedText: {
    color: "green",
    fontWeight: "bold",
  },
  declinedText: {
    color: "red",
    fontWeight: "bold",
  },
  actionRow: {
    display: "flex",
    justifyContent: "center",
    gap: "10px",
  },
  navbar: {
    display: "flex",
    justifyContent: "space-around",
    position: "fixed",
    bottom: 0,
    left: 0,
    width: "100%",
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
  navButtonActive: { borderBottom: "2px solid #5a4478", paddingBottom: "4px" },
};

export default UserRequests;
