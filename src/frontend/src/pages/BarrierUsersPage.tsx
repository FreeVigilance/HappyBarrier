import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

interface IUser {
  id: number;
  phone: string;
  full_name: string;
  role: string;
  is_active: boolean;
  phone_privacy: string;
}

const BarrierUsersPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { barrier_id } = location.state || {};
  const [accessToken, setAccessToken] = useState<string>(
    location.state?.access_token || localStorage.getItem("access_token")!,
  );
  const refreshToken =
    location.state?.refresh_token || localStorage.getItem("refresh_token");

  // existing states
  const [barrierName, setBarrierName] = useState("Загрузка...");
  const [users, setUsers] = useState<IUser[]>([]);
  const [ordering, setOrdering] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [error, setError] = useState("");
  const [blockReason, setBlockReason] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [blockErrors, setBlockErrors] = useState<Record<number, string>>({});
  const [deleteErrors, setDeleteErrors] = useState<Record<number, string>>({});
  const [showReasonInput, setShowReasonInput] = useState<
    Record<number, boolean>
  >({});

  // new states for phone search / invite
  const [phoneQuery, setPhoneQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [foundUser, setFoundUser] = useState<IUser | null>(null);

  const [unblocking, setUnblocking] = useState(false);
  const [unblockError, setUnblockError] = useState("");

  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState("");
  const [inviteSuccess, setInviteSuccess] = useState("");

  const fetchBarrierInfo = async () => {
    try {
      const res = await fetch(`/api/admin/barriers/${barrier_id}/`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const data = await res.json();
      if (res.ok) setBarrierName(data.address);
    } catch {}
  };

  const fetchUsers = async (token = accessToken) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: "10",
    });
    if (ordering) params.append("ordering", ordering);
    if (search.trim()) params.append("search", search.trim());

    try {
      const res = await fetch(
        `/api/admin/barriers/${barrier_id}/users/?${params.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/json",
          },
        },
      );

      if (res.status === 401) return await refreshAndRetry();

      const data = await res.json();
      if (res.ok) {
        setUsers(data.users || []);
        setTotalPages(Math.ceil(data.total_count / 10));
      } else {
        setError("Ошибка загрузки пользователей");
      }
    } catch {
      setError("Ошибка сети при загрузке пользователей");
    }
  };

  const refreshAndRetry = async () => {
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
        fetchUsers(data.access);
      } else {
        navigate("/login");
      }
    } catch {
      setError("Ошибка обновления токена");
    }
  };

  const handleOrdering = () => {
    if (ordering === "") setOrdering("full_name");
    else if (ordering === "full_name") setOrdering("-full_name");
    else setOrdering("");
  };

  const handleDeleteUser = async (userId: number) => {
    if (!window.confirm("Удалить пользователя из шлагбаума?")) return;
    try {
      const res = await fetch(
        `/api/admin/barriers/${barrier_id}/users/${userId}/`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${accessToken}` },
        },
      );
      if (res.ok) {
        setUsers((prev) => prev.filter((u) => u.id !== userId));
        setDeleteErrors((prev) => ({ ...prev, [userId]: "" }));
      } else {
        const data = await res.json();
        setDeleteErrors((prev) => ({
          ...prev,
          [userId]: data.detail || "Ошибка удаления пользователя.",
        }));
      }
    } catch {
      setDeleteErrors((prev) => ({
        ...prev,
        [userId]: "Ошибка сети при удалении.",
      }));
    }
  };

  const handleBlockUser = async (userId: number) => {
    if (!blockReason.trim()) {
      setBlockErrors((prev) => ({
        ...prev,
        [userId]: "Укажите причину блокировки.",
      }));
      return;
    }
    try {
      const res = await fetch(`/api/admin/users/${userId}/block/`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason: blockReason }),
      });
      if (res.ok) {
        setBlockErrors((prev) => ({ ...prev, [userId]: "" }));
        setBlockReason("");
        setSelectedUserId(null);
        setShowReasonInput((prev) => ({ ...prev, [userId]: false }));
        fetchUsers();
      } else {
        const data = await res.json();
        setBlockErrors((prev) => ({
          ...prev,
          [userId]: data.detail || "Ошибка блокировки.",
        }));
      }
    } catch {
      setBlockErrors((prev) => ({
        ...prev,
        [userId]: "Ошибка сети при блокировке.",
      }));
    }
  };

  // search by phone
  const handleSearchByPhone = async () => {
    setSearching(true);
    setSearchError("");
    setFoundUser(null);
    try {
      const res = await fetch("/api/admin/users/search/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ phone: phoneQuery.trim() }),
      });
      const data = await res.json();
      if (res.ok) setFoundUser(data);
      else setSearchError(data.detail || "Пользователь не найден");
    } catch {
      setSearchError("Сетевая ошибка при поиске");
    } finally {
      setSearching(false);
    }
  };

  // unblock found user
  const handleUnblockFoundUser = async () => {
    if (!foundUser) return;
    setUnblocking(true);
    setUnblockError("");
    try {
      const res = await fetch(`/api/admin/users/${foundUser.id}/unblock/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
      });
      const data = await res.json();
      if (res.ok) setFoundUser(data);
      else setUnblockError(data.detail || "Ошибка разблокировки");
    } catch {
      setUnblockError("Сетевая ошибка при разблокировке");
    } finally {
      setUnblocking(false);
    }
  };

  // invite found user
  const handleInviteFoundUser = async () => {
    if (!foundUser) return;
    setInviting(true);
    setInviteError("");
    setInviteSuccess("");
    try {
      const res = await fetch("/api/admin/access_requests/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ user: foundUser.id, barrier: barrier_id }),
      });
      const data = await res.json();
      if (res.ok) {
        setInviteSuccess("Заявка отправлена успешно");
        fetchUsers();
      } else {
        setInviteError(data.detail || "Ошибка отправки заявки");
      }
    } catch {
      setInviteError("Сетевая ошибка при отправке заявки");
    } finally {
      setInviting(false);
    }
  };

  useEffect(() => {
    fetchBarrierInfo();
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [ordering, page, search]);

  return (
    <div style={styles.container}>
      <button
        style={styles.backButton}
        onClick={() =>
          navigate("/admin-barrier-page", {
            state: {
              barrier_id,
              access_token: accessToken,
              refresh_token: refreshToken,
            },
          })
        }
      >
        ← Назад к шлагбауму
      </button>

      <h2 style={styles.title}>Пользователи: {barrierName}</h2>

      {/* phone search / invite block */}
      <div style={{ marginBottom: 20, textAlign: "center" }}>
        <input
          type="text"
          placeholder="+7XXXXXXXXXX"
          value={phoneQuery}
          onChange={(e) => setPhoneQuery(e.target.value)}
          style={{
            ...styles.input,
            maxWidth: 200,
            display: "inline-block",
            marginRight: 8,
          }}
        />
        <button
          style={styles.button}
          onClick={handleSearchByPhone}
          disabled={searching || !phoneQuery.trim()}
        >
          {searching ? "Идёт поиск…" : "Найти пользователя"}
        </button>
        {searchError && <p style={styles.error}>{searchError}</p>}
        {foundUser && (
          <div
            style={{ ...styles.userCard, margin: "16px auto", maxWidth: 300 }}
          >
            <p>
              <strong>{foundUser.full_name}</strong>
            </p>
            <p>{foundUser.phone}</p>
            <p>Роль: {foundUser.role}</p>
            <p style={{ color: foundUser.is_active ? "#388e3c" : "#999999" }}>
              {foundUser.is_active ? "Активен" : "Заблокирован"}
            </p>

            {!foundUser.is_active && (
              <>
                <button
                  style={{
                    ...styles.button,
                    backgroundColor: "#f0d9ff",
                    color: "#5a4478",
                  }}
                  onClick={handleUnblockFoundUser}
                  disabled={unblocking}
                >
                  {unblocking ? "Разблокировка…" : "Разблокировать"}
                </button>
                {unblockError && <p style={styles.error}>{unblockError}</p>}
              </>
            )}

            {foundUser.is_active && (
              <>
                <button
                  style={styles.button}
                  onClick={handleInviteFoundUser}
                  disabled={inviting}
                >
                  {inviting ? "Отправка…" : "Пригласить в шлагбаум"}
                </button>
                {inviteError && <p style={styles.error}>{inviteError}</p>}
                {inviteSuccess && (
                  <p style={{ color: "#388e3c" }}>{inviteSuccess}</p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      <div style={styles.controls}>
        <button style={styles.orderButton} onClick={handleOrdering}>
          Сортировка{" "}
          {ordering === "full_name"
            ? "↑"
            : ordering === "-full_name"
              ? "↓"
              : ""}
        </button>
      </div>

      {users.length > 0 ? (
        <ul style={styles.list}>
          {users.map((user) => (
            <li key={user.id} style={styles.userCard}>
              <p>
                <strong>{user.full_name}</strong>
              </p>
              <p>{user.phone}</p>
              <p>Роль: {user.role}</p>
              <p style={{ color: user.is_active ? "#388e3c" : "#999999" }}>
                {user.is_active ? "Активен" : "Заблокирован"}
              </p>

              <button
                style={styles.button}
                onClick={() =>
                  navigate("/user-profile", {
                    state: {
                      user_id: user.id,
                      access_token: accessToken,
                      refresh_token: refreshToken,
                      barrier_id,
                    },
                  })
                }
              >
                Перейти к пользователю
              </button>

              <button
                style={{
                  ...styles.button,
                  backgroundColor: "#ffe3e3",
                  color: "#d9534f",
                }}
                onClick={() => handleDeleteUser(user.id)}
              >
                Удалить из шлагбаума
              </button>
              {deleteErrors[user.id] && (
                <p style={styles.error}>{deleteErrors[user.id]}</p>
              )}

              {!showReasonInput[user.id] ? (
                <button
                  style={{
                    ...styles.button,
                    backgroundColor: "#f0d9ff",
                    color: "#5a4478",
                  }}
                  onClick={() => {
                    setShowReasonInput((prev) => ({
                      ...prev,
                      [user.id]: true,
                    }));
                    setSelectedUserId(user.id);
                  }}
                >
                  Заблокировать пользователя
                </button>
              ) : (
                <div>
                  <input
                    placeholder="Причина блокировки"
                    value={selectedUserId === user.id ? blockReason : ""}
                    onChange={(e) => {
                      setSelectedUserId(user.id);
                      setBlockReason(e.target.value);
                    }}
                    style={styles.input}
                  />
                  <button
                    style={{
                      ...styles.button,
                      backgroundColor: "#d9534f",
                      color: "white",
                    }}
                    onClick={() => handleBlockUser(user.id)}
                  >
                    Подтвердить блокировку
                  </button>
                  {blockErrors[user.id] && (
                    <p style={styles.error}>{blockErrors[user.id]}</p>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p style={styles.error}>Нет пользователей</p>
      )}

      <div style={styles.pagination}>
        <button
          style={
            page === 1
              ? { ...styles.pageButton, ...styles.pageButtonDisabled }
              : styles.pageButton
          }
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page === 1}
        >
          ← Назад
        </button>

        <span style={styles.pageCounter}>
          {page} / {totalPages}
        </span>

        <button
          style={
            page === totalPages
              ? { ...styles.pageButton, ...styles.pageButtonDisabled }
              : styles.pageButton
          }
          onClick={() => setPage(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
        >
          Вперёд →
        </button>
      </div>

      {error && <p style={styles.error}>{error}</p>}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: "#fff6fb",
    minHeight: "100vh",
    width: "100vw",
    padding: "5vw",
    fontFamily: "sans-serif",
    color: "#000000",
  },
  title: {
    textAlign: "center",
    color: "#5a4478",
    marginBottom: "20px",
  },
  backButton: {
    background: "transparent",
    border: "none",
    color: "#5a4478",
    cursor: "pointer",
    fontSize: "16px",
    marginBottom: "10px",
  },
  controls: {
    display: "flex",
    gap: "10px",
    marginBottom: "10px",
  },
  orderButton: {
    backgroundColor: "#d7c4ed",
    color: "#5a4478",
    border: "none",
    padding: "10px",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: "bold",
  },
  list: {
    listStyle: "none",
    padding: 0,
  },
  userCard: {
    backgroundColor: "#ffffff",
    padding: "clamp(16px, 4vw, 24px)",
    borderRadius: "12px",
    boxShadow: "0 4px 10px rgba(90, 68, 120, 0.1)",
    marginBottom: "20px",
    width: "100%",
    maxWidth: "500px",
    marginLeft: "auto",
    marginRight: "auto",
    color: "#000000",
  },
  button: {
    marginTop: "8px",
    padding: "6px 10px",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    backgroundColor: "#5a4478",
    color: "#ffffff",
  },
  input: {
    width: "100%",
    marginTop: "6px",
    padding: "8px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    fontSize: "14px",
    boxSizing: "border-box",
    backgroundColor: "#ffffff",
    color: "#000000",
  },
  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "20px",
    marginTop: "20px",
    color: "#000000",
  },
  pageButton: {
    backgroundColor: "#5a4478",
    color: "#ffffff",
    border: "none",
    borderRadius: "8px",
    padding: "10px 16px",
    fontSize: "14px",
    fontWeight: "bold",
    cursor: "pointer",
    transition: "background 0.2s ease",
  },
  pageButtonDisabled: {
    backgroundColor: "#aaa",
    color: "#eeeeee",
    cursor: "not-allowed",
  },
  pageCounter: {
    fontSize: "14px",
    fontWeight: "bold",
    color: "#000000",
  },
  error: {
    color: "#d32f2f",
    fontSize: "13px",
    marginTop: "6px",
    textAlign: "center",
  },
};

export default BarrierUsersPage;
