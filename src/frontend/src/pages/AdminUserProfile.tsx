import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const AdminUserProfile: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user_id, barrier_id } = location.state || {};
  const [accessToken, setAccessToken] = useState(
    location.state?.access_token || localStorage.getItem("access_token"),
  );
  const refreshToken =
    location.state?.refresh_token || localStorage.getItem("refresh_token");

  const [user, setUser] = useState<any>(null);
  const [phones, setPhones] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [error, setError] = useState("");

  const dayNames: Record<string, string> = {
    monday: "Понедельник",
    tuesday: "Вторник",
    wednesday: "Среда",
    thursday: "Четверг",
    friday: "Пятница",
    saturday: "Суббота",
    sunday: "Воскресенье",
  };

  const renderSchedule = (schedule: any) => {
    if (!schedule) return null;
    return (
      <div style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}>
        {Object.entries(schedule).map(([day, intervals]: [string, any[]]) =>
          intervals.map((interval, i) => (
            <div key={`${day}-${i}`}>
              {dayNames[day] || day}: {interval.start_time} –{" "}
              {interval.end_time}
            </div>
          )),
        )}
      </div>
    );
  };

  const fetchWithAuth = async (url: string, token: string): Promise<any> => {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) return await refreshTokenAndRetry(url);
    const data = await res.json();
    if (!res.ok)
      throw new Error(
        data.detail || data.start_time || data.end_time || "Ошибка запроса",
      );
    return data;
  };

  const refreshTokenAndRetry = async (url: string) => {
    const res = await fetch("/api/auth/token/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    const data = await res.json();
    if (res.ok && data.access) {
      setAccessToken(data.access);
      localStorage.setItem("access_token", data.access);
      return await fetchWithAuth(url, data.access);
    } else {
      navigate("/login");
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const userData = await fetchWithAuth(
          `/api/admin/users/${user_id}/`,
          accessToken,
        );
        const phonesData = await fetchWithAuth(
          `/api/admin/barriers/${barrier_id}/phones/my/?user=${user_id}&page=${page}&page_size=10`,
          accessToken,
        );

        const rawPhones = phonesData.phones || [];

        const phonesWithSchedules = await Promise.all(
          rawPhones.map(async (phone: any) => {
            if (phone.type === "schedule") {
              try {
                const res = await fetch(
                  `/api/admin/phones/${phone.id}/schedule/`,
                  {
                    headers: {
                      Authorization: `Bearer ${accessToken}`,
                      Accept: "application/json",
                    },
                  },
                );

                if (res.ok) {
                  const schedule = await res.json();
                  return { ...phone, schedule };
                }
              } catch {}
            }
            return phone;
          }),
        );

        setUser(userData);
        setPhones(phonesWithSchedules);
        setTotalPages(Math.ceil(phonesData.total_count / 10));
      } catch (e: any) {
        setError(e.message);
      }
    };
    fetchData();
  }, [user_id, page]);

  if (error) return <p style={styles.error}>{error}</p>;
  if (!user) return <p style={styles.loading}>Загрузка...</p>;

  return (
    <div style={styles.container}>
      <button
        style={styles.backButton}
        onClick={() =>
          navigate("/barrier-users", {
            state: {
              barrier_id,
              access_token: accessToken,
              refresh_token: refreshToken,
            },
          })
        }
      >
        ← Назад к пользователям
      </button>

      <div style={styles.profileCard}>
        <h2 style={styles.title}>{user.full_name}</h2>
        <p>
          <strong>Телефон:</strong> {user.phone}
        </p>
        <p>
          <strong>Роль:</strong> {user.role}
        </p>
        <p>
          <strong>Статус:</strong> {user.is_active ? "Активен" : "Заблокирован"}
        </p>
        <p>
          <strong>Приватность телефона:</strong> {user.phone_privacy}
        </p>
      </div>

      <h3 style={styles.subtitle}>Дополнительные номера</h3>
      {phones.length === 0 ? (
        <p>Нет номеров</p>
      ) : (
        <ul style={styles.list}>
          {phones.map((phone) => (
            <li key={phone.id} style={styles.card}>
              <p>
                <strong>{phone.name}</strong> — {phone.phone}
              </p>
              <p>Тип: {phone.type}</p>
              <p>Активен: {phone.is_active ? "Да" : "Нет"}</p>

              {phone.type === "temporary" && (
                <p
                  style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}
                >
                  С {new Date(phone.start_time).toLocaleString()}
                  <br />
                  По {new Date(phone.end_time).toLocaleString()}
                </p>
              )}

              {phone.type === "schedule" && renderSchedule(phone.schedule)}

              <div
                style={{
                  display: "flex",
                  gap: "10px",
                  marginTop: "10px",
                }}
              >
                <button
                  onClick={() =>
                    navigate("/edit-phone-admin", {
                      state: {
                        user_id,
                        phone_id: phone.id,
                        phone_data: phone,
                        barrier_id,
                        access_token: accessToken,
                        refresh_token: refreshToken,
                      },
                    })
                  }
                  style={{
                    backgroundColor: "#f0d9ff",
                    color: "#5a4478",
                    border: "none",
                    borderRadius: "8px",
                    padding: "8px 12px",
                    cursor: "pointer",
                  }}
                >
                  Редактировать
                </button>
                <button
                  onClick={async () => {
                    if (window.confirm("Удалить этот номер?")) {
                      try {
                        const res = await fetch(
                          `/api/admin/phones/${phone.id}/`,
                          {
                            method: "DELETE",
                            headers: {
                              Authorization: `Bearer ${accessToken}`,
                              Accept: "application/json",
                            },
                          },
                        );
                        if (res.ok) {
                          setPhones((prev) =>
                            prev.filter((p) => p.id !== phone.id),
                          );
                        } else {
                          const data = await res.json();
                          alert(data.detail || "Ошибка удаления номера");
                        }
                      } catch {
                        alert("Ошибка сети при удалении");
                      }
                    }
                  }}
                  style={{
                    backgroundColor: "#ffe3e3",
                    color: "#d9534f",
                    border: "none",
                    borderRadius: "8px",
                    padding: "8px 12px",
                    cursor: "pointer",
                  }}
                >
                  Удалить
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div style={styles.pagination}>
        <button
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page === 1}
        >
          ← Назад
        </button>
        <span>
          {page} / {totalPages}
        </span>
        <button
          onClick={() => setPage(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
        >
          Вперёд →
        </button>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "12px",
          marginTop: "32px",
        }}
      >
        <button
          style={{
            backgroundColor: "#5a4478",
            color: "white",
            padding: "12px 20px",
            borderRadius: "25px",
            border: "none",
            cursor: "pointer",
            fontWeight: "bold",
          }}
          onClick={() =>
            navigate("/add-phone-admin", {
              state: {
                barrier_id,
                user_id,
                access_token: accessToken,
                refresh_token: refreshToken,
              },
            })
          }
        >
          Добавить номер
        </button>

        <button
          style={{
            backgroundColor: "#d7c4ed",
            color: "#5a4478",
            padding: "12px 20px",
            borderRadius: "25px",
            border: "none",
            cursor: "pointer",
            fontWeight: "bold",
          }}
          onClick={() => alert("История изменений пока не реализована")}
        >
          История изменений
        </button>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: "#fef7fb", // фиолетовый фон
    minHeight: "100vh",
    width: "100vw",
    fontFamily: "sans-serif",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    paddingBottom: "100px",
    color: "#000000", // чёрный текст
  },
  title: {
    fontSize: "24px",
    color: "#5a4478", // фиолетовый
    marginBottom: "8px",
  },
  subtitle: {
    marginTop: "24px",
    color: "#5a4478",
    fontSize: "18px",
    fontWeight: 600,
  },
  backButton: {
    background: "transparent",
    border: "none",
    color: "#5a4478",
    cursor: "pointer",
    fontSize: "16px",
    marginBottom: "10px",
    alignSelf: "flex-start",
    marginLeft: "20px",
  },
  profileCard: {
    width: "90%",
    maxWidth: "500px",
    backgroundColor: "#ffffff",
    padding: "15px",
    borderRadius: "10px",
    boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
    margin: "0 auto",
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    color: "#000000",
  },
  list: {
    listStyle: "none",
    padding: 0,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    width: "100%",
    gap: "12px",
    color: "#000000",
  },
  card: {
    width: "90%",
    maxWidth: "500px",
    backgroundColor: "#ffffff",
    padding: "15px",
    borderRadius: "10px",
    boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
    margin: "0 auto",
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    color: "#000000",
  },
  pagination: {
    display: "flex",
    justifyContent: "center",
    gap: "20px",
    marginTop: "24px",
    color: "#000000",
  },
  error: {
    textAlign: "center",
    color: "#d32f2f",
    marginTop: "16px",
  },
  loading: {
    textAlign: "center",
    color: "#000000",
    marginTop: "16px",
  },
};

export default AdminUserProfile;
