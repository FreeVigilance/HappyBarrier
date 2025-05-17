import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";

const AdminPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [phonePrivacy, setPhonePrivacy] = useState<
    "public" | "private" | "protected"
  >("public");
  const [editingPhone, setEditingPhone] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [balance, setBalance] = useState(100);
  const [isAdmin, setIsAdmin] = useState(true);

  const [accessToken] = useState(
    location.state?.access_token || localStorage.getItem("access_token"),
  );
  const [refreshToken] = useState(
    location.state?.refresh_token || localStorage.getItem("refresh_token"),
  );

  const fetchUserData = async () => {
    try {
      const res = await fetch("/api/users/me/", {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: "application/json",
        },
      });
      if (res.ok) {
        const data = await res.json();
        setName(data.full_name || "");
        setPhone(data.phone || "");
        setPhonePrivacy(data.phone_privacy || "public");
      } else {
        navigate("/login");
      }
    } catch (err) {
      console.error("Ошибка загрузки профиля:", err);
    }
  };

  const saveField = async (field: string, value: any) => {
    try {
      const res = await fetch("/api/users/me/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ [field]: value }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || `Ошибка при обновлении ${field}`);
        return false;
      }
      return data;
    } catch (err) {
      console.error("Ошибка сети:", err);
      alert("Ошибка сети");
      return false;
    }
  };

  const handleSaveName = async () => {
    const data = await saveField("full_name", name);
    if (data) setEditingName(false);
  };

  const handlePhoneSave = async () => {
    const data = await saveField("phone", phone);
    if (data) setEditingPhone(false);
  };

  const handlePrivacyChange = async (
    newPrivacy: "public" | "private" | "protected",
  ) => {
    const data = await saveField("phone_privacy", newPrivacy);
    if (data) setPhonePrivacy(data.phone_privacy);
  };

  const handleBalanceCheck = () => {
    const randomBalance = 543;
    setBalance(randomBalance);
  };

  const handleToggleRole = () => {
    setIsAdmin((prev) => {
      const newRole = !prev;
      if (!newRole) {
        navigate("/user", {
          state: {
            phone,
            access_token: accessToken,
            refresh_token: refreshToken,
          },
        });
      }
      return newRole;
    });
  };

  useEffect(() => {
    fetchUserData();
  }, []);

  const navigateWithState = (path: string) => {
    navigate(path, {
      state: {
        phone,
        access_token: accessToken,
        refresh_token: refreshToken,
      },
    });
  };

  return (
    <div style={styles.page}>
      <div style={styles.wrapper}>
        <h1 style={styles.title}>Профиль администратора</h1>

        <div style={styles.card}>
          {editingName ? (
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={styles.input}
            />
          ) : (
            <p style={styles.text}>{name || "—"}</p>
          )}
          <button
            style={styles.mainButton}
            onClick={() =>
              editingName ? handleSaveName() : setEditingName(true)
            }
          >
            {editingName ? "Сохранить" : "Изменить имя"}
          </button>
        </div>

        <div style={styles.card}>
          {editingPhone ? (
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              style={styles.input}
            />
          ) : (
            <p style={styles.text}>{phone || "—"}</p>
          )}
          <button
            style={styles.button}
            onClick={() => navigateWithState("/change-phone-admin")}
          >
            Изменить телефон
          </button>
          <label style={styles.label}>Приватность номера</label>
          <select
            value={phonePrivacy}
            onChange={(e) => handlePrivacyChange(e.target.value as any)}
            style={styles.select}
          >
            <option value="public">Виден всем</option>
            <option value="protected">
              Виден пользователям ваших шлагбаумов
            </option>
            <option value="private">Не виден никому</option>
          </select>
        </div>

        <div style={styles.card}>
          <button
            style={styles.mainButton}
            onClick={() =>
              navigate("/change-password", {
                state: {
                  phone,
                  access_token: accessToken,
                  refresh_token: refreshToken,
                },
              })
            }
          >
            🔒 Поменять пароль
          </button>
        </div>

        <div style={styles.card}>
          <p style={styles.text}>Баланс: {balance} ₽</p>
          <button style={styles.mainButton} onClick={handleBalanceCheck}>
            Проверить баланс
          </button>
        </div>

        <div style={styles.card}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span>Пользователь</span>
            <label style={styles.switch}>
              <input
                type="checkbox"
                checked={isAdmin}
                onChange={handleToggleRole}
                style={styles.switchInput}
              />
              <span
                style={{
                  ...styles.slider,
                  ...(isAdmin ? styles.switchChecked : {}),
                }}
              >
                <span
                  style={{
                    ...styles.sliderBefore,
                    ...(isAdmin ? styles.switchCheckedBefore : {}),
                  }}
                />
              </span>
            </label>
            <span>Администратор</span>
          </div>
        </div>
      </div>

      <div style={styles.navbar}>
        <button
          style={styles.navButton}
          onClick={() =>
            navigate("/admin-barriers", {
              state: { access_token: accessToken, refresh_token: refreshToken },
            })
          }
        >
          Шлагбаумы
        </button>
        <button
          style={styles.navButton}
          onClick={() =>
            navigate("/admin-requests", {
              state: { access_token: accessToken, refresh_token: refreshToken },
            })
          }
        >
          Заявки
        </button>
        <button style={{ ...styles.navButton, ...styles.activeNavButton }}>
          Профиль
        </button>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  page: {
    backgroundColor: "#fef7fb",
    minHeight: "100vh",
    width: "100vw",
    fontFamily: "sans-serif",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    paddingBottom: "100px",
  },
  wrapper: {
    marginTop: "30px",
    width: "100%",
    maxWidth: "400px",
    padding: "0 20px",
  },
  title: {
    fontSize: "26px",
    fontWeight: "bold",
    color: "#5a4478",
    marginBottom: "30px",
    textAlign: "center",
  },
  card: {
    backgroundColor: "#ffffff",
    padding: "20px",
    borderRadius: "16px",
    boxShadow: "0 4px 15px rgba(90, 68, 120, 0.2)",
    marginBottom: "20px",
    width: "100%",
  },
  input: {
    width: "100%",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    fontSize: "clamp(14px, 4vw, 16px)",
    marginBottom: "10px",
    backgroundColor: "#ffffff", // белый фон
    color: "#000000", // чёрный текст
    boxSizing: "border-box", // чтобы padding не ломал ширину
  },
  label: {
    display: "block",
    marginBottom: "6px",
    fontSize: "14px",
    color: "#5a4478",
  },
  select: {
    width: "100%",
    padding: "10px",
    borderRadius: "8px",
    fontSize: "14px",
    border: "1px solid #ccc",
    backgroundColor: "#f8f3fb",
    color: "#333",
    outline: "none",
    marginBottom: "10px",
  },
  mainButton: {
    width: "100%",
    backgroundColor: "#5a4478",
    color: "#ffffff",
    border: "none",
    padding: "12px",
    borderRadius: "25px",
    fontSize: "14px",
    cursor: "pointer",
    fontWeight: "bold",
  },
  text: {
    fontSize: "16px",
    color: "#333",
    marginBottom: "10px",
  },
  navbar: {
    position: "fixed",
    bottom: 0,
    left: 0,
    width: "100%",
    backgroundColor: "#f8f3fb",
    padding: "10px 0",
    display: "flex",
    justifyContent: "space-around",
    boxShadow: "0 -2px 10px rgba(0,0,0,0.05)",
  },
  navButton: {
    background: "none",
    border: "none",
    color: "#5a4478",
    fontSize: "14px",
    cursor: "pointer",
    fontWeight: "bold",
  },
  activeNavButton: {
    borderBottom: "2px solid #5a4478",
    paddingBottom: "4px",
  },
  switch: {
    position: "relative",
    display: "inline-block",
    width: "50px",
    height: "24px",
  },
  switchInput: {
    opacity: 0,
    width: 0,
    height: 0,
  },
  slider: {
    position: "absolute",
    cursor: "pointer",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "#ccc",
    transition: ".4s",
    borderRadius: "24px",
  },
  sliderBefore: {
    position: "absolute",
    content: "''",
    height: "18px",
    width: "18px",
    left: "3px",
    bottom: "3px",
    backgroundColor: "white",
    transition: ".4s",
    borderRadius: "50%",
  },
  switchChecked: {
    backgroundColor: "#5a4478",
  },
  switchCheckedBefore: {
    transform: "translateX(26px)",
  },
  button: {
    width: "100%",
    padding: "10px 15px",
    backgroundColor: "#5a4478",
    color: "#fff",
    border: "none",
    borderRadius: "20px",
    fontSize: "14px",
    cursor: "pointer",
  },
};

export default AdminPage;
